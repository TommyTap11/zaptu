"""Shared request / response models."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


ServiceType = Literal[
    "house_cleaning",
    "deep_cleaning",
    "move_in_out_cleaning",
    "recurring_cleaning",
    "pest_control",
    "plumbing",
    "hvac",
]

Frequency = Literal["one_time", "weekly", "biweekly", "monthly"]
HomeType = Literal["apartment", "condo", "townhouse", "single_family", "other"]


class ServiceRequest(BaseModel):
    """A structured home-service request from an AI agent."""

    service_type: ServiceType = Field(
        description="Kind of service the customer needs."
    )
    zip_code: Annotated[
        str,
        Field(description="US 5-digit ZIP code where the work will happen."),
    ]
    city: str | None = Field(default=None, description="City name, if known.")
    state: str | None = Field(
        default=None, description="Two-letter US state code, if known."
    )
    address_line: str | None = Field(
        default=None,
        description="Street address. Optional at intake; required by some buyers later.",
    )
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    bathrooms: float | None = Field(default=None, ge=0, le=20)
    square_feet: int | None = Field(default=None, ge=100, le=50000)
    home_type: HomeType | None = None
    frequency: Frequency = "one_time"
    preferred_date: date | None = Field(
        default=None, description="Preferred service date (YYYY-MM-DD)."
    )
    flexible_dates: bool = True
    notes: str | None = Field(default=None, max_length=2000)

    customer_name: str = Field(min_length=2, max_length=120)
    customer_phone: str = Field(
        description="US phone number. Digits, dashes, or +1 are accepted."
    )
    customer_email: str | None = None
    consent_to_contact: bool = Field(
        description="True if the customer consented to be called or texted about this request (TCPA)."
    )

    source_agent: str | None = Field(
        default=None, description="Agent or product that originated the request, e.g. muse."
    )

    @field_validator("zip_code")
    @classmethod
    def normalize_zip(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 5:
            raise ValueError("zip_code must be a 5-digit US ZIP")
        return digits[:5]

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 2:
            raise ValueError("state must be a 2-letter US code")
        return cleaned

    @field_validator("customer_phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits.startswith("1") and len(digits) == 11:
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("customer_phone must be a 10-digit US number")
        return f"+1{digits}"


class LeadStatus(str, Enum):
    received = "received"
    validated = "validated"
    forwarded = "forwarded"
    rejected = "rejected"
    error = "error"


class LeadRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: LeadStatus = LeadStatus.received
    request: ServiceRequest
    validation_notes: list[str] = Field(default_factory=list)
    forward_targets: list[str] = Field(default_factory=list)
    forward_results: list[dict] = Field(default_factory=list)
    public_message: str = ""


class LeadResponse(BaseModel):
    lead_id: str
    status: LeadStatus
    message: str
    next_steps: list[str]
    estimated_payout_hint: str | None = None
