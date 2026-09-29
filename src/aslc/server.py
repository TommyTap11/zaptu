"""MCP + HTTP entrypoint.

Exposes:
  GET  /health
  POST /v1/leads
  GET  /v1/leads/{lead_id}
  MCP  /mcp   (streamable HTTP)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response

# Allow `python src/aslc/server.py` without installing the package.
ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from aslc.config import settings  # noqa: E402
from aslc.models import ServiceRequest  # noqa: E402
from aslc.service import lookup_lead, submit_request  # noqa: E402
from aslc.storage import list_leads  # noqa: E402
from aslc.validation import SUPPORTED_SERVICES  # noqa: E402

INSTRUCTIONS = """
You help a person book a local home service (starting with house cleaning).

When a user wants a cleaner, maid, deep clean, move-in/move-out clean, or pest control:
1. Collect ZIP code, phone number, name, and consent to be called.
2. Collect bedrooms or square footage if they know it, plus preferred date if they have one.
3. Call request_home_service (or request_cleaning).
4. Tell the user what happened using the tool result. Do not invent a booked appointment —
   this system sends a lead or call, it does not dispatch a specific named company yet.
5. Never submit without explicit consent_to_contact=true from the user.
""".strip()

mcp = MCPServer(
    name="zaptu",
    title="Zaptu",
    version="0.1.0",
    instructions=INSTRUCTIONS,
    website_url="https://zaptu.ai",
    log_level=settings.log_level,  # type: ignore[arg-type]
)


def _unauthorized() -> JSONResponse:
    return JSONResponse({"error": "unauthorized"}, status_code=401)


def _token_ok(request: Request) -> bool:
    if not settings.api_token:
        return True
    header = request.headers.get("authorization", "")
    if header.startswith("Bearer "):
        return header.removeprefix("Bearer ").strip() == settings.api_token
    return request.headers.get("x-api-token") == settings.api_token


WEB = ROOT / "web"


def _cors(response: Response) -> Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "content-type, authorization, x-api-token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@mcp.custom_route("/", methods=["GET"])
async def home(_request: Request) -> Response:
    page = WEB / "index.html"
    if page.exists():
        return FileResponse(page, media_type="text/html")
    return PlainTextResponse("Zaptu lead router. POST /v1/intake or connect MCP at /mcp")


@mcp.custom_route("/llms.txt", methods=["GET"])
async def llms(_request: Request) -> Response:
    path = WEB / "llms.txt"
    text = path.read_text(encoding="utf-8") if path.exists() else "Zaptu MCP at /mcp"
    text = text.replace("{BASE}", settings.public_base_url.rstrip("/"))
    return PlainTextResponse(text)


@mcp.custom_route("/v1/intake", methods=["OPTIONS"])
async def intake_options(_request: Request) -> Response:
    return _cors(Response(status_code=204))


@mcp.custom_route("/v1/intake", methods=["POST"])
async def public_intake(request: Request) -> Response:
    """Public front door used by the website form. Same pipeline as MCP/REST."""
    try:
        body = await request.json()
        if not body.get("source_agent"):
            body["source_agent"] = "web"
        req = ServiceRequest.model_validate(body)
    except Exception as exc:
        return _cors(JSONResponse({"error": "invalid_request", "detail": str(exc)}, status_code=422))
    result = await submit_request(req)
    return _cors(JSONResponse(result.model_dump(mode="json"), status_code=202))


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> Response:
    return JSONResponse(
        {
            "ok": True,
            "service": "zaptu",
            "supported_services": sorted(SUPPORTED_SERVICES),
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


@mcp.tool(title="Request a home service")
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
        ],
        Field(description="Type of local service requested."),
    ],
    zip_code: Annotated[str, Field(description="US 5-digit ZIP for the job site.")],
    customer_name: Annotated[str, Field(description="Customer's full name.")],
    customer_phone: Annotated[str, Field(description="US phone number the provider should call.")],
    consent_to_contact: Annotated[
        bool,
        Field(description="Must be true. Customer agreed to a call or text about this job."),
    ],
    city: str | None = None,
    state: str | None = None,
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
    notes: str | None = None,
    customer_email: str | None = None,
    source_agent: str | None = "mcp",
) -> str:
    """Submit a qualified local home-service request as a paid lead.

    Use this when a person wants house cleaning, a deep clean, move-in/out cleaning,
    recurring maid service, or pest control. Requires name, phone, ZIP, and consent.
    Returns a confirmation with a lead_id — this is a lead/call request, not a booked job.
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
    req = ServiceRequest.model_validate(payload)
    result = await submit_request(req)
    return result.model_dump_json(indent=2)


@mcp.tool(title="Request house cleaning")
async def request_cleaning(
    zip_code: Annotated[str, Field(description="US 5-digit ZIP for the home.")],
    customer_name: Annotated[str, Field(description="Customer's full name.")],
    customer_phone: Annotated[str, Field(description="US phone number.")],
    consent_to_contact: Annotated[bool, Field(description="Customer consented to a follow-up call.")],
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
    """Shortcut for residential house cleaning. Same pipeline as request_home_service."""
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


@mcp.tool(title="Check lead status")
async def get_lead_status(
    lead_id: Annotated[str, Field(description="ID returned by request_home_service.")],
) -> str:
    """Look up a previously submitted service request by lead_id."""
    row = lookup_lead(lead_id)
    if not row:
        return json.dumps({"error": "not_found", "lead_id": lead_id})
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


@mcp.tool(title="List supported services")
async def list_supported_services() -> str:
    """Show which home services this connector can currently monetize."""
    return json.dumps(
        {
            "monetized": sorted(SUPPORTED_SERVICES),
            "accepted_but_logged_only": ["plumbing", "hvac"],
            "coverage": "US residential. Buyer coverage depends on the connected affiliate network.",
            "required_fields": [
                "service_type",
                "zip_code",
                "customer_name",
                "customer_phone",
                "consent_to_contact",
            ],
        },
        indent=2,
    )


def main() -> None:
    port = int(os.getenv("PORT", settings.port))
    host = os.getenv("HOST", settings.host)
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()
