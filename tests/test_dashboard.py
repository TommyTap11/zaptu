"""Private analytics dashboard at /dashboard/: gated client-side, unlisted, uncounted."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PAGE = WEB / "dashboard" / "index.html"


def html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_dashboard_page_exists_and_is_private():
    assert PAGE.exists()
    t = html()
    assert '<meta name="robots" content="noindex,nofollow" />' in t
    assert "https://zaptu.ai/dashboard" not in (WEB / "sitemap.xml").read_text(encoding="utf-8")
    assert "/dashboard/" not in (WEB / "sitemap.xml").read_text(encoding="utf-8")
    assert "/dashboard" not in (WEB / "llms.txt").read_text(encoding="utf-8")
    assert "/dashboard" not in (WEB / "llms-full.txt").read_text(encoding="utf-8")


def test_dashboard_not_linked_from_public_pages():
    for p in WEB.rglob("*.html"):
        if "dashboard" in p.parts:
            continue
        assert "/dashboard" not in p.read_text(encoding="utf-8"), p


def test_dashboard_has_no_beacon_or_external_trackers():
    t = html()
    assert "/z.js" not in t
    assert "sendBeacon" not in t
    assert "googletagmanager" not in t and "google-analytics" not in t


def test_dashboard_pin_flow():
    t = html()
    # PIN form/pad: user enters PIN 2025, checked client-side before any fetch.
    assert 'id="dash-pin"' in t
    assert 'id="login-form"' in t
    assert "data-pin-digit" in t and "data-pin-clear" in t
    assert 'var DASHBOARD_PIN = "2025"' in t
    assert "pin !== DASHBOARD_PIN" in t
    assert "dash-key" not in t
    assert "sessionStorage" not in t and "localStorage" not in t
    # After the PIN check, stats are fetched from the identical endpoint with Bearer auth.
    assert "https://zaptu.onrender.com/v1/stats?days=30" in t
    assert re.search(r"Bearer\s+[A-Za-z0-9_\-]{16,}", t), "embedded stats token in fetch"
    # Token is kept only in that fetch logic: exactly one occurrence when present on the box.
    token_file = Path("/home/box/agent-data/shared/zaptu/secrets/stats-token.txt")
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
        assert t.count(token) == 1


def test_dashboard_uses_real_stats_fields_and_honest_labels():
    t = html()
    for field in ("data_since", "totals", "per_day", "unique_visitors", "call_clicks",
                  "top_pages", "referrers", "api_by_endpoint", "call_clicks_by_page"):
        assert field in t, field
    assert "Counts reset when the API redeploys; nightly snapshots are the durable record." in t
    assert "not tracked here yet" in t


def test_seo_script_skips_dashboard():
    seo = (ROOT / "scripts" / "seo.py").read_text(encoding="utf-8")
    assert "dashboard" in seo and "PRIVATE" in seo
