"""HTTP-level tests for /v1/intake (JSON + form-urlencoded)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ZAPTU_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ZAPTU_MOCK_FORWARDER", "0")
    monkeypatch.setenv("MOCK_FORWARDING", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")

    from aslc import config

    config.settings.data_dir = tmp_path
    config.settings.mock_forwarding = False
    config.settings.rate_limit_per_minute = 1000
    config.settings.thanks_url = "https://zaptu.ai/thanks"
    config.settings.cors_origins = ("https://zaptu.ai", "https://www.zaptu.ai")
    config.settings.webhook_url = None

    from aslc import server

    app = None
    for attr in ("streamable_http_app", "sse_app", "app"):
        obj = getattr(server.mcp, attr, None)
        if callable(obj):
            try:
                app = obj()
                break
            except TypeError:
                continue
        elif obj is not None:
            app = obj
            break
    if app is None:
        raise RuntimeError("Could not obtain Starlette app from MCPServer")
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "house_cleaning" in body["supported_services"]
    assert "handyman" in body["collected_only"]
    assert body["mock_forwarding"] is False


def test_json_intake(client):
    r = client.post(
        "/v1/intake",
        json={
            "service_type": "house_cleaning",
            "zip_code": "33139",
            "customer_name": "Tom C",
            "customer_phone": "3055550100",
            "consent_to_contact": True,
            "bedrooms": 2,
        },
        headers={"Origin": "https://zaptu.ai"},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] in {"received", "forwarded"}
    assert "being routed" in body["message"].lower()
    assert r.headers.get("access-control-allow-origin") == "https://zaptu.ai"


def test_form_intake_redirects(client):
    r = client.post(
        "/v1/intake",
        data={
            "form-name": "service-request",
            "bot-field": "",
            "customer_name": "Tom C",
            "customer_phone": "3055550100",
            "zip_code": "33139",
            "service_type": "house_cleaning",
            "bedrooms": "2",
            "consent_to_contact": "yes",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "https://zaptu.ai/thanks"


def test_no_consent_rejected(client):
    r = client.post(
        "/v1/intake",
        json={
            "service_type": "house_cleaning",
            "zip_code": "33139",
            "customer_name": "Tom C",
            "customer_phone": "3055550100",
            "consent_to_contact": False,
            "bedrooms": 2,
        },
    )
    assert r.status_code == 422
    assert r.json()["status"] == "rejected"


def test_honeypot_ignored(client):
    r = client.post(
        "/v1/intake",
        data={
            "form-name": "service-request",
            "bot-field": "I am a bot",
            "customer_name": "Spam Bot",
            "customer_phone": "3055550100",
            "zip_code": "33139",
            "service_type": "house_cleaning",
            "consent_to_contact": "yes",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "https://zaptu.ai/thanks"


def test_handyman_form_accepted(client):
    r = client.post(
        "/v1/intake",
        json={
            "service_type": "handyman",
            "zip_code": "33139",
            "customer_name": "Tom C",
            "customer_phone": "3055550100",
            "consent_to_contact": True,
        },
    )
    assert r.status_code == 202
    assert r.json()["status"] == "collected"


def test_plumbing_call_to_connect(client):
    r = client.post(
        "/v1/intake",
        json={
            "service_type": "plumbing",
            "zip_code": "33139",
            "customer_name": "Tom C",
            "customer_phone": "3055550100",
            "consent_to_contact": True,
            "notes": "water heater",
        },
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "call_to_connect"
    assert body["call_to_connect"] == "+13085299543"
    assert body["call_to_connect_display"] == "(308) 529-9543"
    assert "dial" in body["call_instruction"].lower() or "place the call" in body["call_instruction"].lower()
    assert "plumbing" in body["message"].lower() or "308" in body["message"]


def test_health_lists_call_to_connect(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "plumbing" in body["call_to_connect"]
    assert "plumbing" not in body["collected_only"]
