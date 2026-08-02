---
id: 1337
title: Validate MCP task IDs at every task endpoint trust boundary
status: archived
priority: medium
created: 2026-05-04T15:00:05.722955+00:00
updated: 2026-05-05T03:11:46.441578+00:00
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
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run: 101 passed, 0 failed, 0 skipped
- code-reader found a show_task boundary inconsistency; challenger review narrowed the block to a concrete AC4/AC7 issue rather than a broader AC3 claim

### Lint Results
- ruff clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and the task test files

### Coverage
- owlbear_mcp_kanban.server: 95%

### Scope / Diff Notes
- Review scope reconstructed from task history: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py plus tests/test_mcp_task_id_parser_1337.py, tests/test_mcp_create_dr_coerce_1337.py, and tests/test_mcp_kanban.py
- The task body already contained one prior ## Review Evidence section, so this is a second review-cycle gate and the loop-breaker rule applies on fail
- No terminal tool was available in this reviewer session, so dirty-tree contamination and direct commit-diff / TestFromAC immutability checks could not be completed. Confidence deduction applied

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Shared parser/coercer used by every task-id endpoint | parse_task_id is defined at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:76 and is called from show_task/create_dr/move_task/edit_task/start_work/end_work at server.py:353, 400, 428, 476, 531, 568 | PASS |
| 2. Accept JSON numbers and positive decimal strings | parse_task_id happy-path tests at tests/test_mcp_task_id_parser_1337.py:149, 158, 167 and create_dr forwarding proof at tests/test_mcp_create_dr_coerce_1337.py:312 | PASS |
| 3. Reject invalid inputs before engine/filesystem calls | no-side-effect proofs for move/edit/start at tests/test_mcp_task_id_parser_1337.py:406, 432, 455; create_dr pending-dir unchanged at tests/test_mcp_create_dr_coerce_1337.py:266; durable show_task malformed-string rejection before view at serve/mcp-kanban/tests/test_mcp_server_1090.py:147-170 | PASS |
| 4. Rejections raise a clear ToolError mentioning the relevant id field and positive integer requirement | show_task still validates through ShowTaskParams.id: int at serve/mcp-kanban/src/owlbear_mcp_kanban/models.py:55 before parse_task_id at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:352-358. Durable tests at serve/mcp-kanban/tests/test_mcp_server_1090.py:147-170 and tests/test_server_1170.py:564-571 prove malformed string ids take the PydanticValidationError -> ToolError(str(exc)) path, so this endpoint does not use parse_task_id's field-specific positive-integer error contract for malformed string input | FAIL |
| 5. Rejected IDs do not create DR files, mutate task state, or fall through to raw lookup | same no-side-effect proofs above plus show_task assert_not_called evidence at serve/mcp-kanban/tests/test_mcp_server_1090.py:170 | PASS |
| 6. Valid numeric values continue to work for all MCP task tools | valid-id regression tests at tests/test_mcp_task_id_parser_1337.py:532, 549, 566, 583, 600 and tests/test_mcp_create_dr_coerce_1337.py:312 | PASS |
| 7. Existing create_dr coercion tests remain covered and broadened/complemented so the shared parser cannot regress on other endpoints | task-local show_task coverage only exercises int success and zero/negative cases at tests/test_mcp_task_id_parser_1337.py:365-387, 600-609 and tests/test_mcp_kanban.py:757-792; it does not guard the malformed-string/message path that currently bypasses parse_task_id via Pydantic | FAIL |

### Test Quality Assessment
- The fresh green suite is real, but the new task-local show_task proofs do not exercise the malformed-string boundary path that AC4/AC7 required to be unified
- Existing durable show_task tests assert ToolError / not-called behavior, but they do not assert the positive-integer error contract

### Deductions
- -0.06 no terminal tool for dirty-tree / diff-based immutability checks
- -0.03 line-of-defense fan-out required narrowing after challenger review

