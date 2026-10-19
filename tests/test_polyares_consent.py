"""Polyares consent disclosure + consent-record storage (non-plumbing only)."""
from __future__ import annotations

from pathlib import Path

import pytest

from aslc import catalog
from aslc.models import CONSENT_WORDING_VERSION, LeadStatus, ServiceRequest
from aslc.service import lookup_lead, submit_request

WEB = Path(__file__).resolve().parents[1] / "web"
POLYARES_TEXT = "Polyares and its service-provider partners"


def form_pages():
    return [p for p in WEB.rglob("index.html") if 'id="request"' in p.read_text(encoding="utf-8")]


def test_all_request_forms_name_polyares_and_stamp_source():
    pages = form_pages()
    assert len(pages) >= 10
    for p in pages:
        t = p.read_text(encoding="utf-8")
        assert POLYARES_TEXT in t, p
        assert "share my details with Polyares" in t, p
        assert "data.consent_source_page = location.pathname" in t, p


def test_plumbing_pages_unchanged_no_polyares():
    for p in (WEB / "plumbing").rglob("*.html"):
        assert "Polyares" not in p.read_text(encoding="utf-8"), p


def test_privacy_names_polyares_for_non_plumbing():
    t = (WEB / "privacy" / "index.html").read_text(encoding="utf-8")
    assert "For non-plumbing services, we share those details with Polyares" in t
    # Plumbing paragraph unchanged in substance
    assert "dialing the tracking number connects you through our affiliate partner" in t


def test_catalog_and_agent_rules_disclose_polyares():
    rules = " ".join(catalog.AGENT_RULES)
    assert POLYARES_TEXT in rules
    cat = catalog.services_catalog()
    assert all(POLYARES_TEXT in s["note"] for s in cat["collecting"])
    assert "Polyares" not in str(cat["live"])


def _settings(tmp_path, monkeypatch):
    monkeypatch.setenv("ZAPTU_DATA_DIR", str(tmp_path))
    from aslc import config
    config.settings.data_dir = tmp_path
    config.settings.mock_forwarding = False
    config.settings.webhook_url = None


@pytest.mark.asyncio
async def test_consent_record_stored_with_lead(tmp_path, monkeypatch):
    _settings(tmp_path, monkeypatch)
    req = ServiceRequest(
        service_type="pest_control", zip_code="85001", customer_name="Jamie Example",
        customer_phone="3055550100", consent_to_contact=True,
        source_agent="web", consent_source_page="/pest-control/phoenix-az/",
    )
    result = await submit_request(req)
    assert result.lead_id
    lead = lookup_lead(result.lead_id)
    assert lead is not None
    assert lead.consent_timestamp == lead.created_at
    assert lead.consent_wording_version == CONSENT_WORDING_VERSION
    assert lead.consent_source_page == "/pest-control/phoenix-az/"


@pytest.mark.asyncio
async def test_consent_record_falls_back_to_source_agent(tmp_path, monkeypatch):
    _settings(tmp_path, monkeypatch)
    req = ServiceRequest(
        service_type="garage_door", zip_code="85001", customer_name="Jamie Example",
        customer_phone="3055550100", consent_to_contact=True, source_agent="mcp",
    )
    result = await submit_request(req)
    lead = lookup_lead(result.lead_id)
    assert lead.consent_source_page == "mcp"
    assert lead.consent_timestamp is not None


@pytest.mark.asyncio
async def test_plumbing_lead_has_no_consent_record(tmp_path, monkeypatch):
    _settings(tmp_path, monkeypatch)
    req = ServiceRequest(
        service_type="plumbing", zip_code="85001", customer_name="Jamie Example",
        customer_phone="3055550100", consent_to_contact=True, source_agent="web",
        consent_source_page="/plumbing/phoenix-az/",
    )
    result = await submit_request(req)
    assert result.status == LeadStatus.call_to_connect
    lead = lookup_lead(result.lead_id)
    assert lead.consent_timestamp is None
    assert lead.consent_wording_version is None
    assert lead.consent_source_page is None


@pytest.mark.asyncio
async def test_no_consent_lead_has_no_consent_record(tmp_path, monkeypatch):
    _settings(tmp_path, monkeypatch)
    req = ServiceRequest(
        service_type="pest_control", zip_code="85001", customer_name="Jamie Example",
        customer_phone="3055550100", consent_to_contact=False, source_agent="web",
    )
    result = await submit_request(req)
    assert result.status == LeadStatus.rejected
    lead = lookup_lead(result.lead_id)
    assert lead.consent_timestamp is None
