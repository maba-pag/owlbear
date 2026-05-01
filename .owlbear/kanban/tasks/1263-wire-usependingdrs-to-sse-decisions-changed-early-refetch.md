---
id: 1263
title: Wire usePendingDRs to SSE decisions-changed early-refetch
status: research
priority: someday
created: 2026-05-01T09:53:38.534934+00:00
updated: 2026-05-01T09:54:00.066032+00:00
tags:
- cockpit
- frontend
parent: 1236
depends_on:
- 1235
- 1262
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Listen for `decisions-changed` SSE event and trigger immediate refetch of /api/decisions/pending ahead of the 60s timer. Keep 60s poll active (SSE is supplementary, not replacement — avoids stale-data bug when decisions/pending doesn't exist yet). Requires useEventSource hook from #1235 and backend multi-surface events from sibling task. See .owlbear/research/1236-extend-sse-decisions-activity.md