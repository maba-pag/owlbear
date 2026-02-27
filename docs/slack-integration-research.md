# Slack Integration Path — Research

> **Owning task:** #83 — Research Slack integration path (replaces Teams #47)
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear needs a messaging channel to receive user messages and respond. The Teams path is **permanently blocked** — Azure AD app registrations are locked down by IT admins (AADSTS50105). All three Microsoft approaches (M365 Agents SDK, Graph API, Composio) require Azure AD app access.

The pivot is to **Slack**, which allows self-service app creation in a free workspace without corporate IT approval. The existing `ChannelPlugin` Protocol in `src/owlbear/channels/base.py` defines `name`, `send()`, and `receive()` — any Slack adapter must conform to this interface.

**Question:** Which Slack integration approach best fits a laptop-resident daemon behind a firewall, and what's the simplest auth model for a personal workspace?

## 2. Sources Studied

| # | Source | URL | Relevance | What |
|---|--------|-----|-----------|------|
| 1 | Slack Socket Mode docs | <https://docs.slack.dev/apis/events-api/using-socket-mode> | .95 | Protocol spec: WebSocket connection, envelope ack, disconnect handling, no public endpoint |
| 2 | Bolt for Python (slack_bolt) | <https://github.com/slackapi/bolt-python> | .90 | Official framework, AsyncApp, SocketModeHandler, 1.3k stars, v1.27.0, MIT, Python 3.7–3.14 |
| 3 | Python Slack SDK (slack_sdk) | <https://github.com/slackapi/python-slack-sdk> | .90 | Lower-level SDK, `slack_sdk.socket_mode.aiohttp.SocketModeClient`, 4k stars, v3.40.1, MIT |
| 4 | slack_sdk Socket Mode docs | <https://docs.slack.dev/tools/python-slack-sdk/socket-mode> | .90 | Async SocketModeClient with aiohttp, listener pattern, connect/process/ack flow |
| 5 | Bolt Python AI Agent Template | <https://github.com/slack-samples/bolt-python-assistant-template> | .85 | Official template: Assistant class, Socket Mode, OpenAI integration, thread management |
| 6 | Bolt Python Getting Started | <https://docs.slack.dev/tools/bolt-python/getting-started> | .80 | App setup flow, manifest.json, Socket Mode toggle, developer sandbox |
| 7 | slack-bolt on PyPI | <https://pypi.org/project/slack-bolt/> | .75 | Package info, dependency chain, async support requirements (aiohttp) |

## 3. Analysis

### 3.1 Socket Mode Architecture

Socket Mode replaces the traditional HTTP webhook model with an **outbound WebSocket** connection:

1. App calls `apps.connections.open` with an app-level token (`xapp-`)
2. Slack returns a `wss://` URL
3. App connects to the WebSocket and receives events as JSON envelopes
4. App acknowledges each event by sending back the `envelope_id`
5. Connection refreshes every ~3600 seconds; app must reconnect

**Key properties:**

- **No public endpoint** — all connections are outbound from the daemon
- **Works behind firewalls/VPNs** — only needs outbound HTTPS + WSS
- **No ngrok/tunnel needed** — unlike Bot Framework or Events API HTTP mode
- **Up to 10 concurrent WebSocket connections** for redundancy
- **Real-time** — events pushed via WebSocket, not polled (unlike the Graph API approach)

### 3.2 Auth Model

Socket Mode requires **two tokens**:

| Token | Prefix | Purpose | How to get |
|-------|--------|---------|------------|
| App-Level Token | `xapp-` | Opens WebSocket connection (`connections:write` scope) | App Settings → Basic Information → App-Level Tokens |
| Bot Token | `xoxb-` | Calls Web API (send messages, read history, etc.) | App Settings → OAuth & Permissions → Install to Workspace |

**No OAuth flow needed** for a single-workspace personal bot. Tokens are generated once during app setup and stored in config. No corporate IT approval required — the user creates a free Slack workspace at `slack.com/create` and installs the app themselves.

### 3.3 Approach Comparison

| Criterion | slack_bolt AsyncApp (.70) | slack_sdk SocketModeClient (.85) | Raw WebSocket + REST (.40) |
|---|---|---|---|
| **Abstraction level** | High — framework with middleware, routing, decorators | Medium — client + listeners, manual routing | Low — raw websocket + httpx |
| **Async support** | Yes (`AsyncApp` + `AsyncSocketModeHandler`) | Yes (`aiohttp` backend, async listeners) | Manual |
| **Socket Mode** | Built-in via `SocketModeHandler` | Built-in via `SocketModeClient` | Manual (`apps.connections.open` + websocket lib) |
| **Dependencies** | slack_bolt + slack_sdk + aiohttp | slack_sdk + aiohttp | websockets (or aiohttp) + httpx |
| **Package count** | ~3 direct (slack_bolt pulls slack_sdk) | ~2 direct | ~2 direct |
| **Framework overhead** | Middleware chain, routing, ack helpers, `say()` | Minimal — listener callbacks, manual ack | Zero |
| **Maps to ChannelPlugin** | Awkward — framework wants to own the event loop | **Clean** — we control connect/listen/send | Clean but more code |
| **Learning curve** | Higher (framework concepts, decorators) | Lower (callback + WebClient) | Lowest (but most boilerplate) |
| **AI features** | `Assistant` class, streaming, feedback buttons | Use via `WebClient` directly | Manual |
| **Maturity** | GA, v1.27.0 (Nov 2025) | GA, v3.40.1 (Feb 2026) | N/A |
| **KISS score** | Medium | **High** | Low (reinventing the wheel) |
| **YAGNI score** | Low (middleware, shortcuts, modals unused) | **High** | High |

