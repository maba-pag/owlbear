---
id: 1235
title: Replace useBoard polling with EventSource client
status: research
priority: nice-to-have
created: '2026-04-30 16:48:42.996529+00:00'
updated: '2026-04-30 16:48:56.201218+00:00'
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