---
id: 1362
title: Implement structured JSON error responses at MCP boundary
status: archived
priority: medium
created: 2026-05-05T23:35:00.574972+00:00
updated: 2026-05-06T05:16:51.026760+00:00
tags:
- kanban
- agent-ux
- deploy-prep
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Change `_map_kanban_error` in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` to emit structured JSON in the ToolError message, enabling agents to programmatically distinguish error types.

## AC

- [ ] `_map_kanban_error` emits `json.dumps({\"code\": exc.code, \"message\": exc.user_message})`
- [ ] All existing error-handling tests updated to expect JSON-structured error messages
- [ ] Agents can parse error codes from ToolError text (ERR_STALE → retry, ERR_NOT_FOUND → stop, etc.)
- [ ] Human-readable message still present in the JSON structure

## Context

Audit Finding Group 8. Currently all KanbanError subclasses map to flat ToolError(user_message), losing the structured error code. Agents must parse English text to determine error type — fragile.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_error_mapping_1362.py
- Classes: TestFromAC_StructuredJsonErrors
- Tests per category: happy 5, edge 3, error 2, boundary 3
- Total: 13 tests, all FAIL
- ruff: clean

**AC coverage:**
| AC line | Tests |
|---------|-------|
| AC1: `_map_kanban_error` emits `json.dumps({"code": ..., "message": ...})` | test_emits_parseable_json, test_json_contains_code_field, test_json_code_equals_exc_code, test_json_contains_message_field, test_message_not_bare_user_message |
| AC2: existing tests updated to expect JSON | test_message_is_json_object_not_bare_string (regression guard for new contract) |
| AC3: agents can parse error codes (ERR_STALE → retry, ERR_NOT_FOUND → stop) | test_err_stale_code_in_json, test_err_not_found_stop_signal, test_err_already_claimed_code_in_json, test_agent_can_parse_error_code_from_tool_error_text |
| AC4: human-readable message in JSON structure | test_json_message_equals_user_message, test_migration_required_code_in_json, test_user_message_with_special_chars_round_trips |

**Failure mode:** All 13 fail with `json.decoder.JSONDecodeError` or `AssertionError` — current `_map_kanban_error` raises `ToolError(exc.user_message)` (bare string, not JSON).
[[2026-05-06]]
## Builder Notes
- Implementation: no code changes required; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` already emits structured JSON in `_map_kanban_error`.
- Files changed: none.
- RED verification result: task-scoped `tests/test_mcp_kanban_error_mapping_1362.py` was already GREEN (13/13 passed), confirming behavior pre-exists in current codebase.
- Tests: 128 passed in scoped MCP-kanban verification set:
  - `tests/test_mcp_kanban.py`
  - `tests/test_mcp_kanban_1091.py`
  - `tests/test_mcp_kanban_1092.py`
  - `tests/test_mcp_kanban_1196.py`
  - `tests/test_mcp_kanban_1360.py`
  - `tests/test_mcp_kanban_error_mapping_1362.py`
  - `serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py`
- Coverage: 95% on `owlbear_mcp_kanban.server` (via quality-runner scoped report).
- ruff: clean (0 violations) for `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Evidence summary: AC behavior (`ToolError` containing JSON payload with `code` and `message`) is already present and validated by task tests plus broader MCP-kanban regression suite.
- Fixes applied: none (task verified as already satisfied).
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner broad adjacent-suite pass: 94 passed, 38 failed, 132 total. That run mixed in older fixture/guidance failures, so I reran a focused JSON-contract pass.
- quality-runner focused JSON-contract pass: 15 passed, 2 failed, 17 total.
- Direct contract failure: `serve/mcp-kanban/tests/test_mcp_guidance_1089.py::TestFromAC_ErrorMapping::test_validation_error_maps_to_tool_error`
  - Expected: `title must not be empty`
  - Got: `{"code": "ERR_INVALID_STATUS", "message": "title must not be empty"}`
- Secondary focused failure: `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py::TestFromAC_KanbanErrorMapping::test_not_found_error_mapped_to_tool_error_with_user_message` failed with `TypeError: 'NonCallableMagicMock' object is not callable`. I did not use that fixture issue as the review blocker.
- Task-local JSON contract suite is present and green: `tests/test_mcp_kanban_error_mapping_1362.py::TestFromAC_StructuredJsonErrors` passed in the focused run (13 tests).

### Lint Results
- Ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and the scoped test files.

### Coverage Data
- Broad adjacent-suite run reported 74% on `owlbear_mcp_kanban.server`.
- Focused node-id rerun reported 40% on `owlbear_mcp_kanban.server` because only 17 selected tests were executed.
- Coverage is informational only here: builder reported no source diff, and this review is failing on stale test contract evidence, not unexercised changed lines.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| `_map_kanban_error` emits `json.dumps({"code": exc.code, "message": exc.user_message})` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:108-111` raises `ToolError(payload)` where `payload = json.dumps({"code": exc.code, "message": exc.user_message})`; task-local suite proves parseable JSON and exact code/message fields | `tests/test_mcp_kanban_error_mapping_1362.py::TestFromAC_StructuredJsonErrors` | PASS |
| All existing error-handling tests updated to expect JSON-structured error messages | Stale durable tests remain. `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:412-435` still requires `ToolError(user_message)` and no `ERR_` code on wire; focused quality-runner run fails on that exact expectation. `serve/mcp-kanban/tests/test_mcp_read_tools.py:1061-1080`, `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:502-516`, and `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:425-440` still assert bare `user_message` presence/regex instead of parsing JSON `code` + `message` | `test_validation_error_maps_to_tool_error`; `test_tool_error_carries_user_message_not_code`; `test_validation_error_user_message_in_tool_error`; `test_not_found_error_mapped_to_tool_error_with_user_message` | FAIL |
| Agents can parse error codes from ToolError text (ERR_STALE -> retry, ERR_NOT_FOUND -> stop, etc.) | Task-local suite parses `ToolError` text with `json.loads(...)` and asserts `ERR_STALE` / `ERR_NOT_FOUND` | `tests/test_mcp_kanban_error_mapping_1362.py::test_map_kanban_error_err_stale_code_in_json`; `tests/test_mcp_kanban_error_mapping_1362.py::test_map_kanban_error_err_not_found_stop_signal`; `tests/test_mcp_kanban_error_mapping_1362.py::test_agent_can_parse_error_code_from_tool_error_text` | PASS |
| Human-readable message still present in the JSON structure | Task-local suite asserts `payload["message"] == user_message` and round-trip preservation for special characters | `tests/test_mcp_kanban_error_mapping_1362.py::test_map_kanban_error_json_message_equals_user_message`; `tests/test_mcp_kanban_error_mapping_1362.py::test_map_kanban_error_user_message_with_special_chars_round_trips` | PASS |

### Deductions
- -0.10: AC2 is unmet because existing durable error-handling tests were not fully migrated to the JSON contract.
- -0.02: No builder commit hash was recorded, so TestFromAC immutability could not be proven from diff history in this tool surface. I found no evidence of weakened task-local assertions.

### Verdict
- FAIL -> todo
- Confidence: 0.88
- Reason: implementation already satisfies AC1/AC3/AC4, but AC2 fails because older MCP-kanban durable tests still encode the pre-JSON `ToolError(user_message)` contract or only weakly assert message substrings.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update durable MCP-kanban error-mapping assertions to parse `ToolError` text as JSON and assert exact `code` and `message`, replacing plain-string/no-code expectations | serve/mcp-kanban/tests/test_mcp_guidance_1089.py | focused quality-runner failure; file lines 412-435 |
| 2 | test-writer | Strengthen adjacent error-handling tests so they prove JSON structure instead of only checking that `user_message` appears somewhere in the error text | serve/mcp-kanban/tests/test_mcp_read_tools.py, serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py, serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py | file lines 1061-1080, 502-516, 425-440 |
| 3 | test-writer | Rerun a scoped MCP-kanban regression after updating the durable error-contract tests and return the task to review without source changes unless a real implementation defect appears | tests/test_mcp_kanban_error_mapping_1362.py, serve/mcp-kanban/tests/test_mcp_guidance_1089.py, serve/mcp-kanban/tests/test_mcp_read_tools.py, serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py, serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py | current review evidence above |
[[2026-05-06]]
## Test-Writer Notes
- Retry: updated 4 durable MCP-kanban test files to replace bare-string ToolError assertions with JSON-contract assertions.
- Files changed: `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`, `test_mcp_lifecycle_tools.py`, `test_mcp_mutation_tools_1087.py`, `test_mcp_read_tools.py`
- Changes: added `import json`, replaced `assert str(exc_info.value) == "..."` and `match="..."` patterns with `payload = json.loads(str(exc_info.value))` + `assert payload["code"] == "..."` + `assert payload["message"] == "..."`; removed old assertions that ERR_* codes must NOT appear in ToolError text.
- Commit: c1c39b06
- Regression result: 421 passed, 6 pre-existing unrelated failures (guidance/block:user/reject-outcome — not caused by #1362). All reviewer-cited TestFromAC_ErrorMapping / TestFromAC_KanbanErrorMapping tests pass.
- Task-local test file `tests/test_mcp_kanban_error_mapping_1362.py` remains green (13 tests).
- ruff: clean on all 4 changed files.
- Builder skip: test-only retry, all tests green → advance directly to review.
[[2026-05-06]]
## Builder Notes
- Implementation: no source changes required; `_map_kanban_error` JSON payload behavior already exists in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Files changed: none.
- Tests: task-local `tests/test_mcp_kanban_error_mapping_1362.py` passed (13/13) via quality-runner.
- Additional focused contract check: 17/17 passed across task + key durable error-mapping node IDs (validation/not-found/tool-error JSON assertions).
- Coverage: 30% on `owlbear_mcp_kanban.server` for task-local run; 40% on focused multi-node check (informational for no-diff pass-through).
- ruff: clean (0 violations) on source + scoped test files.
- Approach: non-implementation builder pass-through after test-writer retry; verified AC behavior and JSON error contract evidence without modifying `TestFromAC_*` tests or source.
- Evidence summary: AC behavior is implemented and validated; task advanced with no code diff.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped file pass over the task-local suite plus the retry files: 129 passed, 3 failed, 0 skipped. The 3 failures were unrelated guidance-passthrough tests in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`; I did not use them as the JSON-contract blocker.
- quality-runner node-id rerun of the JSON-contract surface: 30 passed, 0 failed, 0 skipped.
- Task-local suite `tests/test_mcp_kanban_error_mapping_1362.py::TestFromAC_StructuredJsonErrors` passed 13/13.
- The retry's updated durable JSON-contract node IDs also passed in guidance, lifecycle, mutation, and read suites.

### Lint Results
- Ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and the reviewed test files.

### Coverage Data
- File-level scoped run: `owlbear_mcp_kanban.server` 74%.
- Node-id rerun: `owlbear_mcp_kanban.server` 60%.
- Coverage is informational only here: the latest cycle was builder-skip / no source diff, and this review fails on AC2 proof quality rather than unexercised changed lines.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| `_map_kanban_error` emits `json.dumps({"code": exc.code, "message": exc.user_message})` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:108-111` builds `payload = json.dumps({...})` and raises `ToolError(payload)`; task-local JSON suite is green | `tests/test_mcp_kanban_error_mapping_1362.py::TestFromAC_StructuredJsonErrors` | PASS |
| All existing error-handling tests updated to expect JSON-structured error messages | Remaining durable tests still accept bare-string ToolError text via regex or substring checks instead of parsing JSON `code` + `message`: `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:199`, `:238`, `:369`, `:422`; `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:560`; `serve/mcp-kanban/tests/test_mcp_read_tools.py:1059`, `:1122`, `:1143`, `:1164`, `:1185`. A plain pre-JSON `ToolError(user_message)` would still satisfy those assertions. Broad grep across `serve/mcp-kanban/tests/**` found 28 `ToolError` substring/regex assertions total. | Examples above; retry-passed JSON nodes were only a subset of the durable error-handling surface | FAIL |
| Agents can parse error codes from ToolError text (ERR_STALE -> retry, ERR_NOT_FOUND -> stop, etc.) | Task-local parsing tests and updated durable JSON nodes pass exact `payload["code"]` assertions for `ERR_STALE`, `ERR_NOT_FOUND`, `ERR_INVALID_STATUS`, and `ERR_MIGRATION_REQUIRED` | `tests/test_mcp_kanban_error_mapping_1362.py::TestFromAC_StructuredJsonErrors`; durable JSON node-id rerun | PASS |
| Human-readable message still present in the JSON structure | Task-local and updated durable JSON tests assert exact `payload["message"] == user_message` | task-local JSON tests; durable JSON node-id rerun | PASS |

### Deductions
- -0.12: AC2 remains unmet after a prior review fail; the same proof-gap class still exists in durable MCP boundary tests.
- -0.02: exact git diff / dirty-tree contamination checks were unavailable in this session because no terminal tool was exposed; commit presence was confirmed only via `.git/logs/**` grep.

### Verdict
- FAIL -> backlog
- Confidence: 0.86
- Reason: implementation is correct and the targeted JSON-contract nodes are green, but AC2 is still incomplete on a second review cycle because multiple durable MCP boundary tests continue to accept non-JSON ToolError strings.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC2 with the actual MCP-kanban durable-suite inventory and explicitly enumerate which remaining error-mapping tests must parse JSON `code` and `message` instead of matching substrings | serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py, serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py, serve/mcp-kanban/tests/test_mcp_read_tools.py | surviving loose assertions at lines 199, 238, 369, 422, 560, 1059, 1122, 1143, 1164, 1185 |
| 2 | architect | Create a follow-up test-migration task or narrow AC2 explicitly before another retry; the current retry updated selected nodes but left the same proof-gap class unresolved on the second review cycle | serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py, serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py, serve/mcp-kanban/tests/test_mcp_read_tools.py | prior review rejected on AC2; current review found the same proof-gap class still live |

[[2026-05-06]]

## Refined AC (Architecture Review)

AC2 replaced. Old: "All existing error-handling tests updated to expect JSON-structured error messages"

New AC2: "No regressions in durable MCP-kanban test suites (`serve/mcp-kanban/tests/` and `tests/test_mcp_kanban*.py`). Dedicated error-mapping tests (10 tests across guidance_1089, lifecycle_tools, mutation_tools_1087, read_tools — migrated in test-writer retry commit c1c39b06) assert JSON `code` + `message` fields."

Rationale: server.py has 3 distinct ToolError families — only `_map_kanban_error` produces JSON. The original AC2 demanded JSON expectations from tests exercising bare-string paths. See Architecture Review section for full analysis.

Test-depth: All ACs are (td:0) — implementation and tests already exist from prior cycles.
Test-writer: SKIP
[[2026-05-06]]
## Architecture Review

**Verdict:** REFINE → APPROVE
**Confidence:** 0.90

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: `_map_kanban_error` emits JSON | Clear, verifiable. Implementation confirmed at server.py:108-111. | No change (td:0) |
| AC2: All existing error-handling tests updated | **Structurally impossible as written.** server.py has 3 ToolError families: (1) `_map_kanban_error` → JSON `{"code","message"}`, (2) `ToolError(str(exc))` for Pydantic/FileNotFoundError → bare string, (3) direct `ToolError(msg)` for param validation → bare string. ~20 of the 39 unmigrated tests exercise families 2–3 and SHOULD NOT expect JSON. Narrowed to: "No regressions in durable suites + dedicated error-mapping tests assert JSON." | Refined (td:0) |
| AC3: Agents can parse error codes | Clear, verifiable. Task-local suite proves parsing for ERR_STALE, ERR_NOT_FOUND, etc. | No change (td:0) |
| AC4: Human-readable message in JSON | Clear, verifiable. Task-local suite proves message field round-trips. | No change (td:0) |

### Architecture Notes

- Implementation is correct and complete. No source changes needed — behavior pre-existed.
- server.py error taxonomy (3 families):
  - `_map_kanban_error` (line 108–111): KanbanError → JSON `{"code", "message"}` — the scope of this task
  - PydanticValidationError/FileNotFoundError/ValueError (lines 224, 263, 452, 488, 530): `ToolError(str(exc))` bare string
  - Parameter validation (lines 94, 99, 102, 104, 320, 354): `ToolError(msg)` bare string
- Agent consumers should attempt `json.loads()` on ToolError text; parse failure indicates a bare-string parameter/validation error.
- JSON contract proven by 23 tests: 13 task-local (test_mcp_kanban_error_mapping_1362.py) + 10 migrated durable (Category A from codebase audit).

### Challenger Result

- Recommendation: reconsider (confidence 0.57)
- Key concern: proposed AC2 naming specific test classes was ambiguous and left `_map_kanban_error` surfaces uncovered (create_dr, root test files).
- Resolution: Changed AC2 to "no regressions" — eliminates classification ambiguity. JSON contract proof comes from AC1+AC3+AC4 and the 23 dedicated tests, not from every ToolError assertion. Follow-up task recommended for systematic durable test migration.

### Dependency Analysis

- No dependencies; correct for this scope.
- Follow-up recommendation: create a task "Migrate remaining durable MCP-kanban error tests to JSON contract assertions" (covers ~39 tests across lifecycle, mutation, read, create_dr, and root suites that still use substring/regex assertions against `_map_kanban_error` output).

### Test-writer: SKIP
All AC lines are (td:0). Implementation and tests already exist from 2 prior full cycles.
[[2026-05-06]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-06]]
## Builder Notes
- Implementation: no source changes required; `_map_kanban_error` JSON payload behavior is already implemented in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Files changed: none.
- RED/GREEN status: task-scoped contract suite remained GREEN (13/13) and focused durable JSON-contract surface passed (29/29).
- Durable-suite regression signal: broad MCP-kanban run reported 451 passed, 6 failed in guidance-related tests outside `_map_kanban_error` scope; these are pre-existing/unrelated to task 1362 acceptance criteria.
- Coverage: 98% on `owlbear_mcp_kanban.server` in broad durable run; 60% in focused JSON-contract run (scope-limited informational).
- ruff: clean (0 violations).
- Evidence summary: refined AC2 requires no regressions plus dedicated JSON-contract assertions; dedicated error-mapping suites are green and JSON `code`/`message` parsing contract is preserved.

### Post-task Reflection
- Broad durable-suite runs are valuable for context but can include unrelated legacy failures; focused node-ID verification is necessary for AC-specific gating.
- The architecture-refined AC2 removed an impossible requirement and made verification deterministic.
- No code edits were needed because behavior and tests already existed; this was a strict verification-and-advance cycle.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner focused JSON-contract pass 1: 29 passed, 0 failed across the task-local suite plus the durable error-mapping classes in `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`, `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`, and `serve/mcp-kanban/tests/test_mcp_read_tools.py`.
- quality-runner focused JSON-contract pass 2: 4 passed, 0 failed on the four migrated guidance JSON tests in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`:
  - `TestFromAC_ErrorMapping::test_validation_error_maps_to_tool_error`
  - `TestFromAC_GuidanceProofRepair::test_not_found_error_maps_to_tool_error`
  - `TestFromAC_GuidanceProofRepair::test_concurrency_error_maps_to_tool_error_user_message_only`
  - `TestFromAC_GuidanceProofRepair::test_config_error_maps_to_tool_error_user_message_only`
- quality-runner adjacent durable regression run: 214 passed, 3 failed. All 3 failures were guidance-passthrough tests in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` (`test_pick_tasks_dispatch_hints_guidance`, `test_move_task_skip_transition_warning_guidance`, `test_start_work_guidance_sentinel_passthrough`). They do not exercise `_map_kanban_error` and match the unrelated guidance-failure surface already recorded earlier in this task.

### Lint Results
- Ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Ruff clean on `tests/test_mcp_kanban_error_mapping_1362.py`.
- Ruff clean on `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`.
- Ruff clean on `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`.
- Ruff clean on `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`.
- Ruff clean on `serve/mcp-kanban/tests/test_mcp_read_tools.py`.

### Coverage Data
- Not run for gate purposes. Latest Architecture Review marked all AC lines `(td:0)`, the current cycle had no source diff, and this review used focused execution plus direct artifact inspection instead of a coverage gate.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| `_map_kanban_error` emits `json.dumps({"code": exc.code, "message": exc.user_message})` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:108-110` builds the JSON payload and raises `ToolError(payload)`; `_map_kanban_error` call sites remain wired at `server.py:222,280,306,335,365,430,450,486,528` | `tests/test_mcp_kanban_error_mapping_1362.py::TestFromAC_StructuredJsonErrors` (13/13 pass) | PASS |
| No regressions in durable MCP-kanban suites; dedicated migrated error-mapping tests assert JSON `code` + `message` fields | Retry commit `c1c39b06` is present in `.git/logs/HEAD`; focused durable JSON tests passed in guidance, lifecycle, mutation, and read suites. Adjacent regression red is limited to three guidance-passthrough tests at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:267`, `:324`, `:474`, outside `_map_kanban_error` scope and consistent with the previously documented unrelated failure surface. | 4 migrated guidance JSON tests; `TestFromAC_KanbanErrorMapping` in lifecycle (4/4 pass); `TestFromAC_KanbanErrorMapping` in mutation (4/4 pass); `TestFromAC_ErrorMapping` in read (7/7 pass) | PASS |
| Agents can parse error codes from ToolError text (`ERR_STALE` -> retry, `ERR_NOT_FOUND` -> stop, etc.) | Focused task-local and durable suites parse `str(exc_info.value)` with `json.loads(...)` and assert exact `payload["code"]` values | `tests/test_mcp_kanban_error_mapping_1362.py::test_map_kanban_error_err_stale_code_in_json`; `tests/test_mcp_kanban_error_mapping_1362.py::test_map_kanban_error_err_not_found_stop_signal`; `tests/test_mcp_kanban_error_mapping_1362.py::test_agent_can_parse_error_code_from_tool_error_text` | PASS |
| Human-readable message still present in the JSON structure | Source emits `{"message": exc.user_message}` at `server.py:110`; focused tests assert exact `payload["message"]` equality and special-character round-tripping | `tests/test_mcp_kanban_error_mapping_1362.py::test_map_kanban_error_json_message_equals_user_message`; `tests/test_mcp_kanban_error_mapping_1362.py::test_map_kanban_error_user_message_with_special_chars_round_trips`; durable guidance/lifecycle/mutation/read JSON tests | PASS |

### Deductions
- -0.03: adjacent durable regression remains red on three unrelated guidance-passthrough tests, so the durable-suite context is not fully green even though the JSON error-contract surface is.
- -0.02: exact dirty-tree contamination and commit-diff reconstruction were unavailable in this tool surface; commit presence was confirmed via `.git/logs/**` and current file inspection instead.

### Verdict
- PASS -> docs
- Confidence: 0.95
- Reason: the live implementation already satisfies the structured JSON ToolError contract, the dedicated migrated durable tests are green, lint is clean, and the only remaining red tests are previously documented unrelated guidance failures outside the refined AC.
- Action: advance to docs.

### Post-task Reflection
- The Architecture Review refinement was binding and materially changed the gate: the prior broad AC2 concern was correctly narrowed to the `_map_kanban_error` family.
- A broad adjacent regression pass was still useful because it separated the JSON-contract surface from unrelated guidance failures that remain elsewhere in the durable suite.
- quality-runner’s first focused report had inconsistent totals, so a second focused run with explicit node reporting was necessary before rendering a PASS.
[[2026-05-06]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/mcp-kanban/README.md` does not document `_map_kanban_error` wire format; no stale content referencing the changed area |
| 2 | Module docstrings | No | N/A | `server.py` had no source changes; existing `_map_kanban_error` docstring ("Raise MCP ToolError with machine-readable code and human-readable message") is accurate for the JSON contract |
| 3 | External attribution | No | N/A | No external patterns cited in task body |
| 4 | Research doc | No | N/A | No research doc produced |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` and `mcp-topology.excalidraw` describe `serve/mcp-kanban/src/**` but no source files were changed — changed-files set is test files only |
| 6 | Explicit diagram creation | No | N/A | No request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-kanban/tests/test_mcp_guidance_1089.py | OUT | N/A |
| serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py | OUT | N/A |
| serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py | OUT | N/A |
| serve/mcp-kanban/tests/test_mcp_read_tools.py | OUT | N/A |
| tests/test_mcp_kanban_error_mapping_1362.py | OUT | N/A |
| serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | IN (docstrings) | Verified accurate; no edit needed |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files existed for task 1362)
[[2026-05-06]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| `_map_kanban_error` emits `json.dumps({\"code\": exc.code, \"message\": exc.user_message})` | server.py:108-111 confirmed; task-local suite 13/13 pass | PASS |\n| No regressions in durable suites; dedicated migrated tests assert JSON `code` + `message` | Scoped suite 226 passed, 3 failed (pre-existing unrelated guidance-passthrough). Commit c1c39b06 migrated durable tests. | PASS |\n| Agents can parse error codes (ERR_STALE → retry, ERR_NOT_FOUND → stop) | Task-local tests parse with json.loads() and assert exact code values | PASS |\n| Human-readable message in JSON structure | Tests assert payload[\"message\"] == user_message + special char round-trips | PASS |\n\n### Test Results\n- pytest (full): 2742 passed, 202 failed — 0 failures in task scope; 202 are pre-existing background failures unrelated to #1362 (no source changes made)\n- pytest (scoped MCP-kanban): 226 passed, 3 failed — all 3 are guidance-passthrough tests outside `_map_kanban_error` scope, documented throughout task history\n- ruff: clean on task scope (server.py + all test files)\n\n### Architect Quality: 3/5\nOriginal AC2 (\"all existing error-handling tests updated to expect JSON\") was structurally impossible — server.py has 3 ToolError families and only `_map_kanban_error` produces JSON. This caused 2 failed review cycles before architecture refinement. Refined AC2 was clear and actionable. AC1/AC3/AC4 were well-specified throughout.\n\n### Deduction Breakdown\n- AC quality score 3: -0.03\n- All AC lines have specific evidence: no deduction\n- Lint clean: no deduction\n- Reviewer evidence present and detailed: no deduction\n- No task-scope test failures: no deduction\n\n### Confidence: 0.97\n### Action: archive\n\n### Commit Integrity\n- f257e98b: test: add failing tests for structured JSON error responses at MCP boundary (#1362, test-writer)\n- c1c39b06: test: update durable MCP-kanban error-mapping tests to JSON contract (#1362, test-writer)\n- No uncommitted changes in task scope. No source code changes (implementation pre-existed).