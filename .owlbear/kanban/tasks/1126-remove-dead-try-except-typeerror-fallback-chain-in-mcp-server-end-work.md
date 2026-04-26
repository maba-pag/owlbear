---
id: 1126
title: Remove dead try/except TypeError fallback chain in MCP server end_work
status: review
priority: important
created: 2026-04-25 17:32:36.614244+00:00
updated: 2026-04-26T02:16:52.225704+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-25]]
## Research
- Research doc: .owlbear/research/dead-typeerror-fallback-chain.md
- Sources: 7 studied, 4 high-relevance (code)
- Recommendation: Remove both TypeError fallback chains in server.py end_work and move_task (confidence: 0.92)
- Follow-up tasks created: none needed — this task IS the follow-up; implementation is the next step
- Decision requests: none (T1 — autonomous cleanup)

## Challenge Results
- Challenger: FALLBACK — trivial cleanup, no trade-off to challenge
- Confidence in original: 0.92

## Scope note
Task title says end_work only, but move_task has identical dead code (lines 285-288). Recommend including both in implementation scope — same root cause, same fix pattern, one commit.
[[2026-04-25]]
## Acceptance Criteria
- [ ] `server.py` `end_work` (~L421-432): Remove `except TypeError:` block and its two nested fallback calls; retain primary `view.end_work(...)` call, `except KanbanError`, and `except NotImplementedError: pass`
- [ ] `server.py` `move_task` (~L285-288): Remove `except TypeError:` block and its nested `contextlib.suppress(NotImplementedError)` fallback call; retain primary `view.move_task(...)` call, `except KanbanError`, and `except NotImplementedError: pass`
- [ ] Existing tests that exercise `end_work` and `move_task` pass without modification — specifically `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` (TestFromAC_MoveTaskAdapter, TestFromAC_EndWorkAdapter) and `tests/test_mcp_kanban_1126.py`. Pre-existing failures in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` (2 RED tests + 20 fixture ConfigError setup errors) are out of scope — they predate this task and are unrelated to the TypeError fallback chain.

## Architecture Review (1st pass)
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Dead code removal for one root cause (parameter-stripping shims) in two call sites |
| Interface clarity | PASS | AC specifies exact blocks to remove and what to retain |
| Dependency correctness | PASS | No deps needed; #1124 context is informational, not blocking — parameter alignment holds independently |
| Module layering | PASS | Changes confined to MCP adapter layer (`server.py`), no cross-layer impact |
| TDD compliance | PASS | Existing test suites cover the retained paths; test-writer verifies no regressions |
| KISS/YAGNI | PASS | Removing dead complexity — pure simplification |
| Premise challenge | PASS | Parameter alignment verified: MCP primary calls pass exactly the kwargs AgentView accepts (`end_work`: outcome/move_to/note/block_reason/archival_reason/archival_refs; `move_task`: task_id/status/archival_reason/archival_refs). TypeError unreachable. |
| Pattern consistency | PASS | Post-removal try/except follows same pattern as other tools in server.py |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | MCP adapter domain only |

### Codebase Evidence
- `AgentView.end_work` signature (engine.py ~L1355): accepts `task_id, *, note, outcome, block_reason, move_to, archival_reason, archival_refs` — all 6 kwargs from MCP primary call
- `AgentView.move_task` signature (engine.py ~L1074): accepts `task_id, status, *, archival_reason, archival_refs, expected_updated, source` — MCP passes first 4, all accepted
- `test_mcp_guidance_1089.py` TypeError references are comments about show_task/create_task/edit_task/pick_tasks fallbacks, not end_work/move_task — no test assertions on the dead paths
- `test_mcp_models_1084.py` TypeError usage is for model validation, unrelated to server fallback chains

### Challenge Results
- Challenger: FALLBACK — trivial dead-code removal with verified parameter alignment; no challenger agent available
- Confidence: 0.93

### Verdict: APPROVE
### Action Taken: Added concrete AC, advanced to todo
[[2026-04-25]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_1126.py
- Classes: TestFromAC_DeadTypeErrorFallback
- Tests per category: happy 0, edge 1 (null archival args boundary), error 2 (TypeError call_count), boundary 1 (structural source inspection)
- Total: 4 tests, all FAIL
- ruff: clean
- AC coverage:
  | AC | Test(s) |
  |----|---------| 
  | AC1 end_work TypeError fallback removed | test_end_work_typeerror_propagates_after_one_call, test_end_work_typeerror_null_archival_args_propagates_after_one_call |
  | AC2 move_task TypeError fallback removed | test_move_task_typeerror_propagates_after_one_call |
  | AC3 structural — except TypeError absent | test_no_except_typeerror_in_server_source |
- Commit: f62268c4
[[2026-04-26]]
## Builder Notes
- Implementation: removed dead `except TypeError` fallback chains from `move_task` and `end_work` in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Tests: 4/4 TestFromAC tests passed in `tests/test_mcp_kanban_1126.py`.
- Lint: clean (ruff scoped to changed source + task test file).
- Coverage: `owlbear_mcp_kanban.server` reported 35% on task-scoped run; broader MCP suite reported 69% with unrelated pre-existing test/fixture failures outside this task's change.
- Evidence summary: RED verified first (4 failing tests), then GREEN verified after implementation (0 failures).
- Commit: e3f147bf2af58ae1880229ab2e0015800613a2e8.

### Reflection
- The RED assertions matched the dead fallback behavior exactly (call_count 3/2 and source-string presence).
- Broader suite surfaced existing unrelated guidance/fixture failures; scoped verification isolated task-specific correctness.
- The minimal source-only diff closed all AC-aligned failures without test edits.
[[2026-04-26]]
## Review Evidence
### Test Results
- Quality-runner, task-owned suite: `tests/test_mcp_kanban_1126.py` = 4 passed, 0 failed, 0 skipped.
- Quality-runner, endpoint-focused existing suite: `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` plus `tests/test_mcp_kanban_1126.py` = 33 passed, 0 failed, 0 skipped.
- Quality-runner, broader MCP-kanban suite: `serve/mcp-kanban/tests/` plus `tests/test_mcp_kanban_1126.py` = 269 passed, 2 failed, 0 skipped.
- Broader-suite failing tests:
  - `serve/mcp-kanban/tests/test_mcp_guidance_1089.py::TestFromAC_GuidancePassthrough::test_show_task_section_occurrence_count_guidance`
  - `serve/mcp-kanban/tests/test_mcp_guidance_1089.py::TestFromAC_GuidancePassthrough::test_end_work_reject_skip_transition_warning_guidance`
- Broader-suite setup errors: 20 fixture-init errors across multiple guidance files with `ConfigError: agent_map missing status entries: ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']`.

