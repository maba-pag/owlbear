---
id: 1235
title: Replace useBoard polling with EventSource client
status: backlog
priority: nice-to-have
created: 2026-04-30 16:48:42.996529+00:00
updated: 2026-05-01T09:35:18.793158+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1233
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Replace the 3s setInterval in useBoard.ts with an EventSource connection to /api/events. On receiving tasks-changed event, trigger the existing refetch logic. Implement fallback: after 15s without events or repeated connection failures, resume 3s polling. Integrate with health badge (green=SSE connected, yellow=reconnecting, red=polling fallback). Preserve existing test contracts. See .owlbear/research/1233-realtime-cockpit-updates.md
[[2026-05-01]]
## Research

**Key findings:** EventSource integration requires a new `useEventSource` hook + `paused` option on existing `usePollingFetch`. Critical correction from challenger: fallback trigger must be readyState-based (15s in CONNECTING or permanent CLOSED), NOT "15s without data events" — silence on invalidation-only SSE means no mutations, a healthy state. Architecture uses Option A (separate hooks, separate concerns). Graceful degradation: deploying before backend #1234 is safe — EventSource fails immediately on missing endpoint, fallback activates, behavior identical to today.

**Challenge outcome:** reconsider (0.39 confidence in original). Challenger identified false-fallback contradiction, stale task framing (timer in usePollingFetch not useBoard), initial hydration gap, backend not live. All addressed in revised design. Revised confidence: 0.75.

**Trade-off matrix:** See .owlbear/research/1235-eventsource-client-implementation.md §3.1 and §3.3.

**Follow-up tasks created:** #1259 (paused option), #1260 (useEventSource hook), #1261 (integration orchestration).

**Classification:** T1 — autonomous. Approach already approved in #1233. No new capability (refinement of transport layer), no architecture change.

**Doc:** .owlbear/research/1235-eventsource-client-implementation.md