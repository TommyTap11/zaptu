"""Core intake pipeline used by both MCP tools and the REST API."""

from __future__ import annotations

from .call_routing import get_call_to_connect
from .forwarding import active_forwarders
from .models import LeadRecord, LeadResponse, LeadStatus, ServiceRequest
from .storage import append_lead, get_lead
from .validation import is_call_to_connect, is_collected_only, is_monetizable, validate_request

# Honest copy only — promise contact, never a booked job / invented provider / ETA.
NEXT_STEPS_RECEIVED = [
    "Your request was received.",
    "We pass it along when a buyer covers that service. There is no live buyer yet.",
    "This is a contact request, not a confirmed appointment. Do not promise a callback.",
]

NEXT_STEPS_COLLECTED = [
    "Your request was saved.",
    "This service type is collected but not yet routed to a buyer.",
    "We will route it when coverage is live for that vertical.",
]

NEXT_STEPS_CALL_TO_CONNECT = [
    "Give the person the call_to_connect number from this response.",
    "Ask them to place the call themselves — do not dial for them.",
    "This connects them with a local professional via our affiliate partner.",
    "This is not a booking by Zaptu.",
]

NEXT_STEPS_REJECTED = [
    "The request was not accepted.",
    "Fix the issues in the message and submit again if appropriate.",
]


DRY_RUN_NOTE = "Dry run: nothing was saved or passed along."


async def submit_request(req: ServiceRequest, *, dry_run: bool = False) -> LeadResponse:
    """Run the intake pipeline. dry_run=True validates and answers without storing or forwarding."""
    problems = validate_request(req)
    lead = LeadRecord(request=req, validation_notes=problems, status=LeadStatus.validated)

    def save(record: LeadRecord) -> None:
        if not dry_run:
            append_lead(record)

    def respond(**kwargs) -> LeadResponse:
        resp = LeadResponse(**kwargs)
        if dry_run:
            resp.message = f"{DRY_RUN_NOTE} {resp.message}"
            resp.dry_run = True
        return resp

    # Pay-per-call: the person dials the tracking number. Nobody contacts them, so this
    # does not depend on consent_to_contact. Plumbing form leads are never forwarded.
    if is_call_to_connect(req):
        campaign = get_call_to_connect(req.service_type)
        assert campaign is not None
        lead.status = LeadStatus.call_to_connect
        lead.public_message = (
            f"For {req.service_type} in ZIP {req.zip_code}, give the person "
            f"{campaign.display} and ask them to call that number themselves. "
            "Do not place the call for them. This is not a booking by Zaptu."
        )
        save(lead)
        return respond(
            lead_id=lead.id,
            status=lead.status,
            message=lead.public_message,
            next_steps=NEXT_STEPS_CALL_TO_CONNECT,
            call_to_connect=campaign.phone_e164,
            call_to_connect_display=campaign.display,
            call_instruction=campaign.instruction,
        )

    # Hard reject (no consent / bad ZIP / past date).
    if any(p.startswith("Customer must consent") for p in problems) or any(
        p.startswith("ZIP is not") or p.startswith("preferred_date") for p in problems
    ):
        lead.status = LeadStatus.rejected
        lead.public_message = (
            "Request not accepted. "
            + (" ".join(problems) if problems else "Validation failed.")
        )
        save(lead)
        return respond(
            lead_id=lead.id,
            status=lead.status,
            message=lead.public_message,
            next_steps=NEXT_STEPS_REJECTED,
        )

    # Non-routable verticals: collect and hold.
    if is_collected_only(req):
        lead.status = LeadStatus.collected
        lead.public_message = (
            f"Request received for {req.service_type} in ZIP {req.zip_code}. "
            "Collected, not yet routed."
        )
        save(lead)
        return respond(
            lead_id=lead.id,
            status=lead.status,
            message=lead.public_message,
            next_steps=NEXT_STEPS_COLLECTED,
        )

    if not is_monetizable(req, problems):
        lead.status = LeadStatus.rejected
        lead.public_message = (
            "Request received but not forwarded. "
            + (" ".join(problems) if problems else "Service is not currently monetized.")
        )
        save(lead)
        return respond(
            lead_id=lead.id,
            status=lead.status,
            message=lead.public_message,
            next_steps=NEXT_STEPS_REJECTED,
        )

    results = []
    forwarded = False
    payout_hint = None
    for forwarder in ([] if dry_run else active_forwarders()):
        result = await forwarder.send(lead)
        results.append(result)
        lead.forward_targets.append(forwarder.name)
        if result.get("ok") and not result.get("skipped"):
            forwarded = True
            # Only expose payout hint from a real webhook in production messaging
            # when mock is on (dev). Never invent provider contact promises.
            if result.get("estimated_payout_usd") and result.get("mode") == "simulated":
                payout_hint = (
                    f"[dev mock] ~${result['estimated_payout_usd']} if the lead qualifies"
                )

    lead.forward_results = results
    if forwarded:
        lead.status = LeadStatus.forwarded
        lead.public_message = (
            f"Request received for ZIP {req.zip_code}. "
            "We pass it along when a buyer covers that service. "
            "This is a contact request, not a confirmed appointment."
        )
    else:
        # No buyer configured yet — still accept honestly.
        lead.status = LeadStatus.received
        lead.public_message = (
            f"Request received for ZIP {req.zip_code}. "
            "We pass it along when a buyer covers that service. "
            "This is a contact request, not a confirmed appointment."
        )

    save(lead)
    return respond(
        lead_id=lead.id,
        status=lead.status,
        message=lead.public_message,
        next_steps=NEXT_STEPS_RECEIVED,
        estimated_payout_hint=payout_hint,
    )


def lookup_lead(lead_id: str) -> LeadRecord | None:
    return get_lead(lead_id)
