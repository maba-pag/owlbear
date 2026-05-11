---
id: 1451
title: 'P4-14: Normalize MCP filters, annotations, and errors'
status: review
priority: needed
created: 2026-05-08T19:32:19.525089+00:00
updated: 2026-05-11T08:09:45.167538+00:00
tags:
  - phase-4
  - scope:mcp-kanban
  - type:build
  - filters
  - errors
  - annotations
  - validation
  - deployment-readiness
parent: 1437
depends_on:
  - 1450
  - 1445
  - 1447
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: AgentView/MCP interface behavior for list filters, status-destination validation, annotations, descriptions, and error envelopes.
Out of scope: Cockpit UI, setup seed, agent guidance, and docs.

## Acceptance Criteria
1. list_tasks treats ids=[] as an explicit empty ID request and returns an empty tasks list without falling back to unfiltered board listing.
2. list_tasks with archival_reason and no status argument searches archive storage and returns tasks whose archival_reason matches the requested product archive reason.
3. move_task and end_work destination handling use one shared validation path for status names, archive reason requirements, archive refs, completed-only archival, and predicate failures.
4. MCP tool annotations and descriptions state that move_task is mutating and not idempotent, pick_tasks is read-only after dispatch side effects are removed, and resolve_drs performs DR mutation.
5. MCP errors for KanbanError, Pydantic validation, malformed ID, and stale write cases surface structured code and message fields without raw tracebacks or internal paths.
6. Builder verifies AC-1 through AC-5 using the probe artifacts from #1450 and does not use pytest or vitest as the functional proof.
[[2026-05-11]]


## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes within kanban MCP interface normalization |
| Interface clarity | PASS after refinement | AC-3 narrowed to archival-constraint helper; AC-5 paths enumerated; AC-6 demoted to guidance |
| Dependency correctness | PASS | #1450 (probes), #1445 (pick_tasks read-only), #1447 (resolve_drs) — all archived/done |
| Module layering | PASS | Changes in serve/kanban (AgentView) and serve/mcp-kanban (server.py); MCP→kanban direction correct |
| TDD compliance | PASS | Probe suite TestMergedFrom1450 in tests/test_mcp_kanban.py provides RED coverage; package-level suites in serve/mcp-kanban/tests/ also constrain behavior |
| KISS/YAGNI | PASS | Shared helper reduces duplication; no new abstractions |
| Premise challenge | PASS | Normalizing inconsistent error surfaces and duplicated validation is warranted |
| Pattern consistency | PASS | Follows existing KanbanError/code taxonomy; structured {code, message} envelope pattern |
| Security surface | PASS | AC-5 explicitly prevents leaking internal paths; no new external boundaries |
| Single domain | PASS | kanban MCP domain only |

### AC Assessment

| AC Line | Original | Refined | Action |
|---------|----------|---------|--------|
| AC-1 | ids=[] returns empty | Keep as-is (td:0) — MCP layer short-circuits at server.py:212; AgentView would also return empty via set arithmetic | No change |
| AC-2 | archival_reason auto-searches archive | Keep as-is (td:0) — MCP layer resolves status=archived at server.py:215; AgentView post-filters at agent_view.py:210 | No change |
| AC-3 | "one shared validation path" | Narrowed (td:1) — see below | Refined |
| AC-4 | move_task not idempotent, descriptions | Tightened (td:0) — see below | Refined |
| AC-5 | structured errors | Enumerated (td:1) — see below | Refined |
| AC-6 | builder uses probes not pytest | Demoted to builder guidance — not a verifiable code criterion | Moved |

### AC-3 Refinement

move_task and end_work share a single private helper for archival-constraint validation (archival-reason requirement, archival-ref constraints, completed-only archival check, archival-field prohibition on non-archive moves). Both methods call this helper instead of duplicating the validate_archival / ERR_ARCHIVAL_FIELDS_FORBIDDEN logic inline. Status-name validation (different valid sets per outcome) and outcome-specific error codes (ERR_MOVE_TO_INVALID_STATUS vs ERR_INVALID_STATUS) remain in each method. The success-outcome derived-next-status predicate check is end_work-specific and stays there. Explicit-target predicate checks (move_task status, end_work reject/block move_to) may optionally be included in the shared helper.

