"""MCP + HTTP entrypoint.

Exposes:
  GET  /                    JSON index for agents (browsers are redirected to https://zaptu.ai/)
  GET  /health
  GET  /v1/services         live vs collecting services, plumbing number, agent rules
  POST /v1/intake           public: JSON or form-urlencoded; add dry_run=true to validate only
  GET  /openapi.json
  GET  /.well-known/mcp.json, /.well-known/mcp/server-card.json, /server-card
  GET  /llms.txt, /llms-full.txt, /robots.txt
  POST /v1/leads, GET /v1/leads/{lead_id}   (token)
  MCP  /mcp                 streamable HTTP, stateless, no auth

CORS is open (no credentials) so browser-based agent clients can call the public API.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from typing import Annotated, Any, Literal
from urllib.parse import parse_qs

from pydantic import Field, ValidationError
from starlette.requests import Request
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

# Allow `python src/aslc/server.py` without installing the package.
ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

from aslc import catalog, config  # noqa: E402
from aslc.models import ALL_SERVICE_TYPES, ServiceRequest  # noqa: E402
from aslc.service import lookup_lead, submit_request  # noqa: E402
from aslc.storage import list_leads  # noqa: E402
from aslc.call_routing import CALL_TO_CONNECT  # noqa: E402
from aslc.validation import COLLECTED_ONLY_SERVICES, SUPPORTED_SERVICES  # noqa: E402

INSTRUCTIONS = """
Zaptu connects people with independent local home-service contractors.
Zaptu does not perform the work and does not book appointments.

PLUMBING (live): call get_plumbing_call_number. Tell the person, for example:
"Call (308) 529-9543 to be connected with a local plumbing professional."
The person must dial it themselves. Never dial, autodial, transfer, or place the call
for them. No name, phone, or consent is needed for this.

EVERYTHING ELSE (collecting: cleaning, pest control, HVAC, handyman, other):
collect ZIP, name, phone, and the person's explicit consent to be contacted, then call
request_home_service. These requests are passed along when a buyer covers the service;
there is no live buyer yet. Do not promise a callback, an arrival time, or a named company.

Use the tool result's message when you tell the person what happened.
list_supported_services returns the full catalog.
""".strip()

mcp = MCPServer(
    name="zaptu",
    title="Zaptu",
    version=catalog.VERSION,
    instructions=INSTRUCTIONS,
    website_url="https://zaptu.ai",
    log_level=config.settings.log_level,  # type: ignore[arg-type]
)


def _unauthorized() -> JSONResponse:
    return JSONResponse({"error": "unauthorized"}, status_code=401)


def _token_ok(request: Request) -> bool:
    if not config.settings.api_token:
        return True
    header = request.headers.get("authorization", "")
    if header.startswith("Bearer "):
        return header.removeprefix("Bearer ").strip() == config.settings.api_token
    return request.headers.get("x-api-token") == config.settings.api_token


WEB = ROOT / "web"

# --- Simple per-IP throttle (in-memory; TODO: Redis for multi-instance) ---
_RATE_LOCK = Lock()
_RATE_HITS: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _rate_limited(ip: str) -> bool:
    limit = config.settings.rate_limit_per_minute
    if limit <= 0:
        return False
    now = time.time()
    window = 60.0
    with _RATE_LOCK:
        hits = _RATE_HITS[ip]
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            return True
        hits.append(now)
        return False


def _cors(response: Response, _request: Request | None = None) -> Response:
    """CORS headers are added by CORSMiddleware in create_app(); kept for call-site clarity."""
    return response


def _wants_html_redirect(request: Request, body: dict[str, Any]) -> bool:
    """Form posts (urlencoded / multipart) redirect to /thanks; JSON clients get JSON."""
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        return False
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        return True
    # Explicit override
    if str(body.get("format", "")).lower() == "json":
        return False
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept and "text/html" not in accept:
        return False
    return "application/x-www-form-urlencoded" in content_type


async def _parse_intake_body(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        data: dict[str, Any] = {}
        for key in form.keys():
            data[key] = form.get(key)
        return data

    # Fallback: try JSON, then urlencoded bytes
    raw = await request.body()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    parsed = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}


def _normalize_intake_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Map Netlify form fields onto the shared ServiceRequest shape."""
    data = dict(body)
    # Drop Netlify / honeypot bookkeeping from the model payload (honeypot checked earlier).
    data.pop("form-name", None)
    data.pop("bot-field", None)

    if not data.get("source_agent"):
        data["source_agent"] = "web"

    # Empty optional strings -> omit
    for key in list(data.keys()):
        if data[key] == "":
            data[key] = None

    return data


