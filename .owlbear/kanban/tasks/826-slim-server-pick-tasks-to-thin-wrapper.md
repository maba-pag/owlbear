---
id: 826
title: Slim server pick_tasks to thin wrapper
status: in-progress
priority: important
created: '2026-04-10T21:23:21.110689+00:00'
updated: '2026-04-12T14:14:00.118217+00:00'
tags:
- phase-3
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 825
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `server.py` `pick_tasks` MCP tool calls `pick_dispatchable()` from `owlbear_kanban.dispatch`
- No inline gating logic remains in `server.py` (no `_check_pick_gates`, no rank maps)
- Response format unchanged: dispatch wrapper with task details
- Boundary conversion from `Task` to `KanbanTask` happens in server
- #825 tests pass GREEN
- All existing MCP tests pass (O4)

## Context

Phase 3, step 4. Final task. Depends on #825 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/slim-server-pick-tasks.md
- Sources: 8 studied, 5 high-relevance (all codebase-internal)
- Recommendation: Option A — direct delegation with mock updates (confidence: .90)
  - Remove 8 module-level symbols + `_check_pick_gates` + `import re` from server.py
  - Add `from owlbear_kanban.dispatch import pick_dispatchable` import
  - Replace pick_tasks body with 3-line delegation: `pick_dispatchable(engine, limit=limit, tag=tag)` → format dispatch dict
  - Update 6 superseded tests to mock `pick_dispatchable` instead of `engine.list_tasks`
- Key finding: AC3 regression guard tests from #825 will break after refactoring — builder must add `patch("owlbear_mcp_kanban.server.pick_dispatchable")` to provide test Task data
- Key finding: "Boundary conversion from Task to KanbanTask" AC line is a principle, not a format change — dispatch dict format stays `{"task_id": int, "status": str}`
- Blocker: #824 (dispatch.py) must be complete first — currently in-progress
- Follow-up tasks created: #848 (clean up stale test_pick_tasks.py — 38 pre-existing broken tests)
- Decision requests: none
- Tier: T1 — mechanical extraction of pre-existing logic, no new capability
[[2026-04-12]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One thing: slim server.py pick_tasks to thin wrapper delegating to dispatch.py |
| Interface clarity | PASS | AC specifies delegation target, removal scope, format preservation, and test requirements |
| Dependency correctness | PASS | depends_on: [825] correct; transitive chain #824→#825→#826 properly ordered |
| Module layering | PASS | Server imports from owlbear_kanban.dispatch (lower layer), no upward imports |
| TDD compliance | PASS | #825 is the RED test task preceding this GREEN implementation |
| KISS/YAGNI | PASS | Mechanical extraction of pre-existing logic, no new capability (T1) |
| Premise challenge | PASS | Required by Phase 3 brief O3: dispatch logic importable without MCP server |
| Pattern consistency | PASS | Follows existing server thin-wrapper pattern used by other tools |
| Security surface | N/A | No new system boundaries — removal only |
| Single domain | PASS | scope:mcp-kanban only |

### AC Assessment
| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1: server.py pick_tasks calls pick_dispatchable() | Clear, testable via delegation mock at owlbear_mcp_kanban.server.pick_dispatchable | None |
| AC2: No inline gating logic in server.py | Clear, testable via hasattr checks for 8 _PICK_* symbols + _check_pick_gates | None |
| AC3: Response format unchanged | Clear, regression guards in #825 AC3 tests | None |
| AC4: Boundary conversion Task→KanbanTask in server | Principle, not format change — research §3.3 clarifies dispatch dict stays as-is | Acceptable with research context |
| AC5: #825 tests pass GREEN | Clear, runnable | None |
| AC6: All existing MCP tests pass (O4) | Clear — covers 6 superseded tests needing mock update from engine.list_tasks to pick_dispatchable | None |

### Codebase Evidence
- server.py L6: `import re` — sole consumer is _PICK_AC_PATTERN, safe to remove
- server.py L326-374: 8 _PICK_* module-level symbols + _check_pick_gates — all targeted for removal, none in __all__
- server.py L376-399: pick_tasks inline logic — replaced by 3-line delegation to pick_dispatchable()
- dispatch.py exists with pick_dispatchable(engine, *, limit, tag) -> list[Task] — server formats to {"dispatch": [...]}
- 6 pre-existing tests will break: 5 in test_kanban_mcp_migration.py (L600-660, L818-840), 1 in test_mcp_adapter_slimming_819.py (L277-291) — all mock engine.list_tasks, need update to mock pick_dispatchable. Covered by AC6.
- 4 AC3 regression guards in test_server_pick_tasks_thin_wrapper_825.py also need mock target update — covered by AC5.

### Challenge Results
- Challenger: FALLBACK — challenger subagent not in available agent list
- Architect response: Proceeded with APPROVE based on thorough codebase verification, precise AC, and complete research doc

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable. Research doc provides detailed implementation guidance including exact line changes and test impact matrix. Dependency chain #824→#825→#826 correctly ordered. T1 mechanical extraction with no architectural risk.
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_slim_server_pick_tasks_826.py
- Classes: TestFromAC_DelegationEngine, TestFromAC_NoInlineGatingComplete, TestFromAC_BoundaryConversion
- Tests per category: happy 4, edge 1, error 0, boundary 2
- Total: 7 tests, all FAIL
- ruff: clean
- Commit: 3d7141f2

### AC Coverage Table
| AC line | Tests | Status |
|---------|-------|--------|
| AC1: server calls pick_dispatchable(engine, ...) | test_pick_tasks_passes_engine_as_first_positional_arg | RED |
| AC2: no _PICK_MAX_PRIORITY_RANK in server | test_no_pick_max_priority_rank_in_server | RED |
| AC2: no _PICK_MAX_STATUS_RANK in server | test_no_pick_max_status_rank_in_server | RED |
| AC4: Task.id → task_id int | test_task_object_id_becomes_task_id_int_in_dispatch | RED |
| AC4: Task.status → status str | test_task_object_status_becomes_status_str_in_dispatch | RED |
| AC4: multiple Task objects ordered | test_multiple_task_objects_all_appear_in_dispatch_order | RED |
| AC4: empty list → empty dispatch | test_empty_task_list_from_pick_dispatchable_yields_empty_dispatch | RED |

### Gap rationale
- AC1 base (delegation + limit + tag kwargs) covered by #825 — this file adds the engine-arg gap.
- AC2 base (_check_pick_gates, _PICK_PRIORITY/STATUS_RANK, _PICK_AC_PATTERN, _PICK_CLARITY_STATUSES, _PICK_NON_IMPL_TAGS) covered by #825 — this file adds the two omitted _PICK_MAX_* symbols (8th-of-8).
- AC3 regression guards in #825 use engine.list_tasks mock (current code); after refactoring builder must update them (#825 AC5). AC4 tests here are the canonical post-refactor regression guard pattern using pick_dispatchable mock.
- AC5 (#825 tests GREEN) and AC6 (O4 pass) are verified by builder at GREEN phase — no additional test files needed.

### RED failure modes (verified by pytest)
- 5 tests: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attr
- 2 tests: AssertionError — _PICK_MAX_PRIORITY_RANK/_PICK_MAX_STATUS_RANK still in server.py