### AC-4 Refinement — Contract Break

**idempotentHint change:** move_task currently has `idempotentHint=True`, defended by two explicit tests:
- `serve/mcp-kanban/tests/test_tool_annotations.py::TestFromAC_ToolAnnotations::test_move_task_idempotent_hint_true`
- `serve/mcp-kanban/tests/test_tool_annotations.py::TestFromAC_AnnotationContractRestore_1475::test_move_task_idempotent_hint_true_per_original_ac`

Strictly, move_task is NOT idempotent: repeated calls update `updated` timestamp and create activity events. The AC requirement to set `idempotentHint=False` is correct. **Builder must update both test classes** in `test_tool_annotations.py` to assert `False` and update their docstrings to reflect the revised contract.

**Descriptions:** Update tool docstrings for move_task (state: mutating, non-idempotent), pick_tasks (state: read-only, idempotent), and resolve_drs (state: mutates DR files on disk).

### AC-5 Refinement — Enumerated Raw ToolError Paths

Seven raw-string ToolError paths need structured `{code, message}` JSON envelopes:

1. `_show_validated` FileNotFoundError → `ToolError(msg)` — server.py:270
2. `create_dr` request_type guard → `ToolError(msg)` — server.py:327
3. `move_task` missing status → `ToolError(msg)` — server.py:381
4. `start_work` ValueError/FileNotFoundError → `ToolError(str(exc))` — server.py:479-480
5. `end_work` ValueError/FileNotFoundError → `ToolError(str(exc))` — server.py:516-517
6. `list_tasks` PydanticValidationError → `ToolError(str(exc))` — server.py:231
7. `pick_tasks` PydanticValidationError → `ToolError(str(exc))` — server.py:559

Use consistent codes: ERR_NOT_FOUND for FileNotFoundError, ERR_PARAM_VALIDATION for Pydantic and parameter guards, ERR_INVALID_ID for malformed IDs (already done). No raw tracebacks or internal file paths in any error response.

### Builder Guidance

- Probe suite `tests/test_mcp_kanban.py::TestMergedFrom1450` provides primary verification; builder may extend the probe class with additional assertions for AC-4 (idempotentHint=False) and AC-5 (Pydantic envelope) but does not create new test files.
- The probe test `test_move_task_idempotent_hint_is_false` only checks `isinstance(bool)` — the builder should add an explicit `assert ann.idempotentHint is False` assertion to the probe class.
- Test-writer: SKIP not applicable — td:1 lines present; test-writer processes normally using td annotations.

### Challenge Result

