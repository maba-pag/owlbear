---
id: 1264
title: Wire ActivityTab to SSE activity-changed live updates
status: research
priority: someday
created: 2026-05-01T09:53:38.547262+00:00
updated: 2026-05-01T09:54:00.072737+00:00
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

Refactor ActivityTab from one-shot useEffect fetch to a refetchable pattern (e.g. usePollingFetch with polling disabled, or a simpler useFetch wrapper). Listen for `activity-changed` SSE event and trigger session data refetch. Requires useEventSource hook from #1235 and backend multi-surface events from sibling task. See .owlbear/research/1236-extend-sse-decisions-activity.md