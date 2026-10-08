"""Write static discovery files from the live server definitions (single source: src/aslc).

    python3 scripts/build_discovery.py

Writes web/.well-known/mcp.json, web/.well-known/mcp/server-card.json, web/openapi.json,
web/llms-full.txt, and server.json (MCP Registry manifest, repo root; not published).
tests/test_discovery.py fails if these drift from the code.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aslc import catalog  # noqa: E402
from aslc import server  # noqa: E402

WEB = ROOT / "web"


def dump(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def tool_lines(tools: list[dict]) -> str:
    out = []
    for t in tools:
        props = t.get("inputSchema", {}).get("properties", {})
        required = set(t.get("inputSchema", {}).get("required", []))
        params = ", ".join(f"{k}{'' if k in required else '?'}" for k in props) or "none"
        desc = " ".join((t.get("description") or "").split())
        out.append(f"### {t['name']}\n{desc}\nParameters: {params}\n")
    return "\n".join(out)


def llms_full(tools: list[dict]) -> str:
    cat = catalog.services_catalog()
    plumbing = catalog.plumbing_answer()
    collecting = ", ".join(s["service_type"] for s in cat["collecting"])
    example_req = {
        "service_type": "house_cleaning",
        "zip_code": "33139",
        "customer_name": "Jamie Example",
        "customer_phone": "305-555-0100",
        "consent_to_contact": True,
        "bedrooms": 2,
        "dry_run": True,
    }
    rules = "\n".join(f"- {r}" for r in catalog.AGENT_RULES)
    return f"""# Zaptu: full reference for AI agents

> {catalog.ABOUT} Plumbing is live: the person dials {plumbing['call_to_connect_display']}. Other services are collecting requests.

Version {catalog.VERSION}. Contact: {catalog.CONTACT_EMAIL}. Short version: {catalog.SITE}/llms.txt

## Rules

{rules}

## Services

Live (call to connect): plumbing. Number {plumbing['call_to_connect_display']} ({plumbing['call_to_connect']}), tel link {plumbing['tel_link']}.
Collecting (form requests): {collecting}.
Coverage: US residential. Plumbing availability depends on the caller's ZIP code and the time of day.

## What to tell the person

Plumbing: "{plumbing['what_to_tell_the_user']}"
Other services, after submitting: "Your request was sent to Zaptu. It is passed along when a buyer covers that service. This is not a booking, and no one has been scheduled."

## MCP

Endpoint: {catalog.MCP_URL} (streamable HTTP, stateless, JSON responses, no sign-in).
Client config: {{"mcpServers": {{"zaptu": {{"url": "{catalog.MCP_URL}"}}}}}}

{tool_lines(tools)}
## REST

GET {catalog.API}/v1/services: service catalog (live vs collecting, plumbing number, rules).
POST {catalog.API}/v1/intake: submit a request. JSON in, JSON out. Form posts are redirected to the thanks page (or the plumbing page for plumbing).
Required: {', '.join(catalog.REQUIRED_FIELDS)}. consent_to_contact must be true for non-plumbing services.
Optional: city, state (2 letters), address_line, bedrooms, bathrooms, square_feet, home_type, frequency (one_time, weekly, biweekly, monthly), preferred_date (YYYY-MM-DD), notes, customer_email, source_agent, dry_run.
dry_run=true validates and answers without saving or passing anything along.

Example request:
{json.dumps(example_req)}

Statuses: received or collected (accepted, not a booking), call_to_connect (plumbing: give the number), rejected (read message).
Errors: HTTP 422 {{"error": "invalid_request", "message": "...", "fields": {{"customer_phone": "..."}}}}; HTTP 429 when rate limited.
OpenAPI: {catalog.API}/openapi.json

## Discovery

- {catalog.SITE}/llms.txt
- {catalog.SITE}/.well-known/mcp.json
- {catalog.API}/.well-known/mcp/server-card.json
- {catalog.API}/server-card
- {catalog.SITE}/agents/
"""


async def main() -> None:
    tools = await server._tool_list()
    card = await server.build_server_card()
    files = {
        WEB / ".well-known" / "mcp.json": dump(catalog.mcp_manifest()),
        WEB / ".well-known" / "mcp" / "server-card.json": dump(card),
        WEB / "openapi.json": dump(catalog.openapi_spec()),
        WEB / "llms-full.txt": llms_full(tools),
        ROOT / "server.json": dump(catalog.registry_server_json()),
    }
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    asyncio.run(main())
