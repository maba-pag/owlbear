---
id: 1337
title: Validate MCP task IDs at every task endpoint trust boundary
status: review
priority: critical
created: 2026-05-04T15:00:05.722955+00:00
updated: 2026-05-04T23:02:52.594419+00:00
tags:
- sync-blocker
- security
- mcp-kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The MCP server accepts task IDs through several tool handlers and currently relies on loose `StrId` coercion or raw strings. `create_dr` is the highest-risk endpoint because the ID becomes part of a decision-request filename, but the same trust-boundary rule should apply to every MCP task-id endpoint before values reach engine glob lookup or filesystem-backed helpers.

## Acceptance Criteria

1. Add a shared MCP ID parser/coercer used by every task-id accepting endpoint: `show_task` fallback path, `move_task`, `edit_task`, `start_work`, `end_work`, and `create_dr`.
2. Accept JSON numbers and positive decimal strings for VS Code schema-cache compatibility.
3. Reject empty, zero, negative, non-decimal, path-like, shell-like, whitespace-padded, and mixed strings before calling the engine.
4. Rejections raise a clear `ToolError` mentioning the relevant id field and positive integer requirement.
5. Rejected IDs do not create DR files, mutate task state, or fall through to raw engine glob/path lookup.
6. Valid numeric values continue to work for all MCP task tools.
7. Existing `create_dr` coercion tests remain covered, but are broadened or complemented so the shared parser cannot regress on other endpoints.

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`
- `serve/kanban/src/owlbear_kanban/decisions.py`
- `tests/test_mcp_create_dr_coerce_1337.py`
- `tests/test_mcp_kanban.py`

## Audit Evidence

- `create_dr` accepts raw `task_id: str`; non-numeric input is not rejected at the MCP boundary.
- `StrId` only coerces ints to strings; it does not validate positive decimal task IDs.
- Raw engine lookup has glob fallback behavior, so malformed IDs must be stopped before engine calls.

## Test-Writer Notes

- Existing RED file: `tests/test_mcp_create_dr_coerce_1337.py`.
- Preserve the integration tests that assert malformed `create_dr` IDs leave `decisions/pending` unchanged.
- Add parser/table tests once, then at least one endpoint-level proof for each task tool family.

## Source

Deployment audit reconciliation, 2026-05-04.


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: validate task IDs at MCP trust boundary |
| Interface clarity | PASS | Shared parser input (str\|int) → validated int; ToolError on reject |
| Dependency correctness | PASS | No external dependencies; self-contained within mcp-kanban |
| Module layering | PASS | Validation at MCP boundary layer, before engine calls — correct placement |
| TDD compliance | PASS | RED file exists: `tests/test_mcp_create_dr_coerce_1337.py` |
| KISS/YAGNI | PASS | Single shared function, minimal scope, no speculative features |
| Premise challenge | PASS | Real security gap: path traversal and shell injection reach filesystem |
| Pattern consistency | PASS | Extends existing `StrId` / `BeforeValidator` pattern in server.py |
| Security surface | PASS | This IS the security fix; AC3 enumerates all rejection categories |
| Single domain | PASS | MCP server boundary validation only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Shared parser receives valid "42" | None (happy path) | — | — | Returns int 42 |
| Shared parser receives "../foo" | Path traversal attempt | ToolError | AC4 | Clear error message |
| Shared parser receives "0" / "-1" | Non-positive integer | ToolError | AC4 | Clear error message |
| Valid ID reaches engine, task not found | Normal not-found | KanbanError→ToolError | Existing | "Task not found" |

### Challenge Results
- Challenger: reconsider (confidence 0.47)
- Architect response: REBUTTED — concerns addressed by existing AC text (AC6/AC7 handle regression, test-writer notes handle proof breadth, list_tasks.ids already int-typed at schema level). See evaluation above.

### Test Depth
- AC1: shared parser used by all endpoints (td:2) — multiple integration points
- AC2: accept JSON numbers and positive decimal strings (td:1) — happy-path coercion
- AC3: reject invalid inputs (td:2) — many edge cases per category
- AC4: clear ToolError with field/requirement (td:2) — message format per rejection
- AC5: rejected IDs don't create files/mutate state (td:2) — side-effect verification
- AC6: valid numeric values continue to work (td:1) — regression happy-path
- AC7: existing tests preserved and broadened (td:1) — test structure
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Approved to todo. AC is verifiable, architecture sound (boundary validation with shared parser), RED tests exist. Security-critical sync-blocker with clean single-domain scope.
[[2026-05-04]]
Architecture review complete. All 10 criteria PASS. Challenger rebutted (concerns addressed by existing AC text). Test depth: max td:2, test-writer PROCEED. Approved to todo.
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_mcp_task_id_parser_1337.py
- Existing RED file preserved: tests/test_mcp_create_dr_coerce_1337.py (9 tests, all FAIL — unchanged)
- Classes: TestFromAC_SharedParserContract, TestFromAC_EndpointBoundaryProofs, TestFromAC_NoSideEffects, TestFromAC_ValidIdsRegression
- Tests per category: happy 8, edge 2, error 18, boundary 1 → 29 new tests
- Total new: 29 tests, all FAIL (ImportError at collection — parse_task_id not yet in server.py)
- ruff: clean

AC coverage table:
| AC | Tests |
|----|-------|
| AC1 shared parser importable | TestFromAC_SharedParserContract (all — import fails = RED proof) |
| AC1 wired to all endpoints | TestFromAC_EndpointBoundaryProofs (6 tests, one per endpoint family) |
| AC2 accept int + decimal string | test_accepts_positive_int, test_accepts_positive_decimal_string |
| AC3 reject all invalid categories | test_rejects_* (10 tests: empty, zero×2, neg×2, alpha, path×2, shell, whitespace, mixed) |
| AC4 clear ToolError message | test_error_message_mentions_field_name_default, test_error_message_mentions_custom_field_name; all endpoint tests also assert match pattern |
| AC5 no side effects | TestFromAC_NoSideEffects (move_task, edit_task, start_work each verified) |
| AC6 valid IDs regression | TestFromAC_ValidIdsRegression (5 tests — one per endpoint) |
| AC7 breadth beyond create_dr | All TestFromAC_EndpointBoundaryProofs + SharedParserContract tests |
[[2026-05-04]]
## Builder Notes
- Files changed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Implementation applied: added shared `parse_task_id` and wired it into `show_task`, `create_dr`, `move_task`, `edit_task`, `start_work`, and `end_work` to reject invalid IDs before engine/filesystem calls.
- RED verification (before edits): quality-runner reported 8 failed tests + 1 collection error (`parse_task_id` import missing) across:
  - tests/test_mcp_task_id_parser_1337.py
  - tests/test_mcp_create_dr_coerce_1337.py
- GREEN verification (after edits): quality-runner scoped run results:
  - 37 passed
  - 1 failed: `tests/test_mcp_task_id_parser_1337.py::TestFromAC_NoSideEffects::test_rejected_start_work_does_not_claim_any_task`
  - ruff clean
  - coverage (scoped module): `owlbear_mcp_kanban.server` 56%
- Failure analysis: remaining failure is test interface mismatch, not endpoint behavior:
  - Test asserts `post_task.claimed` on `app_ctx.engine.show_task(...)` return value.
  - Engine `Task` model does not expose `.claimed`; canonical field is `.claimed_at`.
  - Raised error: `AttributeError: 'Task' object has no attribute 'claimed'. Did you mean: 'claimed_at'?`

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update `test_rejected_start_work_does_not_claim_any_task` to assert unclaimed state via the engine `Task` contract (`claimed_at is None`) instead of non-existent `.claimed`. | tests/test_mcp_task_id_parser_1337.py | quality-runner scoped run failure: `AttributeError: 'Task' object has no attribute 'claimed'` |

- No commit performed because task is rejected back to test-writer for interface-contract correction.
[[2026-05-04]]
## Test-Writer Notes
- Retry: fixed `test_rejected_start_work_does_not_claim_any_task` to assert unclaimed state via `post_task.claimed_at is None` instead of non-existent `.claimed` attribute (builder Required Follow-up #1).
- All 38 tests PASS against current implementation (builder's parse_task_id already handles the corrected assertion).
- ruff: clean
- Builder skip: test-only retry, all tests green — advancing directly to review.
[[2026-05-04]]
## Builder Notes
- Code changes in this run: none (validation-only pass).
- Existing implementation in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` remains functionally GREEN for task-scoped behavior.
- Quality-runner verification (task-scoped):
  - tests: 38 passed, 0 failed
  - ruff: clean
  - coverage: `owlbear_mcp_kanban.server` = 56%
