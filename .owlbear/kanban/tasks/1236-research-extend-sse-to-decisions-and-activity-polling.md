---
id: 1236
title: Research — extend SSE to decisions and activity polling
status: todo
priority: someday
created: 2026-04-30 16:48:43.009769+00:00
updated: 2026-05-01T09:54:33.824747+00:00
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
[[2026-05-01]]
## Planning

Created 3 follow-up subtasks at research status:

| ID | Title | Tags | Priority | Deps |
|----|-------|------|----------|------|
| #1262 | Extend SSE watcher to recursive kanban_dir with typed multi-surface events | cockpit, backend | someday | #1234 |
| #1263 | Wire usePendingDRs to SSE decisions-changed early-refetch | cockpit, frontend | someday | #1235, #1262 |
| #1264 | Wire ActivityTab to SSE activity-changed live updates | cockpit, frontend | someday | #1235, #1262 |

Dependency graph:
```
#1234 → #1262 (backend multi-surface watcher)
#1235 ──┬──→ #1263 (decisions early-refetch)
#1262 ──┘
#1235 ──┬──→ #1264 (activity live updates)
#1262 ──┘
```

All tasks parented under #1236.
[[2026-05-01]]
## Research

**Key findings:** Multi-surface SSE extension is feasible via recursive `awatch(kanban_dir)` with path-based event classification. Three typed invalidation events: `tasks-changed`, `decisions-changed`, `activity-changed`. Critical design revision from challenger: SSE supplements (not replaces) decisions/activity polling — avoids stale-data bug when paths don't exist at subscribe time.

**Challenge outcome:** reconsider (0.29 confidence in original). Challenger identified critical stale-data contradiction (pause polling + skip missing paths), authority drift (expanding #1234 scope without approval), frontend delta undercount, and scan invalidation gap. All addressed: switched to recursive watch, made SSE supplementary for non-tasks surfaces, recommended separate implementation task, acknowledged frontend dependency chain. Revised confidence: 0.72.

**Trade-off matrix:** See .owlbear/research/1236-extend-sse-decisions-activity.md §3.1 (watch architecture), §3.5 (late-path handling), §3.9 (scope strategy).

**Classification:** T1 — autonomous. Extension follows approved SSE architecture from #1233. No new capabilities, same transport, same invalidation model.

**Follow-up tasks:** #1262 (backend watcher extension), #1263 (decisions SSE wire-up), #1264 (activity SSE wire-up).

**Doc:** .owlbear/research/1236-extend-sse-decisions-activity.md