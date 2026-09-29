# Affiliate / pay-per-call networks

Do not build a provider marketplace first. Sell the call or form lead into networks that already buy house cleaning and pest control.

## First networks to apply to

| Network | Why | Typical cleaning payout (public listings, 2026) |
|---|---|---|
| eLocal | Form leads + live calls, ping/post API | ~$15 / lead or duration-based call |
| Service Direct Earn API | Ping/post into thousands of local buyers | Varies by ZIP / trade |
| The Client Connector | Home-services RTB across 20+ networks | 50–90% of buyer bid |
| UpN3xt | Cleaning-specific pay-per-call | ~$15 / qualified call |
| Lead Smart | Nationwide cleaning calls | $2–$30 listed range |
| Exclusive Live Calls | Higher payout, stricter traffic rules | listed up to $54 CPA on some cleaning offers |

Google Ads / LSA cleaning CPL sits roughly **$28–$70**. Affiliate payouts in the **$15–$25** range are realistic for a qualified inbound call. Your margin is payout minus whatever it costs to originate the agent request (near zero if Muse users bring the demand).

## Traffic rules you will be asked to meet

- US callers only
- Homeowner / tenant / property manager
- Minimum talk time often **60–90 seconds**
- No incentivized or shared leads
- TCPA consent on file
- Often: search / high-intent only (some networks reject Facebook Marketplace)

Agent-originated demand is new to these networks. Expect a manual review. Frame it as “consumer asked their assistant to find a cleaner, assistant collected consent and phone, we connect the live call.”

## How this repo talks to a network

Today:

1. `MockNetworkForwarder` always “accepts” monetized services so the MCP demo works.
2. `WebhookForwarder` POSTs the structured lead to `LEAD_WEBHOOK_URL` (Zapier, Make, Ringba inbound webhook, or your own script).

Next adapter to write: a ping/post client.

Typical ping/post shape:

```
POST /ping  { zip, category, phone_sha?, trusted_form? }
← { bid_id, payout, accept }
POST /post  { bid_id, full PII, consent timestamp }
← { status, lead_id }
```

Implement that in `src/aslc/forwarding.py` as `PingPostForwarder` once you have credentials. Keep the webhook as a fallback.

## Compliance

Store `consent_to_contact=true`, timestamp (`created_at`), source agent, and the raw request. Do not submit without consent. Do not text using this pipeline until you have a separate 10DLC / A2P path.