FIELD_LABELS = {
    "service_type": "Service",
    "zip_code": "ZIP",
    "customer_name": "Name",
    "customer_phone": "Phone",
    "consent_to_contact": "Consent",
}

FIELD_MESSAGES = {
    "customer_phone": "Phone must be a 10-digit US number, like 305-555-0100.",
    "zip_code": "ZIP must be a 5-digit US ZIP code.",
    "customer_name": "Please enter a name (at least 2 characters).",
    "service_type": "Pick a service: " + ", ".join(ALL_SERVICE_TYPES) + ".",
    "state": "State must be a 2-letter code, like FL.",
    "preferred_date": "Preferred date must look like YYYY-MM-DD.",
    "bedrooms": "Bedrooms must be a whole number from 0 to 20.",
    "bathrooms": "Bathrooms must be a number from 0 to 20.",
    "square_feet": "Square feet must be a whole number from 100 to 50000.",
    "notes": "Notes must be 2000 characters or fewer.",
}

TRUTHY = {"1", "true", "yes", "on", "y"}


def _friendly_errors(exc: ValidationError) -> dict[str, str]:
    """Readable, JSON-safe messages keyed by field (pydantic ctx objects are not serializable)."""
    out: dict[str, str] = {}
    for err in exc.errors():
        field = str(err["loc"][0]) if err.get("loc") else "request"
        if err.get("type") == "missing":
            msg = f"{FIELD_LABELS.get(field, field)} is required."
        else:
            msg = FIELD_MESSAGES.get(field) or str(err.get("msg", "Invalid value.")).removeprefix("Value error, ")
        out.setdefault(field, msg)
    return out


def _error_page(messages: list[str], status_code: int = 422) -> HTMLResponse:
    """Plain HTML error for no-JS form posts, with a way back to the form."""
    items = "".join(f"<li>{_esc(m)}</li>" for m in messages)
    body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="robots" content="noindex" /><title>Request not sent | Zaptu</title>
