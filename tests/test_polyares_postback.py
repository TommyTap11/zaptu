"""Polyares conversion postback: GET and POST /v1/polyares-postback."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

import pytest
from starlette.testclient import TestClient


def _payload(**overrides):
    body = {
        "clickid": "clk-1",
        "event": "lead",
        "lead_id": "lead-1",
        "payout": "12.50",
        "category": "plumbing",
        "sub1": "miami",
        "sub2": "web",
        "sub3": "agent",
        "timestamp": "2026-11-06T12:00:00Z",
        "delivery_id": "del-1",
    }
    body.update(overrides)
    return body


def _sign(secret: str, fields: dict) -> str:
    from aslc.polyares_postback import canonical_message

    message = canonical_message({k: str(v) for k, v in fields.items() if v is not None and str(v) != ""})
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ZAPTU_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POLYARE_POSTBACK_SECRET", raising=False)
    monkeypatch.delenv("POLYARES_POSTBACK_SECRET", raising=False)
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")

    from aslc import config

    config.settings.data_dir = tmp_path
    config.settings.rate_limit_per_minute = 1000

    from aslc import server

    return TestClient(server.create_app(host="0.0.0.0"))


def test_post_json_happy_path_logs_payout_category_event(client, caplog):
    caplog.set_level(logging.INFO, logger="zaptu.polyares")
    response = client.post("/v1/polyares-postback", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body == {"ok": True, "status": "accepted", "duplicate": False, "event": "lead"}
    assert response.headers["cache-control"] == "no-store"

    from aslc.polyares_postback import list_conversions

    rows = list_conversions()
    assert len(rows) == 1
    assert rows[0]["payout"] == "12.50"
    assert rows[0]["category"] == "plumbing"
    assert rows[0]["event"] == "lead"
    assert rows[0]["delivery_id"] == "del-1"
    assert rows[0]["idem_key"] == "d:del-1"
    text = caplog.text
    assert "event=lead" in text
    assert "category=plumbing" in text
    assert "payout=12.50" in text


def test_get_query_postback(client):
    response = client.get("/v1/polyares-postback", params=_payload(event="call", payout="40"))
    assert response.status_code == 200
    assert response.json()["event"] == "call"
    assert response.json()["duplicate"] is False

    from aslc.polyares_postback import list_conversions

    assert list_conversions()[0]["event"] == "call"
    assert list_conversions()[0]["payout"] == "40"


def test_idempotent_upsert_updates_same_delivery(client):
    first = client.post("/v1/polyares-postback", json=_payload())
    assert first.json()["duplicate"] is False
    second = client.post(
        "/v1/polyares-postback",
        json=_payload(event="call", payout="18.00", category="pest"),
    )
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["event"] == "call"

    from aslc.polyares_postback import list_conversions

    rows = list_conversions()
    assert len(rows) == 1
    assert rows[0]["payout"] == "18.00"
    assert rows[0]["event"] == "call"
    assert rows[0]["category"] == "pest"
    assert rows[0]["received_at"]
    assert rows[0]["updated_at"] >= rows[0]["received_at"]


def test_same_lead_different_delivery_ids_stay_separate(client):
    client.post("/v1/polyares-postback", json=_payload(delivery_id="del-a", event="lead"))
    client.post("/v1/polyares-postback", json=_payload(delivery_id="del-b", event="return", payout="0"))

    from aslc.polyares_postback import list_conversions

    rows = list_conversions()
    assert len(rows) == 2
    assert {row["event"] for row in rows} == {"lead", "return"}


def test_lead_id_fallback_is_idempotent(client):
    body = _payload()
    del body["delivery_id"]
    assert client.post("/v1/polyares-postback", json=body).json()["duplicate"] is False
    body["payout"] = "9"
    assert client.get("/v1/polyares-postback", params=body).json()["duplicate"] is True

    from aslc.polyares_postback import list_conversions

    rows = list_conversions()
    assert len(rows) == 1
    assert rows[0]["idem_key"] == "l:lead-1"
    assert rows[0]["payout"] == "9"


def test_missing_secret_accepts_and_warns(client, caplog, monkeypatch):
    monkeypatch.delenv("POLYARE_POSTBACK_SECRET", raising=False)
    monkeypatch.delenv("POLYARES_POSTBACK_SECRET", raising=False)
    caplog.set_level(logging.WARNING, logger="zaptu.polyares")
    response = client.post("/v1/polyares-postback", json=_payload())
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "POLYARE_POSTBACK_SECRET is unset" in caplog.text
    assert "without HMAC" in caplog.text


def test_valid_hmac_accepted_and_secret_is_not_logged(client, caplog, monkeypatch):
    secret = "test-postback-secret"
    monkeypatch.setenv("POLYARE_POSTBACK_SECRET", secret)
    caplog.set_level(logging.INFO, logger="zaptu.polyares")
    fields = _payload()
    response = client.post(
        "/v1/polyares-postback",
        json=fields,
        headers={"X-Polyares-Signature": _sign(secret, fields)},
    )
    assert response.status_code == 200
    assert response.json()["duplicate"] is False
    assert secret not in caplog.text
    assert "POLYARE_POSTBACK_SECRET is unset" not in caplog.text


def test_raw_body_hmac_and_bad_signature(client, monkeypatch):
    secret = "test-postback-secret"
    monkeypatch.setenv("POLYARE_POSTBACK_SECRET", secret)
    raw = json.dumps(_payload()).encode("utf-8")
    good = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    ok = client.post(
        "/v1/polyares-postback",
        content=raw,
        headers={"Content-Type": "application/json", "X-Signature": f"sha256={good}"},
    )
    assert ok.status_code == 200

    bad = client.post(
        "/v1/polyares-postback",
        json=_payload(delivery_id="del-2"),
        headers={"X-Polyares-Signature": "ab" * 32},
    )
    assert bad.status_code == 401
    assert bad.json()["error"] == "invalid_signature"

    missing = client.post("/v1/polyares-postback", json=_payload(delivery_id="del-3"))
    assert missing.status_code == 401

    from aslc.polyares_postback import list_conversions

    assert [row["delivery_id"] for row in list_conversions()] == ["del-1"]


def test_spelled_secret_alias_verifies(client, monkeypatch):
    secret = "alias-postback-secret"
    monkeypatch.delenv("POLYARE_POSTBACK_SECRET", raising=False)
    monkeypatch.setenv("POLYARES_POSTBACK_SECRET", secret)
    fields = _payload()
    response = client.post(
        "/v1/polyares-postback",
        json=fields,
        headers={"X-Polyares-Signature": _sign(secret, fields)},
    )
    assert response.status_code == 200
    unsigned = client.post("/v1/polyares-postback", json=_payload(delivery_id="del-9"))
    assert unsigned.status_code == 401


def test_invalid_event_and_missing_id_are_rejected(client):
    bad_event = client.post("/v1/polyares-postback", json=_payload(event="sale"))
    assert bad_event.status_code == 422
    assert bad_event.json()["error"] == "invalid_request"
    missing = client.post(
        "/v1/polyares-postback",
        json={"event": "lead", "payout": "1", "category": "hvac"},
    )
    assert missing.status_code == 422
    assert "delivery_id or lead_id" in missing.json()["message"]

    from aslc.polyares_postback import list_conversions

    assert list_conversions() == []


def test_form_post_and_blank_secret_counts_as_unset(client, caplog, monkeypatch):
    monkeypatch.setenv("POLYARE_POSTBACK_SECRET", "   ")
    caplog.set_level(logging.WARNING, logger="zaptu.polyares")
    response = client.post("/v1/polyares-postback", data=_payload(event="return", payout="0"))
    assert response.status_code == 200
    assert response.json()["event"] == "return"
    assert "POLYARE_POSTBACK_SECRET is unset" in caplog.text


def test_postgres_upsert_is_idempotent(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler.example:6543/postgres")
    monkeypatch.delenv("POLYARE_POSTBACK_SECRET", raising=False)

    from aslc import polyares_postback as pb

    class FakeCursor:
        def __init__(self, con):
            self.con = con
            self._result = []

        def execute(self, sql, params=None):
            text = " ".join(sql.split())
            self.con.queries.append(text)
            params = params or ()
            if text.startswith(("CREATE TABLE", "CREATE INDEX")):
                self._result = []
            elif text.startswith("SELECT payload FROM polyares_conversions WHERE idem_key"):
                row = self.con.rows.get(params[0])
                self._result = [(row,)] if row else []
            elif text.startswith("INSERT INTO polyares_conversions"):
                assert "ON CONFLICT (idem_key) DO UPDATE" in text
                self.con.rows[params[0]] = params[11]
                self._result = []
            elif text.startswith("SELECT payload FROM polyares_conversions ORDER BY"):
                self._result = [(payload,) for payload in self.con.rows.values()]
            else:
                raise AssertionError(text)

        def fetchone(self):
            return self._result[0] if self._result else None

        def fetchall(self):
            return list(self._result)

    class FakeConn:
        def __init__(self):
            self.rows = {}
            self.queries = []
            self.commits = 0

        def cursor(self):
            return FakeCursor(self)

        def commit(self):
            self.commits += 1

        def close(self):
            pass

    con = FakeConn()
    monkeypatch.setattr(pb, "_pg_connect", lambda: con)
    first = pb.record_postback(_payload(), raw_body=b"", query_string=b"", headers={})
    second = pb.record_postback(
        _payload(event="call", payout="15.00"),
        raw_body=b"",
        query_string=b"",
        headers={},
    )
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    rows = pb.list_conversions()
    assert len(rows) == 1
    assert rows[0]["payout"] == "15.00"
    assert rows[0]["event"] == "call"
    assert any("CREATE TABLE IF NOT EXISTS polyares_conversions" in q for q in con.queries)
    assert all("%s" in q for q in con.queries if q.startswith("INSERT"))
    assert con.commits >= 1


def test_postgres_failure_returns_503(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler.example:6543/postgres")

    from aslc import polyares_postback as pb

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(pb, "_pg_connect", boom)
    response = client.post("/v1/polyares-postback", json=_payload())
    assert response.status_code == 503
    assert response.json()["error"] == "storage_unavailable"


def test_receiver_does_not_forward_or_intake():
    import ast
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "src" / "aslc" / "polyares_postback.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(alias.name for alias in node.names)
    blob = " ".join(imported)
    assert "submit_request" not in blob
    assert "forwarding" not in blob
    assert "service" not in blob.split()
