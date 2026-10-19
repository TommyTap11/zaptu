"""Anonymous visit counter: /v1/hit, /v1/stats, API counting, site script."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"
TOKEN = "test-stats-token"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from aslc import config

    config.settings.data_dir = tmp_path
    config.settings.rate_limit_per_minute = 1000
    config.settings.webhook_url = None
    monkeypatch.delenv("ZAPTU_ANALYTICS_DB", raising=False)
    monkeypatch.setenv("STATS_TOKEN", TOKEN)
    from aslc import server

    with TestClient(server.create_app(host="0.0.0.0")) as c:
        yield c


def stats(client, **kw):
    r = client.get("/v1/stats", headers={"Authorization": f"Bearer {TOKEN}"}, **kw)
    assert r.status_code == 200, r.text
    return r.json()


def beacon(client, body, ua=UA, **headers):
    return client.post("/v1/hit", content=body, headers={"Content-Type": "text/plain", "User-Agent": ua, **headers})


def test_stats_requires_token(client):
    assert client.get("/v1/stats").status_code == 401
    assert client.get("/v1/stats", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_dashboard_stats_requires_correct_pin(client, monkeypatch):
    monkeypatch.setenv("DASHBOARD_PIN", "0000-test-pin")
    # Missing pin.
    assert client.get("/v1/dashboard-stats").status_code == 401
    # Wrong pin.
    assert client.get("/v1/dashboard-stats", headers={"X-Dashboard-Pin": "wrong"}).status_code == 401
    # Right pin returns the same shape as /v1/stats.
    r = client.get("/v1/dashboard-stats", headers={"X-Dashboard-Pin": "0000-test-pin"})
    assert r.status_code == 200, r.text
    assert r.json() == stats(client)
    # Stats token access is unaffected.
    assert client.get("/v1/stats", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200


def test_dashboard_stats_fails_closed_without_server_pin(client, monkeypatch):
    monkeypatch.delenv("DASHBOARD_PIN", raising=False)
    assert client.get("/v1/dashboard-stats", headers={"X-Dashboard-Pin": "anything"}).status_code == 401


def test_dashboard_pin_ok_is_constant_time_env_check(monkeypatch):
    from aslc import analytics

    monkeypatch.setenv("DASHBOARD_PIN", "0000-test-pin")
    assert analytics.dashboard_pin_ok("0000-test-pin")
    assert not analytics.dashboard_pin_ok("0000-test-pi")
    assert not analytics.dashboard_pin_ok("")
    assert not analytics.dashboard_pin_ok(None)
    monkeypatch.delenv("DASHBOARD_PIN", raising=False)
    assert not analytics.dashboard_pin_ok("0000-test-pin")


def test_default_token_is_hash_only(monkeypatch):
    from aslc import analytics

    monkeypatch.delenv("STATS_TOKEN", raising=False)
    assert not analytics.token_ok("wrong")
    assert not analytics.token_ok(None)
    assert len(analytics.DEFAULT_STATS_TOKEN_SHA256) == 64


def test_pageview_counted_with_referrer_and_uniques(client):
    assert beacon(client, '{"e":"pageview","p":"/plumbing/miami-fl/?x=1","r":"https://www.google.com/"}').status_code == 204
    beacon(client, '{"e":"pageview","p":"/","r":"https://chatgpt.com/"}')
    beacon(client, '{"e":"pageview","p":"/","r":"https://www.bing.com/search?q=x"}')
    s = stats(client)
    assert s["totals"]["visits"] == 3
    assert s["per_day"][0]["unique_visitors"] == 1
    refs = {r["name"]: r["count"] for r in s["referrers"]}
    assert refs == {"Google": 1, "ChatGPT": 1, "Bing": 1}
    pages = {r["name"] for r in s["top_pages"]}
    assert "/plumbing/miami-fl/" in pages


def test_bots_dnt_and_junk_filtered(client):
    beacon(client, '{"e":"pageview","p":"/"}', ua="Googlebot/2.1")
    beacon(client, '{"e":"pageview","p":"/"}', ua="")
    beacon(client, '{"e":"pageview","p":"/"}', DNT="1")
    beacon(client, '{"e":"evil","p":"/"}')
    assert beacon(client, "not json").status_code == 204
    s = stats(client)
    assert s["totals"]["visits"] == 1  # only the "not json" default pageview


def test_call_click_counted(client):
    beacon(client, '{"e":"call_click","p":"/plumbing/"}')
    s = stats(client)
    assert s["totals"]["call_clicks"] == 1
    assert s["call_clicks_by_page"][0]["name"] == "/plumbing/"


def test_no_ip_or_user_agent_stored(client, tmp_path):
    beacon(client, '{"e":"pageview","p":"/"}', **{"X-Forwarded-For": "203.0.113.77"})
    raw = (tmp_path / "analytics.sqlite3").read_bytes()
    assert b"203.0.113.77" not in raw and b"iPhone" not in raw
    cols = [r[1] for r in sqlite3.connect(tmp_path / "analytics.sqlite3").execute("PRAGMA table_info(events)")]
    assert "ip" not in cols


def test_api_and_mcp_usage_counted(client):
    client.get("/v1/services")
    client.post("/v1/intake", json={"service_type": "plumbing", "zip_code": "33101", "dry_run": True})
    client.post(
        "/mcp",
        headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_plumbing_call_number", "arguments": {}}},
    )
    api = {r["name"]: r["count"] for r in stats(client)["api_by_endpoint"]}
    assert api["/v1/services"] == 1
    assert api["/v1/intake"] == 1
    assert api["mcp"] == 1
    assert api["mcp_tool:get_plumbing_call_number"] == 1


def test_every_page_loads_counter_script():
    pages = [p for p in WEB.rglob("*.html") if "dashboard" not in p.parts]  # dashboard loads no beacon by design
    assert pages
    for p in pages:
        assert '<script src="/z.js" defer></script>' in p.read_text(encoding="utf-8"), p


def test_counter_script_is_cookieless_beacon():
    js = (WEB / "z.js").read_text(encoding="utf-8")
    assert "sendBeacon" in js and "https://zaptu.onrender.com/v1/hit" in js and "api.zaptu.ai/v1/hit" not in js
    assert 'a[href^="tel:"]' in js
    for bad in ("cookie", "localStorage", "sessionStorage"):
        assert bad not in js


def test_privacy_mentions_anonymous_counting():
    text = (WEB / "privacy" / "index.html").read_text(encoding="utf-8")
    assert "count visits anonymously" in text and "do not store IP addresses" in text


def test_location_unknown_for_private_ip_without_lookup(monkeypatch):
    from aslc import analytics

    analytics._GEO_CACHE.clear()
    monkeypatch.setattr(analytics, "_fetch_geo", lambda ip: (_ for _ in ()).throw(AssertionError("no lookup")))
    assert analytics.lookup_location("10.0.0.5")["country"] == "unknown"
    assert analytics.lookup_location("127.0.0.1")["country"] == "unknown"
    assert analytics.lookup_location("not-an-ip")["country"] == "unknown"
    assert analytics.lookup_location("203.0.113.9")["country"] == "unknown"  # documentation range, not global


def test_location_lookup_failure_is_unknown(monkeypatch):
    from aslc import analytics

    analytics._GEO_CACHE.clear()
    monkeypatch.setattr(analytics, "_fetch_geo", lambda ip: (_ for _ in ()).throw(RuntimeError("down")))
    assert analytics.lookup_location("9.9.9.9") == analytics.UNKNOWN_LOCATION


def test_hit_stores_coarse_location_cached_by_24(client, tmp_path, monkeypatch):
    from aslc import analytics

    analytics._GEO_CACHE.clear()
    calls = []

    def fake_fetch(ip):
        calls.append(ip)
        return {"status": "success", "country": "United States", "regionName": "Florida",
                "city": "Miami", "lat": 25.7617, "lon": -80.1918}

    monkeypatch.setattr(analytics, "_fetch_geo", fake_fetch)
    beacon(client, '{"e":"pageview","p":"/"}', **{"X-Forwarded-For": "8.8.8.8"})
    beacon(client, '{"e":"pageview","p":"/"}', **{"X-Forwarded-For": "8.8.8.99, 10.0.0.1"})  # same /24 -> cache
    assert calls == ["8.8.8.8"]
    s = stats(client)
    assert s["top_locations"] == [{"country": "United States", "region": "Florida", "city": "Miami",
                                   "lat": 25.7617, "lng": -80.1918, "visits": 2}]
    raw = (tmp_path / "analytics.sqlite3").read_bytes()
    assert b"8.8.8" not in raw  # raw IP never stored, only coarse location
    cols = [r[1] for r in sqlite3.connect(tmp_path / "analytics.sqlite3").execute("PRAGMA table_info(events)")]
    for col in ("country", "region", "city", "lat", "lng"):
        assert col in cols


def test_sqlite_old_events_table_is_migrated(tmp_path, monkeypatch):
    db_file = tmp_path / "old.sqlite3"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE events (day TEXT, ts TEXT, kind TEXT, name TEXT, referrer TEXT, visitor TEXT)")
    con.commit(); con.close()
    monkeypatch.setenv("ZAPTU_ANALYTICS_DB", str(db_file))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from aslc import analytics

    analytics._GEO_CACHE.clear()
    assert analytics.record_hit("pageview", "/", "", "10.0.0.1", UA)
    cols = [r[1] for r in sqlite3.connect(db_file).execute("PRAGMA table_info(events)")]
    assert {"country", "region", "city", "lat", "lng"} <= set(cols)
    assert analytics.stats(30)["top_locations"][0]["country"] == "unknown"
