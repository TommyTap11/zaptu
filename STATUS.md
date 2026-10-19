# Zaptu status

Last updated: 2026-10-19 (America/New_York)

## Dashboard access (2026-10-19)
- Private dashboard stays at https://zaptu.ai/dashboard/ (noindex, not in sitemap, not linked publicly, no visit beacon on that page).
- Access is now checked on the server: the page asks the user to type a PIN in a single clean sign-in input (no on-screen keypad) and sends it as the `X-Dashboard-Pin` header to `GET /v1/dashboard-stats` on the API.
- The server compares that header in constant time against the `DASHBOARD_PIN` environment variable (set only in Render; fail-closed when unset). The PIN value and the stats token are not in this repo, the dashboard page, or this file.
- `GET /v1/stats` with the existing stats token is unchanged and still works alongside the new endpoint.
- Visit/lead counts are stored in Postgres (`DATABASE_URL`), so they survive API restarts/redeploys; nightly snapshots remain a backup record.
- Visitor location (2026-10-19): on /v1/hit the IP (first X-Forwarded-For) is used transiently for a free ip-api.com city-level lookup (1.5s timeout, fail-silent, cached by /24, private/local -> unknown); only country/region/city + approx lat/lng are stored (events columns, migration-safe ALTER for Postgres + SQLite; raw IP never stored). Stats (`/v1/stats`, `/v1/dashboard-stats`) add `top_locations`; the dashboard shows a 'Visits by place' list plus a Leaflet/OpenStreetMap map (tiles load only after PIN login) with the note 'Locations are approximate, from IP address, city-level only.' No Dashboard link was added to the public site (Tom decided against it).

## Money / traffic (honest baseline at last check)
- Revenue: $0 earned so far, 0 leads sold. API/MCP call volume is mostly directory bots, not demand.
- Plumbing is call-to-connect only; other categories are collecting with no live form buyer yet.
