"""Qualify a service request before it is forwarded as a paid lead."""

from __future__ import annotations

from datetime import date

from .config import settings
from .models import ServiceRequest

# Cleaning-focused MVP coverage. Expand later with buyer zip files.
SUPPORTED_SERVICES = {
    "house_cleaning",
    "deep_cleaning",
    "move_in_out_cleaning",
    "recurring_cleaning",
    "pest_control",
}

# Stub: treat these as "thin" markets where mock buyer declines.
THIN_ZIPS = {"00000", "99999"}


def validate_request(req: ServiceRequest) -> list[str]:
    """Return human-readable problems. Empty list means the lead is forwardable."""
    problems: list[str] = []

    if settings.require_consent and not req.consent_to_contact:
        problems.append(
            "Customer must consent to being contacted about this request (TCPA)."
        )

    if req.service_type not in SUPPORTED_SERVICES:
        problems.append(
            f"{req.service_type} is accepted as a request but not yet monetized. "
            "It will be logged only."
        )

    if req.zip_code in THIN_ZIPS:
        problems.append("ZIP is not in a covered buyer market.")

    if req.preferred_date and req.preferred_date < date.today():
        problems.append("preferred_date is in the past.")

    if req.service_type.endswith("cleaning"):
        if req.bedrooms is None and req.square_feet is None:
            problems.append(
                "Cleaning leads convert better with bedrooms or square_feet. "
                "Add at least one if the customer knows it."
            )

    return problems


def is_monetizable(req: ServiceRequest, problems: list[str]) -> bool:
    hard_blocks = [
        p
        for p in problems
        if p.startswith("Customer must consent")
        or p.startswith("ZIP is not")
        or p.startswith("preferred_date")
    ]
    if hard_blocks:
        return False
    return req.service_type in SUPPORTED_SERVICES
