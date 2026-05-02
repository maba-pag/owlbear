---
id: 1278
title: Implement ActivityTab SSE live refetch
status: research
priority: someday
created: 2026-05-02T12:10:47.689197+00:00
updated: 2026-05-02T12:10:55.624668+00:00
tags:
- cockpit
- frontend
parent: 1236
depends_on:
- 1276
- 1277
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Refactor ActivityTab from one-shot useEffect fetch to usePollingFetch (paused when SSE open, fallback interval 120s). Listen for activity-changed via useSSEEvent('activity-changed') and trigger refetch() on mtime change. Keep initial mount fetch behavior. See .owlbear/research/1264-activity-tab-sse-wiring.md