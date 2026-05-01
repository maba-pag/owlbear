---
id: 1260
title: Create useEventSource hook
status: research
priority: nice-to-have
created: 2026-05-01T09:34:24.718353+00:00
updated: 2026-05-01T09:34:40.328311+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1235
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Create hooks/useEventSource.ts implementing the SSE connection state machine: connect, listen for tasks-changed events, track readyState transitions, implement 15s reconnect-stall detection, cleanup on unmount. Returns {status, lastEventMtime}. See .owlbear/research/1235-eventsource-client-implementation.md §3.2 and §3.5