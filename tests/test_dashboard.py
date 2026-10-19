"""Private analytics dashboard at /dashboard/: server-PIN gated, unlisted, uncounted."""

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


def test_dashboard_pin_is_not_hardcoded():
    t = html()
    # The entered PIN is checked by the server: kept only in session storage,
    # sent as the X-Dashboard-Pin header to the dashboard-stats endpoint.
    assert "sessionStorage" in t
    assert "localStorage" not in t
    assert "X-Dashboard-Pin" in t
    assert "/v1/dashboard-stats" in t
    assert "Bearer" not in t
    # No PIN comparison/value baked into the page, and no real credential present.
    assert not re.search(r"(?:pin|PIN)\s*={2,3}\s*['\"][0-9]+", t)
    assert not re.search(r"data-pin-value", t)
    for name in ("stats-token.txt", "stats-token-old-leaked.txt"):
        token_file = Path("/home/box/agent-data/shared/zaptu/secrets") / name
        if token_file.exists():
            assert token_file.read_text(encoding="utf-8").strip() not in t


def test_dashboard_has_clean_pin_entry():
    t = html()
    # One clean, centered PIN input + single submit; no on-screen keypad grid.
    assert t.count('id="dash-pin"') == 1
    assert 'type="password"' in t
    assert 'inputmode="numeric"' in t
    assert "letter-spacing:.35em" in t.replace(" ", "")
    assert '<button type="submit">View dashboard</button>' in t
    assert "keypad" not in t.lower()
    assert "data-digit" not in t
    assert 'data-action="clear"' not in t and 'data-action="back"' not in t
    assert 'id="login-panel"' in t


def test_dashboard_uses_real_stats_fields_and_honest_labels():
    t = html()
    for field in ("data_since", "totals", "per_day", "unique_visitors", "call_clicks",
                  "top_pages", "referrers", "api_by_endpoint", "call_clicks_by_page", "top_locations"):
        assert field in t, field
    assert "Counts are stored in the database and survive API restarts; nightly snapshots are a backup record." in t
    assert "not tracked here yet" in t


def test_seo_script_skips_dashboard():
    seo = (ROOT / "scripts" / "seo.py").read_text(encoding="utf-8")
    assert "dashboard" in seo and "PRIVATE" in seo


def test_dashboard_has_location_map_and_list():
    t = html()
    assert 'id="top-locations"' in t and 'id="map"' in t
    assert "Visits by place" in t
    assert "Locations are approximate, from IP address, city-level only." in t
    # Leaflet/OpenStreetMap is loaded dynamically only after PIN login succeeds
    # (renderMap is called from render(), which runs only on a 200 stats reply).
    assert "loadLeaflet" in t and "leaflet@1.9.4" in t and "tile.openstreetmap.org" in t
    assert '<link rel="stylesheet" href="https://unpkg.com' not in t
    assert '<script src="https://unpkg.com' not in t
