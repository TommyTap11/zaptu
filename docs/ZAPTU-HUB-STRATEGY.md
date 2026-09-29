# Zaptu Hub Strategy Brief
Paste-ready strategy update — 29 Sep 2026. Companion to `grok-build-brief.md` (the build spec) and `monetization-plan.md` (the money plan).

---

## 1. The vision: Zaptu as an agent services hub

Zaptu is not just a lead router. It is the **transaction hub between AI personal assistants and real-world services**.

- The assistant connects to Zaptu **once**.
- Zaptu fans out to every service behind it: cleaners today, restaurants, plumbers, and more later.
- One integration for the assistant, infinite services for the user — and Zaptu sits at the toll booth.

**Why the hub wins:** assistants cannot integrate 1:1 with every local business. Whoever owns the middleware owns the transaction layer of the agent economy. The moat compounds: cross-service memory (Zaptu knows your cleaner AND your restaurant tastes), unified billing, one trust relationship instead of fifty. A provider's own MCP server cannot do any of that.

---

## 2. The hardest part of the funnel (and the plan to beat it)

Ranked by difficulty:

1. **Earning the call (cold start).** No volume → no buyers → no reason for assistants to call you → no volume. This kills most plays. Beat it by manufacturing your own volume from day one (see §3) so the business works with zero assistant distribution.
2. **The incentive gap.** The assistant gets no cut of your lead fee. It will only call your tool if it's clearly the best outcome *for the user* — fastest path to a real provider with least effort. Monetization must be invisible to that decision. Optimize the user experience, not the payout.
3. **Quality you can't fully control.** In pay-per-lead, your only lever is intake qualification. You don't control buyer speed-to-contact. Mitigation: track downstream outcomes where possible, prefer buyers with SLA commitments, cut slow buyers even if they bid highest.

---

## 3. Distribution: one pipeline, many front doors

Architecture rule: **every front door is just another client of the same `submit_request` pipeline.** Website widget, Telegram bot, MCP server, REST API — all go through identical qualification, dedup, and consent checks, and route to the same buyers. When assistant distribution kicks in later, nothing downstream changes.

Front doors, ranked by leverage:

1. **Chat widget on zaptu.ai (build first).** "I need a cleaner" chat → collects name, phone, ZIP, consent → fires the pipeline. The business works on day one with zero assistant distribution. Doubles as the live demo.
2. **Dogfood demo.** The zaptu.ai assistant runs ON your own MCP server — visitor chats, backend calls your own tools live. Marketing + product validation in one.
3. **WhatsApp / Telegram bot.** People already hire cleaners over chat. Telegram is free and trivial; WhatsApp reaches more normal humans but the Business API is heavier.
4. **QR-code flyers in Miami residential buildings.** "Need a cleaner? Scan, chat, done." Unsexy, near-zero cost, and local services still run on this.

Every bot must promise only "a provider will contact you" — never a confirmed booking.

---

## 4. Using Grok against the cold start

Grok's capabilities (verified Sep 2026): API function calling (ranked #1 of 168 models for agentic tool use, $2/$6 per 1M tokens), **Grok Automations** (cron-scheduled background jobs, ~$0.02 per daily run), and **native X search** (keyword/semantic/thread — no other assistant has this firehose).

Deploy it as staff for the funnel:

1. **Grok as the brain of the bot front doors.** The zaptu.ai chat widget runs on the Grok API with one function tool: `submit_request`. Grok handles the messy human conversation, extracts structured fields, calls the function. Fractions of a cent per conversation.
2. **Grok Automations as a demand radar.** Daily job: "Search X for people in Miami asking for house cleaners/maids. Return genuine requests with links, ranked by intent." ~$0.60/month. **The automation finds; the human replies.** Auto-replying to strangers is spam and gets accounts banned.
3. **Grok as buyer-outreach researcher.** One deep-research job: "Find 20 Miami cleaning companies and lead buyers with contact names/emails; draft personalized outreach per buyer." An afternoon of Grok = a week of manual work.
4. **Grok as content engine.** Landing pages, Miami cleaning-price FAQs, `agents.md` docs — the SEO content feeding both human Google traffic and assistant discoverability.

Cost guardrail: put a hard monthly budget cap on the xAI API key from day one. Expected spend is single dollars/month; cap it anyway.

---

## 5. Competitive landscape: crowded below, empty at our altitude

The space splits into layers. Zaptu's layer is the empty one.

- **Layer 1 — Protocols (rails, not rivals):** MCP, x402 (Coinbase), Google AP2, Visa Intelligent Commerce, Mastercard Agent Pay. Build ON these.
- **Layer 2 — Tool/integration hubs:** Composio (1,500+ integrations, one MCP gateway, managed OAuth), Arcade.dev, Nango, Executor.sh. They serve *developers'* agents hitting SaaS APIs. None arranges a house cleaning or takes a cut of a local transaction.
- **Layer 3 — Agent payments:** Skyfire ($8.5M seed, Know-Your-Agent identity + wallets, F5 partnership), Nevermined (x402 + Visa), Payman (agents pay humans), Stripe Agent Toolkit. They solve *how agents pay*, not *what the user buys*.
- **Layer 4 — Agent primitives:** email/phone/memory APIs for agents (AgentMail, etc.).

**The gap — Zaptu's layer:** the consumer-services transaction hub. "Clean my house" → arranged → money moves → Zaptu takes a cut. Nobody owns this. Everyone is selling shovels; nobody runs the marketplace at the end of the dig.

**Implications:**
- Don't rebuild their layers. Ride Skyfire/x402 for payments later; Composio exists for SaaS integrations. Zaptu stays narrow: service routing + lead economics.
- Real threats are a Layer 2 player moving up or big tech owning the assistant surface (OS-level "book a cleaner"). Speed matters — the wedge is open NOW.
- **Security lesson (Composio, May 2026 breach):** attackers pivoted through their OAuth token store — the crown jewels of a hub. This validates the sequencing: the lead-router phase holds ZERO user credentials, so there is nothing to steal. Only take on key-holding when revenue justifies the security investment.

---

## 6. Sequencing: the hub emerges, it is not built first

A hub built day one is a mile wide and an inch deep. The hub is the destination; the lead router is the vehicle.

1. **Vertical 1 — the lead router** (current build). No credentials, affiliate revenue, proves the pipe. One trade (cleaning), one market (Miami), one buyer type.
2. **Shared infrastructure hardens underneath:** tool registry, routing, metering, MCP gateway. Hub components, built without calling it a hub.
3. **Vertical 2** (e.g. restaurant recommendations/ordering). Now the hub exists in practice: two verticals, one gateway, one billing layer.
4. **Then the hub story goes public:** "connect once, reach every service." Add verticals or let providers plug into Zaptu.

---

## 7. Business model (unchanged, hub-compatible)

1. **Pay per accepted lead** via home-services affiliate networks (Lead Smart et al.) — revenue from day one, no user credentials.
2. **Pay per qualified call** as alternative/parallel stream.
3. **x402 metering** later: cents per paid API call, free discovery tier.
4. **Direct provider revenue share** once demand and reliability are proven.
5. **Sponsored placement** only after meaningful traffic.

Every stage works for the lead router AND generalizes to the hub.

---

## 8. What NOT to build

- Don't build agent wallets/payments infra — ride Skyfire/x402/Nevermined.
- Don't build SaaS integrations — Composio/others exist.
- Don't hold user credentials (OAuth tokens, payment methods) until revenue justifies the security burden. The affiliate lead model is the perfect wedge precisely because it needs none.
- Don't pitch the hub publicly until vertical 1 has real volume. The hub story without transactions is vapor.
