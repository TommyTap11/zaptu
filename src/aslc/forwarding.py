"""Pluggable lead destinations.

MVP ships two adapters:
  - webhook: POST the structured lead to LEAD_WEBHOOK_URL (Zapier, Make, or a network)
  - mock: simulate a pay-per-call / ping-post network so the product works before contracts

Add a real ping/post client (eLocal, Service Direct Earn API, Phonexa) here later.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from .config import settings
from .models import LeadRecord


class Forwarder(Protocol):
    name: str

    async def send(self, lead: LeadRecord) -> dict: ...


class WebhookForwarder:
    name = "webhook"

    async def send(self, lead: LeadRecord) -> dict:
        if not settings.webhook_url:
            return {"target": self.name, "ok": False, "skipped": True, "reason": "LEAD_WEBHOOK_URL not set"}
        headers = {"Content-Type": "application/json"}
        if settings.webhook_token:
            headers["Authorization"] = f"Bearer {settings.webhook_token}"
        payload = {
            "lead_id": lead.id,
            "created_at": lead.created_at.isoformat(),
            "service_type": lead.request.service_type,
            "zip_code": lead.request.zip_code,
            "city": lead.request.city,
            "state": lead.request.state,
            "customer_name": lead.request.customer_name,
            "customer_phone": lead.request.customer_phone,
            "customer_email": lead.request.customer_email,
            "bedrooms": lead.request.bedrooms,
            "bathrooms": lead.request.bathrooms,
            "square_feet": lead.request.square_feet,
            "home_type": lead.request.home_type,
            "frequency": lead.request.frequency,
            "preferred_date": (
                lead.request.preferred_date.isoformat()
                if lead.request.preferred_date
                else None
            ),
            "notes": lead.request.notes,
            "consent_to_contact": lead.request.consent_to_contact,
            "source_agent": lead.request.source_agent,
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(settings.webhook_url, json=payload, headers=headers)
            return {
                "target": self.name,
                "ok": response.is_success,
                "status_code": response.status_code,
                "body": response.text[:500],
            }
        except httpx.HTTPError as exc:
            return {"target": self.name, "ok": False, "error": str(exc)}


class MockNetworkForwarder:
    """Stands in for a pay-per-call / ping-post buyer until a contract is live."""

    name = "mock_network"

    async def send(self, lead: LeadRecord) -> dict:
        if not settings.mock_forwarding:
            return {"target": self.name, "ok": False, "skipped": True}
        payout = {
            "house_cleaning": 18,
            "deep_cleaning": 22,
            "move_in_out_cleaning": 24,
            "recurring_cleaning": 20,
            "pest_control": 35,
        }.get(lead.request.service_type, 0)
        accepted = payout > 0
        return {
            "target": self.name,
            "ok": accepted,
            "accepted": accepted,
            "estimated_payout_usd": payout,
            "mode": "simulated",
            "note": "Replace with a live network ping/post when an affiliate account is approved.",
        }


def active_forwarders() -> list[Forwarder]:
    forwarders: list[Forwarder] = [MockNetworkForwarder(), WebhookForwarder()]
    return forwarders
