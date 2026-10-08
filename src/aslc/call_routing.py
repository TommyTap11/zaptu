"""Call-to-connect routing for pay-per-call affiliate campaigns.

Plumbing (and later other trades) return a tracking number the *consumer*
must dial. AI agents and Zaptu must never place the call.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CallToConnectCampaign:
    service_type: str
    phone_e164: str
    display: str
    tel_href: str
    network: str
    campaign_id: str
    instruction: str


# The Client Connector plumbing campaign.
# Exclusive to Client Connector. Consumer-initiated live inbound calls only.
_AGENT_INSTRUCTION = (
    "Give the person this phone number and ask them to place the call themselves. "
    "Do not dial, autodial, transfer, or place the call on their behalf. "
    "This must be a live inbound call from the consumer."
)

CALL_TO_CONNECT: dict[str, CallToConnectCampaign] = {
    "plumbing": CallToConnectCampaign(
        service_type="plumbing",
        phone_e164="+13085299543",
        display="(308) 529-9543",
        tel_href="tel:+13085299543",
        network="the_client_connector",
        campaign_id="11864",
        instruction=_AGENT_INSTRUCTION,
    ),
}


def get_call_to_connect(service_type: str) -> CallToConnectCampaign | None:
    return CALL_TO_CONNECT.get(service_type)


def is_call_to_connect_service(service_type: str) -> bool:
    return service_type in CALL_TO_CONNECT
