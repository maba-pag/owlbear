# Real-Time Cockpit Updates: SSE vs WebSocket

> **Owning task:** #1233 — Research — WebSocket/SSE real-time updates for cockpit
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

The cockpit polls `/api/tasks` every 3s with mtime comparison. When MCP or cockpit mutates tasks, the change takes up to 3s to appear. The task asks: which transport (WebSocket vs SSE) fits best, how to detect mutations, deployment impact, and fallback strategy.

**Scope clarification:** This research covers the primary task-list polling (3s interval in `useBoard.ts`). Other polling surfaces (decisions at 60s, scan at 60s, health at 3s) are noted but deferred to implementation-phase scoping.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | germano.dev/sse-websockets (2022, 263 HN comments) | Technical deep-dive + demo | 0.9 |
| 2 | digitalbiztalk.com — SSE vs WebSockets 2026 | Comparison article | 0.7 |
| 3 | Medium — FastAPI SSE implementation (2025) | FastAPI-specific howto | 0.8 |
| 4 | github.com/sysid/sse-starlette | Battle-tested SSE lib for Starlette | 0.9 |
| 5 | github.com/samuelcolvin/watchfiles | Rust async file watcher | 0.8 |
| 6 | uvicorn.org/settings — concurrency limits | Deployment reference | 0.7 |
| 7 | Codebase: serve/cockpit/ (routes, cache, hooks, tests) | Live implementation | 1.0 |

## 3. Analysis

### 3.1 Transport: SSE vs WebSocket

| Criterion | SSE | WebSocket | Winner |
|-----------|-----|-----------|--------|
| Direction needed | Server→client only | Bidirectional | SSE (cockpit only needs push) |
| Protocol | Standard HTTP streaming | Upgrade to WS protocol | SSE (no proxy/infra changes) |
| Auto-reconnect | Built-in (EventSource) | Manual implementation | SSE |
| Auth | Same-origin cookies/headers | Query-param or initial handshake | SSE (localhost, trivial) |
| Compression | HTTP gzip natively | RFC 7692 (complex) | SSE |
| New dependencies | sse-starlette (1 dep) | websockets + custom mgmt | SSE |
| Complexity (server) | ~30 LOC endpoint | ~80 LOC + connection registry | SSE |
| Complexity (client) | EventSource (native API) | WebSocket + reconnect logic | SSE |
| HTTP/2 multiplexing | Yes (shares connection) | No (dedicated TCP) | SSE |
| Binary data | No (text/JSON only) | Yes | WebSocket (irrelevant here) |
| Bidirectional comms | No | Yes | WebSocket (irrelevant here) |

**Verdict:** SSE is the clear fit. The cockpit use case is purely server→client notification. WebSocket adds bidirectional machinery that will never be used.

### 3.2 Mutation Detection Approaches

| Approach | Catches cockpit writes | Catches MCP writes | Catches CLI writes | Latency | Complexity |
|----------|----------------------|--------------------|--------------------|---------|------------|
| A: Explicit push after API | Yes | No | No | <50ms | Low |
| B: File watcher (watchfiles) | Yes (side-effect) | Yes | Yes | ~100ms | Medium |
| C: Hybrid (A for in-process, B for external) | Yes | Yes | Yes | <50ms in-proc, ~100ms ext | Medium-high |
| D: Fast poll (reduce to 500ms) | Yes | Yes | Yes | ≤500ms | Lowest |

**Recommendation: Option B (file watcher) for v1.**

Rationale:
- Single detection mechanism for all mutation sources (cockpit API, MCP server, CLI kanban-md)
- `watchfiles` uses OS-native events (FSEvents on macOS, inotify on Linux) — near-instant
- Avoids coupling SSE notification into every mutation path
- Single-process uvicorn on localhost means no cross-worker coordination needed
- ~100ms latency is imperceptible vs. current 3000ms

### 3.3 Event Model

Two options for what SSE pushes:

| Model | Payload | Client action | Preserves existing contract |
|-------|---------|---------------|----------------------------|
| Invalidation-only | `event: tasks-changed\ndata: {"mtime": 1234}` | Client calls GET /api/tasks | Yes — same response model |
| Full push | `event: tasks-update\ndata: {full task list}` | Client replaces state directly | No — bypasses cache/filtering |

**Recommendation: Invalidation-only.** The client's existing fetch logic (mtime comparison, filtering, error handling) stays intact. SSE just replaces the timer trigger. This preserves all existing test contracts in `useBoard.test.ts` and `usePolling.test.ts`.

### 3.4 Fallback Strategy

```
EventSource connects → receives events → triggers refetch
    ↓ (on error/close)
EventSource auto-reconnects (built-in exponential backoff)
    ↓ (after N failed reconnects or >15s without event)
Fall back to 3s polling (existing useBoard interval logic)
    ↓ (SSE reconnects successfully)
Resume SSE-driven updates, stop polling
```

Health badge (`useConnectionHealth.ts`) integrates: SSE connected = green, reconnecting = yellow, polling fallback = red→yellow transition.

### 3.5 Deployment Impact

| Concern | Impact |
|---------|--------|
| Connection count | 1-3 SSE connections (localhost, single user, few tabs) |
| Uvicorn workers | Single worker sufficient — async SSE generators don't block |
| Memory | Negligible — one asyncio.Event per connection |
| File watcher overhead | Minimal — OS-native, one directory watched |
| Port/infra changes | None — same HTTP server, same port |

## 4. Recommendation

**Use SSE with invalidation-only events, triggered by a watchfiles-based file watcher.**

Confidence: **0.78**

Challenge: reconsider — confidence in original: 0.67. Challenger correctly identified gaps in fallback definition, scope boundaries, and mutation-detection comparison. These are now addressed above. The core SSE-over-WebSocket verdict was not disputed.

Risks:
1. **watchfiles adds a dependency** — mitigated: it's by the Pydantic author, Rust-based, well-maintained, already used by uvicorn for reload
2. **Fallback complexity** — mitigated: invalidation-only model means polling and SSE share the same fetch path
3. **Scope creep into other polling surfaces** — mitigated: research scopes to task-list only; decisions/activity are separate follow-up

## 5. Follow-up Tasks

1. **Implement SSE endpoint + watchfiles watcher** (backend) — add `/api/events` SSE endpoint, watch tasks dir, emit invalidation events
2. **Replace useBoard polling with EventSource** (frontend) — EventSource triggers refetch, fallback to polling on disconnect
3. **Extend to decisions/activity polling** (future) — watch decisions dir, activity.jsonl; emit typed events