### 3.4 Why Not slack_bolt?

`slack_bolt` is designed around a framework pattern — it owns the event loop, routes events to decorated handlers, and manages middleware chains. For OwlBear, this creates friction:

- **Double abstraction** — OwlBear's `ChannelPlugin` already abstracts the channel; wrapping a framework inside a protocol adapter is awkward
- **Framework fights protocol** — `slack_bolt` wants `@app.message()` decorators; we want `async for msg in channel.receive()`
- **Unused features** — shortcuts, modals, slash commands, middleware chain — all YAGNI for v1
- **Heavier dependency** — pulls in the full framework when we only need WebSocket + Web API

### 3.5 Why slack_sdk?

`slack_sdk.socket_mode.aiohttp.SocketModeClient` provides exactly what we need:

- **Async-native** — uses aiohttp, fits our async ChannelPlugin
- **Listener pattern** — register a callback for incoming events, ack manually
- **WebClient included** — `AsyncWebClient` for sending messages via `chat.postMessage`
- **Minimal** — no framework overhead, just the client
- **Same library** — slack_bolt uses slack_sdk internally anyway

### 3.6 ChannelPlugin Mapping

| ChannelPlugin method | slack_sdk mapping |
|---|---|
| `name` → `"slack"` | Property returning `"slack"` |
| `send(message)` | `AsyncWebClient.chat_postMessage(channel=channel_id, text=message)` |
| `receive(prompt=...)` | Listen for `message.im` events via `SocketModeClient`, yield `event["text"]`; if `prompt`, post it first via `send()` |
| (connect — lifecycle) | `SocketModeClient(app_token=..., web_client=AsyncWebClient(token=...))` then `await client.connect()` |
| (disconnect — lifecycle) | `await client.disconnect()` or `client.close()` |

The current `ChannelPlugin` protocol does not have `connect()`/`disconnect()` methods (the architecture doc shows them but the implementation doesn't). The adapter can handle connection lifecycle internally in `__aenter__`/`__aexit__` or via explicit methods added later.

### 3.7 Scopes Needed

Minimal bot token scopes for v1:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages |
| `im:history` | Read DM history (for `message.im` events) |
| `app_mentions:read` | Receive `@OwlBear` mentions (optional, for channel use) |

App-level token scope: `connections:write` (required for Socket Mode).

Event subscriptions: `message.im` (DM messages to the bot).

### 3.8 Testing Strategy

| Layer | Approach |
|-------|----------|
| Unit tests | Mock `SocketModeClient` and `AsyncWebClient`. Verify `SlackChannel.send()` calls `chat_postMessage`. Verify `SlackChannel.receive()` yields text from event payloads. |
| Protocol compliance | Same pattern as `test_channels.py` — verify `isinstance(SlackChannel(...), ChannelPlugin)` |
| Integration (optional) | Use a real free Slack workspace with a test channel. Mark with `@pytest.mark.api`. |
| Mocking library | `unittest.mock.AsyncMock` for async methods. No need for `responses` or `aiohttp` test server. |

## 4. Recommendation (.90 confidence)

**`slack_sdk` with `socket_mode.aiohttp.SocketModeClient`** — the simplest path that provides real-time messaging behind a firewall.

**Rationale:**

1. **No public endpoint** — daemon connects outbound via WebSocket, works on any laptop/VPN
2. **No corporate IT approval** — user creates a free Slack workspace, installs their own app
3. **Real-time** — events pushed via WebSocket (vs. 5–15s polling latency with Graph API)
4. **Minimal dependencies** — `slack_sdk[socket_mode]` + `aiohttp` (~2 packages)
5. **Clean ChannelPlugin mapping** — listener-based `receive()` matches the protocol naturally
6. **KISS** — no framework, no middleware chain, no unused features
7. **YAGNI** — we need send + receive in DMs. The Bolt framework's routing, shortcuts, and modals are overkill
8. **Async-native** — `AsyncWebClient` + async `SocketModeClient` fit our async codebase

**Trade-off accepted:** We lose `slack_bolt`'s convenience helpers (`say()`, `ack()`, decorators). For a single-purpose ChannelPlugin adapter, this is acceptable — we write ~100 LOC instead of learning a framework.

**Future upgrade path:** If we need slash commands, modals, or the `Assistant` AI features, migrating to `slack_bolt` is straightforward — it wraps the same `slack_sdk` underneath.

## 5. Follow-up Tasks

1. **Create free Slack workspace + OwlBear app** — Manual setup: create workspace, create app with manifest, enable Socket Mode, generate tokens, subscribe to `message.im`.
2. **Add `slack_sdk[socket_mode]` + `aiohttp` to pyproject.toml** — Add dependencies.
3. **Implement `SlackChannel` adapter** — `src/owlbear/channels/slack.py` implementing `ChannelPlugin` using `slack_sdk.socket_mode.aiohttp.SocketModeClient` + `AsyncWebClient`.
4. **Add Slack config to settings** — `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN` in `pydantic-settings`, plus `SLACK_CHANNEL_ID` for the target DM/channel.
5. **Write tests for `SlackChannel`** — Protocol compliance, send/receive mocks, disconnect handling.
6. **Add `bearclaw slack` CLI commands** — `bearclaw slack auth` (validate tokens), `bearclaw slack test` (send test message).
7. **Document Slack setup in README** — App creation steps, token config, workspace setup guide.