Challenger confidence: 0.41, recommendation: block. Concerns addressed:
1. AC-1/AC-2 scope — MCP-layer normalization is sufficient; AgentView also returns empty for ids=[] via set arithmetic. Kept as verification guards.
2. AC-4 contract conflict — acknowledged; builder must update test_tool_annotations.py explicitly. Justified by strict idempotency semantics.
3. AC-3 shared-helper scope — narrowed to archival constraints; outcome-specific codes/validation remain separate.
4. AC-5 enumerated paths — all 7 raw ToolError sites listed with target codes.
5. AC-6 demotion — moved to builder guidance with proof reference preserved.
Override: PROCEED. All concerns resolved through AC refinement; no architectural blocker remains.
[[2026-05-11]]
Architecture review complete. AC refined: AC-3 narrowed to archival-constraint shared helper (status-name validation stays per-method); AC-4 idempotentHint contract break acknowledged with explicit test update requirement; AC-5 enumerated 7 raw ToolError paths; AC-6 demoted to builder guidance. Challenger override at 0.41 — all concerns resolved through refinement. td:0 for AC-1/2/4, td:1 for AC-3/5.
[[2026-05-11]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_1451.py
- Classes: TestFromAC_SharedArchivalHelper, TestFromAC_StructuredErrors
- AC coverage:
  - AC-1 (td:0): skipped — already tested in TestMergedFrom1450
  - AC-2 (td:0): skipped — already tested in TestMergedFrom1450
  - AC-3 (td:1): 3 tests — existence of _validate_archival_constraints, invocation by move_task, invocation by end_work
  - AC-4 (td:0): skipped — builder must update existing test_tool_annotations.py assertions
  - AC-5 (td:1): 18 tests — 2 per enumerated path (envelope + specific code): _show_validated FileNotFoundError (ERR_NOT_FOUND), create_dr request_type guard (ERR_PARAM_VALIDATION), move_task missing status (ERR_PARAM_VALIDATION), start_work ValueError (ERR_PARAM_VALIDATION), start_work FileNotFoundError (ERR_NOT_FOUND), end_work ValueError (ERR_PARAM_VALIDATION), end_work FileNotFoundError (ERR_NOT_FOUND), list_tasks PydanticValidationError (ERR_PARAM_VALIDATION), pick_tasks PydanticValidationError (ERR_PARAM_VALIDATION)
- Tests per category: happy 0, edge 0, error 21, boundary 0
- Total: 21 tests, all FAIL (RED confirmed)
- ruff: clean
[[2026-05-11]]
## Builder Notes
- Implementation: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/tests/test_tool_annotations.py`, `tests/test_mcp_kanban.py`.
- Fixes applied:
  - Added shared `_validate_archival_constraints` helper and delegated both `move_task` and `end_work` through it for archival-target validation path reuse.
  - Normalized raw MCP adapter errors to structured JSON `{"code","message"}` envelopes for: `_show_validated` FileNotFoundError, `create_dr` request_type guard, `move_task` missing status, `start_work` ValueError/FileNotFoundError, `end_work` ValueError/FileNotFoundError, `list_tasks` Pydantic validation, and `pick_tasks` Pydantic validation.
  - Updated `move_task` ToolAnnotations to `idempotentHint=False` and aligned annotation contract tests accordingly.
  - Updated tool descriptions/docstrings to state: `move_task` is mutating/non-idempotent, `pick_tasks` is read-only/idempotent, `resolve_drs` mutates DR files.
  - Strengthened probe assertion in `TestMergedFrom1450` to explicitly assert `move_task` idempotent hint is false.
- Verification evidence:
  - RED verified pre-change: `tests/test_mcp_kanban_1451.py` had 21/21 failing (quality-runner).
  - GREEN scoped pass: 57 passed / 0 failed (`tests/test_mcp_kanban_1451.py`, `serve/mcp-kanban/tests/test_tool_annotations.py`, `tests/test_mcp_kanban.py::TestMergedFrom1450`).
  - Expanded compatibility+coverage pass: 444 passed / 0 failed across MCP-kanban suites (`serve/mcp-kanban/tests`, `tests/test_mcp_kanban_1451.py`, `tests/test_mcp_kanban.py::TestMergedFrom1450`, `tests/test_mcp_schema_assertion.py`, `tests/test_mcp_resolve_drs_1447.py`).
  - Lint: clean (`ruff` violations: 0).
  - Coverage: `owlbear_mcp_kanban.server` = 96% (303 stmts, 13 missed).
- Commit: `fa324f5e` (`feat: normalize mcp-kanban validation and errors (#1451, builder)`).
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner over-scoped run on `tests/test_mcp_kanban.py` surfaced unrelated durable-suite failures: `tests/test_mcp_kanban.py::TestMergedFrom1197::test_server_1170_make_engine_mock_uses_noncallable_agent_view` and `tests/test_mcp_kanban.py::TestMergedFrom1360::test_server_module_line_count_reduced`. I did not gate on that run.
- quality-runner narrowed rerun on the actual task surface passed: `57 passed, 0 failed, 0 skipped` for `tests/test_mcp_kanban_1451.py`, `serve/mcp-kanban/tests/test_tool_annotations.py`, and `tests/test_mcp_kanban.py::TestMergedFrom1450`.
- code-reader adversarial pass corroborated missing AC proof on AC-3/4/5.

### Lint Results
- `ruff`: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/tests/test_tool_annotations.py`, `tests/test_mcp_kanban_1451.py`, and `tests/test_mcp_kanban.py`.

### Coverage Data
- quality-runner narrowed rerun reported `owlbear_mcp_kanban.server` overall coverage at `66%`.
- I did not treat module-level coverage as the sole fail trigger here. The fail is driven by specific uncovered/under-proven changed paths in AC-3/4/5.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC-1 | `list_tasks` short-circuits explicit empty ids at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:258`; probe tests `tests/test_mcp_kanban.py:1597`, `tests/test_mcp_kanban.py:1602`, and `tests/test_mcp_kanban.py:1613` prove empty result / no fallback board listing. | PASS |
| AC-2 | `list_tasks` forces archived lookup when only `archival_reason` is supplied at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:261`; probe tests `tests/test_mcp_kanban.py:1618`, `tests/test_mcp_kanban.py:1625`, and `tests/test_mcp_kanban.py:1633` prove archived-task lookup and reason filtering. | PASS |
| AC-3 | Shared helper exists at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:141`, but `end_work` only copies `move_to` into `target_status` when `outcome == "reject"` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:560`, while the published MCP contract says `move_to` is optional for `success` or `block` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:735`. Engine-level contract proves those paths are real: `serve/kanban/tests/test_engine_end_work.py:363` (`block+move_to`) and `serve/kanban/tests/test_engine_end_work.py:602` (`success+move_to`). Task tests only drive `move_task(..., status="in-progress")` and `end_work(outcome="success", note="done")` at `tests/test_mcp_kanban_1451.py:170` and `tests/test_mcp_kanban_1451.py:199`, so the destination-bearing `end_work` path is both under-tested and currently inconsistent with the MCP contract. | FAIL |
| AC-4 | Runtime text is updated in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:397`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:415`, and `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:604`, but the scoped tests only assert move-task / pick-tasks hints (`serve/mcp-kanban/tests/test_tool_annotations.py:134`, `serve/mcp-kanban/tests/test_tool_annotations.py:185`, `tests/test_mcp_kanban.py:1689`, `tests/test_mcp_kanban.py:1699`). The annotation suite still declares `All 7 tools have annotations` at `serve/mcp-kanban/tests/test_tool_annotations.py:12` and `serve/mcp-kanban/tests/test_tool_annotations.py:56`, so it does not prove the `resolve_drs` description contract at all. | FAIL |
| AC-5 | The adapter maps KanbanError to JSON at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:112` and has a path-scrubbing helper at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:131`. Task tests do prove JSON envelopes for not-found / Pydantic / malformed-id / stale-write cases (`tests/test_mcp_kanban_1451.py:252`, `tests/test_mcp_kanban_1451.py:506`, `tests/test_mcp_kanban_1451.py:538`, `tests/test_mcp_kanban.py:1704`, `tests/test_mcp_kanban.py:1737`). But the live KanbanError coverage still accepts plain-string ToolErrors (`tests/test_mcp_kanban.py:513`, `tests/test_mcp_kanban.py:648`, `tests/test_mcp_kanban.py:806`) and helper-routing tests stub `_map_kanban_error` to `raise ToolError(exc.user_message)` (`tests/test_mcp_kanban.py:1119`, `tests/test_mcp_kanban.py:1146`, `tests/test_mcp_kanban.py:1179`, `tests/test_mcp_kanban.py:1206`, `tests/test_mcp_kanban.py:1233`). The no-internal-paths clause is also unproved because the not-found task test injects only `FileNotFoundError("no such task file")` at `tests/test_mcp_kanban_1451.py:242` and `tests/test_mcp_kanban_1451.py:262`, so `_safe_not_found_message()`'s path-scrubbing branch is never forced. | FAIL |

### Test Integrity
- Builder notes explicitly state `serve/mcp-kanban/tests/test_tool_annotations.py` was modified. Current snapshot shows stronger exact `False` assertions for `move_task` idempotency at `serve/mcp-kanban/tests/test_tool_annotations.py:134` and `serve/mcp-kanban/tests/test_tool_annotations.py:185`; I do not see evidence of weakened assertions in the current tree.
- Confidence is slightly reduced because the current tool surface did not let me run `git diff` / `git status`; commit presence was confirmed via `.git/logs` (`fa324f5e` exists), but immutability/dirty-tree proof is lower-confidence than a direct diff.

### Deductions
- `-0.05` no direct `git diff` / `git status` evidence in current tool surface; commit existence only.
- `-0.10` AC-3 implementation/contract inconsistency on `end_work` destination handling.
- `-0.07` AC-4 description contract is not actually proven by the scoped tests.
- `-0.08` AC-5 KanbanError / path-scrubbing proof remains weak or missing.

### Verdict
- Confidence: `0.70`
- FAIL -> `in-progress`
- Rationale: first review failure, and the task has mixed implementation + proof issues. One builder retry can fix the `end_work` destination handling and add the missing AC-4/AC-5 proof without another handoff.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | builder | Route `end_work` destination-bearing `move_to` paths through the same archival-validation setup used by `move_task`, or narrow the published MCP contract if `success`/`block` must not accept `move_to`. | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | `server.py:560` only handles `reject`, while `server.py:735` advertises `success`/`block`; engine contract proves `block+move_to` and `success+move_to` at `serve/kanban/tests/test_engine_end_work.py:363` and `serve/kanban/tests/test_engine_end_work.py:602`. |
| 2 | builder | Add destination-bearing `end_work` tests that exercise the shared archival helper through a real `move_to` path, including at least one block/reject archived-target case. | `tests/test_mcp_kanban_1451.py`, `tests/test_mcp_kanban.py` | Current helper tests only hit `move_task(..., status="in-progress")` and `end_work(outcome="success", note="done")` at `tests/test_mcp_kanban_1451.py:170` and `tests/test_mcp_kanban_1451.py:199`. |
| 3 | builder | Add explicit AC-4 metadata assertions for the updated descriptions of `move_task`, `pick_tasks`, and `resolve_drs`. | `serve/mcp-kanban/tests/test_tool_annotations.py`, `tests/test_mcp_kanban.py`, `tests/test_mcp_resolve_drs_1447.py` | Current scoped tests prove hints only and do not cover `resolve_drs` description text; annotation suite still scopes itself to `All 7 tools` at `serve/mcp-kanban/tests/test_tool_annotations.py:12` / `:56`. |
| 4 | builder | Strengthen AC-5 proof to assert JSON `{code,message}` output on real KanbanError paths and force `_safe_not_found_message()` to scrub a path-like FileNotFoundError message. | `tests/test_mcp_kanban.py`, `tests/test_mcp_kanban_1451.py` | Plain-string matches at `tests/test_mcp_kanban.py:513`, `:648`, `:806` and helper stubs at `:1119`, `:1146`, `:1179`, `:1206`, `:1233` would still pass if `_map_kanban_error` stopped returning JSON; path scrub branch untested because task fixture uses `"no such task file"` at `tests/test_mcp_kanban_1451.py:242` / `:262`. |
[[2026-05-11]]
## Builder Notes
- Implementation: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py.
- Fix applied: aligned `end_work` target-status derivation so `move_to` for outcomes `success`, `block`, and `reject` routes through the shared `_validate_archival_constraints` path (previously only `reject` populated `target_status`).
- Behavior impact: contract and implementation now agree for destination-bearing `end_work` calls; archival-constraint prevalidation is consistently applied before engine invocation when `move_to` is used on supported outcomes.
- Tests: 458 passed, 0 failed, 0 skipped (scoped quality-runner set: `serve/mcp-kanban/tests`, `tests/test_mcp_kanban_1451.py`, `tests/test_mcp_kanban.py::TestMergedFrom1450`, `tests/test_mcp_kanban.py::TestEndWorkDirectPath`, `tests/test_mcp_kanban.py::TestNoRetryOnTypeError`, `tests/test_mcp_kanban.py::TestMergedFrom1092`, `tests/test_mcp_schema_assertion.py`, `tests/test_mcp_resolve_drs_1447.py`).
- Coverage: `owlbear_mcp_kanban.server` 96%.
- Lint: ruff clean (0 violations) on changed and task-surface files.
- Test integrity: no `TestFromAC_*` classes modified.
- Commit: `3025c84f` (`fix: align end_work move_to validation paths (#1451, builder)`).
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner scoped task-surface pass: `127 passed, 0 failed, 0 skipped` for `tests/test_mcp_kanban_1451.py`, `serve/mcp-kanban/tests/test_tool_annotations.py`, `tests/test_mcp_kanban.py::TestMergedFrom1450`, `tests/test_mcp_kanban.py::TestEndWorkDirectPath`, `tests/test_mcp_kanban.py::TestNoRetryOnTypeError`, `tests/test_mcp_kanban.py::TestMergedFrom1092`, `tests/test_mcp_schema_assertion.py`, and `tests/test_mcp_resolve_drs_1447.py`.
- quality-runner adjacent regression pass: `2 passed, 0 failed` for `tests/test_mcp_end_work_fail.py::TestFromAC_EndWorkSuccessMoveTo`.
- quality-runner adjacent error-mapping pass: `5 passed, 0 failed` for `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py::TestFromAC_KanbanErrorMapping` and `tests/test_mcp_kanban.py::TestShowValidated`.

### Lint Results
- `ruff`: clean on the scoped review surfaces above.

### Coverage Data
- quality-runner scoped task-surface run reported `owlbear_mcp_kanban.server` at `75%` statement coverage.
- I did not use module-level percentage as the sole gate. The blocking issue is an explicit AC-5 proof gap on a changed branch.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC-1 | `tests/test_mcp_kanban.py::TestMergedFrom1450::test_empty_ids_returns_empty_task_list`, `::test_empty_ids_returns_empty_for_multi_task_board`, and `::test_empty_ids_returns_missing_ids_is_none` passed; these prove explicit `ids=[]` returns an empty task list without falling back to board listing. | PASS |
| AC-2 | `tests/test_mcp_kanban.py::TestMergedFrom1450::test_archival_reason_without_status_finds_archived_task`, `::test_archival_reason_filter_all_returned_tasks_match`, and `::test_archival_reason_duplicate_excludes_completed_reason` passed; these prove archive lookup and reason filtering when only `archival_reason` is supplied. | PASS |
| AC-3 | Implementation now derives `target_status` for `success`, `block`, and `reject` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:560`, delegates archival checks through `_validate_archival_constraints` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:141`, and adjacent runtime tests `tests/test_mcp_end_work_fail.py::TestFromAC_EndWorkSuccessMoveTo::test_end_work_success_with_move_to_returns_task_response` plus `::test_end_work_success_move_to_advances_to_specified_status` passed. Task-local helper tests at `tests/test_mcp_kanban_1451.py::TestFromAC_SharedArchivalHelper` also passed. | PASS |
| AC-4 | Tool descriptions now state mutation/read-only semantics directly in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:397`, `:423`, and `:611`. Annotation assertions passed for `move_task` idempotent false in `serve/mcp-kanban/tests/test_tool_annotations.py`, for `pick_tasks` readOnly/idempotent in `tests/test_mcp_kanban.py::TestMergedFrom1450`, and for `resolve_drs` annotations in `tests/test_mcp_resolve_drs_1447.py::TestFromAC_ResolveDrsRegistration`. AC-4 is `td:0`, so direct artifact inspection is acceptable for the description wording. | PASS |
| AC-5 | Structured `{code,message}` envelopes are exercised by `tests/test_mcp_kanban_1451.py::TestFromAC_StructuredErrors` and `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py::TestFromAC_KanbanErrorMapping`, and the implementation contains `_safe_not_found_message()` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:131` with the slash/backslash scrub at `:136`. However, no test forces a path-like `FileNotFoundError` message through that branch: current task tests inject only `FileNotFoundError("no such task file")` at `tests/test_mcp_kanban_1451.py:242` and `:262`, and the durable `_show_validated` check at `tests/test_mcp_kanban.py:480` only regex-matches the same non-path string. If the slash/backslash scrub were removed, the suite would stay green while internal path leakage regressed. | FAIL |

### Deductions
- `-0.04` no direct `git diff` / `git status` evidence in the current tool surface; commit existence was confirmed via `.git/logs` (`fa324f5e`, `3025c84f`).
- `-0.06` AC-5 still has a false-green branch: the explicit internal-path scrubbing clause is implemented but not discriminated by a test.

### Verdict
- Confidence: `0.88`
- FAIL -> `backlog`
- Rationale: the remaining issue is proof quality, not the repaired implementation. This is the second review cycle on the same unresolved proof gap, so the loop-breaker rule routes the task to `backlog` for AC/test-plan refinement rather than another narrow builder retry.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Refine AC-5 proof requirements and create a follow-up test task that forces a path-like `FileNotFoundError` through `_show_validated`, then asserts the scrubbed JSON `{code,message}` envelope so internal paths cannot false-green. | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `tests/test_mcp_kanban_1451.py`, `tests/test_mcp_kanban.py` | `_safe_not_found_message` exists at `server.py:131` / `:136`, but current tests use only `"no such task file"` at `tests/test_mcp_kanban_1451.py:242` / `:262` and regex-only matching at `tests/test_mcp_kanban.py:480`, so the scrub branch is currently unproved. |
[[2026-05-11]]

## Architecture Re-Review (cycle 3)

### Context

Returned from review cycle 2 with a single unresolved gap: AC-5 path-scrubbing branch in `_safe_not_found_message()` (server.py:135-136) is implemented but untested. The slash/backslash detection→fallback branch can be deleted without any test failing — a false-green on a security-relevant code path.

AC-1 through AC-4 passed review. AC-3 implementation was repaired in cycle 2 (commit `3025c84f`). The gap is purely test coverage, not implementation.

### AC-5 Refinement

Original AC-5: "MCP errors for KanbanError, Pydantic validation, malformed ID, and stale write cases surface structured code and message fields without raw tracebacks or internal paths."

Added sub-clause to discriminate the path-scrubbing branch:

**AC-5a (td:1):** At least one `_show_validated` FileNotFoundError test injects a path-containing message (e.g., `FileNotFoundError("/var/data/kanban/tasks/99.md")`) and asserts that the JSON envelope `message` field contains the fallback text (`"Task '99' not found"`), not the original path. This proves `_safe_not_found_message()` scrubs internal paths.

**Implementation note for test-writer:** Add one test to the existing `TestFromAC_StructuredErrors` class in `tests/test_mcp_kanban_1451.py`. Mock `engine.show_task` with `side_effect=FileNotFoundError("/var/data/kanban/tasks/99.md")`, call `_show_validated(app_ctx, 99)`, parse the ToolError as JSON, and assert `payload["message"] == "Task '99' not found"` and `"/var/" not in payload["message"]`.

### Challenger

Skipped — this is a proof-quality re-refinement of an already-approved architecture. The original challenger ran at cycle 1 (confidence 0.41, concerns resolved through AC refinement, override justified). No architectural decision has changed; only one test requirement is being added.

### Verdict

APPROVED — AC-5a added as a discriminating test requirement for the path-scrubbing branch. All other AC lines passed review in cycle 2. Test-writer processes AC-5a (td:1); builder adds the single test.
[[2026-05-11]]
Architecture re-review (cycle 3): added AC-5a (td:1) requiring path-scrub discrimination test for _safe_not_found_message(). Single test addition — inject path-like FileNotFoundError, assert fallback replaces internal path in JSON envelope. All other AC lines passed in cycle 2. Challenger skipped (proof refinement, not new architecture).
[[2026-05-11]]
## Test-Writer Notes
- Retry (cycle 3): AC-5a path-scrub discrimination test added.
- Test file: tests/test_mcp_kanban_1451.py
- Class: TestFromAC_StructuredErrors (existing)
- New test: `test_show_validated_path_like_not_found_scrubs_internal_path`
  - Injects `FileNotFoundError("/var/data/kanban/tasks/99.md")` into `engine.show_task`
  - Calls `_show_validated(app_ctx, 99)`
  - Parses ToolError as JSON and asserts `payload["message"] == "Task '99' not found"` and `"/var/" not in payload["message"]`
  - Forces the slash-detection branch in `_safe_not_found_message()` — removing that branch would cause this test to fail
- **Step 1b.1 advance:** New test PASSES immediately — implementation already correctly scrubs path-like messages. No builder work required.
- ruff: clean (0 violations)
- Commit: `0cb11c67`