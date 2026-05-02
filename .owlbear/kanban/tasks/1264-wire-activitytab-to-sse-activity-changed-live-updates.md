---
id: 1264
title: Wire ActivityTab to SSE activity-changed live updates
status: todo
priority: someday
created: 2026-05-01T09:53:38.547262+00:00
updated: 2026-05-02T12:11:13.658846+00:00
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
[[2026-05-02]]
## Planning

Created 3 follow-up research tasks (all parent #1236, tags: cockpit/frontend, priority: someday):

| ID | Title | Depends on |
|----|-------|-----------|
| #1276 | Create EventSourceProvider context and useSSEEvent hook | — |
| #1277 | Refactor useBoard to consume EventSourceProvider context | #1276 |
| #1278 | Implement ActivityTab SSE live refetch | #1276, #1277 |

Dependency graph: #1276 → #1277 → #1278 (with #1278 also depending directly on #1276).
[[2026-05-02]]
## Research

**Key findings:** Backend already emits `activity-changed` SSE events (#1262 done). Core problem is connection sharing — `useBoard` owns the single EventSource instance; ActivityTab cannot listen without duplicating the connection.

**Recommendation (0.78):** EventSourceProvider context — single shared SSE connection via React context, typed per-event subscriptions via `useSSEEvent(eventType)` hook. ActivityTab refactored to `usePollingFetch` (paused when SSE open) + SSE-triggered refetch.

**Trade-off matrix:** Context (1 conn, ~60 LOC, medium refactor) > Lift+props (1 conn, ~30 LOC, props drilling) > Duplicate connections (2–3 conn, ~10 LOC, tech debt).

**Follow-up tasks created:** #1276 (EventSourceProvider), #1277 (refactor useBoard), #1278 (ActivityTab implementation).

**Doc:** .owlbear/research/1264-activity-tab-sse-wiring.md