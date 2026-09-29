# Zaptu — Agent Service Lead Connector

Repo: **https://github.com/TommyTap11/zaptu**  
Public home: **[zaptu.ai](https://zaptu.ai)** (owned).

```bash
git clone https://github.com/TommyTap11/zaptu.git
cd zaptu
```


Zaptu is the intended **transaction hub between AI assistants and real-world local services**. This codebase is vertical 1 of that hub: an MCP server and public API that turns “book me a house cleaner” into a structured, monetizable lead for existing pay-per-call and affiliate networks.

Start with house cleaning in Miami. Expand to pest control, plumbing, HVAC — then other verticals behind the same gateway.

Strategy brief: `docs/ZAPTU-HUB-STRATEGY.md`

## One-liner

Agents request local services. This service validates the request, logs it, and forwards it as a paid lead or tracked call.

## Why this MVP

- Muse and other agents can already attach a remote MCP URL as a custom connector.
- House cleaning and pest control networks already buy calls and form leads — no need to sign up individual maids on day one.
- The same intake pipeline can later sell direct to partnered companies.
- Public brand is Zaptu. Every front door (zaptu.ai widget, Telegram, MCP, REST) must call the same `submit_request` pipeline. Do not fork qualification per channel.

## What is implemented

| Surface | Path | Purpose |
|---|---|---|
| MCP tools | `/mcp` | `request_home_service`, `request_cleaning`, `get_lead_status`, `list_supported_services` |
| Health | `GET /health` | Deploy probes |
| REST intake | `POST /v1/leads` | Same pipeline for non-MCP agents |
| REST lookup | `GET /v1/leads/{id}` | Status check |
| Storage | `data/leads.jsonl` | MVP log |
| Forwarding | webhook + mock network | Plug a real buyer without rewriting tools |

## Quick start

```bash
pip install -r requirements.txt
export PYTHONPATH=src
python src/aslc/server.py
```

- API: http://localhost:8000/health
- MCP: http://localhost:8000/mcp

Submit a test lead:

```bash
curl -s http://localhost:8000/v1/leads \
  -H 'content-type: application/json' \
  -d '{
    "service_type": "house_cleaning",
    "zip_code": "33139",
    "customer_name": "Ada Lovelace",
    "customer_phone": "3055550199",
    "consent_to_contact": true,
    "bedrooms": 3,
    "frequency": "biweekly",
    "source_agent": "curl"
  }'
```

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Fastest path for MCP + validation |
| MCP | Official `mcp` 2.x `MCPServer` | Streamable HTTP, custom routes, tool schemas from type hints |
| HTTP | Starlette routes on the MCP app | One process, one port |
| Models | Pydantic v2 | Shared schema for MCP, REST, and storage |
| Forwarding | httpx adapters | Swap mock → webhook → ping/post |
| Hosting | Render / Railway / Fly / Docker | Free-cheap tiers, `PORT` env already wired |
| Store | JSONL file | Zero ops. Replace with Postgres when volume appears |

Not used on purpose: a provider marketplace, auth-heavy OAuth, a frontend. Those are later.

## Monetization path

1. **Now** — log every request, simulate a buyer, optionally POST to a webhook.
2. **Week 2** — apply to eLocal, Service Direct Earn API, The Client Connector, UpN3xt. See `docs/NETWORKS.md`.
3. **Later** — direct cleaning companies, then pest/plumbing/HVAC with the same tool.

Public 2026 ranges: affiliate cleaning calls often list **~$15–$25**; Google LSA cleaning CPL is roughly **$28–$70**. Agent-originated demand has near-zero media cost if Muse users bring the job.

## Muse

Custom connector today (paste the `/mcp` URL). Official directory later via muse.ai/platform. Details in `docs/MUSE.md`.

## Project layout

```
src/aslc/
  server.py       MCP tools + REST
  models.py       request / lead schema
  validation.py   TCPA, ZIP, date, coverage
  forwarding.py   mock + webhook adapters
  service.py      shared intake pipeline
  storage.py      JSONL log
  config.py       env
docs/
  MUSE.md
  NETWORKS.md
```

## What this does not do yet

- Live call bridging / DIDs
- Real ping/post contracts
- Multi-tenant API keys per agent vendor
- Official Muse review package
- Non-US addresses

Those are sequential, not blockers for a first hosted endpoint.

## License

Use it. If you operationalize this as a business, add a privacy policy before you take real phone numbers at volume.
