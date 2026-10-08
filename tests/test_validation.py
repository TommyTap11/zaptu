from datetime import date, timedelta

import pytest

from aslc.models import ServiceRequest
from aslc.validation import is_collected_only, is_monetizable, validate_request


def _base(**overrides):
    data = dict(
        service_type="house_cleaning",
        zip_code="33101",
        customer_name="Ada Lovelace",
        customer_phone="305-555-0199",
        consent_to_contact=True,
        bedrooms=3,
    )
    data.update(overrides)
    return ServiceRequest.model_validate(data)


def test_phone_and_zip_normalize():
    req = _base(customer_phone="(305) 555-0199", zip_code="33101-1234")
    assert req.customer_phone == "+13055550199"
    assert req.zip_code == "33101"


def test_bad_phone_rejected():
    with pytest.raises(Exception):
        _base(customer_phone="555")


def test_invalid_us_area_code_rejected():
    with pytest.raises(Exception):
        _base(customer_phone="0055550199")


def test_consent_is_required():
    req = _base(consent_to_contact=False)
    problems = validate_request(req)
    assert any("consent" in p.lower() for p in problems)
    assert not is_monetizable(req, problems)


def test_consent_yes_string_coerced():
    req = _base(consent_to_contact="yes")
    assert req.consent_to_contact is True


def test_past_date_blocked():
    req = _base(preferred_date=date.today() - timedelta(days=2))
    problems = validate_request(req)
    assert any("past" in p for p in problems)
    assert not is_monetizable(req, problems)


def test_cleaning_without_size_is_warning_not_block():
    req = _base(bedrooms=None, square_feet=None)
    problems = validate_request(req)
    assert problems
    assert is_monetizable(req, problems)


def test_plumbing_collected_not_monetized():
    req = _base(service_type="plumbing")
    problems = validate_request(req)
    assert not is_monetizable(req, problems)
    assert is_collected_only(req)


def test_handyman_and_other_accepted():
    for st in ("handyman", "other"):
        req = _base(service_type=st)
        assert is_collected_only(req)
        assert not is_monetizable(req, validate_request(req))
