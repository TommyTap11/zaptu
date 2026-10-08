"""Single source of truth for agent-facing metadata.

Used by the MCP tools, the REST discovery endpoints (/v1/services, /openapi.json,
server cards), and scripts/build_discovery.py, which writes static copies to web/.
Copy rules (The Client Connector): no prices, no superlatives, no guarantees, never
imply Zaptu performs the work, and the person always dials the plumbing number.
"""

from __future__ import annotations

from typing import Any

from .call_routing import CALL_TO_CONNECT
from .models import ALL_SERVICE_TYPES, LeadResponse, ServiceRequest
from .validation import COLLECTED_ONLY_SERVICES, ROUTABLE_SERVICES

VERSION = "0.2.0"
SITE = "https://zaptu.ai"
API = "https://api.zaptu.ai"
MCP_URL = f"{API}/mcp"
CONTACT_EMAIL = "hello@zaptu.ai"
REGISTRY_NAME = "ai.zaptu/zaptu"  # reverse-DNS name for MCP registries (domain-owned)
PROTOCOL_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26"]

SHORT_DESCRIPTION = "Connect people with independent local home-service contractors. For plumbing, the person dials."

ABOUT = (
    "Zaptu connects people with independent local home-service contractors. "
    "Zaptu does not perform the work and does not book appointments."
)

REQUIRED_FIELDS = ["service_type", "zip_code", "customer_name", "customer_phone", "consent_to_contact"]

AGENT_RULES = [
    "Plumbing is live: give the person the phone number and ask them to dial it themselves.",
    "Never dial, autodial, transfer, or place a call on the person's behalf.",
    "Other services are collecting: submit only with the person's explicit consent to be contacted.",
    "A request is not a booking. Do not promise a callback, an arrival time, or a named company.",
    "Zaptu does not perform the work. Contractors are independent.",
]

SERVICE_LABELS = {
    "house_cleaning": "House cleaning",
    "deep_cleaning": "Deep cleaning",
    "move_in_out_cleaning": "Move-in / move-out cleaning",
    "recurring_cleaning": "Recurring cleaning",
    "pest_control": "Pest control",
    "plumbing": "Plumbing",
    "hvac": "HVAC",
    "handyman": "Handyman",
    "other": "Other home service",
}


def plumbing_answer(zip_code: str | None = None) -> dict[str, Any]:
    """What an agent needs to hand a person the plumbing number. No personal data required."""
    c = CALL_TO_CONNECT["plumbing"]
    where = f" for ZIP {zip_code}" if zip_code else ""
    return {
        "service_type": "plumbing",
        "status": "call_to_connect",
        "call_to_connect": c.phone_e164,
        "call_to_connect_display": c.display,
        "tel_link": c.tel_href,
        "what_to_tell_the_user": (
            f"To be connected with a local plumbing professional{where}, call {c.display}. "
            "Please place the call yourself. Zaptu does not perform the work and this is not a booking."
        ),
        "call_instruction": c.instruction,
        "coverage_note": "Availability depends on the caller's ZIP code and the time of day.",
        "web_page": f"{SITE}/plumbing/",
    }


def services_catalog() -> dict[str, Any]:
    collecting = sorted(ROUTABLE_SERVICES | COLLECTED_ONLY_SERVICES, key=ALL_SERVICE_TYPES.index)
    return {
        "name": "Zaptu",
        "about": ABOUT,
        "version": VERSION,
        "live": [
            {
                "service_type": key,
                "label": SERVICE_LABELS.get(key, key),
                "mode": "call_to_connect",
                **{k: v for k, v in plumbing_answer().items() if k not in {"service_type", "status"}},
                "how": "Call get_plumbing_call_number (MCP) or GET /v1/services and read the number to the person. No personal details needed.",
            }
            for key in CALL_TO_CONNECT
        ],
        "collecting": [
            {
                "service_type": key,
                "label": SERVICE_LABELS.get(key, key),
                "mode": "request_form",
                "status": "collecting",
                "note": "Accepted and passed along when a buyer covers the service. No live buyer yet, so do not promise a callback.",
            }
            for key in collecting
        ],
        "all_service_types": list(ALL_SERVICE_TYPES),
        "required_fields_for_requests": REQUIRED_FIELDS,
        "rules": AGENT_RULES,
        "coverage": "US residential.",
        "endpoints": {
            "mcp": MCP_URL,
            "intake": f"{API}/v1/intake",
            "services": f"{API}/v1/services",
            "openapi": f"{API}/openapi.json",
            "docs": f"{SITE}/agents/",
            "llms": f"{SITE}/llms.txt",
        },
        "contact": CONTACT_EMAIL,
    }


def _schema_defs(model: type) -> dict[str, Any]:
    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    defs = schema.pop("$defs", {})
    return {model.__name__: schema, **defs}


