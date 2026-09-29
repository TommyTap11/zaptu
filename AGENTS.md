# Agent notes

Brand: Zaptu (zaptu.ai). This repo is vertical 1 — the home-services lead router.

- Tools live in `src/aslc/server.py`.
- Shared pipeline is `src/aslc/service.py` — REST, MCP, and any future widget must stay on the same function.
- Add a new trade by extending `ServiceType` and `SUPPORTED_SERVICES`.
- Add a buyer by implementing `Forwarder` in `src/aslc/forwarding.py`.
- Do not tell the end user a specific company is booked. This product sells a lead/call.
- Never drop `consent_to_contact`.
- Do not hold user OAuth tokens in this phase.