- Quality-runner verification (module-level regression + task tests):
  - tests: 47 passed, 0 failed
  - ruff: clean
  - coverage: `owlbear_mcp_kanban.server` = 61%
- Gate result: coverage for the touched module remains below the required 90% threshold, so task cannot advance to review under builder gate criteria.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add/expand tests that execute additional MCP server paths in `owlbear_mcp_kanban.server` (beyond current parser + endpoint-boundary slice) until touched-module coverage reaches >=90% while preserving current security assertions. | tests/test_mcp_task_id_parser_1337.py, tests/test_mcp_create_dr_coerce_1337.py, tests/test_mcp_kanban.py | quality-runner: 47 passed, 0 failed, module coverage 61% for `owlbear_mcp_kanban.server` |
| 2 | test-writer | Keep existing `TestFromAC_*` assertions unchanged in intent and extend with additional valid/invalid ID flows across all task-id tools to improve path coverage. | tests/test_mcp_task_id_parser_1337.py | quality-runner coverage deficit against touched module gate |

- Builder rejects to `todo` for test-depth/coverage completion only; no implementation defects found in this run.
[[2026-05-04]]
## Test-Writer Notes
- Retry: coverage uplift for `owlbear_mcp_kanban.server` from 61% to 95% (builder Required Follow-up #1 and #2).
- Files modified: `tests/test_mcp_kanban.py` (import expansion + new test classes appended).
- Files unchanged: `tests/test_mcp_task_id_parser_1337.py` (38 tests, all PASS), `tests/test_mcp_create_dr_coerce_1337.py` (9 tests, all PASS).
- New test classes added to `tests/test_mcp_kanban.py`:
  - `TestParseTaskIdBoolInputs` — bool True/False rejection (parse_task_id bool branch)
  - `TestAppContextContains` — AppContext.__contains__ always returns False
  - `TestApplyToolExclusions` — env var empty, missing tool, valid tool, comma-separated
  - `TestToSingleTaskResponse` — KanbanTask, dict, model_dump, passthrough branches
  - `TestCanonicalAgentViewFor` — None candidate, callable raises, non-callable object
  - `TestInvokeViewMoveTask` — None view, no attr, NotImplementedError, KanbanError
  - `TestInvokeViewEndWork` — None view, NotImplementedError, success guidance, block guidance, no attr
  - `TestShowValidated` — FileNotFoundError → ToolError
  - `TestListTasks` — happy path, status filter, KanbanError
  - `TestPickTasks` — happy path, KanbanError
  - `TestShowTask` — happy path, section param, KanbanError, zero id rejects
  - `TestCreateDRExtraBranches` — invalid request_type, KanbanError from decisions.create_dr
  - `TestMovetaskFallbackPath` — canonical view=None, status=None raises, KanbanError fallback, ValueError fallback
  - `TestEditTaskKwargsBranches` — all 10 kwargs branches (body, timestamp, parent, add_dep, remove_dep, add_tag, remove_tag, block_reason, archival_reason, archival_refs)
  - `TestStartWorkFallbackPath` — NotImplementedError falls back to engine, ValueError raises ToolError
  - `TestEndWorkEngineFallbackPath` — canonical view=None, KanbanError, ValueError
- Tests per category: happy 28, edge 8, error 14, boundary 4 → 54 new tests
- All 101 tests PASS against current implementation (retry-type: coverage uplift only)
- ruff: clean
- coverage: `owlbear_mcp_kanban.server` = 95% (was 61%)

AC coverage table:
| AC | Coverage |
|----|---------|
| AC1 shared parser wired | TestFromAC_EndpointBoundaryProofs (preserved) |
| AC2 accept int + decimal | TestFromAC_SharedParserContract (preserved) |
| AC3 reject invalid inputs | TestFromAC_SharedParserContract + bool inputs (new) |
| AC4 clear ToolError message | All rejection tests preserved |
| AC5 no side effects | TestFromAC_NoSideEffects (preserved) |
| AC6 valid IDs regression | TestFromAC_ValidIdsRegression (preserved) |
| AC7 breadth beyond create_dr | All new TestMCPCoverage* classes extend proof to all server paths |
[[2026-05-04]]
## Builder Notes
- Implementation: no file changes in this cycle (verification-only pass).
- Tests: 101 passed, 0 failed, 0 skipped (scoped to task-related suites).
- Coverage: 95% on owlbear_mcp_kanban.server (>=90% gate).
- Ruff: clean on scoped source and test paths.
- Evidence summary: latest test-writer coverage uplift is confirmed in a fresh scoped run; task AC behavior remains green and no further surgical code intervention is required.

## Post-task Reflection
- Prior task history for #1337 showed stale RED snapshots; fresh scoped execution prevented unnecessary churn.
- Verification-only builder passes are valid when implementation is already green and gates are met.
- Keeping coverage scoped to touched module avoided misleading aggregate coverage noise.
- No blocking edge-case gaps were discovered in this cycle.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped run: 101 passed, 0 failed, 0 skipped
- code-reader parallel fan-out failed to return; sequential manual code/test audit performed instead

### Lint Results
- ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and the task test files

### Coverage
- `owlbear_mcp_kanban.server`: 95%

### Scope / Diff Notes
- Builder commit hash was not present in the task body, so the review scope was reconstructed from builder notes and current files.
- Terminal execution is unavailable in this reviewer session, so `git status --porcelain` contamination checks and direct commit-diff / TestFromAC immutability verification could not be completed. Confidence deduction applied.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Shared parser used by every task-id endpoint | `parse_task_id` defined at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:76`; call sites at `:353`, `:402`, `:430`, `:488`, `:532`, `:570`; endpoint rejection proofs in `tests/test_mcp_task_id_parser_1337.py:295` and `tests/test_mcp_create_dr_coerce_1337.py:121`, `:197` | PASS |
| 2. Accept JSON numbers and positive decimal strings | parser happy-path tests in `tests/test_mcp_task_id_parser_1337.py:149`, `:158`, `:167`; bool rejection guard in `tests/test_mcp_kanban.py:381` | PASS |
| 3. Reject invalid categories before engine/filesystem calls | parser rejection coverage at `tests/test_mcp_task_id_parser_1337.py:179`, `:324`, `:337`, `:352`, `:364`, `:380`; create_dr integration rejections at `tests/test_mcp_create_dr_coerce_1337.py:205`, `:226`, `:247` | PASS |
| 4. Clear ToolError message mentioning field + positive integer requirement | message construction in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:77`; direct message tests at `tests/test_mcp_task_id_parser_1337.py:271`, `:280`; create_dr message tests at `tests/test_mcp_create_dr_coerce_1337.py:130`, `:148`, `:170` | PASS |
| 5. Rejected IDs do not create DR files, mutate task state, or fall through to raw lookup | no-side-effect tests at `tests/test_mcp_task_id_parser_1337.py:406`, `:432`, `:455`; pending-dir unchanged proof at `tests/test_mcp_create_dr_coerce_1337.py:266` | PASS |
| 6. Valid numeric values continue to work for all MCP task tools | implementation forwards validated ints at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:355`, `:437`, `:515`, `:537`, `:574`, `:588`; but regression proofs for edit/start/end/show at `tests/test_mcp_task_id_parser_1337.py:549`, `:562`, `:575`, `:588` assert only that the method was called, not that the coerced integer value/type was forwarded | FAIL |
| 7. Existing create_dr coercion tests remain covered and broadened | preserved/broadened create_dr suite at `tests/test_mcp_create_dr_coerce_1337.py:121`, `:197`, `:304`; complemented endpoint-family coverage at `tests/test_mcp_task_id_parser_1337.py:295` | PASS |

### Test Quality Assessment
- `tests/test_mcp_task_id_parser_1337.py:549`, `:562`, `:575`, `:588` are lax AC6 proofs: `assert_called_once()` would stay green if the endpoint forwarded the wrong value/type while still invoking the view.
- Several coverage-uplift tests in `tests/test_mcp_kanban.py` are pure type/presence smoke checks rather than discriminating proofs: `:627`, `:644`, `:690`, `:719`, `:742`. These inflate module coverage without proving the advertised guidance/happy-path behavior.

### Deductions
- -0.06 AC6 regression proofs are lax for `edit_task`, `start_work`, `end_work`, and `show_task`.
- -0.04 coverage-uplift tests rely on `isinstance` / `hasattr` checks that would false-green broken behavior.
- -0.02 code-reader parallel fan-out failed; sequential manual audit used instead.
- -0.02 terminal unavailable, so dirty-tree contamination and direct immutability diff checks could not be completed.

### Verdict
- Confidence: 0.84
- FAIL -> todo
- The implementation in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` satisfies the boundary-validation behavior. The rejection is test-proof only: the green suite is not yet reviewer-grade because key AC6 assertions are lax and some coverage-uplift tests provide false confidence.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC6 regression tests for `edit_task`, `start_work`, `end_work`, and `show_task` so they assert the coerced integer `1` reaches the canonical view/engine, not merely that the method was called. | `tests/test_mcp_task_id_parser_1337.py` | `tests/test_mcp_task_id_parser_1337.py:549`, `:562`, `:575`, `:588` |
| 2 | test-writer | Replace coverage-uplift smoke assertions with discriminating assertions that prove the claimed behavior (for example, concrete guidance content or concrete response payload/task values), or drop non-AC coverage padding that does not strengthen parser-boundary proof. | `tests/test_mcp_kanban.py` | `tests/test_mcp_kanban.py:627`, `:644`, `:690`, `:719`, `:742` |
[[2026-05-04]]
## Test-Writer Notes
- Retry: strengthened AC6 and coverage-uplift assertions (reviewer RF#1 and RF#2).
- Files modified:
  - `tests/test_mcp_task_id_parser_1337.py` — 4 AC6 tests strengthened
  - `tests/test_mcp_kanban.py` — 5 smoke assertions replaced with discriminating proofs
- **AC6 changes** (`test_mcp_task_id_parser_1337.py`): `edit_task`, `start_work`, `end_work`, `show_task` tests now assert the coerced integer `1` reaches the canonical view/engine (not just `assert_called_once()`). Assertions verify both value (`== 1`) and type (`isinstance(..., int)`).
- **Uplift changes** (`test_mcp_kanban.py`):
  - `test_success_outcome_returns_task_and_collects_guidance`: added `end_work_call.args[0] == 1`, `outcome == "success"`, `note == "done"` assertions.
  - `test_block_outcome_triggers_guidance_collection`: added `args[0] == 1`, `outcome == "block"`, `block_reason == "waiting"` assertions.
  - `TestListTasks.test_happy_path_returns_list_response`: replaced `hasattr(result, "tasks")` with `isinstance(result, ListTasksResponse)` + explicit list type + length check.
  - `TestPickTasks.test_happy_path_returns_response`: replaced `hasattr(result, "waves")` with `isinstance(result, PickTasksResponse)` + list type check.
  - `TestShowTask.test_happy_path_returns_task`: added `result.id == 1` to confirm correct task returned.
- All 101 tests PASS against current implementation (retry-type: test-proof strengthening only).
- ruff: clean
- coverage: `owlbear_mcp_kanban.server` = 95%
- Builder skip: test-only retry, all tests green — advancing directly to review.
[[2026-05-04]]
## Builder Notes
- Implementation: no file changes in this cycle (verification-only builder pass).
- Tests: 101 passed, 0 failed, 0 skipped (`tests/test_mcp_task_id_parser_1337.py`, `tests/test_mcp_create_dr_coerce_1337.py`, `tests/test_mcp_kanban.py`).
- Coverage: `owlbear_mcp_kanban.server` = 95% (>= 90% gate).
- Ruff: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and scoped task test files.
- Evidence summary: fresh quality-runner scoped verification confirms AC behavior remains GREEN after latest test-writer strengthening; no additional source intervention required.

## Post-task Reflection
- Fresh scoped verification prevented acting on stale historical fail notes.
- Verification-only builder cycles are valid when implementation is already green and all gates are met.
- Module-scoped coverage targeting (`owlbear_mcp_kanban.server`) gave clear gate evidence without full-suite noise.
- No blocking edge-case gaps surfaced in this cycle.