def openapi_spec() -> dict[str, Any]:
    error = {
        "type": "object",
        "properties": {
            "error": {"type": "string", "example": "invalid_request"},
            "message": {"type": "string", "example": "Phone must be a 10-digit US number."},
            "fields": {"type": "object", "additionalProperties": {"type": "string"}},
        },
        "required": ["error", "message"],
    }
    request_schema = {
        "allOf": [
            {"$ref": "#/components/schemas/ServiceRequest"},
            {
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "default": False,
                        "description": "Validate only. Nothing is stored or passed along.",
                    }
                },
            },
        ]
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Zaptu API",
            "version": VERSION,
            "description": (
                ABOUT
                + " Plumbing returns a phone number the person must dial themselves; never dial for them. "
                "Other services are collecting: requests are accepted and passed along when a buyer covers the service. "
                "A request is not a booking. Add \"dry_run\": true to validate without saving anything."
            ),
            "contact": {"email": CONTACT_EMAIL, "url": f"{SITE}/agents/"},
        },
        "servers": [{"url": API}],
        "externalDocs": {"url": f"{SITE}/agents/", "description": "Agent guide"},
        "paths": {
            "/v1/services": {
                "get": {
                    "operationId": "listServices",
                    "summary": "Which services are live vs collecting, the plumbing number, and agent rules",
                    "responses": {"200": {"description": "Service catalog", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/v1/intake": {
                "post": {
                    "operationId": "submitServiceRequest",
                    "summary": "Submit a home-service request (lead, not a booking)",
                    "description": (
                        "JSON clients get JSON back. HTML form posts (application/x-www-form-urlencoded) are redirected "
                        "to the thanks page, or to the plumbing page for plumbing. For plumbing the response includes "
                        "call_to_connect: give the person the number and have them dial it. "
                        "consent_to_contact must be true for non-plumbing services."
                    ),
                    "parameters": [
                        {"name": "dry_run", "in": "query", "required": False, "schema": {"type": "boolean"},
                         "description": "Validate only. Nothing is stored or passed along."}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": request_schema,
                                "example": {
                                    "service_type": "house_cleaning",
                                    "zip_code": "33139",
                                    "customer_name": "Jamie Example",
                                    "customer_phone": "305-555-0100",
                                    "consent_to_contact": True,
                                    "bedrooms": 2,
                                    "dry_run": True,
                                },
                            },
                            "application/x-www-form-urlencoded": {"schema": request_schema},
                        },
                    },
                    "responses": {
                        "202": {"description": "Accepted (received, collected, or call_to_connect)",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LeadResponse"}}}},
                        "200": {"description": "dry_run result; nothing stored",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LeadResponse"}}}},
                        "303": {"description": "Form post redirect to the thanks page or plumbing page"},
                        "422": {"description": "Invalid or rejected request with a readable message",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "429": {"description": "Too many requests", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            },
            "/health": {
                "get": {"operationId": "health", "summary": "Service health",
                        "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}}}
            },
        },
        "components": {"schemas": {**_schema_defs(ServiceRequest), **_schema_defs(LeadResponse), "Error": error}},
    }


def mcp_manifest() -> dict[str, Any]:
    """Zaptu's own discovery document at /.well-known/mcp.json."""
    plumbing = plumbing_answer()
    return {
        "name": "zaptu",
        "title": "Zaptu",
        "version": VERSION,
        "description": ABOUT + " Plumbing returns a phone number the person dials; agents must not place the call.",
        "website": f"{SITE}/",
        "docs": f"{SITE}/agents/",
        "llms": f"{SITE}/llms.txt",
        "llms_full": f"{SITE}/llms-full.txt",
        "contact": CONTACT_EMAIL,
        "transport": "streamable-http",
        "mcp_url": MCP_URL,
        "authentication": {"required": False},
        "api_base": API,
        "intake": f"{API}/v1/intake",
        "services": f"{API}/v1/services",
        "openapi": f"{API}/openapi.json",
        "server_card": f"{API}/.well-known/mcp/server-card.json",
        "live": {"plumbing": {"call_to_connect": plumbing["call_to_connect"], "display": plumbing["call_to_connect_display"], "rule": plumbing["call_instruction"]}},
        "collecting": [s["service_type"] for s in services_catalog()["collecting"]],
        "required_fields": REQUIRED_FIELDS,
        "rules": AGENT_RULES,
    }


def server_card(tools: list[dict[str, Any]], instructions: str) -> dict[str, Any]:
    """Static server card: Smithery / SEP-1649 fields plus registry-style identity fields."""
    return {
        "name": REGISTRY_NAME,
        "title": "Zaptu",
        "version": VERSION,
        "description": SHORT_DESCRIPTION,
        "websiteUrl": f"{SITE}/",
        "remotes": [{"type": "streamable-http", "url": MCP_URL, "supportedProtocolVersions": PROTOCOL_VERSIONS}],
        "serverInfo": {"name": "zaptu", "title": "Zaptu", "version": VERSION, "websiteUrl": f"{SITE}/"},
        "protocolVersion": PROTOCOL_VERSIONS[0],
        "transport": {"type": "streamable-http", "url": MCP_URL, "endpoint": "/mcp"},
        "capabilities": {"tools": {"listChanged": False}},
        "authentication": {"required": False},
        "instructions": instructions,
        "documentationUrl": f"{SITE}/agents/",
        "iconUrl": f"{SITE}/icon-512.png",
        "contact": CONTACT_EMAIL,
        "tools": tools,
        "resources": [],
        "prompts": [],
    }


def server_card_v1() -> dict[str, Any]:
    """SEP-2127 / MCP Registry v1 server card (strict field set)."""
    return {
        "$schema": "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json",
        "name": REGISTRY_NAME,
        "version": VERSION,
        "description": SHORT_DESCRIPTION,
        "title": "Zaptu",
        "websiteUrl": f"{SITE}/",
        "icons": [{"src": f"{SITE}/icon-512.png", "mimeType": "image/png", "sizes": ["512x512"]}],
        "remotes": [{"type": "streamable-http", "url": MCP_URL, "supportedProtocolVersions": PROTOCOL_VERSIONS}],
    }


def registry_server_json() -> dict[str, Any]:
    """server.json for the official MCP Registry (publish with mcp-publisher; needs domain auth)."""
    return {
        "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
        "name": REGISTRY_NAME,
        "title": "Zaptu",
        "description": SHORT_DESCRIPTION,
        "version": VERSION,
        "websiteUrl": SITE,
        "remotes": [{"type": "streamable-http", "url": MCP_URL}],
    }
