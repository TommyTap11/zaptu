"""Qualify a service request before it is forwarded as a paid lead."""

from __future__ import annotations

from datetime import date

from . import config
from .models import ServiceRequest

# Verticals we currently try to route to a buyer.
ROUTABLE_SERVICES = {
    "house_cleaning",
    "deep_cleaning",
    "move_in_out_cleaning",
    "recurring_cleaning",
    "pest_control",
}

# Accepted by the form / MCP but held until a buyer exists.
COLLECTED_ONLY_SERVICES = {
    "plumbing",
    "hvac",
    "handyman",
    "other",
}

# Back-compat alias used by /health and list_supported_services.
SUPPORTED_SERVICES = ROUTABLE_SERVICES

# Stub: treat these as "thin" markets where buyers decline.
THIN_ZIPS = {"00000", "99999"}


def validate_request(req: ServiceRequest) -> list[str]:
    """Return human-readable problems. Empty-ish list means the lead can proceed."""
    problems: list[str] = []

    if config.settings.require_consent and not req.consent_to_contact:
        problems.append(
            "Customer must consent to being contacted about this request (TCPA)."
        )

    if req.service_type in COLLECTED_ONLY_SERVICES:
        problems.append(
            f"{req.service_type} is collected, not yet routed. "
            "It will be held until a buyer covers that vertical."
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
    return req.service_type in ROUTABLE_SERVICES


def is_collected_only(req: ServiceRequest) -> bool:
    return req.service_type in COLLECTED_ONLY_SERVICES
