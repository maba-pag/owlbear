---
id: 1236
title: Research — extend SSE to decisions and activity polling
status: research
priority: someday
created: '2026-04-30 16:48:43.009769+00:00'
updated: '2026-04-30 16:48:56.208215+00:00'
tags:
- cockpit
- architecture
parent:
depends_on:
- 1233
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Investigate extending the SSE /api/events stream to cover decisions polling (currently 60s) and activity/session data. Requires watching decisions directory and activity.jsonl in addition to tasks dir. See .owlbear/research/1233-realtime-cockpit-updates.md