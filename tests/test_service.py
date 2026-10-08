import json
from io import StringIO

import pytest

from aslc.models import LeadStatus, ServiceRequest
from aslc.service import submit_request
from aslc.storage import mask_phone


def _reload_settings(monkeypatch, tmp_path, **env):
    monkeypatch.setenv("ZAPTU_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))
    # Rebuild settings object fields used at runtime
    from aslc import config

    config.settings.data_dir = tmp_path
    config.settings.mock_forwarding = (
        str(env.get("ZAPTU_MOCK_FORWARDER", "0")).lower() in {"1", "true", "yes", "on"}
        or str(env.get("MOCK_FORWARDING", "false")).lower() in {"1", "true", "yes", "on"}
    )
    config.settings.webhook_url = env.get("LEAD_WEBHOOK_URL") or None
    tmp_path.mkdir(parents=True, exist_ok=True)


@pytest.mark.asyncio
async def test_no_buyer_honest_received(tmp_path, monkeypatch):
    _reload_settings(
        monkeypatch,
        tmp_path,
        ZAPTU_MOCK_FORWARDER="0",
        MOCK_FORWARDING="false",
        LEAD_WEBHOOK_URL=None,
    )
    req = ServiceRequest(
        service_type="house_cleaning",
        zip_code="33139",
        customer_name="Tom C",
        customer_phone="3055550100",
        consent_to_contact=True,
        bedrooms=2,
        source_agent="pytest",
    )
    result = await submit_request(req)
    assert result.status == LeadStatus.received
    assert result.lead_id
    assert "pass it along" in result.message.lower() or "received" in result.message.lower()
    assert "provider should contact" not in result.message.lower()
    assert result.estimated_payout_hint is None
    for step in result.next_steps:
        assert "15–30" not in step
        assert "provider will" not in step.lower() or "may contact" in step.lower()


@pytest.mark.asyncio
async def test_mock_forward_only_when_flag(tmp_path, monkeypatch):
    _reload_settings(monkeypatch, tmp_path, ZAPTU_MOCK_FORWARDER="1")
    req = ServiceRequest(
        service_type="house_cleaning",
        zip_code="33139",
        customer_name="Tom C",
        customer_phone="3055550100",
        consent_to_contact=True,
        bedrooms=2,
        source_agent="pytest",
    )
    result = await submit_request(req)
    assert result.status == LeadStatus.forwarded
    assert result.estimated_payout_hint is not None
    assert "mock" in result.estimated_payout_hint.lower()


@pytest.mark.asyncio
async def test_handyman_collected(tmp_path, monkeypatch):
    _reload_settings(monkeypatch, tmp_path, ZAPTU_MOCK_FORWARDER="0")
    req = ServiceRequest(
        service_type="handyman",
        zip_code="33139",
        customer_name="Tom C",
        customer_phone="3055550100",
        consent_to_contact=True,
        source_agent="pytest",
    )
    result = await submit_request(req)
    assert result.status == LeadStatus.collected
    assert "not yet routed" in result.message.lower()


@pytest.mark.asyncio
async def test_no_consent_rejected(tmp_path, monkeypatch):
    _reload_settings(monkeypatch, tmp_path)
    req = ServiceRequest(
        service_type="house_cleaning",
        zip_code="33139",
        customer_name="Tom C",
        customer_phone="3055550100",
        consent_to_contact=False,
        bedrooms=2,
    )
    result = await submit_request(req)
    assert result.status == LeadStatus.rejected


@pytest.mark.asyncio
async def test_stdout_lead_log_masks_phone(tmp_path, monkeypatch, capsys):
    _reload_settings(monkeypatch, tmp_path, ZAPTU_MOCK_FORWARDER="0")
    req = ServiceRequest(
        service_type="pest_control",
        zip_code="33139",
        customer_name="Tom C",
        customer_phone="3055550199",
        consent_to_contact=True,
        source_agent="pytest",
    )
    result = await submit_request(req)
    captured = capsys.readouterr().out
    assert result.lead_id
    assert "3055550199" not in captured
    assert "+13055550199" not in captured
    # At least one structured event line
    lines = [ln for ln in captured.splitlines() if ln.startswith("{")]
    assert lines
    event = json.loads(lines[-1])
    assert event["event"] == "lead_accepted"
    assert event["phone_masked"].endswith("0199")
    assert "*" in event["phone_masked"]


def test_mask_phone():
    assert mask_phone("+13055550100").endswith("0100")
    assert "555" not in mask_phone("+13055550100") or "*" in mask_phone("+13055550100")


@pytest.mark.asyncio
async def test_plumbing_call_to_connect(tmp_path, monkeypatch):
    _reload_settings(monkeypatch, tmp_path, ZAPTU_MOCK_FORWARDER="0", LEAD_WEBHOOK_URL=None)
    req = ServiceRequest(
        service_type="plumbing",
        zip_code="33139",
        customer_name="Tom C",
        customer_phone="3055550100",
        consent_to_contact=True,
        source_agent="pytest",
        notes="clogged drain",
    )
    result = await submit_request(req)
    assert result.status == LeadStatus.call_to_connect
    assert result.call_to_connect == "+13085299543"
    assert result.call_to_connect_display == "(308) 529-9543"
    assert result.call_instruction
    assert "do not" in result.call_instruction.lower()
    assert "dial" in result.call_instruction.lower() or "place the call" in result.call_instruction.lower()
    assert "(308) 529-9543" in result.message
    assert "not a booking" in result.message.lower()
    # Must not look like a form forward
    assert result.estimated_payout_hint is None
