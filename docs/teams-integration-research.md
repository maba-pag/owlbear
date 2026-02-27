# Teams Integration Path — Research

> **Owning task:** #47 — Research Teams integration path
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear needs a Microsoft Teams channel to receive user messages and respond. The daemon is **laptop-resident** (no public cloud hosting). The existing `ChannelPlugin` Protocol in `src/owlbear/channels/base.py` defines `send()`, `receive()`, `connect()`, and `disconnect()` — any Teams adapter must conform to this interface.

**Question:** Which integration approach best fits a laptop-resident daemon that cannot expose a public endpoint?

Three candidates: M365 Agents SDK (Bot Framework successor), Composio MCP, and direct Microsoft Graph API.

## 2. Sources Studied

| # | Source | URL | Relevance | What |
|---|--------|-----|-----------|------|
| 1 | M365 Agents SDK (Python) | <https://github.com/microsoft/Agents-for-python> | .90 | Official successor to Bot Framework; Python packages, Teams handler, auth |
| 2 | M365 Agents SDK migration guide (Python) | <https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/bf-migration-python> | .85 | Package mapping, initialization patterns, Teams bot examples |
| 3 | Bot Framework Python SDK (archived) | <https://github.com/microsoft/botbuilder-python> | .70 | Archived Jan 5, 2026; confirms migration to M365 Agents SDK |
| 4 | Composio Teams toolkit | <https://composio.dev/toolkits/microsoft_teams> | .75 | 180 Teams tools, OAuth2, MCP gateway, send/list/manage actions |
| 5 | Composio Teams docs | <https://docs.composio.dev/apps/microsoft_teams> | .70 | Auth details, action inventory, version info |
| 6 | Graph API — Send chat message | <https://learn.microsoft.com/en-us/graph/api/chat-post-messages?view=graph-rest-1.0&tabs=python> | .90 | Python snippet for sending messages via `msgraph` SDK |
| 7 | Graph API — Teams change notifications | <https://learn.microsoft.com/en-us/graph/teams-change-notification-in-microsoft-teams-overview> | .85 | Subscription model, 60-min max, webhook endpoint required |
| 8 | Microsoft Dev Tunnels | <https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/overview> | .65 | Tunnel local ports to public URLs; public preview, not production |
| 9 | Teams bot concepts | <https://learn.microsoft.com/en-us/microsoftteams/platform/bots/bot-basics> | .75 | Activity model, bot scopes (1:1, group, channel), 15s timeout |

## 3. Analysis

### 3.1 Approach Comparison

| Criterion | M365 Agents SDK (.65) | Composio MCP (.45) | Graph API + Polling (.80) |
|---|---|---|---|
| **Public endpoint required** | Yes — Bot Service webhook | No (SaaS proxy) | No (polling) |
| **Real-time messages** | Yes (push via Activity) | No (poll only) | No (poll, ~5–30s latency) |
| **Send messages** | Yes (TurnContext) | Yes (20+ send tools) | Yes (POST /chats/{id}/messages) |
| **Receive messages** | Yes (on_message handler) | Poll "Get all chat messages" | Poll GET /chats/{id}/messages |
| **Auth model** | Azure Bot registration + MSAL | Composio OAuth2 (managed) | Azure AD app + MSAL (device-flow) |
| **Python 3.12+ support** | Yes (3.10–3.14) | Yes (pip install composio) | Yes (msgraph-sdk) |
| **Async support** | Yes (aiohttp) | Yes | Yes (async msgraph client) |
| **Dependency count** | ~6 packages (microsoft-agents-*) | 2 (composio, composio-mcp) | 1 (msgraph-sdk, + msal) |
| **Third-party SaaS dep** | No (direct Microsoft) | **Yes** (Composio cloud) | No (direct Microsoft) |
| **Laptop-resident fit** | Needs tunnel (dev tunnels/ngrok) | Works behind firewall | Works behind firewall |
| **Adaptive Cards** | Full support | Limited | Full (via Graph) |
| **Maturity** | GA (v0.6.1, Dec 2025) | Production (v20260225) | Stable (Graph v1.0) |
| **Maps to ChannelPlugin** | Awkward (push-based, needs HTTP server) | Clean (poll/send) | Clean (poll/send) |
| **KISS score** | Low | Medium | **High** |
| **YAGNI score** | Low (many features unused) | Medium (SaaS overhead) | **High** |

