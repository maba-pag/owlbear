---
id: 1044
title: Brief B — Kanban Engine + Cockpit Backend/API Surface
status: todo
priority: needed
created: 2026-04-21T09:48:03.854046+00:00
updated: 2026-04-21T10:51:25.509707+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
parent:
depends_on:
- 1043
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief

Source brief: .owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md
Normative source: .owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md
Depends on storage contract: parent task 1043

Scope: engine views, projections, lifecycle rules, activity/session semantics, cockpit backend/API exposure of the locked admin/history methods, MCP and cockpit adapter rewires, and engine-facing tests.

## Planner Source

Decompose from paper-integration.md §1, §4, and §5.
Respect the revised brief language: our service-side cockpit backend/API surface is in scope now, but cockpit UI/product decisions remain out of scope.
Do not create cockpit UI/operator-console tasks here; keep task 1042 separate and blocked.

## Notes

- This parent is above Brief C and below Brief A.
- The harness invariant around retries and stale end_work is locked; do not create agent-side OCC tasks that contradict it.

[[2026-04-21]]
## Planning
### Decomposition: Brief B — Kanban Engine + Cockpit Backend/API Surface
- Tasks created: 19
- Dependency layers: 10
- Phase: engine

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| #1065 | B-01: RED — models + errors tests | needed | #1059 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1066 | B-02: GREEN — models + errors | critical | #1065 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1067 | B-03: RED — engine init + config validation tests | needed | #1066 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1068 | B-04: GREEN — engine init + config validation | critical | #1067 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1069 | B-05: RED — list_tasks + show_task tests | needed | #1068 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1071 | B-06: GREEN — list_tasks + show_task | needed | #1069 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1070 | B-07: RED — create_task + edit_task tests | needed | #1068 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1072 | B-08: GREEN — create_task + edit_task | needed | #1070 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1073 | B-09: RED — move_task + start_work tests | needed | #1072 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1075 | B-10: GREEN — move_task + start_work | needed | #1073 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1077 | B-11: RED — end_work tests | needed | #1075 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1080 | B-12: GREEN — end_work | important | #1077 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1074 | B-13: RED — pick_tasks tests | needed | #1072 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1076 | B-14: GREEN — pick_tasks | needed | #1074 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1078 | B-15: RED — CockpitView tests | needed | #1071, #1075 | phase:engine, brief:b, scope:kanban, tdd:red |
| #1081 | B-16: GREEN — CockpitView | needed | #1078 | phase:engine, brief:b, scope:kanban, tdd:green |
| #1082 | B-17: RED — cockpit backend route tests | needed | #1081 | phase:engine, brief:b, scope:kanban, scope:cockpit, tdd:red |
| #1083 | B-18: GREEN — cockpit backend routes | important | #1082 | phase:engine, brief:b, scope:kanban, scope:cockpit, tdd:green |
| #1079 | B-19: orchestration skill rewrite | important | #1076 | phase:engine, brief:b, scope:kanban |

### Dependency Graph
Two parallel tracks fork from B-04 (#1068 engine init GREEN):
- Reads track: B-05 → B-06
- Writes track: B-07 → B-08 → B-09 → B-10 → B-11 → B-12
- pick_tasks fork: B-08 → B-13 → B-14 → B-19
- CockpitView: B-06 + B-10 → B-15 → B-16 → B-17 → B-18
Cross-brief: B-01 (#1065) depends on C-14 (#1059 storage.py public surface GREEN)

### Notes
- B-17/B-18 MCP adapter removed per constraint — Brief A (#1045) owns serve/mcp-kanban/
- B-19 added for w-orchestration/SKILL.md rewrite (documentation-only, depends on pick_tasks GREEN)
- CockpitView (B-15/B-16) may additionally depend on C-18 (#1063 engine activity/session wiring) at build time for list_activity/list_sessions — not added as formal dependency since tests can mock the activity store