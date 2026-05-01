---
id: 1261
title: Integrate EventSource into useBoard with fallback orchestration
status: research
priority: nice-to-have
created: 2026-05-01T09:34:27.630685+00:00
updated: 2026-05-01T09:34:40.346445+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1235
- 1259
- 1260
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Wire useEventSource into useBoard: SSE open pauses polling, tasks-changed triggers refetchTasks(), SSE failure/stall resumes polling. Update useConnectionHealth to accept transport-state override for health badge (green=SSE open, yellow=reconnecting, red=fallback). See .owlbear/research/1235-eventsource-client-implementation.md §3.4 and §3.6. Depends on the paused-option (#1259) and useEventSource (#1260) tasks.