---
id: 826
title: Slim server pick_tasks to thin wrapper
status: archived
priority: medium
created: '2026-04-10T21:23:21.110689+00:00'
updated: '2026-04-13T20:44:19.152543+00:00'
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
[[2026-04-13]]
## Builder Notes

### Files changed
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — removed `import re`; added `from owlbear_kanban.dispatch import pick_dispatchable`; deleted 48-line block (`_PICK_AC_PATTERN`, `_PICK_CLARITY_STATUSES`, `_PICK_NON_IMPL_TAGS`, `_PICK_PRIORITY_RANK`, `_PICK_STATUS_RANK`, `_PICK_MAX_PRIORITY_RANK`, `_PICK_MAX_STATUS_RANK`, `_check_pick_gates`); replaced `pick_tasks` body with 3-line delegation
- `tests/test_slim_server_pick_tasks_826.py` — no changes (canonical AC tests, passed as written)
- `tests/test_server_pick_tasks_thin_wrapper_825.py` — updated 4 AC3 regression-guard tests to use `patch("owlbear_mcp_kanban.server.pick_dispatchable")` mock (as noted in task body AC5 requirement)
- `tests/test_kanban_mcp_migration.py` — updated 5 superseded pick_tasks tests to use `pick_dispatchable` mock (AC6 requirement)
- `tests/test_mcp_adapter_slimming_819.py` — updated 1 superseded pick_tasks test to use `pick_dispatchable` mock (AC6 requirement)

### Test results
- `test_slim_server_pick_tasks_826.py`: **7 passed** (was 7 FAIL RED) ✅
- `test_server_pick_tasks_thin_wrapper_825.py`: **14 passed** ✅
- `test_kanban_mcp_migration.py + test_mcp_adapter_slimming_819.py + test_pick_dispatchable_823.py`: **107 passed** ✅
- Full scope suite (152 tests): **152 passed** ✅

### Coverage
- `owlbear_mcp_kanban/server.py`: **92%** (with all MCP test files) ✅

### Lint
- ruff: **clean** ✅

