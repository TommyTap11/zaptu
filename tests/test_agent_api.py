"""Agent-facing API: MCP tools, discovery documents, CORS, errors, dry runs."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from aslc import config

    config.settings.data_dir = tmp_path
    config.settings.mock_forwarding = False
    config.settings.rate_limit_per_minute = 1000
    config.settings.thanks_url = "https://zaptu.ai/thanks/"
    config.settings.webhook_url = None
    from aslc import server

    with TestClient(server.create_app(host="0.0.0.0")) as c:
        yield c


def rpc(client, method, params=None, id_=1):
    r = client.post("/mcp", headers=MCP_HEADERS, json={"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}})
    assert r.status_code == 200, r.text
    return r.json()


def call_tool(client, name, args):
    body = rpc(client, "tools/call", {"name": name, "arguments": args})
    text = body["result"]["content"][0]["text"]
    return json.loads(text)


def leads_file(tmp_path: Path) -> list[str]:
    return [line for f in tmp_path.glob("*.jsonl") for line in f.read_text().splitlines()]


# --- MCP -------------------------------------------------------------------

def test_mcp_initialize_and_instructions(client):
    res = rpc(client, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}})["result"]
    assert res["serverInfo"]["name"] == "zaptu"
    instr = res["instructions"]
    assert "(308) 529-9543" in instr and "get_plumbing_call_number" in instr
    assert "Never dial" in instr


def test_mcp_tools_list_has_plumbing_tool_and_annotations(client):
    tools = {t["name"]: t for t in rpc(client, "tools/list")["result"]["tools"]}
    assert {"get_plumbing_call_number", "request_home_service", "request_cleaning", "get_lead_status", "list_supported_services"} <= set(tools)
    assert tools["get_plumbing_call_number"]["annotations"]["readOnlyHint"] is True
    assert tools["get_plumbing_call_number"]["inputSchema"].get("required", []) == []
    assert tools["request_home_service"]["annotations"]["readOnlyHint"] is False
    assert tools["list_supported_services"]["annotations"]["readOnlyHint"] is True


def test_mcp_plumbing_tool_returns_number_person_dials(client, tmp_path):
    out = call_tool(client, "get_plumbing_call_number", {"zip_code": "33139"})
    assert out["status"] == "call_to_connect"
    assert out["call_to_connect"] == "+13085299543"
    assert out["call_to_connect_display"] == "(308) 529-9543"
    assert "place the call yourself" in out["what_to_tell_the_user"]
    assert "Do not dial" in out["call_instruction"]
    assert leads_file(tmp_path) == []  # read-only, no personal data stored


def test_mcp_request_home_service_plumbing_without_consent_still_gets_number(client):
    out = call_tool(client, "request_home_service", {
        "service_type": "plumbing", "zip_code": "33139", "customer_name": "Test Person",
        "customer_phone": "3055550100", "consent_to_contact": False,
    })
    assert out["status"] == "call_to_connect"
    assert out["call_to_connect"] == "+13085299543"


def test_mcp_request_validation_error_is_readable(client):
    out = call_tool(client, "request_home_service", {
        "service_type": "house_cleaning", "zip_code": "33139", "customer_name": "Test Person",
        "customer_phone": "123", "consent_to_contact": True,
    })
    assert out["error"] == "invalid_request"
    assert "10-digit" in out["fields"]["customer_phone"]


def test_mcp_list_services_live_vs_collecting(client):
    out = call_tool(client, "list_supported_services", {})
    assert [s["service_type"] for s in out["live"]] == ["plumbing"]
    assert "pest_control" in [s["service_type"] for s in out["collecting"]]
    assert "plumbing" not in [s["service_type"] for s in out["collecting"]]
    assert "campaign_id" not in json.dumps(out)
    assert out["contact"] == "hello@zaptu.ai"


def test_mcp_get_is_405_and_cors_preflight_open(client):
    assert client.get("/mcp").status_code == 405
    r = client.options("/mcp", headers={"Origin": "https://agent.example", "Access-Control-Request-Method": "POST",
                                         "Access-Control-Request-Headers": "content-type, mcp-protocol-version"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "*"
    r = client.options("/v1/intake", headers={"Origin": "https://agent.example", "Access-Control-Request-Method": "POST"})
    assert r.headers["access-control-allow-origin"] == "*"
    r = client.options("/v1/intake", headers={"Origin": "https://zaptu.ai", "Access-Control-Request-Method": "POST",
                                              "Access-Control-Request-Headers": "content-type",
                                              "Access-Control-Request-Private-Network": "true"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-private-network"] == "true"


# --- REST + discovery ------------------------------------------------------

def test_root_redirects_browsers_and_serves_json_index(client):
    r = client.get("/", headers={"Accept": "text/html"}, follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "https://zaptu.ai/"
    body = client.get("/", headers={"Accept": "application/json"}).json()
    assert body["mcp"] == "https://api.zaptu.ai/mcp"
    assert "(308) 529-9543" in body["plumbing"]


def test_services_openapi_and_cards(client):
    svc = client.get("/v1/services").json()
    assert svc["live"][0]["call_to_connect"] == "+13085299543"
    spec = client.get("/openapi.json").json()
    assert spec["openapi"].startswith("3.1")
    assert "/v1/intake" in spec["paths"] and "/v1/services" in spec["paths"]
    assert "ServiceRequest" in spec["components"]["schemas"]
    assert spec["info"]["contact"]["email"] == "hello@zaptu.ai"
    card = client.get("/.well-known/mcp/server-card.json").json()
    assert card["serverInfo"]["name"] == "zaptu"
    assert card["authentication"] == {"required": False}
    assert card["remotes"][0] == {"type": "streamable-http", "url": "https://api.zaptu.ai/mcp", "supportedProtocolVersions": ["2025-11-25", "2025-06-18", "2025-03-26"]}
    assert "get_plumbing_call_number" in [t["name"] for t in card["tools"]]
    v1 = client.get("/server-card")
    assert v1.headers["content-type"].startswith("application/mcp-server-card+json")
    assert v1.json()["$schema"].endswith("/schemas/v1/server-card.schema.json")
    assert len(v1.json()["description"]) <= 100
    manifest = client.get("/.well-known/mcp.json").json()
    assert manifest["contact"] == "hello@zaptu.ai"
    assert client.get("/llms-full.txt").status_code == 200


def test_health_hides_internal_paths(client):
    body = client.get("/health").json()
    assert body["ok"] is True and "data_dir" not in body


# --- intake errors, dry run, form flow -------------------------------------

GOOD = {"service_type": "house_cleaning", "zip_code": "33139", "customer_name": "Test Person",
        "customer_phone": "3055550100", "consent_to_contact": True, "bedrooms": 2}


def test_json_validation_error_is_422_not_500(client):
    r = client.post("/v1/intake", json={**GOOD, "customer_phone": "123", "zip_code": "1"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "invalid_request"
    assert set(body["fields"]) == {"customer_phone", "zip_code"}
    assert "10-digit" in body["message"]


def test_missing_field_message(client):
    payload = dict(GOOD)
    payload.pop("customer_name")
    r = client.post("/v1/intake", json=payload)
    assert r.status_code == 422 and r.json()["fields"]["customer_name"] == "Name is required."


def test_form_validation_error_is_html_page(client):
    data = {k: str(v) for k, v in GOOD.items()} | {"customer_phone": "12", "consent_to_contact": "yes"}
    r = client.post("/v1/intake", data=data, follow_redirects=False)
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("text/html")
    assert "Phone must be a 10-digit US number" in r.text
    assert "history.back()" in r.text


def test_form_without_consent_shows_error_not_thanks(client):
    data = {k: str(v) for k, v in GOOD.items() if k != "consent_to_contact"}
    r = client.post("/v1/intake", data=data, follow_redirects=False)
    assert r.status_code == 422
    assert "consent" in r.text.lower()


def test_form_plumbing_goes_to_plumbing_page(client):
    data = {k: str(v) for k, v in GOOD.items()} | {"service_type": "plumbing", "consent_to_contact": "yes"}
    r = client.post("/v1/intake", data=data, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "https://zaptu.ai/plumbing/"


def test_dry_run_stores_nothing(client, tmp_path):
    r = client.post("/v1/intake", json={**GOOD, "dry_run": True})
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is True and body["message"].startswith("Dry run")
    r = client.post("/v1/intake?dry_run=1", data={k: str(v) for k, v in GOOD.items()} | {"consent_to_contact": "yes"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "https://zaptu.ai/thanks/"
    assert leads_file(tmp_path) == []
    r = client.post("/v1/intake", json=GOOD)
    assert r.status_code == 202
    assert len(leads_file(tmp_path)) == 1


def test_default_thanks_url_has_trailing_slash():
    from aslc.config import Settings

    assert Settings().thanks_url == "https://zaptu.ai/thanks/"


# --- static copies stay in sync with the code ------------------------------

def test_static_discovery_files_match_code():
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_discovery", ROOT / "scripts" / "build_discovery.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from aslc import catalog, server

    tools = asyncio.run(server._tool_list())
    card = asyncio.run(server.build_server_card())
    assert json.loads((WEB / ".well-known" / "mcp.json").read_text()) == catalog.mcp_manifest()
    assert json.loads((WEB / ".well-known" / "mcp" / "server-card.json").read_text()) == card
    assert json.loads((WEB / "openapi.json").read_text()) == catalog.openapi_spec()
    assert (WEB / "llms-full.txt").read_text() == mod.llms_full(tools)
    assert json.loads((ROOT / "server.json").read_text()) == catalog.registry_server_json()
