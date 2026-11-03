"""Dashboard v2: Polyares sales numbers file, call-number split, data-center tagging, private headers."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PAGE = WEB / "dashboard" / "index.html"
DATA = WEB / "dashboard" / "polyares.json"

spec = importlib.util.spec_from_file_location("polyares_numbers", ROOT / "scripts" / "polyares_numbers.py")
pn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pn)


def html() -> str:
    return PAGE.read_text(encoding="utf-8")


def good() -> dict:
    return {
        "source": "Entered by hand from the Polyares portal.",
        "as_of": "2026-11-03T09:20:00-05:00",
        "sold_forms": 0, "sold_calls": 0, "revenue_usd": 0.0, "leads": [],
        "call_numbers": [{"service": "Plumbing", "number": "855-360-1813", "status": "Live", "pages": 66}],
    }


def test_committed_polyares_file_is_valid_and_matches_portal():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert pn.validate(data) == []
    # Portal on Nov 3: 0 sold forms, 0 sold calls, $0.00. No invented numbers.
    assert (data["sold_forms"], data["sold_calls"], data["revenue_usd"]) == (0, 0, 0)
    assert "Polyares portal" in data["source"] and "Not fetched automatically" in data["source"]
    nums = {n["service"]: n["number"] for n in data["call_numbers"]}
    assert nums == {"Plumbing": "855-360-1813", "Pest control": "855-341-9295"}


def test_polyares_file_carries_no_consumer_details():
    raw = DATA.read_text(encoding="utf-8").lower()
    for word in ("email", "phone_number", "first_name", "last_name", "address", "@"):
        assert word not in raw, word


@pytest.mark.parametrize("change, msg", [
    ({"sold_forms": -1}, "sold_forms"),
    ({"sold_calls": 1.5}, "sold_calls"),
    ({"sold_forms": True}, "sold_forms"),
    ({"revenue_usd": -5}, "revenue_usd"),
    ({"as_of": "yesterday"}, "as_of"),
    ({"as_of": "2026-11-03T09:20:00"}, "UTC offset"),
    ({"source": ""}, "source"),
    ({"leads": [{"date": "2026-11-04", "kind": "form", "service": "Plumbing", "city": "Miami, FL", "payout_usd": 30, "email": "x"}]}, "no consumer details"),
    ({"leads": [{"date": "2026-11-04", "kind": "visit", "payout_usd": 30}]}, "kind"),
    ({"leads": [{"date": "2026-11-04", "kind": "call", "payout_usd": 30}]}, "more lead rows"),
])
def test_validate_rejects_bad_data(change, msg):
    data = good()
    data.update(change)
    errors = pn.validate(data)
    assert any(msg in e for e in errors), errors


def test_set_numbers_and_status_round_trip(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps(good()), encoding="utf-8")
    data = pn.set_numbers(pn.load(path), 2, 1, 87.5, "2026-11-05T09:00:00-05:00")
    data["leads"] = [{"date": "2026-11-05", "kind": "call", "service": "Plumbing", "city": "Miami, FL", "payout_usd": 45}]
    data = pn.set_number_status(data, "plumbing", "Paused")
    pn.save(data, path)
    back = pn.load(path)
    assert (back["sold_forms"], back["sold_calls"], back["revenue_usd"]) == (2, 1, 87.5)
    assert back["call_numbers"][0]["status"] == "Paused"
    with pytest.raises(ValueError):
        pn.set_number_status(back, "roofing", "Live")
    back["sold_forms"] = -3
    with pytest.raises(ValueError):
        pn.save(back, path)


def test_dashboard_reads_polyares_file_with_honest_labels():
    t = html()
    assert '"/dashboard/polyares.json"' in t
    for field in ("sold_forms", "sold_calls", "revenue_usd", "as_of", "call_numbers", "leads"):
        assert field in t, field
    assert "not fetched automatically" in t
    assert "No sold leads yet." in t
    # Polyares file is fetched only inside load(), i.e. after a PIN check against the stats API.
    assert t.index(": fetchPolyares();") > t.index("function load(")


def test_dashboard_splits_call_clicks_by_service():
    t = html()
    assert "function callSplit" in t
    assert 'indexOf("/plumbing/") === 0' in t and 'indexOf("/pest-control/") === 0' in t
    assert '"Plumbing " + split.plumbing + " · Pest " + split.pest' in t


def test_dashboard_tags_data_center_towns_and_test_pages():
    t = html()
    assert '"Ashburn|Virginia"' in t and '"Council Bluffs|Iowa"' in t
    assert 'id="hide-dc"' in t and "data center" in t
    assert '"/__zaptu-test/"' in t and "our test" in t


def test_dashboard_has_no_stale_buyer_references():
    t = html().lower()
    assert "client connector" not in t and "tcc" not in t
    assert "308-529-9543" not in t and "3085299543" not in t


def test_dashboard_tables_scroll_on_mobile():
    t = html()
    assert ".scroll{overflow-x:auto" in t
    assert "@media(max-width:420px){.stat-grid{grid-template-columns:1fr}}" in t


def test_dashboard_private_headers():
    headers = (WEB / "_headers").read_text(encoding="utf-8")
    block = headers.split("/dashboard/*", 1)[1].split("\n\n", 1)[0]
    assert "X-Robots-Tag: noindex, nofollow" in block
    assert "Cache-Control: no-store" in block
    assert "dashboard" not in (WEB / "robots.txt").read_text(encoding="utf-8")