### Commit
- `37784a5b` on `dev` — feat(mcp-kanban): slim pick_tasks to thin wrapper via pick_dispatchable (#826)

### Evidence summary
- AC1: `pick_tasks` calls `pick_dispatchable(engine, limit=limit, tag=tag)` — verified by 7 new tests + 5 updated tests
- AC2: All 8 `_PICK_*` symbols + `_check_pick_gates` removed from server.py — verified by tests
- AC3: Response format `{"dispatch": [{"task_id": int, "status": str}]}` unchanged — verified by regression guards
- AC4: Task.id → task_id int, Task.status → status str — verified by TestFromAC_BoundaryConversion (4 tests)
- AC5: #825 tests GREEN (14/14) ✅
- AC6: All existing MCP tests pass — 107/107 ✅
[[2026-04-13]]
## Review Evidence
### Test Results
- pytest (scoped): **129 passed, 0 failed** — quality-runner independent run
- test_slim_server_pick_tasks_826.py: 7 passed
- test_server_pick_tasks_thin_wrapper_825.py: 14 passed
- test_kanban_mcp_migration.py + test_mcp_adapter_slimming_819.py + test_pick_dispatchable_823.py: 107 passed

### Lint
- ruff: **clean** (0 violations across all changed files)

### Coverage
- `owlbear_mcp_kanban.server`: **92%** (combined MCP test suite)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: server.py pick_tasks calls pick_dispatchable(engine, ...) | test_pick_tasks_passes_engine_as_first_positional_arg | Yes — asserts args[0] is mock_engine with specific identity check | COVERED |
| AC2: _PICK_MAX_PRIORITY_RANK removed | test_no_pick_max_priority_rank_in_server | Yes — hasattr check fails if symbol present | COVERED |
| AC2: _PICK_MAX_STATUS_RANK removed | test_no_pick_max_status_rank_in_server | Yes — hasattr check fails if symbol present | COVERED |
| AC4: Task.id → task_id int | test_task_object_id_becomes_task_id_int_in_dispatch | Yes — exact value + isinstance(int) check | COVERED |
| AC4: Task.status → status str | test_task_object_status_becomes_status_str_in_dispatch | Yes — exact value + isinstance(str) check | COVERED |
| AC4: multiple tasks ordered | test_multiple_task_objects_all_appear_in_dispatch_order | Yes — exact equality of both dispatch entries | COVERED |
| AC4: empty list → empty dispatch | test_empty_task_list_from_pick_dispatchable_yields_empty_dispatch | Yes — exact == {"dispatch": []} | COVERED |
| AC1 base + AC2 base + AC3 | test_server_pick_tasks_thin_wrapper_825.py (14 tests) | Yes — delegation, symbol removal, format | COVERED |
| AC5 + AC6 | test_kanban_mcp_migration.py / test_mcp_adapter_slimming_819.py | Yes — existing MCP contract preserved | COVERED |

#### Security Review
- No new system boundaries introduced — removal only
- No hardcoded secrets, injection vectors, or path traversal
- No new dependencies
- No issues

#### Test Integrity (TestFromAC Modifications)
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_PickTasksResponseFormat (4 tests, #825) | Mock target: `engine.list_tasks` → `pick_dispatchable` | PRESERVED — necessary mechanical update reflecting refactored code path; all assertions (isinstance, key sets, exact equality) unchanged |
| TestFromAC_PickTasks in test_kanban_mcp_migration.py (4 tests) | Mock target same swap; docstring stale but assertion logic equivalent | PRESERVED — delegation boundary verified at new boundary; no assertion dropped |
| test_mcp_adapter_slimming_819.py (1 test) | Mock target updated | PRESERVED |
| test_slim_server_pick_tasks_826.py (7 tests) | No changes — canonical AC tests | PRESERVED |

No WEAKENED or REMOVED tests detected.

#### Test Quality
- **Assertion specificity**: STRONG — exact type checks, exact value assertions, exact key-set assertions
- **Negative/error-path**: ADEQUATE — no error path in the 3-line thin wrapper (pick_dispatchable errors propagate naturally)
- **Manual mutation**: passing `str(t.id)` instead of `int(t.id)` would be caught by isinstance tests
- **Test independence**: PASS — no shared mutable state
- **Test names**: PASS — descriptive names throughout

#### Data Safety
- No LLM output, no shared mutable state, no multi-step atomicity concerns — removal only

#### Implementation-Aware Test Gap Analysis
- pick_tasks body is 3 lines with no branches: `tasks = pick_dispatchable(...)`, `return {"dispatch": [...]}`. Coverage 92% confirms all paths exercised. No significant untested paths.

#### Loop Detection
- 1 Builder Notes section → CLEAN

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: pick_tasks calls pick_dispatchable() | server.py L17 import, L337 call | TestFromAC_DelegationEngine; #825 delegation tests | PASS |
| AC2: No inline gating logic | grep confirms no _PICK_* in server.py; no _check_pick_gates | TestFromAC_NoInlineGatingComplete; #825 NoInlineGating tests | PASS |
| AC3: Response format unchanged | server.py L338: {"dispatch": [{"task_id": int(t.id), "status": str(t.status)}]} | TestFromAC_PickTasksResponseFormat (4 tests, updated mock) | PASS |
| AC4: Boundary conversion | int(t.id), str(t.status) at server.py L338 | TestFromAC_BoundaryConversion (4 tests) | PASS |
| AC5: #825 tests GREEN | 14/14 in quality-runner | test_server_pick_tasks_thin_wrapper_825.py | PASS |
| AC6: All MCP tests pass | 107/107 in quality-runner | test_kanban_mcp_migration.py + test_mcp_adapter_slimming_819.py | PASS |

### Deductions
- 0 deductions

### Verdict
PASS #826 → docs | confidence .96
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | pick_tasks response format unchanged ({\"dispatch\": [{\"task_id\": int, \"status\": str}]}); copilot-instructions.md has no entry for pick_tasks or dispatch logic |
| 2 | Module docstrings | Yes | Verified | server.py pick_tasks docstring accurate post-refactoring: "Pick dispatchable tasks: gate-filtered, sorted by priority/status, capped at limit. Optional tag pre-filters candidates before gating (e.g. 'phase-2')." No edit needed. |
| 3 | External attribution | No | N/A | Research doc states all 5 high-relevance sources were codebase-internal (no external repos, articles, or docs) |
| 4 | CLI changes | No | N/A | MCP server internal refactoring only — no CLI commands added or modified |
| 5 | Research doc | Yes | Verified | .owlbear/research/slim-server-pick-tasks.md exists; linked in task body; follow-up #848 created (status: research) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no .owlbear/scratch/826-* files found)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: server.py pick_tasks calls pick_dispatchable() | server.py L17 import, L337 `pick_dispatchable(app_ctx.engine, limit=limit, tag=tag)` | PASS |
| AC2: No inline gating logic in server.py | grep `_PICK_*\|_check_pick_gates` → 0 matches in server.py | PASS |
| AC3: Response format unchanged | server.py L338: `{"dispatch": [{"task_id": int(t.id), "status": str(t.status)}]}` | PASS |
| AC4: Boundary conversion in server | server.py L338: `int(t.id)`, `str(t.status)` at server layer | PASS |
| AC5: #825 tests GREEN | 14/14 passed (in 697 total) | PASS |
| AC6: All existing MCP tests pass | 107/107 passed (in 697 total) | PASS |

### Test Results
- pytest: 697 passed, 6 failed (0 in task scope — all pre-existing failures in orchestrator, knowledge, planner, agent-validation, memory, doc-writer domains), 1 skipped
- ruff: clean

### Architect Quality: 4/5
AC was precise and testable across all 6 lines. Minor imprecision: AC4 says "Task to KanbanTask" but actual conversion is Task to dict — clarified by research doc. No builder improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (−0)
- Lint violations: 0 (−0)
- AC quality ≤ 3: no (−0)
- Missing reviewer evidence: no (−0) — reviewer section thorough with per-AC mapping
- In-scope test failures: 0 (−0)

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3d7141f2 | test | tests/test_slim_server_pick_tasks_826.py | #826 |
| 37784a5b | feat | server.py, test_kanban_mcp_migration.py, test_mcp_adapter_slimming_819.py, test_server_pick_tasks_thin_wrapper_825.py | #826 |