<link rel="stylesheet" href="{catalog.SITE}/style.css" /></head>
<body><main><p class="eyebrow">Zaptu</p><h1>Request not sent</h1>
<p class="lede">Please fix this and send it again:</p><ul class="errors">{items}</ul>
<p><a class="btn-call" href="javascript:history.back()">Go back to the form</a></p>
<p class="note"><a href="{catalog.SITE}/#request">Start a new request</a> &middot; Plumbing? <a href="{catalog.SITE}/plumbing/">Call to connect</a> &middot; <a href="mailto:{catalog.CONTACT_EMAIL}">{catalog.CONTACT_EMAIL}</a></p>
</main></body></html>"""
    return HTMLResponse(body, status_code=status_code)


def _esc(text: str) -> str:
    import html

    return html.escape(str(text), quote=True)


def _json(data: Any, status_code: int = 200, cache: str | None = None) -> JSONResponse:
    resp = JSONResponse(data, status_code=status_code)
    if cache:
        resp.headers["Cache-Control"] = cache
    return resp


def _wants_html(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    return "text/html" in accept


@mcp.custom_route("/", methods=["GET"])
async def home(request: Request) -> Response:
    """Browsers go to the website; agents and curl get a small JSON index."""
    if _wants_html(request):
        return RedirectResponse(url=f"{catalog.SITE}/", status_code=301)
    return _json(
        {
            "name": "Zaptu API",
            "about": catalog.ABOUT,
            "version": catalog.VERSION,
            "mcp": catalog.MCP_URL,
            "services": f"{catalog.API}/v1/services",
            "intake": f"{catalog.API}/v1/intake",
            "openapi": f"{catalog.API}/openapi.json",
            "server_card": f"{catalog.API}/.well-known/mcp/server-card.json",
            "docs": f"{catalog.SITE}/agents/",
            "llms": f"{catalog.SITE}/llms.txt",
            "plumbing": catalog.plumbing_answer()["what_to_tell_the_user"],
            "rules": catalog.AGENT_RULES,
            "contact": catalog.CONTACT_EMAIL,
        }
    )


def _web_text(name: str, fallback: str) -> str:
    path = WEB / name
    text = path.read_text(encoding="utf-8") if path.exists() else fallback
    return text.replace("{BASE}", config.settings.public_base_url.rstrip("/"))


@mcp.custom_route("/llms.txt", methods=["GET"])
async def llms(_request: Request) -> Response:
    return PlainTextResponse(_web_text("llms.txt", "Zaptu MCP at /mcp"))


@mcp.custom_route("/llms-full.txt", methods=["GET"])
async def llms_full(_request: Request) -> Response:
    return PlainTextResponse(_web_text("llms-full.txt", "See https://zaptu.ai/agents/"))


@mcp.custom_route("/robots.txt", methods=["GET"])
async def robots(_request: Request) -> Response:
    return PlainTextResponse("User-agent: *\nAllow: /\n\nSitemap: https://zaptu.ai/sitemap.xml\n")


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(_request: Request) -> Response:
    return RedirectResponse(url=f"{catalog.SITE}/favicon.ico", status_code=301)


@mcp.custom_route("/v1/services", methods=["GET"])
async def services(_request: Request) -> Response:
    return _json(catalog.services_catalog(), cache="public, max-age=300")


@mcp.custom_route("/openapi.json", methods=["GET"])
async def openapi(_request: Request) -> Response:
    return _json(catalog.openapi_spec(), cache="public, max-age=300")


@mcp.custom_route("/.well-known/mcp.json", methods=["GET"])
async def well_known_mcp(_request: Request) -> Response:
    return _json(catalog.mcp_manifest(), cache="public, max-age=300")


async def _tool_list() -> list[dict[str, Any]]:
    tools = await mcp.list_tools()
    return [t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in tools]


async def build_server_card() -> dict[str, Any]:
    return catalog.server_card(await _tool_list(), INSTRUCTIONS)


@mcp.custom_route("/.well-known/mcp/server-card.json", methods=["GET"])
async def server_card(_request: Request) -> Response:
    return _json(await build_server_card(), cache="public, max-age=300")


@mcp.custom_route("/server-card", methods=["GET"])
async def server_card_v1(_request: Request) -> Response:
    resp = _json(catalog.server_card_v1(), cache="public, max-age=300")
    resp.headers["Content-Type"] = "application/mcp-server-card+json"
    return resp


@mcp.custom_route("/.well-known/mcp-server-card", methods=["GET"])
async def server_card_v1_well_known(request: Request) -> Response:
    return await server_card_v1(request)


@mcp.custom_route("/v1/intake", methods=["POST"])
async def public_intake(request: Request) -> Response:
    """Public front door used by the website form and API clients."""
    ip = _client_ip(request)
    content_type = (request.headers.get("content-type") or "").lower()
    is_form = "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type

    if _rate_limited(ip):
        if is_form:
            return _error_page(["Too many requests from this connection. Please wait a minute and try again."], 429)
        return _json({"error": "rate_limited", "message": "Too many requests. Wait a minute and try again."}, 429)

    try:
        body = await _parse_intake_body(request)
    except Exception:
        if is_form:
            return _error_page(["We could not read that request. Please try again."])
        return _json({"error": "invalid_request", "message": "Body must be a JSON object or a form post."}, 422)

    # Honeypot: pretend success, do not store.
    honeypot = body.get("bot-field")
    if honeypot is not None and str(honeypot).strip() != "":
        if _wants_html_redirect(request, body):
            return RedirectResponse(url=config.settings.thanks_url, status_code=303)
        return _json({"lead_id": "ignored", "status": "received", "message": "Request received.", "next_steps": []}, 202)

    dry_run = str(body.pop("dry_run", "") or request.query_params.get("dry_run", "")).strip().lower() in TRUTHY
    payload = _normalize_intake_payload(body)
    payload.pop("format", None)
    try:
        req = ServiceRequest.model_validate(payload)
    except ValidationError as exc:
        fields = _friendly_errors(exc)
        if _wants_html_redirect(request, body):
            return _error_page(list(fields.values()))
        return _json({"error": "invalid_request", "message": " ".join(fields.values()), "fields": fields}, 422)

    result = await submit_request(req, dry_run=dry_run)

    if _wants_html_redirect(request, body):
        if result.status.value == "rejected":
            return _error_page([result.message])
        if result.status.value == "call_to_connect":
            return RedirectResponse(url=f"{catalog.SITE}/plumbing/", status_code=303)
        return RedirectResponse(url=config.settings.thanks_url, status_code=303)

    if result.status.value == "rejected":
        status_code = 422
    else:
        status_code = 200 if dry_run else 202
    return _json(result.model_dump(mode="json"), status_code)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> Response:
    return JSONResponse(
        {
            "ok": True,
            "service": "zaptu",
            "version": catalog.VERSION,
            "supported_services": sorted(SUPPORTED_SERVICES),
            "collected_only": sorted(COLLECTED_ONLY_SERVICES),
            "call_to_connect": sorted(CALL_TO_CONNECT.keys()),
            "form_routing": "collecting",
            "note": (
                "Plumbing is live call-to-connect. Cleaning/pest and other form services "
                "are accepted and passed along when a buyer webhook covers them — "
                "no live form buyer yet. Do not promise a provider callback."
            ),
            "mock_forwarding": config.settings.mock_forwarding,
        }
    )


@mcp.custom_route("/v1/leads", methods=["POST"])
async def create_lead_http(request: Request) -> Response:
    if not _token_ok(request):
        return _unauthorized()
    try:
        body = await request.json()
        req = ServiceRequest.model_validate(body)
    except Exception as exc:
        return JSONResponse({"error": "invalid_request", "detail": str(exc)}, status_code=422)
    result = await submit_request(req)
    return JSONResponse(result.model_dump(mode="json"), status_code=202)


@mcp.custom_route("/v1/leads", methods=["GET"])
async def list_leads_http(request: Request) -> Response:
    if not _token_ok(request):
        return _unauthorized()
    limit = int(request.query_params.get("limit", "50"))
    rows = [
        {
            "id": row.id,
            "created_at": row.created_at.isoformat(),
            "status": row.status.value,
            "service_type": row.request.service_type,
            "zip_code": row.request.zip_code,
            "customer_name": row.request.customer_name,
        }
        for row in list_leads(limit=min(limit, 200))
    ]
    return JSONResponse({"leads": rows})


@mcp.custom_route("/v1/leads/{lead_id}", methods=["GET"])
async def get_lead_http(request: Request) -> Response:
    if not _token_ok(request):
        return _unauthorized()
    lead_id = request.path_params["lead_id"]
    row = lookup_lead(lead_id)
    if not row:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse(json.loads(row.model_dump_json()))


READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
SUBMIT = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True)


@mcp.tool(title="Get the plumbing call-to-connect number", annotations=READ_ONLY)
async def get_plumbing_call_number(
    zip_code: Annotated[
        str | None, Field(description="Optional US ZIP of the job site. Not required.")
    ] = None,
) -> str:
    """Get the phone number a person dials to be connected with a local plumbing professional.

    Use this for any plumbing need (leak, clog, water heater, sewer, burst pipe).
    No name, phone, or consent is needed. Read what_to_tell_the_user to the person.
    The person must place the call themselves: never dial, autodial, transfer, or
    call on their behalf. Zaptu does not perform the work and this is not a booking.
    """
    return json.dumps(catalog.plumbing_answer(zip_code), indent=2)


@mcp.tool(title="Request a home service", annotations=SUBMIT)
async def request_home_service(
    service_type: Annotated[
        Literal[
            "house_cleaning",
            "deep_cleaning",
            "move_in_out_cleaning",
            "recurring_cleaning",
            "pest_control",
            "plumbing",
            "hvac",
            "handyman",
            "other",
        ],
        Field(description="Type of local service requested. For plumbing, prefer get_plumbing_call_number."),
    ],
    zip_code: Annotated[str, Field(description="US 5-digit ZIP for the job site.")],
    customer_name: Annotated[str, Field(description="Customer's full name.")],
    customer_phone: Annotated[str, Field(description="US phone number for follow-up contact about this request.")],
    consent_to_contact: Annotated[
        bool,
        Field(description="Must be true for non-plumbing services: the person agreed to a call or text about this request."),
    ],
    city: str | None = None,
    state: Annotated[str | None, Field(description="2-letter US state code.")] = None,
    address_line: str | None = None,
    bedrooms: int | None = None,
    bathrooms: float | None = None,
    square_feet: int | None = None,
    home_type: Literal["apartment", "condo", "townhouse", "single_family", "other"] | None = None,
    frequency: Literal["one_time", "weekly", "biweekly", "monthly"] = "one_time",
    preferred_date: str | None = Field(
        default=None, description="Preferred date as YYYY-MM-DD, if any."
    ),
    flexible_dates: bool = True,
    notes: Annotated[str | None, Field(description="What the person needs, in their words.")] = None,
    customer_email: str | None = None,
    source_agent: Annotated[str | None, Field(description="Your agent or product name.")] = "mcp",
    dry_run: Annotated[bool, Field(description="Validate only; nothing is saved or passed along.")] = False,
) -> str:
    """Submit a home-service request (a lead, not a booking).

    Cleaning, pest control, HVAC, handyman, and other are collecting: the request is
    passed along when a buyer covers the service, and there is no live buyer yet, so do
    not promise a callback. Requires name, phone, ZIP, and the person's explicit consent.

    For plumbing, the result includes call_to_connect and call_instruction: give the
    person the number and have them dial it. Never place the call yourself.
    get_plumbing_call_number does the same without any personal details.
    """
    payload = {
        "service_type": service_type,
        "zip_code": zip_code,
        "city": city,
        "state": state,
        "address_line": address_line,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "square_feet": square_feet,
        "home_type": home_type,
        "frequency": frequency,
        "preferred_date": preferred_date or None,
        "flexible_dates": flexible_dates,
        "notes": notes,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "consent_to_contact": consent_to_contact,
        "source_agent": source_agent,
    }
    try:
        req = ServiceRequest.model_validate(payload)
    except ValidationError as exc:
        fields = _friendly_errors(exc)
        return json.dumps({"error": "invalid_request", "message": " ".join(fields.values()), "fields": fields}, indent=2)
    result = await submit_request(req, dry_run=dry_run)
    return result.model_dump_json(indent=2)


@mcp.tool(title="Request house cleaning", annotations=SUBMIT)
async def request_cleaning(
    zip_code: Annotated[str, Field(description="US 5-digit ZIP for the home.")],
    customer_name: Annotated[str, Field(description="Customer's full name.")],
    customer_phone: Annotated[str, Field(description="US phone number.")],
    consent_to_contact: Annotated[bool, Field(description="Must be true: the person agreed to a call or text about this request.")],
    bedrooms: int | None = None,
    bathrooms: float | None = None,
    square_feet: int | None = None,
    frequency: Literal["one_time", "weekly", "biweekly", "monthly"] = "one_time",
    preferred_date: str | None = None,
    notes: str | None = None,
    customer_email: str | None = None,
    city: str | None = None,
    state: str | None = None,
) -> str:
    """Shortcut for residential house cleaning (collecting; not a booking). Same pipeline as request_home_service."""
    return await request_home_service(
        service_type="house_cleaning" if frequency == "one_time" else "recurring_cleaning",
        zip_code=zip_code,
        customer_name=customer_name,
        customer_phone=customer_phone,
        consent_to_contact=consent_to_contact,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        square_feet=square_feet,
        frequency=frequency,
        preferred_date=preferred_date,
        notes=notes,
        customer_email=customer_email,
        city=city,
        state=state,
        source_agent="mcp-cleaning",
    )


@mcp.tool(title="Check lead status", annotations=READ_ONLY)
async def get_lead_status(
    lead_id: Annotated[str, Field(description="ID returned by request_home_service.")],
) -> str:
    """Look up a previously submitted service request by lead_id."""
    row = lookup_lead(lead_id)
    if not row:
        return json.dumps({"error": "not_found", "lead_id": lead_id, "message": "No request with that lead_id."})
    return json.dumps(
        {
            "lead_id": row.id,
            "status": row.status.value,
            "created_at": row.created_at.isoformat(),
            "service_type": row.request.service_type,
            "zip_code": row.request.zip_code,
            "message": row.public_message,
            "validation_notes": row.validation_notes,
        },
        indent=2,
    )


@mcp.tool(title="List supported services", annotations=READ_ONLY)
async def list_supported_services() -> str:
    """Which services are live (plumbing: the person dials a number) vs collecting, plus the rules for agents."""
    return json.dumps(catalog.services_catalog(), indent=2)


class _StatelessGetGuard:
    """Stateless server: no standalone SSE stream, so GET /mcp answers 405 (allowed by the spec)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "GET" and scope["path"].rstrip("/") == "/mcp":
            resp = JSONResponse(
                {"error": "method_not_allowed", "message": "POST JSON-RPC to /mcp. See https://zaptu.ai/agents/"},
                status_code=405,
                headers={"Allow": "POST"},
            )
            await resp(scope, receive, send)
            return
        await self.app(scope, receive, send)


def create_app(host: str = "0.0.0.0") -> Starlette:
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        host=host,
    )
    app.add_middleware(_StatelessGetGuard)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id", "Mcp-Protocol-Version"],
        # Public, credential-free API: also answer Chrome Private Network Access preflights
        # (sent when a visitor's DNS maps api.zaptu.ai to a private address, e.g. split DNS).
        allow_private_network=True,
        max_age=86400,
    )
    return app


def main() -> None:
    import uvicorn

    port = int(os.getenv("PORT", config.settings.port))
    host = os.getenv("HOST", config.settings.host)
    uvicorn.run(create_app(host=host), host=host, port=port, log_level=config.settings.log_level.lower())


if __name__ == "__main__":
    main()
