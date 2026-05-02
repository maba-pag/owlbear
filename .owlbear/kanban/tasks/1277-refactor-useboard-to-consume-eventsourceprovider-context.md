---
id: 1277
title: Refactor useBoard to consume EventSourceProvider context
status: research
priority: someday
created: 2026-05-02T12:10:47.678864+00:00
updated: 2026-05-02T12:10:55.620154+00:00
tags:
- cockpit
- frontend
parent: 1236
depends_on:
- 1276
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Replace the internal useEventSource('/api/events') call in useBoard with useSSEEvent('tasks-changed') from the new EventSourceProvider context. Adjust Shell to wrap children with EventSourceProvider. Update useBoard tests to provide context. See .owlbear/research/1264-activity-tab-sse-wiring.md