### 3.2 Critical Issue: Public Endpoint

The **fundamental constraint** for a laptop-resident daemon is that it cannot reliably expose a public HTTPS endpoint:

- **M365 Agents SDK** requires Azure Bot Service to deliver Activities to your endpoint. Local development uses dev tunnels, but these are public preview and not suitable for always-on production. Running ngrok/cloudflared persistently is fragile.
- **Graph API change notifications** (webhooks) also require a public endpoint and subscriptions expire every 60 minutes. Not viable without a tunnel.
- **Polling** (Graph API or Composio) works entirely behind a firewall. The daemon initiates all connections outbound.

### 3.3 Composio Concerns

- **SaaS dependency** — all API calls route through Composio's cloud. Violates OwlBear's laptop-resident principle.
- **No native PydanticAI integration** — supports Claude SDK, OpenAI, LangChain, CrewAI. Would need a custom adapter.
- **No real-time receive** — must poll for messages, same as Graph API, but adds a middleman.
- **Cost** — free tier may be limited; enterprise pricing unclear.
- **Vendor lock-in** — if Composio changes APIs or pricing, we're stuck.

### 3.4 Graph API Polling Design

Polling fits the ChannelPlugin protocol naturally:

| ChannelPlugin method | Graph API mapping |
|---|---|
| `connect()` | Authenticate via MSAL device-flow; resolve target chat/channel ID |
| `send(message)` | `POST /chats/{chat_id}/messages` with `ChatMessage` body |
| `receive()` | `GET /chats/{chat_id}/messages?$top=10&$orderby=createdDateTime desc`, filter for messages newer than last-seen timestamp |
| `disconnect()` | Close httpx/Graph client session |

Polling interval: 5–15 seconds. Rate limit: Graph API allows ~10K requests per 10 minutes per app per tenant — polling one chat every 10s = 8,640/day, well within limits.

## 4. Recommendation (.80 confidence)

**Microsoft Graph API with polling** — the simplest path that works behind a firewall.

**Rationale:**

1. **No public endpoint needed** — daemon polls outbound, works on any laptop/VPN.
2. **Minimal dependencies** — `msgraph-sdk` + `msal` (we already use MSAL for Copilot auth).
3. **Clean ChannelPlugin mapping** — poll-based `receive()` matches the existing Protocol.
4. **KISS** — no tunnel infrastructure, no SaaS middleman, no HTTP server.
5. **YAGNI** — we need send + receive in one chat. The Agents SDK's Teams activity handlers, Adaptive Cards, and full bot platform are overkill for v1.
6. **Reuses auth patterns** — device-flow OAuth via MSAL mirrors our Copilot auth flow.

**Trade-off accepted:** 5–15 second polling latency. For a developer assistant daemon, this is acceptable — the user types in Teams, OwlBear picks it up within seconds.

**Future upgrade path:** If real-time push becomes critical, migrate to M365 Agents SDK with a persistent dev tunnel or Azure relay. The ChannelPlugin abstraction makes this a swap-in replacement.

## 5. Follow-up Tasks

1. **Register Azure AD app for Graph API** — Create app registration with `Chat.ReadWrite` + `ChatMessage.Send` delegated permissions; configure device-flow redirect. Priority: high.
2. **Implement `TeamsChannel` adapter** — `src/owlbear/channels/teams.py` conforming to `ChannelPlugin`. Uses `msgraph-sdk` + `msal` for auth, polling loop for `receive()`, Graph API for `send()`. Priority: high. Depends: task 1.
3. **Add `bearclaw teams` CLI commands** — `bearclaw teams auth` (device-flow login), `bearclaw teams status` (connection check), `bearclaw teams chat` (set target chat ID). Priority: medium. Depends: task 2.
4. **Write tests for TeamsChannel** — Unit tests with mocked Graph client. Integration test pattern for manual verification against real Teams tenant. Priority: high. Depends: task 2.
5. **Document Teams setup in README** — User-facing setup guide: Azure AD app creation, permissions, `bearclaw teams auth` flow. Priority: low. Depends: task 3.
