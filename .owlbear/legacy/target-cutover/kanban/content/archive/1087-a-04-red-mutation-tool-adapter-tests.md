---
id: 1087
title: 'A-04: RED — mutation tool adapter tests'
status: archived
priority: medium
created: 2026-04-21 10:53:48.099115+00:00
updated: 2026-04-28T05:37:50.430721+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:red
parent: 1045
depends_on:
- 1083
- 1085
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.4–§5.5, paper-integration.md §1.4–§1.5
Module: `serve/mcp-kanban/tests/test_mcp_mutation_tools.py`

Test the 2 mutation tool adapters: `create_task`, `edit_task`. All tests mock `AgentView`. Tests verify: correct AgentView method called with correct args, SingleTaskResponse returned, KanbanError → ToolError mapping.

## Acceptance Criteria

- [ ] `create_task`: title, body, priority, tags, parent, depends_on forwarded; SingleTaskResponse returned (AC24 — dep validation delegated to engine)
- [ ] `create_task`: no `status` param accepted (engine controls entry status per D50)
- [ ] `edit_task`: all 13 params forwarded; SingleTaskResponse returned
- [ ] `edit_task`: `body` + `append_body` both set → engine raises ValidationError → adapter maps to ToolError (AC14)
- [ ] `edit_task`: `archival_reason` / `archival_refs` on non-archived → engine raises → ToolError
- [ ] `edit_task`: no-op call → engine raises → ToolError
- [ ] Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message
- [ ] All tests fail (RED phase)
[[2026-04-24]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Classes: TestFromAC_CreateTaskAdapter, TestFromAC_EditTaskAdapter, TestFromAC_KanbanErrorMapping
- Tests per category: happy 10, edge 3, error 9, boundary 0
- Total: 22 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| create_task: all 6 params forwarded to AgentView | test_calls_agent_view_create_task, test_forwards_title, test_forwards_body, test_forwards_priority, test_forwards_tags_as_list, test_forwards_parent, test_forwards_depends_on_as_list |
| create_task: no status param (D50) | test_create_task_has_no_status_parameter |
| create_task: SingleTaskResponse returned | test_create_task_returns_single_task_response |
| create_task: dep validation → ToolError (AC24) | test_create_task_dep_not_found_raises_tool_error |
| edit_task: all 13 params forwarded | test_edit_task_forwards_all_13_params, test_edit_task_forwards_id_as_int |
| edit_task: SingleTaskResponse returned | test_edit_task_returns_single_task_response |
| edit_task: body+append_body → ToolError (AC14) | test_edit_task_body_and_append_body_raises_tool_error |
| edit_task: archival_reason on non-archived → ToolError | test_edit_task_archival_reason_on_non_archived_raises_tool_error |
| edit_task: archival_refs on non-archived → ToolError | test_edit_task_archival_refs_on_non_archived_raises_tool_error |
| edit_task: no-op → ToolError | test_edit_task_no_op_raises_tool_error |
| KanbanError → ToolError with user_message | test_validation_error_user_message_in_tool_error, test_not_found_error_maps_to_tool_error, test_concurrency_error_maps_to_tool_error, test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception |

### Failure analysis (selected)
- adapter calls `engine.create_task()` not `engine.agent_view().create_task()` → 7 assertion failures
- `status` param still present on `create_task` → 1 assertion failure
- returns `KanbanTask` not `SingleTaskResponse` → 2 assertion failures
- `edit_task` missing `block_reason`/`archival_reason`/`archival_refs` params → TypeError → 3 failures
- `KanbanError` not caught; only `ValueError`/`FileNotFoundError` → 4 "Did not raise" failures

Commit: `8ddd2bb9` — serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py (512 lines)
[[2026-04-24]]
## Builder Notes
- Scope reviewed: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py and serve/mcp-kanban/src/owlbear_mcp_kanban/server.py.
- RED verification rerun via quality-runner did not reach adapter assertions. Fixture setup fails at KanbanEngine init with ConfigError: agent_map missing status entries for all board statuses.
- Evidence: failure occurs in app_ctx_with_mock_agent_view when loading _CONFIG_YAML lacking required agent_map keys.
- Result: Test assumptions are currently infeasible against the active engine config contract, so GREEN verification cannot be completed.
- test-writer: update fixture config in test_mcp_mutation_tools_1087.py to include a valid agent_map for all statuses, then rerun RED and requeue builder.
[[2026-04-24]]
## Test-Writer Notes (revision)
- Test file: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Commit: 1c85a4ed — fixture fix + test bug fix

### Changes made
1. **Fixture fix**: Added `agent_map` for all 7 statuses to `_CONFIG_YAML` in both `test_mcp_mutation_tools_1087.py` and `test_mcp_read_tools.py`. `_validate_engine_config` (added since original RED write) requires every status in `agent_map`; blank `{}` caused `ConfigError` at `KanbanEngine.__init__`.
2. **Test bug fix**: `test_create_task_forwards_title` was raising `IndexError` because `args[0]` was accessed on an empty tuple (adapter passes `title` as keyword, not positional). Fixed to `call.args[0] if call.args else call.kwargs.get("title")`.

### Current state: 22/22 PASS (adapter pre-implemented)
After fixing the fixture, all 22 tests pass. The adapter in `server.py` was updated (in a different task/session, prior to this builder attempt) to:
- Call `engine.agent_view().create_task()` (not `engine.create_task()` directly)
- Call `engine.agent_view().edit_task()` with all 13 params
- Map `KanbanError` → `ToolError` with `user_message`
- Exclude `status` from `create_task` signature (D50)
All AC lines are satisfied by the current adapter implementation.

### For builder
Tests are GREEN — verify all 22 pass and advance to review. No code changes needed to `server.py`.

### AC Coverage
| AC | Status |
|----|--------|
| create_task: 6 params forwarded to AgentView | 7 tests PASS |
| create_task: no status param (D50) | 1 test PASS |
| create_task: SingleTaskResponse returned | 1 test PASS |
| create_task: dep validation → ToolError (AC24) | 1 test PASS |
| edit_task: all 13 params forwarded | 2 tests PASS |
| edit_task: SingleTaskResponse returned | 1 test PASS |
| edit_task: body+append_body → ToolError (AC14) | 1 test PASS |
| edit_task: archival_reason on non-archived → ToolError | 1 test PASS |
| edit_task: archival_refs on non-archived → ToolError | 1 test PASS |
| edit_task: no-op → ToolError | 1 test PASS |
| KanbanError → ToolError with user_message | 4 tests PASS |

[[2026-04-24]]
## Builder Notes
- Validation only: no source edits required; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` already satisfies AC per revised Test-Writer notes.
- Tests: 22/22 passed in `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py` (quality-runner scoped).
- Lint: ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`.
- Coverage: 41% on `owlbear_mcp_kanban.server` in scoped run; no builder code changes in this pass.
- Evidence summary: adapter contract behaviors and KanbanError→ToolError mapping are verified by the 22 AC-linked tests, all green.

[[2026-04-28]]
## Review Evidence
### Test Results
- Scoped quality-runner: pytest 22 passed, 0 failed on serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.

### Lint
- Scoped ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.

### Coverage
- Scoped run: owlbear_mcp_kanban.server 43% (below the 90% review gate).
- Broader server-context run: 111 passed, 14 failed; owlbear_mcp_kanban.server 60% (still below gate). I used the broader run as regression context only; the primary rejection basis below stays tied to 1087 ownership.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| create_task: title/body/priority/tags/parent/depends_on forwarded; SingleTaskResponse returned | server.py:275-293 forwards the six fields; task tests cover each forwarded field and dep validation; live AgentView.create_task already returns SingleTaskResponse in engine.py:2437-2527 | PASS |
| create_task: no status param accepted | server.py:275-283 has no status param; test_mcp_mutation_tools_1087.py:267 checks the public signature | PASS |
| edit_task: all 13 params forwarded; SingleTaskResponse returned | happy-path forwarding proof only covers populated values in test_mcp_mutation_tools_1087.py:314-349; adapter drops falsey/default inputs at server.py:382-404; AgentView distinguishes explicit block_reason presence from omission via engine.py:2601 and engine.py:2709-2715 | FAIL |
| edit_task: body + append_body -> ToolError | test_mcp_mutation_tools_1087.py:380-393 plus server.py:407-408 | PASS |
| edit_task: archival_reason / archival_refs on non-archived -> ToolError | test_mcp_mutation_tools_1087.py:397-427 plus server.py:407-408 | PASS |
| edit_task: no-op call -> ToolError | test_mcp_mutation_tools_1087.py:431-444 plus server.py:407-408 | PASS |
| Error mapping: KanbanError subclasses -> ToolError with user_message | exact user_message checks exist for ValidationError/NotFoundError/ConcurrencyError at test_mcp_mutation_tools_1087.py:458-509; adapters raise ToolError(exc.user_message) at server.py:296 and server.py:408 | PASS |

Note on stale AC text: the top-level checkbox "All tests fail (RED phase)" is superseded by the later Test-Writer revision in the task body that records the fixture repair and current green state. I reviewed the latest task-body refinement, not the stale earlier checkbox text.

#### Security Review
- No issues in the reviewed adapter scope. The touched paths are argument-forwarding and KanbanError -> ToolError translation only.

#### Test Integrity
- No evidence in the current file of weakened or removed TestFromAC methods. The three expected TestFromAC classes remain present and aligned with the task body.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | exact user_message checks exist for representative subclasses at test_mcp_mutation_tools_1087.py:458, :476, :494 |
| Negative/error-path breadth | STRONG | dedicated tests exist for dep not found, body+append_body, archival field misuse, no-op, and multiple KanbanError subclasses |
| Test independence and naming | STRONG | tmp_path-backed fixture and descriptive TestFromAC method names |

#### Data Safety
- No issues found in the reviewed scope.

#### Implementation-Aware Gaps
- AC3 is under-proved. The suite never exercises the explicit clear/unset path for block_reason. The adapter only forwards block_reason when truthy at server.py:400-401, while AgentView.edit_task distinguishes explicit presence from omission via engine.py:2601 and engine.py:2709-2715. The current green suite only checks a populated block_reason value at test_mcp_mutation_tools_1087.py:320-349.
- Coverage is still below gate even after broadening context: 43% on the task-owned scoped run and 60% on the broader server-context run. The green subset is not enough proof for owlbear_mcp_kanban.server.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- I did not count the adapter's direct return of AgentView.create_task/edit_task as a defect by itself, because the live AgentView methods already return SingleTaskResponse in engine.py:2437-2527 and engine.py:2529-2778.
- The broader server-context run surfaced adjacent guidance-suite failures, but I treated those as regression context rather than primary 1087 ownership.

### Verdict
- Deductions: coverage gate miss; AC3 forwarding-proof gap.
- Confidence: 0.84
- Verdict: FAIL
- Action: return to todo. Test-writer should add task-owned coverage for the falsey/default edit_task forwarding path (especially block_reason clear vs omission behavior) and expand server proof enough to satisfy the coverage gate; builder will likely need a follow-up adapter fix once those tests are red.
[[2026-04-28]]
## Test-Writer Notes (retry)
- Test file: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Classes: TestFromAC_EditTaskAdapter (additions)
- Tests per category: 0 happy, 1 edge (empty block_reason), 0 error, 1 boundary (signature default)
- New total: 24 tests — 22 PASS (existing), 2 FAIL (new)
- ruff: clean
- Commit: bae406ad

### AC Coverage (retry additions)

| Reviewer Gap | Tests Added |
|---|---|
| AC3: `block_reason` clear/omission forwarding-proof gap | test_edit_task_block_reason_default_is_none, test_edit_task_empty_block_reason_forwarded_to_unblock |

### Failure analysis (new tests)
- `test_edit_task_block_reason_default_is_none`: `edit_task` `block_reason` param defaults to `""` not `None`; adapter cannot distinguish omission from explicit unblock. Asserts `default is None` → FAIL.
- `test_edit_task_empty_block_reason_forwarded_to_unblock`: adapter uses `if block_reason:` which silently drops `""`. Asserts `"block_reason" in kwargs` when called with `block_reason=""` → FAIL.

### Builder note on coverage gate
Coverage is 43% (scoped) / 60% (full suite) on `owlbear_mcp_kanban.server`. The gap is structural — the server module contains 10+ tool functions; this task's scope covers 2 of them. After fixing the adapter, coverage improves by the new block_reason branches. Full 90% gate requires the other lifecycle/read-tool test files to be included in the coverage run (or a separate coverage-scoped task).
[[2026-04-28]]
## Builder Notes
- Implementation: [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py)
- Fixes applied: updated `edit_task` to preserve omission-vs-explicit-unblock semantics by changing `block_reason` default to `None` and forwarding whenever `block_reason is not None` (so `""` is forwarded).
- Commit: `5b929d56`.
- Tests (task-scoped): 24 passed, 0 failed in [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py) via quality-runner.
- Lint (task-scoped): clean for [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py) and [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py).
- Coverage: 38% on `owlbear_mcp_kanban.server` in task-scoped run.
- Broader context run: mcp-kanban suite reached 60% on `owlbear_mcp_kanban.server`, with 15 unrelated guidance-suite failures not introduced by this change.
- Evidence summary: both retry RED failures are now GREEN (`block_reason` default contract and explicit empty-string forwarding for unblock), while preserving existing KanbanError -> ToolError mapping behavior.
[[2026-04-28]]
## Review Evidence
### Scope
- Task-owned suite reviewed: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Runtime adapter reviewed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Live engine contract checked: serve/kanban/src/owlbear_kanban/engine.py and serve/kanban/tests/test_engine_create_edit_1070.py

### Test Results
- Scoped quality-runner: pytest 24 passed, 0 failed on serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.
- Broader package-context quality-runner: pytest 294 passed, 13 failed across serve/mcp-kanban/tests. I used this broader run for module-coverage and regression context only, not as the primary ownership gate.

### Lint
- Scoped ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.

### Coverage
- Scoped run: owlbear_mcp_kanban.server 38%.
- Broader package-context run: owlbear_mcp_kanban.server 60%.
- The review coverage gate is unmet in both runs.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Were Violated? | Verdict |
|---------|-------------|---------------------------------|---------|
| create_task forwards title, body, priority, tags, parent, depends_on and returns SingleTaskResponse | Forwarding proof is direct in test_create_task_forwards_title/body/priority/tags_as_list/parent/depends_on_as_list; response proof is only test_create_task_returns_single_task_response at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:254-263 | Forwarded fields: yes. Response contract: not fully. The test preloads the mock with SingleTaskResponse and only asserts isinstance, so a transformed or replacement SingleTaskResponse would still pass. | LAX |
| create_task does not accept status | test_create_task_has_no_status_parameter at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:267-272 | Yes. The signature inspection would fail immediately if status were exposed. | COVERED |
| edit_task forwards all 13 params and returns SingleTaskResponse | Forwarding proof is direct in test_edit_task_forwards_all_13_params, test_edit_task_forwards_id_as_int, and the new block_reason tests at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:447-481; response proof is only test_edit_task_returns_single_task_response at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:366-375 | Forwarded fields: yes, including the explicit empty-string unblock path. Response contract: not fully. The test again preloads the mock with SingleTaskResponse and only asserts isinstance. | LAX |
| edit_task body plus append_body maps engine ValidationError to ToolError | test_edit_task_body_and_append_body_raises_tool_error at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:380-393 | Yes. It requires ToolError on the named adapter entry point. | COVERED |
| edit_task archival_reason and archival_refs on non-archived map engine error to ToolError | test_edit_task_archival_reason_on_non_archived_raises_tool_error and test_edit_task_archival_refs_on_non_archived_raises_tool_error at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:397-427 | Yes. Both require ToolError. | COVERED |
| edit_task no-op call maps engine error to ToolError | test_edit_task_no_op_raises_tool_error at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:431-444 | Yes. It requires ToolError on the adapter entry point. | COVERED |
| KanbanError subclasses map to MCP ToolError with user_message | test_validation_error_user_message_in_tool_error, test_not_found_error_maps_to_tool_error, test_concurrency_error_maps_to_tool_error, test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:495-562 | Yes. The suite asserts ToolError plus exact user_message propagation for representative subclasses and the base class. | COVERED |

#### Security Review
- No issues found in the reviewed boundary scope. The task covers typed argument forwarding and KanbanError to ToolError translation only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suite for task 1087 | No builder-authored weakening or removal observed. The retry added two block_reason tests at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:447-481 and they strengthen the D53 omission versus explicit-unblock proof. | PRESERVED / STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The response-contract tests at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:254-263 and :366-375 seed the mock with SingleTaskResponse and only assert isinstance on the returned value. That does not prove passthrough fidelity or payload correctness. |
| Negative and error-path coverage | STRONG | Dedicated ToolError tests exist for dependency validation, body plus append_body, archival misuse, no-op, and representative KanbanError subclasses. |
| Manual mutation reasoning | WEAK | A regression that returns a different SingleTaskResponse payload from create_task or edit_task would stay green under the current type-only assertions. |
| Test independence | STRONG | The fixture builds a fresh board and fresh MagicMock AgentView for each test. |
| Descriptive test names | STRONG | Test names are behavior-specific and map cleanly to the AC lines. |

#### Data Safety
- No issues found in the reviewed scope.

#### Implementation-Aware Gaps
- The builder fix for D53 is real. The MCP adapter now defaults block_reason to None and forwards block_reason whenever it is not None in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:392-438. The live AgentView contract in serve/kanban/src/owlbear_kanban/engine.py:2529-2778 distinguishes omission from explicit empty-string unblock via the _BLOCK_REASON_UNSET sentinel, and the new task tests plus serve/kanban/tests/test_engine_create_edit_1070.py:336-379 align with that behavior.
- The remaining gap is proof scope, not the D53 implementation. Module coverage for owlbear_mcp_kanban.server remains 38% in the task-owned run and 60% even in broader package context, both below the 90% review gate. For a task scoped to two mutation adapters inside a larger server module, that gap now looks structural rather than a small missing branch.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- create_task and edit_task return AgentView results directly in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:305-326 and :392-438. I did not count that as an implementation defect because the live AgentView methods already return SingleTaskResponse in serve/kanban/src/owlbear_kanban/engine.py:2437-2527 and :2529-2778.
- The broader package-context run still shows adjacent guidance-suite failures in the same module, but I treated those as regression context only. The owned rejection basis is already established by weak response proof plus the unresolved module-coverage gate.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| create_task forwarding and SingleTaskResponse | Forwarded field assertions are direct; response proof is type-only at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:254-263 | test_create_task_forwards_* and test_create_task_returns_single_task_response | FAIL |
| create_task omits status | Signature check at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:267-272 | test_create_task_has_no_status_parameter | PASS |
| edit_task forwards all 13 params and SingleTaskResponse | Forwarding proof is direct including empty-string unblock; response proof is type-only at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:366-375 | test_edit_task_forwards_all_13_params, test_edit_task_forwards_id_as_int, test_edit_task_empty_block_reason_forwarded_to_unblock, test_edit_task_returns_single_task_response | FAIL |
| edit_task body plus append_body error mapping | ToolError assertion on adapter entry point | test_edit_task_body_and_append_body_raises_tool_error | PASS |
| edit_task archival field misuse error mapping | ToolError assertions on adapter entry point | test_edit_task_archival_reason_on_non_archived_raises_tool_error, test_edit_task_archival_refs_on_non_archived_raises_tool_error | PASS |
| edit_task no-op error mapping | ToolError assertion on adapter entry point | test_edit_task_no_op_raises_tool_error | PASS |
| KanbanError subclass mapping with user_message | Exact user_message assertions for representative subclasses plus base KanbanError catch | test_validation_error_user_message_in_tool_error, test_not_found_error_maps_to_tool_error, test_concurrency_error_maps_to_tool_error, test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception | PASS |

### Deductions
- Response-contract assertions for both adapters are too weak for a mocked boundary task. They prove type only, not exact passthrough or payload fidelity.
- owlbear_mcp_kanban.server remains far below the 90% module-coverage gate even after broadening context, which makes the current review gate infeasible at this task boundary.

### Verdict
- Confidence: 0.88
- Verdict: FAIL
- Action: move back to backlog. Architect should re-scope the coverage obligation for owlbear_mcp_kanban.server or split the broader module-proof requirement into a separate task, then Test-Writer should tighten the response-contract assertions from type-only checks to exact passthrough or payload-equality proof.
[[2026-04-28]]

## Architecture Review
### AC Refinements

**Response-contract tightening (AC lines 1 & 3):** "SingleTaskResponse returned" → "adapter returns the unmodified SingleTaskResponse from AgentView — tests must prove passthrough fidelity (e.g. `result is expected` or field-equality on the returned envelope), not just `isinstance`."

**RED-phase AC line (AC line 8):** Satisfied. Test-writer delivered 22 failing tests (commit 8ddd2bb9); test-writer revision added 2 more (commit bae406ad). Builder made all 24 green (commits 1c85a4ed, 5b929d56). This is the expected RED→GREEN pipeline lifecycle, not a contract violation.

**Coverage scope (reviewer request):** The 90% module-coverage gate is structurally infeasible for a task covering 2 of 8 tool functions in `owlbear_mcp_kanban.server`. Coverage gate for this task applies to the task-owned adapter codepaths (`create_task`, `edit_task` functions and their error-mapping branches) only. Module-wide coverage will be aggregated when sibling tasks (#1088 lifecycle adapters) complete. The reviewer should evaluate coverage of the task-owned functions, not the full module.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Covers exactly 2 mutation adapters + their error mapping |
| Interface clarity | PASS after refinement | Response-contract AC tightened to require passthrough proof |
| Dependency correctness | PASS | #1083 (models), #1085 (AgentView contract) both archived/done |
| Module layering | PASS | MCP adapter → AgentView → engine; no upward imports |
| TDD compliance | PASS | RED tests written first, builder GREEN followed |
| KISS/YAGNI | PASS | Thin forwarding adapters, no unnecessary abstraction |
| Premise challenge | PASS | MCP tool adapters are required infrastructure for kanban board access |
| Pattern consistency | PASS | Follows same adapter pattern as read tools (#1086); KanbanError→ToolError mapping consistent with module conventions |
| Security surface | PASS | Typed argument forwarding only; no user input parsing, no file I/O |
| Single domain | PASS | scope:mcp-kanban only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| create_task forwarding | AgentView raises KanbanError | ValidationError / NotFoundError | Yes — mapped to ToolError | Agent sees descriptive error |
| edit_task forwarding | AgentView raises KanbanError | ValidationError / ConcurrencyError | Yes — mapped to ToolError | Agent sees descriptive error |
| edit_task block_reason=None vs "" | Omission vs explicit unblock | N/A | Yes — sentinel semantics (D53) | Correct block state mutation |

### Challenge Results
- Challenger: reconsider (0.47)
- Key concerns: RED-phase governance drift, identity vs payload fidelity, coverage scoping undocumented
- Architect response: rebutted. (1) RED→GREEN is pipeline flow, not drift — documented above. (2) Accepted payload fidelity over strict identity — reflected in AC refinement. (3) Coverage scope now formally documented with rationale. (4) Sibling task status acknowledged as future work.

### Verdict: APPROVE (with refinement)
### Action: Advance to todo. Test-writer: tighten the 2 response-contract tests per refined AC (passthrough fidelity, not just isinstance). Coverage gate scoped to task-owned adapter functions.

[[2026-04-28]]
Architecture review complete. REFINE → APPROVE. AC refined: (1) response-contract tests must prove passthrough fidelity, not just isinstance; (2) coverage gate scoped to task-owned adapter functions (create_task, edit_task), not full module. Challenger rebutted at 0.47. RED→GREEN lifecycle documented as expected pipeline flow.
[[2026-04-28]]
## Test-Writer Notes (retry 2)
- Test file: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Retry action: pass-through (no new tests)
- 24 existing tests preserved

### Why pass-through

**Reviewer cited weak tests** (response-contract assertions use `isinstance`, not identity proof). Per w-tdd-red §1b: "If reviewer cites code quality, weak tests, or security (not missing tests): Pass through — the builder will address the findings."

**Architect directive** ("tighten the 2 response-contract tests to passthrough fidelity") cannot be executed in retry mode:
1. Modifying existing passing tests is prohibited in retry cycles.
2. New passthrough fidelity tests (`assert result is expected`) would be **GREEN immediately** — both adapters return the AgentView result directly with no post-processing (`return app_ctx.engine.agent_view().create_task(...)` and `return app_ctx.engine.agent_view().edit_task(...)`). Writing GREEN tests in RED phase is also prohibited.

### Coverage gate note (architect re-scope)
- 38% module coverage reflects the full `owlbear_mcp_kanban.server` module (8+ tool functions). Task-owned functions (`create_task`, `edit_task`) are fully covered by the existing 24 tests.
- Architect scoped the gate to task-owned adapter paths. Reviewer should evaluate coverage only on `create_task` and `edit_task` functions, not the full module.

### Passthrough fidelity by code inspection
- `create_task`: `return app_ctx.engine.agent_view().create_task(...)` — direct return, no transformation.
- `edit_task`: `return app_ctx.engine.agent_view().edit_task(int(task_id), **kwargs)` — direct return, no transformation.
- Identity `result is agent_view_return_value` holds by construction. Cannot be proven RED because the implementation is already correct.
[[2026-04-28]]
## Builder Notes
- Non-implementation pass-through on retry-2: no source edits were required in this builder cycle.
- Verification (quality-runner scoped): 24 passed, 0 failed on serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.
- Lint (quality-runner scoped): ruff clean for serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.
- Coverage (quality-runner scoped): owlbear_mcp_kanban.server 38% module-level.
- Coverage-scope note: per Architecture Review refinement in this task body, the gate for #1087 is task-owned adapter paths (create_task/edit_task), not full-module server coverage.
- Evidence summary: adapter behavior remains green for all 24 TestFromAC tests, including block_reason omission-vs-explicit-unblock semantics and KanbanError -> ToolError mapping.
[[2026-04-28]]
## Review Evidence
### Test Results
- Scoped quality-runner: pytest 24 passed, 0 failed on serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.

### Lint
- Scoped ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.

### Coverage
- quality-runner reports owlbear_mcp_kanban.server at 38% module coverage.
- Per the latest Architecture Review section in .owlbear/kanban/tasks/1087-a-04-red-mutation-tool-adapter-tests.md:302, the binding gate for #1087 is the task-owned create_task/edit_task adapter paths, not full-module server coverage. I did not count the 38% module figure as a blocking defect in this review.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| create_task forwards title/body/priority/tags/parent/depends_on and returns SingleTaskResponse | Forwarding is directly asserted in serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:175-251 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:311-333. The response-contract proof is still insufficient under the Architecture Review refinement at .owlbear/kanban/tasks/1087-a-04-red-mutation-tool-adapter-tests.md:302 because the test only asserts isinstance at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:263 while the production adapter directly returns the AgentView result at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:324. | test_create_task_forwards_* and test_create_task_returns_single_task_response | FAIL |
| create_task does not accept status | Signature check at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:267-272 matches serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:311-318. | test_create_task_has_no_status_parameter | PASS |
| edit_task forwards all 13 params and returns SingleTaskResponse | Forwarding and task_id coercion are directly asserted in serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:314-361 and 447-481 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:397-445. The response-contract proof is still insufficient under the same Architecture Review refinement because the test only asserts isinstance at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:375 while the adapter directly returns the AgentView result at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:443. | test_edit_task_forwards_all_13_params, test_edit_task_forwards_id_as_int, test_edit_task_empty_block_reason_forwarded_to_unblock, test_edit_task_returns_single_task_response | FAIL |
| edit_task body plus append_body maps engine ValidationError to ToolError | ToolError expectation at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:380-393 matches the KanbanError catch in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:444-445. | test_edit_task_body_and_append_body_raises_tool_error | PASS |
| edit_task archival_reason and archival_refs on non-archived map engine error to ToolError | ToolError expectations at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:397-427 match the same adapter mapping path. | test_edit_task_archival_reason_on_non_archived_raises_tool_error, test_edit_task_archival_refs_on_non_archived_raises_tool_error | PASS |
| edit_task no-op call maps engine error to ToolError | ToolError expectation at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:431-444 matches the same adapter mapping path. | test_edit_task_no_op_raises_tool_error | PASS |
| KanbanError subclasses map to MCP ToolError with user_message | Exact user_message checks exist at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:495-562; adapter catches KanbanError in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:332-333 and 444-445. | test_validation_error_user_message_in_tool_error, test_not_found_error_maps_to_tool_error, test_concurrency_error_maps_to_tool_error, test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception | PASS |

#### Security Review
- No issues in the reviewed adapter boundary. The task-owned code paths only forward typed inputs to AgentView and map KanbanError to ToolError.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task 1087 TestFromAC suite | No builder-authored weakening or removal observed in the current workspace state. The latest cycle passed through with no source edits; retry-added block_reason tests remain present. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The response tests only assert isinstance at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:263 and 375, despite the architect refinement in .owlbear/kanban/tasks/1087-a-04-red-mutation-tool-adapter-tests.md:302 requiring passthrough-fidelity proof stronger than type-only checks. |
| Negative and error-path coverage | STRONG | Dedicated ToolError tests exist for dependency validation, body plus append_body, archival misuse, no-op edit, and representative KanbanError subclasses. |
| Manual mutation reasoning | WEAK | A mutated adapter that returned a different SingleTaskResponse payload would stay green under the current type-only assertions even though the refined response contract forbids that. |
| Test independence and naming | STRONG | The fixture rebuilds a fresh tmp_path-backed board and MagicMock AgentView per test, and the test names map directly to the task contract. |

#### Data Safety
- No issues found in the reviewed scope.

#### Implementation-Aware Gaps
- The remaining gap is evidentiary, not a confirmed implementation bug. The production code directly returns AgentView results at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:324 and 443, but the task-owned tests do not prove the refined passthrough-fidelity contract.
- I did not retain the earlier module-coverage objection. The latest Architecture Review explicitly scoped coverage to the task-owned adapter paths.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- Engine sentinel semantics for omission versus explicit unblock remain aligned with the MCP adapter: serve/kanban/src/owlbear_kanban/engine.py:2542 and 2601 define and check _BLOCK_REASON_UNSET, and the task-owned block_reason tests still cover the explicit empty-string unblock path.
- The two earlier Review Evidence sections remain in the task body at .owlbear/kanban/tasks/1087-a-04-red-mutation-tool-adapter-tests.md:123 and 216. This review is therefore the third review failure on the same task.

### Deductions
- The architect-refined response contract is still not proved by the task-owned tests.
- Third review failure requires backlog routing under the reviewer loop-breaker rule.

### Verdict
- Confidence: 0.88
- Verdict: FAIL
- Action: reject to backlog. The remaining defect is test-proof quality after the latest architecture refinement, not module-wide coverage and not an obvious runtime bug. Architect and test-writer need a route for passthrough-fidelity evidence that is compatible with the current retry and TDD rules before this task re-enters review.
[[2026-04-28]]
## Architecture Review (retry)

### Prior Review History
Three consecutive review FAILs on the same evidentiary gap: response-contract tests assert `isinstance` but the refined AC requires passthrough fidelity. The workflow deadlocked because:
1. Test-writer retry rules pass through on "weak tests" (reviewer feedback, not missing tests)
2. New passthrough-fidelity tests would be GREEN immediately (adapter already correct)
3. Builder has nothing to fix — passes through

### Route Through Deadlock
The task re-enters `todo` with **architect-changed AC** (below). This is NOT a retry pass-through scenario. The test-writer implements new/changed AC, even when that means updating existing tests. The previous architect review already declared RED-phase satisfied (22 original failures + 2 retry failures). Updating 2 assertions for changed AC is a test refinement, not a new RED requirement.

### AC Refinement (supersedes prior Architecture Review §AC Refinements)
**Response-contract tests (AC lines 1 & 3):** The 2 response tests (`test_create_task_returns_single_task_response`, `test_edit_task_returns_single_task_response`) must assert passthrough identity: `assert result is expected`. Both tests already seed `expected = _make_single_task_response(...)` and set `mock_av.*.return_value = expected` — the only change is replacing the `isinstance` assertion with `result is expected`. This is justified by the local `_to_single_task_response` normalizer in the same module (server.py:172), which neighboring tools use; without identity proof, a future refactor routing through that normalizer would preserve type but alter payload.

**Coverage scope (unchanged from prior review):** Gate applies to task-owned adapter functions (`create_task`, `edit_task`), not full `owlbear_mcp_kanban.server` module. Module-wide coverage aggregates when sibling tasks complete.

**RED-phase AC line (unchanged):** Satisfied per prior review. No new RED requirement.

### Test-Writer Directive
Update these 2 existing tests (do NOT pass through — this is architect-changed AC):
1. `test_create_task_returns_single_task_response` — replace `isinstance(result, SingleTaskResponse)` with `result is expected`
2. `test_edit_task_returns_single_task_response` — replace `isinstance(result, SingleTaskResponse)` with `result is expected`

Both will be GREEN immediately. That is expected — the adapter is already correct. This is an evidentiary strengthening, not a new RED requirement.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 2 mutation adapters + error mapping only |
| Interface clarity | PASS after refinement | Response-contract AC now specifies exact assertion change |
| Dependency correctness | PASS | #1083, #1085 archived |
| Module layering | PASS | MCP adapter → AgentView → engine; no upward imports |
| TDD compliance | PASS | RED satisfied (24 failures across 2 commits); test refinement is not new RED |
| KISS/YAGNI | PASS | Thin forwarding adapters |
| Premise challenge | PASS | MCP tool adapters are required infrastructure |
| Pattern consistency | PASS | Same adapter pattern as read tools; KanbanError→ToolError consistent |
| Security surface | PASS | Typed argument forwarding only |
| Single domain | PASS | scope:mcp-kanban |

### Challenge Results
- Challenger: reconsider (0.41)
- Key concerns: (1) passthrough-fidelity gap is real — `_to_single_task_response` normalizer in same module makes type-preserving regression plausible; (2) workflow deadlock is a process issue, not proof that type-only is sufficient; (3) tests already seed expected objects but don't use them for assertion
- Architect response: **accepted concerns (1) and (2)**. Passthrough-fidelity requirement retained. Route through deadlock provided: architect-changed AC triggers test-writer implementation (not retry pass-through). Concern (3) confirms the fix is trivial — 1-line change per test.

### Verdict: APPROVE (with refinement)
### Action: Advance to todo. Test-writer: update 2 response tests per directive above. Builder: verify GREEN. Reviewer: coverage gate scoped to task-owned adapter functions.
[[2026-04-28]]
Architecture review (retry). REFINE → APPROVE. Passthrough-fidelity requirement retained (challenger accepted: _to_single_task_response normalizer makes type-preserving regression plausible). Route through 3-cycle deadlock: architect-changed AC triggers test-writer implementation, not retry pass-through. Test-writer directive: replace isinstance assertions with `result is expected` in 2 response tests. Coverage gate scoped to task-owned adapter functions.
[[2026-04-28]]
## Test-Writer Notes (retry 3)
- Test file: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Retry action: architect-changed AC — updated 2 response-contract assertions
- 24 tests total — all PASS (expected per architect: adapter already correct)
- ruff: clean
- Commit: 255fdd78

### Changes made
Per architect directive (Architecture Review retry section): replaced `isinstance` assertions with identity checks in 2 response tests:
1. `test_create_task_returns_single_task_response` — `assert result is expected`
2. `test_edit_task_returns_single_task_response` — `assert result is expected`

Both tests already seeded `expected = _make_single_task_response(...)` and set `mock_av.*.return_value = expected`. Only the assertion line changed. Tests remain GREEN because the adapters directly return the AgentView result (passthrough fidelity already implemented).

### AC Coverage
| AC Line | Tests | Status |
|---------|-------|--------|
| create_task: 6 params forwarded; SingleTaskResponse (passthrough identity) | 7 forwarding tests + test_create_task_returns_single_task_response (now `result is expected`) | COVERED |
| create_task: no status param (D50) | test_create_task_has_no_status_parameter | COVERED |
| create_task: dep validation → ToolError (AC24) | test_create_task_dep_not_found_raises_tool_error | COVERED |
| edit_task: all 13 params forwarded; SingleTaskResponse (passthrough identity) | 4 forwarding tests + test_edit_task_returns_single_task_response (now `result is expected`) | COVERED |
| edit_task: body+append_body → ToolError (AC14) | test_edit_task_body_and_append_body_raises_tool_error | COVERED |
| edit_task: archival_reason/refs on non-archived → ToolError | 2 tests | COVERED |
| edit_task: no-op → ToolError | test_edit_task_no_op_raises_tool_error | COVERED |
| KanbanError subclasses → ToolError with user_message | 4 tests | COVERED |

### Coverage gate note
Task-owned adapter functions (create_task, edit_task) are fully covered. Module-level 38% reflects the full server module (8+ tool functions beyond task scope). Architect scoped gate to task-owned adapter paths.
[[2026-04-28]]
## Builder Notes
- Implementation: no source edits in this builder pass; verified existing adapter behavior in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py against latest task AC refinement.
- Tests: 24 passed, 0 failed in serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py (quality-runner scoped).
- Coverage: 38% on owlbear_mcp_kanban.server in scoped run; per latest Architecture Review refinement in this task body, the acceptance gate for #1087 is task-owned create_task/edit_task adapter paths rather than full-module percentage.
- ruff: clean for serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.
- Evidence summary: response-contract identity assertions (architect refinement) are present in the task-owned suite and all adapter-forwarding and KanbanError->ToolError checks are green.
[[2026-04-28]]
## Review Evidence
### Scope
- Task-owned suite reviewed: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Runtime adapter reviewed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Live engine contract checked: serve/kanban/src/owlbear_kanban/engine.py

### Test Results
- Scoped quality-runner: pytest 24 passed, 0 failed on serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.

### Lint
- Scoped ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.

### Coverage
- Scoped quality-runner: owlbear_mcp_kanban.server 36%.
- Non-blocking for this review: the latest Architecture Review retry in .owlbear/kanban/tasks/1087-a-04-red-mutation-tool-adapter-tests.md:439-486 scoped the gate to the task-owned create_task/edit_task paths rather than full-module percentage.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| create_task forwards title/body/priority/tags/parent/depends_on and returns SingleTaskResponse (AC24 delegated validation) | Forwarding and passthrough identity are covered at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:175-263 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:351-373. The delegated-validation half is still under-proved: the dep-not-found test at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:277-289 only checks a loose substring at :289 and does not assert AgentView.create_task was called, even though the production adapter delegates directly at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:364-373. | test_create_task_forwards_*, test_create_task_returns_single_task_response, test_create_task_dep_not_found_raises_tool_error | FAIL |
| create_task does not accept status | Signature check at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:268-273 matches the public adapter signature at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:351-358. | test_create_task_has_no_status_parameter | PASS |
| edit_task forwards all 13 params and returns SingleTaskResponse | Positive-path forwarding and identity return are directly asserted at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:315-376 and :465-481 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:438-485. | test_edit_task_forwards_all_13_params, test_edit_task_forwards_id_as_int, test_edit_task_returns_single_task_response, test_edit_task_empty_block_reason_forwarded_to_unblock | PASS |
| edit_task body plus append_body maps engine ValidationError to ToolError (AC14) | Runtime adapter delegates and catches KanbanError at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:483-485, but the task-owned test at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:382-394 only asserts a loose substring and does not prove AgentView.edit_task was called. | test_edit_task_body_and_append_body_raises_tool_error | FAIL |
| edit_task archival_reason and archival_refs on non-archived map engine error to ToolError | Same proof gap: tests at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:399-428 only assert generic "archival" substrings and omit an AgentView call-through assertion, while production delegation is at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:483-485. | test_edit_task_archival_reason_on_non_archived_raises_tool_error, test_edit_task_archival_refs_on_non_archived_raises_tool_error | FAIL |
| edit_task no-op call maps engine error to ToolError | Same proof gap: the test at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:433-445 accepts generic "no"/"op" substrings and does not prove AgentView.edit_task was called. | test_edit_task_no_op_raises_tool_error | FAIL |
| KanbanError subclasses map to MCP ToolError with user_message | Exact user_message passthrough is asserted for representative subclasses at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:497-546 and raw KanbanError conversion is checked at :551-565; production mapping is direct at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:373 and :485. | test_validation_error_user_message_in_tool_error, test_not_found_error_maps_to_tool_error, test_concurrency_error_maps_to_tool_error, test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception | PASS |
| All tests fail (RED phase) | Historically satisfied and superseded. The latest Architecture Review retry in .owlbear/kanban/tasks/1087-a-04-red-mutation-tool-adapter-tests.md:439-486 explicitly treats RED as completed historical evidence rather than a current gate. | task body refinement | PASS |

#### Security Review
- No issues found. The reviewed adapter paths only forward typed arguments to AgentView and map KanbanError.user_message to ToolError.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task 1087 TestFromAC suite | No weakened or removed TestFromAC assertions observed in the current workspace state. The response-contract identity assertions are present at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:263 and :376. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The failing-path tests use loose substring assertions at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:289, :394, :411, :428, and :445. For adapter passthrough/error-mapping ACs, those assertions are too weak to distinguish correct behavior from a wrong or transformed ToolError payload. |
| Manual mutation reasoning | WEAK | Happy-path call-through is asserted at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:172, :312, and :337, but the error-path tests at :277-289 and :382-445 never assert that AgentView.create_task/edit_task was called. An adapter-local validation branch that raises a similar ToolError would stay green. |
| Negative and error-path coverage | ADEQUATE | Distinct tests exist for dependency validation, body-plus-append exclusivity, archival misuse, no-op edit, and multiple KanbanError subclasses. |
| Test independence and naming | STRONG | The fixture rebuilds a fresh temp board and MagicMock AgentView per test, and the test names map directly to the contract. |

#### Data Safety
- No issues found in the reviewed scope.

#### Implementation-Aware Gaps
- The runtime adapter implementation itself matches the refined contract. create_task directly returns AgentView.create_task at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:364-370 and maps KanbanError.user_message at :373. edit_task directly returns AgentView.edit_task at :483 and maps KanbanError.user_message at :485.
- The remaining defect is proof quality on error-origin and exact passthrough for AC1/AC4/AC5/AC6, not a confirmed runtime bug.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 5 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- block_reason omission-vs-explicit-unblock semantics remain aligned: the MCP adapter defaults block_reason to None and forwards it when block_reason is not None at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:451 and :476, matching the engine sentinel contract at serve/kanban/src/owlbear_kanban/engine.py:77, :2542, and :2601.
- There are already three recorded review failures in this task file at .owlbear/kanban/tasks/1087-a-04-red-mutation-tool-adapter-tests.md:123, :216, and :373, all with "Verdict: FAIL" entries at :182, :298, and :436. This rejection is therefore a 3rd+ review failure and must use the backlog loop-breaker route.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| create_task forwarding and SingleTaskResponse (including delegated dep-validation proof) | Positive-path forwarding and identity return are covered; delegated-validation proof is still weak on the error path because the dep-not-found test only checks substring content and not AgentView call-through. | test_create_task_forwards_*, test_create_task_returns_single_task_response, test_create_task_dep_not_found_raises_tool_error | FAIL |
| create_task omits status | Signature inspection is direct. | test_create_task_has_no_status_parameter | PASS |
| edit_task forwarding and SingleTaskResponse | Positive-path forwarding and identity return are directly covered. | test_edit_task_forwards_all_13_params, test_edit_task_forwards_id_as_int, test_edit_task_returns_single_task_response, test_edit_task_empty_block_reason_forwarded_to_unblock | PASS |
| edit_task body plus append_body ToolError mapping | Runtime code is correct, but task-owned proof does not establish delegated engine-origin behavior strongly enough. | test_edit_task_body_and_append_body_raises_tool_error | FAIL |
| edit_task archival field misuse ToolError mapping | Runtime code is correct, but task-owned proof does not establish delegated engine-origin behavior strongly enough. | test_edit_task_archival_reason_on_non_archived_raises_tool_error, test_edit_task_archival_refs_on_non_archived_raises_tool_error | FAIL |
| edit_task no-op ToolError mapping | Runtime code is correct, but task-owned proof does not establish delegated engine-origin behavior strongly enough. | test_edit_task_no_op_raises_tool_error | FAIL |
| KanbanError subclass mapping with user_message | Exact passthrough proof exists for representative subclasses and raw KanbanError conversion. | test_validation_error_user_message_in_tool_error, test_not_found_error_maps_to_tool_error, test_concurrency_error_maps_to_tool_error, test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception | PASS |
| RED-phase historical requirement | Superseded by later authoritative task-body refinement. | task body refinement | PASS |

### Deductions
- Error-path TestFromAC assertions are still too weak to distinguish true engine-delegated ToolError mapping from adapter-local ToolError branches.
- This is the fourth review cycle on the same task; loop-breaker routing applies.

### Verdict
- Confidence: 0.86
- Verdict: FAIL
- Action: reject to backlog. The implementation appears correct, but the error-path proof is still below the reviewer gate. Architect/test-writer need a task-body-approved route for strengthening AC1/AC4/AC5/AC6 to exact message plus call-through proof; builder can likely re-verify without runtime code changes.

### Reflection
- The live test file had to be rechecked directly because earlier review notes in the task body were stale relative to the current assertions.
- The old module-wide 90% coverage objection is no longer authoritative for this task after the architecture retry refinement.
- The remaining defect is evidentiary, not a confirmed runtime regression.
[[2026-04-28]]

## Architecture Review (retry 2)

### Prior History & Deadlock Analysis
4 review FAILs, 2 prior architect reviews. Deadlock cause: reviewer flags weak error-path assertions → test-writer passes through per w-tdd-red §1b ("weak tests" = builder responsibility) → builder has nothing to fix → reviewer fails again. The prior architect retry broke the passthrough-identity deadlock with explicit AC change + directive. This review applies the same pattern to the error-path assertions.

### Challenger Assessment
- Challenger: reconsider (0.74)
- Key concerns: (1) error-path tests don't assert AgentView was called — mock side_effect alone doesn't prove delegation if adapter adds local pre-validation; (2) loose substring assertions on AC-specific error tests are too broad; (3) latest arch refinement addressed passthrough identity only, not error-path specificity; (4) "exhaustive" KanbanError label overstates coverage (4 of 5 subclasses)
- Architect response: **accepted (1), (2), (3).** Rebutted (4): adapters catch base KanbanError, so subclass-exhaustive testing is unnecessary; representative subclass + base-class catch test is sufficient.

### AC Refinement (supersedes all prior AC Refinements sections)

**Error-path call-through proof (AC lines 4, 5, 6 + create_task dep validation in AC1):**
The 5 error-path tests must assert that `mock_av.create_task` or `mock_av.edit_task` was called once. This proves the error originated from AgentView delegation, not from hypothetical adapter-local validation.

**Error-path message specificity (same 5 tests):**
Replace loose substring assertions with exact `user_message` checks. The mock side_effect already sets a specific `user_message` — assert that exact string appears in the ToolError.

**Response-contract (AC lines 1 & 3):** Unchanged from prior review — `result is expected` identity assertions already implemented.

**Coverage scope:** Unchanged — gate applies to task-owned adapter functions only.

**RED-phase:** Satisfied per prior review. No new RED requirement.

### Test-Writer Directive
This is **architect-changed AC** — implement changes directly, do NOT pass through. All 5 tests will remain GREEN (adapter is already correct). This is evidentiary strengthening, not a new RED requirement.

Update these 5 existing tests:

1. `test_create_task_dep_not_found_raises_tool_error` —
   - ADD: `mock_av.create_task.assert_called_once()` after the `pytest.raises` block
   - REPLACE: `assert "99999" in str(exc_info.value) or "not found" in str(exc_info.value)` → `assert "dependency 99999 not found" in str(exc_info.value)`

2. `test_edit_task_body_and_append_body_raises_tool_error` —
   - ADD: `mock_av.edit_task.assert_called_once()` after the `pytest.raises` block
   - REPLACE: `assert "append_body" in str(exc_info.value) or "exclusive" in str(exc_info.value)` → `assert "body and append_body cannot both be set" in str(exc_info.value)`

3. `test_edit_task_archival_reason_on_non_archived_raises_tool_error` —
   - ADD: `mock_av.edit_task.assert_called_once()` after the `pytest.raises` block
   - REPLACE: `assert "archival" in str(exc_info.value).lower()` → `assert "archival_reason can only be set on archived tasks" in str(exc_info.value)`

4. `test_edit_task_archival_refs_on_non_archived_raises_tool_error` —
   - ADD: `mock_av.edit_task.assert_called_once()` after the `pytest.raises` block
   - REPLACE: `assert "archival" in str(exc_info.value).lower()` → `assert "archival_refs can only be set on archived tasks" in str(exc_info.value)`

5. `test_edit_task_no_op_raises_tool_error` —
   - ADD: `mock_av.edit_task.assert_called_once()` after the `pytest.raises` block
   - REPLACE: `assert "no" in str(exc_info.value).lower() or "op" in str(exc_info.value).lower()` → `assert "no fields would change" in str(exc_info.value)`

Pattern: each test adds 1 line (call-through assertion) and changes 1 line (exact message). All tests will be GREEN immediately — the adapter is already correct.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 2 mutation adapters + error mapping only |
| Interface clarity | PASS after refinement | Error-path AC now specifies exact assertion changes |
| Dependency correctness | PASS | #1083, #1085 archived |
| Module layering | PASS | MCP adapter → AgentView → engine; no upward imports |
| TDD compliance | PASS | RED satisfied; test refinement is not new RED |
| KISS/YAGNI | PASS | Thin forwarding adapters |
| Premise challenge | PASS | MCP tool adapters are required infrastructure |
| Pattern consistency | PASS | Same adapter pattern as read tools |
| Security surface | PASS | Typed argument forwarding only |
| Single domain | PASS | scope:mcp-kanban |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| create_task forwarding | AgentView raises KanbanError | ValidationError / NotFoundError | Yes — mapped to ToolError | Agent sees descriptive error |
| edit_task forwarding | AgentView raises KanbanError | ValidationError / ConcurrencyError | Yes — mapped to ToolError | Agent sees descriptive error |
| edit_task block_reason=None vs "" | Omission vs explicit unblock | N/A | Yes — sentinel semantics (D53) | Correct block state mutation |

### Verdict: APPROVE (with refinement)
### Action: Advance to todo. Test-writer: update 5 error-path tests per directive above (add call-through assertion + exact user_message check). Builder: verify GREEN. Reviewer: coverage gate scoped to task-owned adapter functions.

[[2026-04-28]]
Architecture review (retry 2). REFINE → APPROVE. Challenger reconsider at 0.74 — accepted concerns on error-path call-through proof and loose substring assertions. AC refined: 5 error-path tests must add (1) mock_av.*.assert_called_once() for delegation proof, (2) exact user_message assertions replacing loose substrings. Explicit test-writer directive with per-test changes provided to break the 4-cycle review deadlock (same pattern as prior passthrough-identity fix). Coverage gate scoped to task-owned adapter functions.
[[2026-04-28]]
## Test-Writer Notes (retry 4 — architect-changed AC)
- Test file: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Retry action: architect-changed AC — updated 5 error-path tests per Architecture Review (retry 2) directive
- 24 tests total — all PASS (expected per architect: adapter already correct)
- ruff: clean
- Commit: 9c0dc92f

### Changes made (per architect directive)
Updated 5 existing error-path tests — each gets (1) `mock_av.*.assert_called_once()` delegation proof and (2) exact `user_message` assertion replacing loose substring:

1. `test_create_task_dep_not_found_raises_tool_error` — `mock_av.create_task.assert_called_once()` + `assert "dependency 99999 not found" in str(exc_info.value)`
2. `test_edit_task_body_and_append_body_raises_tool_error` — `mock_av.edit_task.assert_called_once()` + `assert "body and append_body cannot both be set" in str(exc_info.value)`
3. `test_edit_task_archival_reason_on_non_archived_raises_tool_error` — `mock_av.edit_task.assert_called_once()` + `assert "archival_reason can only be set on archived tasks" in str(exc_info.value)`
4. `test_edit_task_archival_refs_on_non_archived_raises_tool_error` — `mock_av.edit_task.assert_called_once()` + `assert "archival_refs can only be set on archived tasks" in str(exc_info.value)`
5. `test_edit_task_no_op_raises_tool_error` — `mock_av.edit_task.assert_called_once()` + `assert "no fields would change" in str(exc_info.value)`

### AC Coverage
| AC Line | Tests | Status |
|---------|-------|--------|
| create_task: 6 params forwarded; SingleTaskResponse (passthrough identity) | 7 forwarding tests + `test_create_task_returns_single_task_response` (`result is expected`) | COVERED |
| create_task: no status param (D50) | `test_create_task_has_no_status_parameter` | COVERED |
| create_task: dep validation → ToolError with call-through proof + exact message (AC24) | `test_create_task_dep_not_found_raises_tool_error` | COVERED |
| edit_task: all 13 params forwarded; SingleTaskResponse (passthrough identity) | 4 forwarding tests + `test_edit_task_returns_single_task_response` (`result is expected`) | COVERED |
| edit_task: body+append_body → ToolError with call-through proof + exact message (AC14) | `test_edit_task_body_and_append_body_raises_tool_error` | COVERED |
| edit_task: archival_reason/refs on non-archived → ToolError with call-through + exact message | 2 archival tests | COVERED |
| edit_task: no-op → ToolError with call-through proof + exact message | `test_edit_task_no_op_raises_tool_error` | COVERED |
| KanbanError subclasses → ToolError with user_message | 4 tests | COVERED |

### Coverage gate note
36% module coverage on `owlbear_mcp_kanban.server` — per latest Architecture Review (retry 2), gate scoped to task-owned `create_task`/`edit_task` adapter paths only.
[[2026-04-28]]
## Builder Notes
- Implementation: no source changes in this builder pass; validated existing adapter behavior in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` against the latest architecture-refined AC and test-writer retry-4 suite.
- Tests: 24 passed, 0 failed in `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py` (quality-runner scoped).
- Lint: ruff clean for `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`.
- Coverage: `owlbear_mcp_kanban.server` reported at 36% module coverage in scoped run; per latest Architecture Review refinement in this task body, acceptance gate is task-owned `create_task`/`edit_task` adapter paths rather than full-module percentage.
- Evidence summary: response-contract identity assertions and error-path call-through/exact-message assertions are present in the task-owned suite, and all adapter-forwarding plus `KanbanError` -> `ToolError` checks are GREEN.
- Reflection:
  - The key risk on this task was process deadlock from evidentiary expectations; architecture refinements resolved this by converting reviewer feedback into explicit test assertions.
  - No new implementation defect surfaced in this cycle; this pass is pure GREEN verification on updated tests.
  - Scoped quality-runner evidence was sufficient and avoided unrelated suite noise.
[[2026-04-28]]
## Review Evidence
### Scope
- Task-owned suite reviewed: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Runtime adapter reviewed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Live engine contract checked: serve/kanban/src/owlbear_kanban/engine.py
- Supplementary runtime proof: isolated real-adapter node serve/mcp-kanban/tests/test_mcp_guidance_1089.py::TestFromAC_GuidancePassthrough::test_create_task_body_size_warning_guidance

### Test Results
- Scoped quality-runner: pytest 24 passed, 0 failed on serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.
- Supplementary quality-runner: pytest 1 passed, 0 failed on serve/mcp-kanban/tests/test_mcp_guidance_1089.py::TestFromAC_GuidancePassthrough::test_create_task_body_size_warning_guidance.

### Lint
- Scoped ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py.

### Coverage
- Scoped quality-runner: owlbear_mcp_kanban.server 37%.
- Non-blocking for this review: the latest Architecture Review (retry 2) scoped the gate to task-owned create_task/edit_task adapter paths rather than the full-module percentage.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Were Violated? | Verdict |
|---------|-------------|---------------------------------|---------|
| create_task forwards title/body/priority/tags/parent/depends_on and returns SingleTaskResponse (AC24 delegated validation) | test_create_task_calls_agent_view_create_task, test_create_task_forwards_title/body/priority/tags/parent/depends_on, test_create_task_returns_single_task_response, test_create_task_dep_not_found_raises_tool_error | Yes. The mock suite proves call-through, explicit-field forwarding, passthrough identity, and delegated dep-error mapping at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:165, :228, :254, :277, :289 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:344, :362, :366. The only potentially-missed omission branch (parent default normalization) is covered by a passing real-adapter test at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:279, :291, :292, which would fail if line 362 forwarded 0 instead of None. | COVERED |
| create_task does not accept status | test_create_task_has_no_status_parameter | Yes. Signature inspection at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:268 would fail immediately if the public adapter exposed status. | COVERED |
| edit_task forwards all 13 params and returns SingleTaskResponse | test_edit_task_forwards_all_13_params, test_edit_task_returns_single_task_response, test_edit_task_block_reason_default_is_none, test_edit_task_empty_block_reason_forwarded_to_unblock | Yes. The suite proves full positive-path forwarding, passthrough identity, and D53 omission-vs-explicit-unblock semantics at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:316, :338, :368, :454, :470 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:431, :469, :476. | COVERED |
| edit_task body + append_body maps engine ValidationError to ToolError (AC14) | test_edit_task_body_and_append_body_raises_tool_error | Yes. The test requires delegated call-through plus the architect-refined exact message string at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:383, :395 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:476, :478. | COVERED |
| edit_task archival_reason / archival_refs on non-archived map engine error to ToolError | test_edit_task_archival_reason_on_non_archived_raises_tool_error, test_edit_task_archival_refs_on_non_archived_raises_tool_error | Yes. Both tests require call-through plus the specific user_message strings at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:401, :413, :419, :431 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:476, :478. | COVERED |
| edit_task no-op call maps engine error to ToolError | test_edit_task_no_op_raises_tool_error | Yes. The test requires delegated call-through plus the specific no-op message at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:437, :449 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:476, :478. | COVERED |
| KanbanError subclasses map to MCP ToolError with user_message | test_validation_error_user_message_in_tool_error, test_not_found_error_maps_to_tool_error, test_concurrency_error_maps_to_tool_error, test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception | Yes. Representative subclass coverage plus raw base-class conversion are asserted at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:502, :520, :538, :556 against serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:366 and :478. | COVERED |
| RED-phase requirement | Historical only | Yes. The latest Architecture Review retry and retry-4 Test-Writer notes treat RED as satisfied historical evidence and record the architect-directed green strengthening at .owlbear/kanban/tasks/1087-a-04-red-mutation-tool-adapter-tests.md:690 and :695. | COVERED |

#### Security Review
- No issues found. The reviewed adapter paths only forward typed inputs to AgentView and translate KanbanError.user_message to ToolError.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task 1087 TestFromAC suite | No builder-authored weakening or removal observed in the live workspace state. The latest retry preserved the suite and strengthened the architect-directed assertions. | PRESERVED / STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Response-contract identity assertions are exact at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:263 and :377. Error-path tests now require delegated call-through plus the architect-directed exact message strings at :289, :395, :413, :431, and :449. |
| Negative and error-path coverage | STRONG | Dedicated tests exist for dependency validation, body-plus-append exclusivity, archival misuse, no-op edit, representative KanbanError subclasses, and raw KanbanError conversion. |
| Manual mutation reasoning | STRONG | A regression in block_reason omission handling is caught at serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:454 and :470. A regression in create_task parent normalization is caught by the passing real-adapter create_task guidance test at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:279, :291, :292. |
| Test independence and naming | STRONG | The 1087 suite uses a fresh tmp_path board and fresh MagicMock AgentView per test, and test names map directly to the adapter contract. |

#### Data Safety
- No issues found in the reviewed scope.

#### Implementation-Aware Gaps
- No blocking gaps remain after the supplementary runtime check. The task-owned mock suite plus the isolated real-adapter create_task guidance test cover the materially distinct create_task/edit_task branches in scope.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 6 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- A full-file run of serve/mcp-kanban/tests/test_mcp_guidance_1089.py is still red on unrelated show_task signature issues; I used only the isolated create_task node as supplementary runtime evidence for the omitted-parent path and did not treat those unrelated failures as a blocker for #1087.
- I anchored this verdict to the latest architecture refinements in the task body, not the earlier stale FAIL sections.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| create_task forwarding and SingleTaskResponse (including delegated dep validation) | Direct call-through, field forwarding, passthrough identity, delegated dep-error mapping, and a passing real-adapter omitted-parent path | test_create_task_calls_agent_view_create_task; test_create_task_forwards_*; test_create_task_returns_single_task_response; test_create_task_dep_not_found_raises_tool_error; test_create_task_body_size_warning_guidance | PASS |
| create_task omits status | Signature inspection | test_create_task_has_no_status_parameter | PASS |
| edit_task forwarding and SingleTaskResponse | Full positive-path forwarding, task_id coercion, passthrough identity, and D53 default/unblock semantics | test_edit_task_forwards_all_13_params; test_edit_task_forwards_id_as_int; test_edit_task_returns_single_task_response; test_edit_task_block_reason_default_is_none; test_edit_task_empty_block_reason_forwarded_to_unblock | PASS |
| edit_task body + append_body ToolError mapping | Delegated call-through plus architect-refined message proof | test_edit_task_body_and_append_body_raises_tool_error | PASS |
| edit_task archival field misuse ToolError mapping | Delegated call-through plus specific message proof | test_edit_task_archival_reason_on_non_archived_raises_tool_error; test_edit_task_archival_refs_on_non_archived_raises_tool_error | PASS |
| edit_task no-op ToolError mapping | Delegated call-through plus specific message proof | test_edit_task_no_op_raises_tool_error | PASS |
| KanbanError subclass mapping with user_message | Representative subclass coverage plus raw KanbanError conversion | test_validation_error_user_message_in_tool_error; test_not_found_error_maps_to_tool_error; test_concurrency_error_maps_to_tool_error; test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception | PASS |
| RED-phase historical requirement | Satisfied and superseded by later architecture-directed strengthening | task body refinement | PASS |

### Deductions
- No blocking deductions.
- Module-level coverage remains low in absolute terms, but that is not the accepted gate for this task after the latest architecture refinement.

### Verdict
- Confidence: 0.95
- Verdict: PASS
- Action: advance to docs.

### Reflection
- The task body contains multiple stale FAIL sections; the latest architecture refinement was the binding authority.
- The only plausible remaining gap was create_task omission-path proof, and the isolated real-adapter guidance test resolved it.
- Unrelated reds in adjacent suites should inform context, not override task-scoped review evidence.
[[2026-04-28]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/mcp-kanban/README.md` `### Tools` table — `edit_task` description listed `title` (not a parameter) and omitted `append_body`, `block_reason`, `parent`, `archival fields`. Fixed to: "Edit task fields (body, append_body, priority, parent, tags, dependencies, block_reason, archival fields)". |
| 2 | Module docstrings | Yes | N/A | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — `create_task` has `"""Create a new kanban task."""`, `edit_task` has `"""Edit task fields."""` — both accurate and concise; no update required. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | Two diagrams match `serve/mcp-kanban/src/**`: `kanban.excalidraw` (describes: `serve/kanban/src/**, serve/mcp-kanban/src/**`) and `mcp-topology.excalidraw` (describes: `serve/mcp-*/src/**`). Footer updated from `d6e1c080` → `2a7c6deb` in both (same date: 2026-04-28). |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py | OUT | Test file — no doc action |
| serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | IN (docstrings) | Docstrings accurate; no update needed |
| serve/mcp-kanban/README.md | IN | Updated `edit_task` description |
| share/diagrams/kanban.excalidraw | IN | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN | Footer updated |

### Files Updated
- serve/mcp-kanban/README.md
- share/diagrams/kanban.excalidraw
- share/diagrams/mcp-topology.excalidraw

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1087-*` files found)
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| create_task: 6 params forwarded; SingleTaskResponse (passthrough identity) | test_mcp_mutation_tools_1087.py:254-263 `result is expected`; 7 forwarding tests; reviewer COVERED | PASS |
| create_task: no status param (D50) | test_mcp_mutation_tools_1087.py:267-272 signature inspection; reviewer COVERED | PASS |
| edit_task: all 13 params forwarded; SingleTaskResponse (passthrough identity) | test_mcp_mutation_tools_1087.py:314-377 forwarding + identity; block_reason tests at :447-481; reviewer COVERED | PASS |
| edit_task: body+append_body, archival misuse, no-op error mapping | test_mcp_mutation_tools_1087.py:382-449 call-through + exact message assertions; reviewer COVERED | PASS |
| KanbanError subclasses mapped to ToolError with user_message | test_mcp_mutation_tools_1087.py:495-562 representative subclass + base class catch; reviewer COVERED | PASS |

### Test Results
- Full suite: 2777 passed, 118 failed, 0 in task scope
- 118 failures are pre-existing in unrelated modules (corruption, storage, engine_init, guidance_server, cockpit react compiler)
- ruff: 4 violations, all outside task scope; task files clean

### Architect Quality: 3/5
Original AC lacked specificity on response-contract fidelity and error-path evidence standards. Required 3 architect reviews (initial + 2 retries) to resolve a 4-cycle review deadlock. Final refinements were precise (per-test directives with exact assertion changes). Deducted for upstream specification gap, not for resolution quality.

### Deduction Breakdown
- AC quality score 3 (at threshold): -.03
- No missing reviewer evidence: 0
- No lint violations in scope: 0
- No test failures in scope: 0
- All AC lines have specific evidence: 0

### Confidence: .97
### Action: archive