### Verdict
- Confidence: 0.87
- FAIL -> backlog
- Fresh scoped evidence is green, but show_task still surfaces malformed string ids through the PydanticValidationError -> ToolError(str(exc)) path instead of the shared positive-integer ToolError contract, and the task-local suites do not lock that boundary down. Because the task already failed review once, the second-cycle loop-breaker routes this rejection to backlog.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rework the retry scope so show_task uses the same field-specific positive-integer ToolError contract as the other task-id endpoints for malformed string input, or explicitly narrow the AC if generic Pydantic integer errors are acceptable | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py, serve/mcp-kanban/src/owlbear_mcp_kanban/models.py | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:352-358; serve/mcp-kanban/src/owlbear_mcp_kanban/models.py:55; serve/mcp-kanban/tests/test_mcp_server_1090.py:147-170; tests/test_server_1170.py:564-571 |
| 2 | architect | Add follow-up proof requirements covering malformed-string show_task inputs and message expectations, because the task-local suites currently only cover int success / zero / negative cases | tests/test_mcp_task_id_parser_1337.py, tests/test_mcp_kanban.py | tests/test_mcp_task_id_parser_1337.py:365-387, 600-609; tests/test_mcp_kanban.py:757-792 |
[[2026-05-05]]

## Rework Scope (Reviewer RF#1, RF#2)

**Root cause:** `show_task` declares `id: int = 0` while all other endpoints use `id: StrId`. This means malformed strings hit `ShowTaskParams.model_validate()` → `PydanticValidationError` → generic `ToolError(str(exc))` before `parse_task_id` runs, bypassing the field-specific positive-integer error contract (AC4).

**Required implementation change:**
1. Change `show_task` parameter from `id: int = 0` to `id: StrId` (matching `move_task`, `edit_task`, `start_work`, `end_work`).
2. Remove `ShowTaskParams.model_validate({"id": id, "section": section})` — `parse_task_id` is the sole validator.
3. Call `parse_task_id(id, field="id")` directly (already present but only reached for int inputs today).
4. Remove the `except PydanticValidationError` catch in `show_task` (dead code after change).

**Required test additions:**
- Add malformed-string show_task boundary tests (e.g., `"../foo"`, `"abc"`, `""`) to `tests/test_mcp_task_id_parser_1337.py` proving the field-specific ToolError message (not generic Pydantic error).
- If `ShowTaskParams` becomes unused after change, delete it from `models.py`.

