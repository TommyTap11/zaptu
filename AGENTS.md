# Agent notes

Brand: Zaptu (zaptu.ai). This repo is vertical 1 — the home-services lead router.

- Tools live in `src/aslc/server.py`.
- Shared pipeline is `src/aslc/service.py` — REST, MCP, and any future widget must stay on the same function.
- Add a new trade by extending `ServiceType` and `SUPPORTED_SERVICES`.
- Add a buyer by implementing `Forwarder` in `src/aslc/forwarding.py`.
- Do not tell the end user a specific company is booked. This product sells a lead/call.
- Never drop `consent_to_contact`.
- Do not hold user OAuth tokens in this phase.
- Agent-facing metadata (service catalog, OpenAPI, server cards, mcp.json) lives in `src/aslc/catalog.py`.
  After changing tools or catalog, run `python3 scripts/build_discovery.py` (static copies in `web/`); tests fail on drift.
- Site regeneration: `python3 scripts/build_plumbing_cities.py && python3 scripts/seo.py`. `seo.py` owns the shared
  header nav, footer links (incl. Contact mailto:hello@zaptu.ai), and icon/manifest tags on every page.
- Plumbing returns the call-to-connect number without needing consent (nobody contacts the person); every other
  service still requires `consent_to_contact=true`.
