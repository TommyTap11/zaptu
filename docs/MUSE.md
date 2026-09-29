# Connecting Meta Muse

Two paths. Use the first today. Use the second when you want directory placement.

## 1. Custom connector (works immediately)

Muse can attach to any public MCP or HTTP API. After this server is hosted:

1. Deploy so `https://YOUR_HOST/health` returns `{"ok": true}`.
2. In Muse, say something like:

> Connect a custom connector called Agent Service Lead Connector.
> MCP URL: `https://YOUR_HOST/mcp`
> Transport: streamable HTTP.
> Tools: `request_home_service`, `request_cleaning`, `get_lead_status`, `list_supported_services`.
> When I ask for a house cleaner, collect ZIP, name, phone, and my consent to be called, then call `request_cleaning`.

3. Muse writes a small MCP client on its VM and stores the URL in its Secure Credentials Store.

Muse Code (terminal) alternative — add to `~/.config/muse/settings.json`:

```json
{
  "schema_version": 1,
  "mcp_servers": {
    "home-services": {
      "transport": "streamable_http",
      "url": "https://YOUR_HOST/mcp",
      "mode": "optional"
    }
  }
}
```

If you set `API_TOKEN`, pass it as a header:

```json
"headers": { "Authorization": "Bearer YOUR_TOKEN" }
```

Note: the MCP tools themselves are currently unauthenticated so an agent can call them. Protect the public host with a token at the edge (Cloudflare / Render) before you take real customer PII at volume.

## 2. Official Muse connector

Meta opened `muse.ai/platform` for submitted connectors (review + Stripe Link). Submit once the server has:

- a stable public URL
- a privacy policy covering lead sharing with affiliate networks
- TCPA consent captured in the tool schema (`consent_to_contact`)
- a short demo video of Muse booking a cleaning request

Until that review lands, custom connectors are enough to test demand.

## Prompt Muse should follow

See the server `instructions` string in `src/aslc/server.py`. The important product constraint: **this is a lead, not a booked appointment.** Agents must not tell the user “Maria’s Maids is coming Tuesday at 10.”
