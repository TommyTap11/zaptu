"""Core intake pipeline used by both MCP tools and the REST API."""

from __future__ import annotations

from .forwarding import active_forwarders
from .models import LeadRecord, LeadResponse, LeadStatus, ServiceRequest
from .storage import append_lead, get_lead
from .validation import is_monetizable, validate_request


NEXT_STEPS_OK = [
    "A local provider (or the affiliate network) will attempt to contact the customer.",
    "Keep the phone nearby for the next 15–30 minutes during business hours.",
    "If nobody calls, the customer can retry or ask the agent to submit again with more detail.",
]

NEXT_STEPS_HELD = [
    "The request was saved but not sold as a live lead.",
    "Fix the validation notes and resubmit, or wait until that service type is enabled.",
]


async def submit_request(req: ServiceRequest) -> LeadResponse:
    problems = validate_request(req)
    lead = LeadRecord(request=req, validation_notes=problems, status=LeadStatus.validated)

    if not is_monetizable(req, problems):
        lead.status = LeadStatus.rejected
        lead.public_message = (
            "Request received but not forwarded. "
            + (" ".join(problems) if problems else "Service is not currently monetized.")
        )
        append_lead(lead)
        return LeadResponse(
            lead_id=lead.id,
            status=lead.status,
            message=lead.public_message,
            next_steps=NEXT_STEPS_HELD,
        )

    results = []
    forwarded = False
    payout_hint = None
    for forwarder in active_forwarders():
        result = await forwarder.send(lead)
        results.append(result)
        lead.forward_targets.append(forwarder.name)
        if result.get("ok") and not result.get("skipped"):
            forwarded = True
            if result.get("estimated_payout_usd"):
                payout_hint = f"~${result['estimated_payout_usd']} if the call/lead qualifies"

    lead.forward_results = results
    lead.status = LeadStatus.forwarded if forwarded else LeadStatus.error
    if forwarded:
        lead.public_message = (
            f"Cleaning/home-service request submitted for ZIP {req.zip_code}. "
            "A provider should contact the customer shortly."
        )
    else:
        lead.public_message = (
            "Request validated but no live buyer accepted it. It has been logged for retry."
        )

    append_lead(lead)
    return LeadResponse(
        lead_id=lead.id,
        status=lead.status,
        message=lead.public_message,
        next_steps=NEXT_STEPS_OK if forwarded else NEXT_STEPS_HELD,
        estimated_payout_hint=payout_hint,
    )


def lookup_lead(lead_id: str) -> LeadRecord | None:
    return get_lead(lead_id)