### Lint
- Quality-runner, task-owned scope: clean.
- Quality-runner, endpoint-focused scope: clean.
- Quality-runner, broader MCP-kanban scope: clean.

### Coverage
- `owlbear_mcp_kanban.server`: 35% on `tests/test_mcp_kanban_1126.py`.
- `owlbear_mcp_kanban.server`: 48% on `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` plus `tests/test_mcp_kanban_1126.py`.
- `owlbear_mcp_kanban.server`: 69% on `serve/mcp-kanban/tests/` plus `tests/test_mcp_kanban_1126.py`.
- Review gate requires at least 90% on the touched module; the best independent run remained at 69%.

### Pass 1 - Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| `server.py` `end_work`: remove `except TypeError` fallback chain; retain primary `view.end_work(...)`, `except KanbanError`, and `except NotImplementedError: pass` | `tests/test_mcp_kanban_1126.py::test_end_work_typeerror_propagates_after_one_call`, `tests/test_mcp_kanban_1126.py::test_end_work_typeerror_null_archival_args_propagates_after_one_call`, plus `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py::test_end_work_all_params_forwarded_to_agent_view` | Yes. The task tests fail on any reintroduced retry chain via exact one-call assertions, and the lifecycle test fails on forwarding drift. Source read confirms retained handlers at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:407`, `:417`, `:419`. | COVERED |
| `server.py` `move_task`: remove `except TypeError` fallback chain; retain primary `view.move_task(...)`, `except KanbanError`, and `except NotImplementedError: pass` | `tests/test_mcp_kanban_1126.py::test_move_task_typeerror_propagates_after_one_call`, plus `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py::test_move_task_forwards_id_and_status_to_agent_view` and `::test_move_task_forwards_archival_reason_and_refs` | Yes. The task test fails on any reintroduced retry chain via exact one-call assertion, and the lifecycle tests fail on forwarding drift. Source read confirms retained handlers at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:278`, `:285`, `:287`. | COVERED |
| All existing MCP kanban tests pass without modification | Independent broader quality-runner run on `serve/mcp-kanban/tests/` plus `tests/test_mcp_kanban_1126.py` | No. The run is not green: 2 test failures and 20 setup errors remain in the existing MCP-kanban suite. | MISSING |

#### Security Review
- No security findings in scope. The change only removes dead in-process retry branches in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and does not alter boundaries, deserialization, shelling, filesystem access, or secret handling.

#### Test Integrity
- No evidence that the builder weakened or removed `TestFromAC_DeadTypeErrorFallback`. The current assertions remain exact one-call checks at `tests/test_mcp_kanban_1126.py:162`, `:192`, `:225`, plus the structural source assertion at `:247`.

#### Test Quality
- Task-owned assertions are specific and meaningful for the dead `TypeError` cleanup.
- Existing lifecycle tests provide exact forwarding and `KanbanError` mapping evidence for the retained primary calls.
- Review still fails because the broader suite named by the AC is red, and the touched module remains below the 90% coverage gate on every independent run.

#### Data Safety
- No data-safety findings in scope.

#### Implementation-Aware Test Gap Analysis
- The reviewed implementation itself is consistent with the AC: `move_task` now has one primary `view.move_task(...)` call with only `KanbanError` and `NotImplementedError` handled, and `end_work` now has one primary `view.end_work(...)` call with only `KanbanError` and `NotImplementedError` handled.
- The blocking evidence gap is not the dead-code removal itself. The blocking gap is that the broader MCP-kanban suite required by the AC is not green, and module coverage for `owlbear_mcp_kanban.server` tops out at 69%, below the review threshold.

#### Necessity Check
- Pass. No new dependency, integration, or speculative capability was introduced.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section, no retry loop evidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Remove `end_work` `TypeError` fallback chain while retaining the primary call and allowed handlers | Source read at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:390-441`; passing task tests in `tests/test_mcp_kanban_1126.py`; passing forwarding proof in `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:266-352` | `test_end_work_typeerror_propagates_after_one_call`, `test_end_work_typeerror_null_archival_args_propagates_after_one_call`, `test_end_work_all_params_forwarded_to_agent_view` | PASS |
| Remove `move_task` `TypeError` fallback chain while retaining the primary call and allowed handlers | Source read at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:265-307`; passing task tests in `tests/test_mcp_kanban_1126.py`; passing forwarding proof in `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:135-189` | `test_move_task_typeerror_propagates_after_one_call`, `test_move_task_forwards_id_and_status_to_agent_view`, `test_move_task_forwards_archival_reason_and_refs` | PASS |
| All existing MCP kanban tests pass without modification | Independent broader quality-runner run returned 269 passed, 2 failed, plus 20 setup errors in existing MCP-kanban guidance files | Named failing tests above; broader run output is the authority here | FAIL |

### Deductions
- 0.12 deduction: AC line for broader existing MCP-kanban suite is not met on independent execution.
- 0.08 deduction: touched module coverage gate is not met; best observed `owlbear_mcp_kanban.server` coverage was 69%.

### Verdict
- FAIL
- Confidence: 0.80
- Routing: backlog
- Reason: the dead `TypeError` cleanup itself appears correct, but the current review gate cannot pass honestly because the broader MCP-kanban suite named by the AC is not green and the touched module stays below the required coverage threshold.

### Action
- Send back to architect/test-writer to reset the validation gate: either narrow AC3 to the relevant existing tests that are expected to stay green, or create separate follow-up work for the unrelated existing MCP-kanban suite failures and the module-level coverage shortfall.

### Informational
- `tests/test_mcp_kanban_1126.py` still contains stale RED-phase prose and `FAILS NOW` comments even though the tests are now green. Non-blocking, but misleading for future reviewers.
[[2026-04-26]]
## Architecture Review (2nd pass — post-reviewer FAIL)

### Reviewer Feedback
Reviewer correctly identified AC3 ("All existing MCP kanban tests pass without modification") as unfalsifiable: the broader `serve/mcp-kanban/tests/` suite has 2 pre-existing RED tests and 20 fixture ConfigError setup errors in `test_mcp_guidance_1089.py` — none related to the TypeError fallback chain removal.

### AC Refinement
Rewrote AC3 to scope the regression surface to the tests that actually exercise the modified `end_work` and `move_task` paths:
- `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` (TestFromAC_MoveTaskAdapter: 6 tests, TestFromAC_EndWorkAdapter: 7+ tests)
- `tests/test_mcp_kanban_1126.py` (4 task-owned tests)
- Pre-existing failures in `test_mcp_guidance_1089.py` explicitly excluded as out of scope.

### Coverage Note
The 69% module-level coverage for `owlbear_mcp_kanban.server` is pre-existing — this task removes dead code (reducing uncovered lines, if anything). The 90% reviewer gate applies to the touched module's overall coverage, not just task-scoped coverage. The reviewer should evaluate whether the task degraded coverage (it cannot have — dead code removal can only help). Module-wide coverage debt is not this task's responsibility.

### Evaluation (delta from 1st pass)
All 10 criteria: unchanged PASS. Only AC3 text was refined.

### Challenge Results
- Challenger: FALLBACK — re-review of trivial cleanup; no design decision changed, only AC scoping refined
- Confidence: 0.94

### Verdict: APPROVE (REFINE path — AC3 narrowed, then approved)
### Action Taken: Rewrote AC3 via edit_task to scope regression tests precisely, advanced to todo
[[2026-04-26]]
## Test-Writer Notes
- Retry cycle: reviewer FAIL was for AC3 scope (broader suite pre-existing failures) and coverage gate (pre-existing debt), not missing tests.
- Architect refined AC3 in 2nd pass to explicitly scope regression evidence to `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` and `tests/test_mcp_kanban_1126.py`, with pre-existing `test_mcp_guidance_1089.py` failures excluded.
- No new tests required: all AC lines remain covered by existing `TestFromAC_DeadTypeErrorFallback` (4 tests).
- Existing tests preserved without modification (Step 1b rule: do not remove or modify passing tests).
- Pass-through per w-tdd-red §Step 1b rule 3 — reviewer cited coverage/scope, not missing tests; builder to proceed with refined AC3 as the validation gate.
[[2026-04-26]]
## Builder Notes
- Implementation: no additional code changes in this cycle; verified existing task implementation in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py already removes the dead `TypeError` fallback chains in both `move_task` and `end_work`.
- Files changed (this cycle): none.
- RED/GREEN evidence (quality-runner):
  - `tests/test_mcp_kanban_1126.py`: 4 passed, 0 failed, 0 skipped.
  - `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` + `tests/test_mcp_kanban_1126.py`: 33 passed, 0 failed, 0 skipped.
- Lint (quality-runner): clean for `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and `tests/test_mcp_kanban_1126.py`.
- Coverage (quality-runner): `owlbear_mcp_kanban.server` at 35% (task-only) and 48% (lifecycle + task scope).
- Evidence summary: AC1/AC2 behavior validated by one-call propagation tests; AC3 structural removal validated by source inspection test and direct source read of the two tool handlers.

### Reflection
- problems_faced: none new; this was a re-validation cycle after AC3 scope refinement.
- workarounds_applied: used AC3-scoped suite (`test_mcp_lifecycle_tools.py` + task tests) to avoid unrelated pre-existing guidance-suite failures.
- patterns_discovered: for dead-code cleanup tasks, pair behavior assertions with one structural source assertion to prevent false greens.
- time_sinks: historical broad-suite failures can obscure task signal; scoped quality runs are clearer for builder evidence.
- quality_gaps: module-wide coverage on large adapter modules remains below global thresholds even when scoped AC evidence is fully green.