**Files impacted:**
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (show_task handler)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` (ShowTaskParams — possibly remove)
- `tests/test_mcp_task_id_parser_1337.py` (new boundary tests for show_task string path)

[[2026-05-05]]
## Architecture Review (Rework Cycle)

### Context
Task returned from reviewer (second review cycle, loop-breaker → backlog) with RF#1 and RF#2: `show_task` uses `id: int` parameter type causing malformed strings to bypass `parse_task_id` via PydanticValidationError path.

### Evaluation (delta only — prior full evaluation PASS on all 10 criteria unchanged)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Pattern consistency | PASS (gap identified, fix scoped) | show_task must use StrId like other 5 endpoints |
| Interface clarity | PASS | Rework scope section defines exact parameter/code changes |
| KISS/YAGNI | PASS | Aligns one outlier endpoint with existing pattern — no new abstractions |

### Rework Analysis
- **Root cause:** `show_task` declared `id: int = 0` while `move_task`/`edit_task`/`start_work`/`end_work` use `id: StrId`. Malformed string input hits ShowTaskParams Pydantic validation → generic ToolError instead of parse_task_id's field-specific contract.
- **Fix:** Change parameter to `StrId`, remove ShowTaskParams pre-validation, remove dead PydanticValidationError catch. Verified `StrId` accepts both int and str inputs per AC2.
- **Test gap:** Add malformed-string show_task boundary tests to prove field-specific ToolError message.

### Challenge
Prior challenger pass (confidence 0.47, rebutted) covers architectural decision. This rework is mechanical alignment, not a design change — skipping re-challenge per proportionality.

### Verdict: APPROVE (rework)
AC lines unchanged (already verifiable). Implementation guidance appended to task body. Test-writer will add boundary tests for the show_task string path; builder aligns the parameter type.
[[2026-05-05]]
## Test-Writer Notes
- Retry (rework cycle): added 5 failing tests for `show_task` malformed-string boundary (reviewer RF#1/RF#2, Rework Scope).
- File modified: `tests/test_mcp_task_id_parser_1337.py`
- New class: `TestFromAC_ShowTaskStringBoundary`
- Tests per category: happy 0, edge 0, error 4, boundary 1 → 5 new tests
- All 5 NEW tests FAIL (RED gate satisfied — discriminating pattern r"positive")
- All 30 existing tests in this file PASS (no regressions)
- ruff: clean

**Failure anatomy (discriminating pattern):**
- New tests assert `pytest.raises(ToolError, match=r"positive")`
- Current `show_task(id: int)` routes strings through `ShowTaskParams.model_validate()` → `PydanticValidationError` → `ToolError("…valid integer…")` — no "positive" → match FAILS
- After builder fix (`id: StrId`): `parse_task_id("abc", field="id")` → `ToolError("id must be a positive integer")` → contains "positive" → match PASSES

**AC coverage table:**
| AC | Tests |
|----|-------|
| AC4 field-specific message for show_task string inputs | `TestFromAC_ShowTaskStringBoundary` (5 tests: path-traversal, alpha, empty, shell, whitespace) |
| AC7 breadth: show_task string path locked down | All 5 new tests prove generic Pydantic path is not acceptable |
[[2026-05-05]]
## Builder Notes
- Implementation: updated `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` to align `show_task` with the shared parser contract.
- Code change details: `show_task` now accepts `id: StrId`, calls `parse_task_id(id, field="id")` before any engine/view call, and no longer routes malformed strings through `ShowTaskParams.model_validate` + `PydanticValidationError` fallback.
- Tests (RED verification before edit): 30 passed, 5 failed in `tests/test_mcp_task_id_parser_1337.py` (all failures in `TestFromAC_ShowTaskStringBoundary`, proving the old Pydantic message path).
- Tests (GREEN verification after edit): 106 passed, 0 failed, 0 skipped across:
  - `tests/test_mcp_task_id_parser_1337.py`
  - `tests/test_mcp_create_dr_coerce_1337.py`
  - `tests/test_mcp_kanban.py`
- Coverage: `owlbear_mcp_kanban.server` = 95% (>= 90% gate).
- Ruff: clean for scoped source + test paths.
- Commit: `ff1c3e99` (`fix: align show_task id parser path (#1337, builder)`) with only `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Approach: surgical boundary fix only; no test edits; no unrelated module changes.

## Post-task Reflection
- The failing tests were truly discriminating: regex `positive` cleanly separated parser-contract errors from generic Pydantic integer parsing errors.
- Constraining the fix to a single boundary handler avoided churn and preserved previously green endpoint behavior.
- Scoped quality evidence (`coverage_modules=["owlbear_mcp_kanban.server"]`) provided a reliable gate signal without full-suite noise.
- Keeping `ShowTaskParams` in models avoided unrelated test fallout since other suites still import/validate it.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_mcp_task_id_parser_1337.py`, `tests/test_mcp_create_dr_coerce_1337.py`, and `tests/test_mcp_kanban.py`: 106 passed, 0 failed, 0 skipped.
- quality-runner adjacent rerun on `tests/test_mcp_kanban_1196.py`: 12 passed, 0 failed, 0 skipped. This refreshed the older `create_dr` `assert_not_called()` and literal-int forwarding proofs instead of relying on stale task-history claims.
- code-reader audit found no security, data-safety, or TestFromAC integrity regressions. Remaining concerns were limited to message-matcher breadth and in-session git-state visibility.

### Lint Results
- ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and the four reviewed test files.

### Coverage
- `owlbear_mcp_kanban.server`: 95% in the task-scoped run.

### Scope / Diff Notes
- Latest builder commit confirmed in git logs: `ff1c3e99` in `.git/logs/HEAD:1911` and `.git/logs/refs/heads/dev:1756`.
- Latest builder notes scoped code changes to `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- This review supersedes the earlier FAIL notes where they conflict with current live code. The prior `show_task` Pydantic-path finding is no longer live: `show_task` now takes `id: StrId` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:343-350`, and the malformed-string regression tests at `tests/test_mcp_task_id_parser_1337.py:661`, `:676`, `:688`, `:700`, and `:712` are green.
- No terminal tool was available in this reviewer session, so dirty-tree contamination and diff-based TestFromAC immutability checks could not be executed independently. Confidence deduction applied.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Shared parser/coercer used by every task-id endpoint | `parse_task_id` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:75`; call sites at `:350`, `:398`, `:426`, `:484`, `:528`, `:566`; endpoint/no-side-effect proofs at `tests/test_mcp_task_id_parser_1337.py:412`, `:438`, `:461`, `:661`, `:676`, `:688`, `:700`, `:712` | PASS |
| 2. Accept JSON numbers and positive decimal strings | parser acceptance tests at `tests/test_mcp_task_id_parser_1337.py:155`, `:164`, `:173`; exact forwarded-int assertions for task endpoints at `tests/test_mcp_task_id_parser_1337.py:538`, `:555`, `:572`, `:589`, `:606`; `create_dr` numeric-string and literal-int forwarding at `tests/test_mcp_create_dr_coerce_1337.py:312` and `tests/test_mcp_kanban_1196.py:315`, `:344` | PASS |
| 3. Reject empty, zero, negative, non-decimal, path-like, shell-like, whitespace-padded, and mixed strings before engine access | parser rejection suite in `tests/test_mcp_task_id_parser_1337.py`; endpoint malformed-string proofs at `tests/test_mcp_task_id_parser_1337.py:661`, `:676`, `:688`, `:700`, `:712`; `create_dr` integration rejections at `tests/test_mcp_create_dr_coerce_1337.py:205`, `:226`, `:247`, `:266`; adjacent `create_dr` no-call proofs at `tests/test_mcp_kanban_1196.py:222`, `:240`, `:260`, `:277`, `:294` | PASS |
| 4. Rejections raise a clear ToolError mentioning the relevant id field and positive integer requirement | exact message source at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:77`; parser message tests at `tests/test_mcp_task_id_parser_1337.py:277`, `:286`; `create_dr` message tests at `tests/test_mcp_create_dr_coerce_1337.py:130`, `:148`, `:170`; `show_task` field-specific regression tests at `tests/test_mcp_task_id_parser_1337.py:661`, `:676`, `:688`, `:700`, `:712` | PASS |
| 5. Rejected IDs do not create DR files, mutate task state, or fall through to raw lookup | parse-before-mutation/file boundaries at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:350`, `:398`, `:426`, `:484`, `:528`, `:566`; task-state no-side-effect tests at `tests/test_mcp_task_id_parser_1337.py:412`, `:438`, `:461`; pending-dir unchanged at `tests/test_mcp_create_dr_coerce_1337.py:266`; adjacent `create_dr` `assert_not_called()` proofs at `tests/test_mcp_kanban_1196.py:222`, `:240`, `:260`, `:277`, `:294`; `show_task` rejects zero before engine at `tests/test_mcp_kanban.py:787` | PASS |
| 6. Valid numeric values continue to work for all MCP task tools | exact forwarded-int assertions for `move_task`, `edit_task`, `start_work`, `end_work`, and `show_task` at `tests/test_mcp_task_id_parser_1337.py:538`, `:555`, `:572`, `:589`, `:606`; `create_dr` forwarding at `tests/test_mcp_create_dr_coerce_1337.py:312` and `tests/test_mcp_kanban_1196.py:315`, `:344`; happy-path `show_task` response guard at `tests/test_mcp_kanban.py:757` | PASS |
| 7. Existing `create_dr` coercion tests remain covered and are broadened/complemented so the shared parser cannot regress on other endpoints | task-local `create_dr` suite at `tests/test_mcp_create_dr_coerce_1337.py:130`, `:148`, `:170`, `:205`, `:226`, `:247`, `:266`, `:312`; cross-endpoint parser suite at `tests/test_mcp_task_id_parser_1337.py`; adjacent durable `create_dr` proofs rerun at `tests/test_mcp_kanban_1196.py:222`, `:240`, `:260`, `:277`, `:294`, `:315`, `:344`; endpoint-regression guards in `tests/test_mcp_kanban.py:627`, `:648`, `:755`, `:787` | PASS |

### Test Quality Assessment
- Assertion specificity: ADEQUATE. Exact forwarded-int assertions now exist for `move_task`, `edit_task`, `start_work`, `end_work`, `show_task`, and `create_dr`.
- Negative/error-path coverage: STRONG. Invalid-category and no-side-effect coverage spans parser, endpoint, integration, and adjacent durable `create_dr` suites.
- Manual mutation reasoning: ADEQUATE. Reverting `show_task` to the old Pydantic string path would fail the positive-match regression tests; moving `create_dr` validation below downstream I/O would fail the adjacent `assert_not_called()` tests.
- Test independence: STRONG.
- Descriptive names: STRONG.
- Caveat: some AC4 message matchers remain broader than ideal, but the live implementation centralizes the exact message at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:77`, and no current evidence shows a live contract miss.

### Deductions
- -0.05 no terminal tool for dirty-tree contamination and diff-based TestFromAC immutability checks.
- -0.02 some AC4 message matchers are broader than ideal, though the implementation centralizes the exact contract at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:77`.

### Verdict
- Confidence: 0.90
- PASS to docs.
- Fresh scoped and adjacent evidence shows the trust-boundary validation contract is live, the prior `show_task` parser-path defect is fixed, and the remaining concerns are non-blocking proof-quality caveats rather than AC misses.
[[2026-05-05]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/mcp-kanban/README.md` Tools table showed `id: int` for `show_task` (directly stale from this task's rework), `move_task`, `edit_task`, `start_work`, `end_work` (pre-existing staleness discovered during review). All updated to `id: str \| int` to match current `StrId` type annotation in `server.py`. Pre-task git inspection confirmed `show_task` was `id: int = 0` before #1337; other endpoints already had `id: StrId` from a prior task. |
| 2 | Module docstrings | Yes | N/A | `parse_task_id` has docstring `"""Parse MCP task identifiers as positive base-10 integers."""`. `show_task` docstring unchanged. All other touched functions have docstrings. No updates needed. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body or research docs. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/mcp-kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/mcp-*/src/**`) both matched. Footer updated from `(5c71fc13)` to `(ba422c28)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. `ShowTaskParams` kept in `models.py` per builder notes. No orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | IN (docstrings) | N/A — docstrings adequate |
| `serve/mcp-kanban/README.md` | IN | Updated — tool signature table |
| `share/diagrams/kanban.excalidraw` | IN | Updated — footer timestamp |
| `share/diagrams/mcp-topology.excalidraw` | IN | Updated — footer timestamp |
| `tests/test_mcp_create_dr_coerce_1337.py` | OUT (test file) | N/A |
| `tests/test_mcp_task_id_parser_1337.py` | OUT (test file) | N/A |
| `tests/test_mcp_kanban.py` | OUT (test file) | N/A |

### Files Updated
- `serve/mcp-kanban/README.md` — `show_task`, `move_task`, `edit_task`, `start_work`, `end_work` signatures updated from `id: int` to `id: str | int`
- `share/diagrams/kanban.excalidraw` — footer to `Last verified: 2026-05-05 (ba422c28)`
- `share/diagrams/mcp-topology.excalidraw` — footer to `Last verified: 2026-05-05 (ba422c28)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/1337-pytest-scoped.txt`
- `.owlbear/scratch/1337-pytest.txt`
- `.owlbear/scratch/1337-ruff-scoped.txt`
- `.owlbear/scratch/1337-ruff.txt`

Commit: `9d311b4e`
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Shared parser at every endpoint | `parse_task_id` at server.py:75; call sites at :350, :398, :426, :484, :528, :566 | PASS |
| 2. Accept JSON numbers + decimal strings | Parser happy-path tests at test_mcp_task_id_parser_1337.py:155, :164, :173 | PASS |
| 3. Reject invalid categories before engine | 10+ rejection tests + no-side-effect proofs confirmed in scoped run (118 pass) | PASS |
| 4. Clear ToolError with field + positive integer | Message at server.py:77; show_task string boundary tests at :661-:712 green | PASS |
| 5. Rejected IDs do not mutate state | No-side-effect proofs at test_mcp_task_id_parser_1337.py:412, :438, :461; pending-dir unchanged proof | PASS |
| 6. Valid IDs continue to work | Exact forwarded-int assertions at :538, :555, :572, :589, :606 | PASS |
| 7. Existing create_dr tests broadened | Suite at test_mcp_create_dr_coerce_1337.py preserved + endpoint-family coverage added | PASS |

### Test Results
- Full suite: 4430 passed, 250 failed (all failures in unrelated suites: engine accessor migration, MCP memory, cockpit react), 5 skipped
- Task-scoped: 118 passed, 0 failed (test_mcp_task_id_parser_1337, test_mcp_create_dr_coerce_1337, test_mcp_kanban, test_mcp_kanban_1196)
- ruff: clean on scoped files

### Commit Integrity
- ff1c3e99: fix: align show_task id parser path (#1337, builder)
- 525d1a84: test: add show_task string-boundary tests (#1337, test-writer)
- b526be91: test: strengthen AC6 integer-forwarding assertions (#1337, test-writer)
- bd98cab7: test: fix claimed_at contract (#1337, test-writer)
- 9d311b4e: docs: update mcp-kanban tool signatures and diagram footers (#1337, doc-writer)
- Working tree clean for all task files

### Architect Quality: 4/5
Specific, verifiable AC lines with enumerated rejection categories. One outlier (show_task param type) required rework but the architect provided a precise Rework Scope section that guided the fix cleanly.

### Deduction Breakdown
- -0.02: show_task param type outlier required rework cycle (resolved, minor process gap)
- No other deductions: all AC lines have specific evidence, reviewer section detailed (3 cycles), full suite passes in task scope, lint clean

### Confidence: 0.98
### Action: archive