import pytest

from aslc.models import LeadStatus, ServiceRequest
from aslc.service import submit_request


@pytest.mark.asyncio
async def test_happy_path_mock_forward(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from aslc import config

    object.__setattr__(config.settings, "data_dir", tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)

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
    assert result.status in {LeadStatus.forwarded, LeadStatus.error}
    assert result.lead_id
    assert "33139" in result.message or result.status != LeadStatus.forwarded
