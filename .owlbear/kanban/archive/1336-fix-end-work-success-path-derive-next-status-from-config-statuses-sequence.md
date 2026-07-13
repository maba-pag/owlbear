---
id: 1336
title: Fix raw engine end_work success default and terminal archive contract
status: archived
priority: medium
created: 2026-05-04T15:00:05.698435+00:00
updated: 2026-05-05T00:53:24.269767+00:00
tags:
- sync-blocker
- kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Raw `KanbanEngine.end_work(outcome="success")` still defaults `move_to="research"`. That public default forces successful work backward unless callers know to override it with `move_to=None`. `AgentView.end_work()` currently masks the bug by passing `move_to=None`, but the raw engine contract remains wrong and is part of the deployment surface.

Current accepted lifecycle behavior: success advances to the next configured status when the task is not terminal; success from terminal status archives the task with `archival_reason="completed"` and no refs. It should not raise merely because the task is terminal.

## Acceptance Criteria

1. Raw `KanbanEngine.end_work(task_id, outcome="success")` derives next status from board config when no explicit `move_to` is supplied.
2. Raw success no longer moves tasks to `research` by default.
3. Success from the terminal status archives the task with `archival_reason="completed"` and `archival_refs=[]`.
4. Explicit `move_to` behavior remains available for non-success outcomes where currently supported, especially `reject`.
5. `AgentView.end_work()` remains compatible and does not need special masking for the raw-engine default.
6. `tests/test_end_work_success_1336.py` is corrected so terminal success expects archive behavior, not an error.
7. Existing lifecycle/session tests continue to pass.

## Key Files

- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `tests/test_end_work_success_1336.py`
- `serve/kanban/tests/test_engine_end_work_1077.py`
- `tests/test_engine_end_work_1080.py`

## Audit Evidence

- Narrow pytest run showed `tests/test_end_work_success_1336.py` still failing because raw success moves to `research`.
- Newer terminal-archive lifecycle tests pass, proving the old terminal-error AC is stale.

## Test-Writer Notes

- Existing RED file: `tests/test_end_work_success_1336.py`
- Keep advancement tests, but rewrite terminal tests to assert completed archival.
- Preserve reject/no-regression tests only where they fail for the intended contract.

## Source

Deployment audit reconciliation, 2026-05-04.
[[2026-05-04]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: fix raw engine `move_to` default |
| Interface clarity | PASS | AC lines are precise and testable |
| Dependency correctness | PASS | No external deps; engine-internal change |
| Module layering | PASS | Change is within kanban engine; no upward imports |
| TDD compliance | PASS | RED file exists (`tests/test_end_work_success_1336.py`); AC6 directs test correction |
| KISS/YAGNI | PASS | Single default-value change; _apply_outcome logic already correct |
| Premise challenge | PASS | Bug is real — raw API misleads direct callers |
| Pattern consistency | PASS | Aligns with AgentView (already defaults None) and MCP server (passes None explicitly) |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | kanban engine only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| success + status not in config.statuses | idx=-1, goes to else branch, advances to statuses[0] | None | Pre-existing | Minimal (edge case for manually-edited tasks) |
| reject + no explicit move_to (new default None) | Status unchanged | None | Yes — AgentView validates; MCP passes explicit | None (all live callers provide move_to for reject) |

### Challenge Results
- Challenger: reconsider (0.72 confidence)
- Architect response: REBUTTED
  - MCP fallback: server.py L536-546 shows `move_to: str | None = None` — always passes explicit None to engine. Engine default irrelevant for this path.
  - AgentView docstring contradiction: pre-existing, not introduced by this task.
  - Reject without move_to: all live callers (AgentView, MCP) pass explicit move_to for reject. Raw engine reject with None leaves status unchanged — more correct than silently routing to research.
  - AC7 proof: downstream builder/reviewer responsibility; AC exists to gate the task.

### Test Depth
- AC1: (td:2) — multiple status transitions
- AC2: (td:1) — single negative assertion
- AC3: (td:2) — terminal archive with field checks
- AC4: (td:1) — regression guard
- AC5: (td:1) — regression guard
- AC6: (td:0) — test correction
- AC7: (td:0) — existing suite passes
- Max depth: 2
- Test-writer: PROCEED (correct existing RED file per AC6 + Test-Writer Notes)

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise; implementation is a single default change plus test correction. Builder note: update engine docstring to reflect new default.

[[2026-05-04]]
Architecture review complete. AC precise and verifiable. Single default-value fix (move_to="research" → None) in engine.end_work signature; _apply_outcome already handles None correctly. All live callers (AgentView, MCP server) pass explicit None. Test file needs correction per AC6 (terminal → archive, not ValueError). Challenger rebutted.
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_end_work_success_1336.py
- Classes: TestFromAC_SuccessStatusAdvancement, TestFromAC_SuccessAtTerminalStatus, TestFromAC_SuccessFromInProgress, TestFromAC_NoDefaultResearch, TestFromAC_RejectWithoutMoveToContract
- Tests per category: happy 6, edge 4, error 0, boundary 0
- Total: 10 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests | Class |
|----|-------|-------|
| AC1 (td:2) | 5 tests — advancement from research/backlog/todo/in-progress/review | TestFromAC_SuccessStatusAdvancement (4), TestFromAC_SuccessFromInProgress (1) |
| AC2 (td:1) | 1 test — negative: success does not set status="research" | TestFromAC_NoDefaultResearch |
| AC3 (td:2) | 3 tests — terminal archives: archival_reason, status=archived, file in archive/ | TestFromAC_SuccessAtTerminalStatus |
| AC4 (td:1) | 1 test — reject without move_to does not set status="research" | TestFromAC_RejectWithoutMoveToContract |
| AC5 (td:1) | 0 tests — AgentView masks bug; test would pass in RED; skipped per skill rule |
| AC6 (td:0) | N/A — meta-AC: test file corrected (this task) |
| AC7 (td:0) | N/A — existing suite; builder responsibility |

Fail reasons confirmed: AC1/AC2/AC4 fail because engine default move_to="research"; AC3 fails because buggy default prevents archive branch in _apply_outcome.
[[2026-05-04]]
## Builder Notes
- Implementation: verified raw `KanbanEngine.end_work` success default behavior and terminal archive contract in `serve/kanban/src/owlbear_kanban/engine.py` (default `move_to=None`; no additional source edits required).
- Files changed: none in this builder pass (working tree diff against HEAD for target source file is empty).
- Tests (scoped GREEN verification): 59 passed, 0 failed, 0 skipped.
  - `tests/test_end_work_success_1336.py`
  - `serve/kanban/tests/test_engine_end_work_1077.py`
  - `tests/test_engine_activity_session.py`
- Lint: clean (`ruff` clean on `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_end_work_success_1336.py`).
- Coverage: `owlbear_kanban.engine` reported 46% in scoped run.
- Evidence summary: AC1/AC2/AC3/AC4 behavior now holds in task-scoped tests; terminal success archives with `archival_reason="completed"` and no refs.
- Additional context: a broader optional regression run including `tests/test_engine_end_work_1080.py` surfaced 3 pre-existing guidance-string assertion failures unrelated to this task’s `move_to` default contract.

### Reflection
- Problems faced: initial broad regression scope mixed task signal with unrelated guidance-string debt.
- Workaround applied: reran scoped quality gate centered on this task’s contract + adjacent lifecycle/session tests.
- Pattern discovered: this area benefits from two-pass verification (broad context then scoped gate) to avoid false routing on unrelated legacy failures.
- Quality gap noted: `owlbear_kanban.engine` module-level coverage remains below phase target in scoped measurement due module size vs narrow task scope.
[[2026-05-04]]
## Review Evidence

### Test Results
- `quality-runner` scoped regression: 74 passed, 3 failed, 0 skipped.
- Failing tests:
  - `tests/test_engine_end_work_1080.py:596` `test_block_outcome_guidance_is_singleton_exact_ar_hint`
  - `tests/test_engine_end_work_1080.py:620` `test_block_with_multi_step_move_to_guidance_exact_list`
  - `tests/test_engine_end_work_1080.py:649` `test_block_with_single_step_move_to_guidance_is_singleton_ar_hint`
- Failure cause is unrelated to task 1336's success-default fix: `tests/test_engine_end_work_1080.py:92` expects `"⚠️ ACTION REQUIRED: Create a Decision Request via the create_dr tool. Blocks without a DR are invisible to the pipeline."`, while live code in `serve/kanban/src/owlbear_kanban/agent_view.py:46` still emits `"⚠️ ACTION REQUIRED: Create a Decision Request for this block via the scribe agent (see w-decision-routing). Blocks without a DR are invisible to the pipeline."`.
- Separation run: task-owned behavior remained green in `tests/test_end_work_success_1336.py`, `serve/kanban/tests/test_engine_end_work_1077.py`, and `tests/test_engine_activity_session.py`; remaining non-task failures were isolated to unrelated legacy cases in `serve/kanban/tests/test_engine_coverage_1068.py`.

### Lint Results
- `ruff`: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/agent_view.py`, and `tests/test_end_work_success_1336.py`.

### Coverage
- Informational only: broad scoped run reported module coverage `owlbear_kanban.engine=48%`, `owlbear_kanban.agent_view=26%`.
- This did not drive the verdict because the available report is module-level rather than diff-scoped.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Raw `KanbanEngine.end_work(..., outcome="success")` derives next status from board config when no explicit `move_to` is supplied. | Engine success branch advances by status-list position in `serve/kanban/src/owlbear_kanban/engine.py:1514-1540`. Task tests at `tests/test_end_work_success_1336.py:138` and `:185` pass only on the stock status order, so a hardcoded sequence would still survive. | FAIL (proof lax) |
| 2. Raw success no longer moves tasks to `research` by default. | Discriminating negative assertion at `tests/test_end_work_success_1336.py:309`; live success branch in `serve/kanban/src/owlbear_kanban/engine.py:1514-1540` no longer defaults to `research`. | PASS |
| 3. Success from terminal status archives with `archival_reason="completed"` and `archival_refs=[]`. | Terminal archive branch is in `serve/kanban/src/owlbear_kanban/engine.py:1531-1540`; task tests at `tests/test_end_work_success_1336.py:223`, `:239`, and `:255`, plus wrapper regression at `serve/kanban/tests/test_engine_end_work_1077.py:209`, observe archive behavior. Proof still depends on `done` being the last stock status. | FAIL (proof lax) |
| 4. Explicit `move_to` behavior remains available for non-success outcomes where currently supported, especially `reject`. | Raw reject branch remains intact at `serve/kanban/src/owlbear_kanban/engine.py:1548-1554`; existing raw regression `serve/kanban/tests/test_engine_coverage_1068.py:1729` exercises `move_to="research"`, and wrapper regressions at `serve/kanban/tests/test_engine_end_work_1077.py:234` and `:256` exercise `move_to="todo"` / `"archived"`. | PASS |
| 5. `AgentView.end_work()` remains compatible and does not need special masking for the raw-engine default. | `AgentView` forwards directly to `engine.end_work(...)` in `serve/kanban/src/owlbear_kanban/agent_view.py:1177-1184`, and its reject matrix remains intact at `serve/kanban/src/owlbear_kanban/agent_view.py:1065-1088`. Compatibility is code-inspected, but there is no discriminating test proving absence of special masking. | FAIL (proof lax) |
| 6. `tests/test_end_work_success_1336.py` is corrected so terminal success expects archive behavior, not an error. | The terminal-success block now asserts archival behavior at `tests/test_end_work_success_1336.py:223`, `:239`, and `:255`. | PASS |
| 7. Existing lifecycle/session tests continue to pass. | Executed regression is still red in `tests/test_engine_end_work_1080.py:596`, `:620`, and `:649` because the expected D54 guidance string at `tests/test_engine_end_work_1080.py:92` no longer matches live code at `serve/kanban/src/owlbear_kanban/agent_view.py:46`. | FAIL |

### Additional Review Findings
- No security or rollback/data-loss regression was found in the reviewed `end_work` paths.
- Existing `## Review Evidence` sections before this review: `0`. This is the first review failure; backlog routing is due AC/test-quality scope, not the loop-breaker rule.
- TestFromAC immutability confidence is slightly reduced because the available tool surface did not expose a commit diff or dirty-tree check for exact ownership reconstruction.

### Deductions
- AC1 proof does not distinguish config-derived logic from a hardcoded stock status sequence.
- AC3 proof still assumes the stock config where `done` is the last listed status.
- AC5 is only code-inspected, not directly proven by a discriminating wrapper test.
- AC7 inherits unrelated D54 guidance-string debt from `tests/test_engine_end_work_1080.py`.
- Exact commit-diff / dirty-tree provenance was unavailable in this review surface, so immutability evidence is lower-confidence.

### Verdict
- `FAIL` with confidence `0.82`.
- Core implementation appears correct, but the review gate is not met because AC1/AC3/AC5 remain under-proven and AC7 is red on unrelated lifecycle debt outside task 1336's owned change surface.
- Action: reject to `backlog` for AC/test-quality re-scoping rather than sending the task back to the builder.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-scope AC7 to task-owned suites or split the unrelated D54 guidance-string mismatch into a separate task/dependency before retrying review. | `tests/test_engine_end_work_1080.py`, `serve/kanban/src/owlbear_kanban/agent_view.py` | `quality-runner` failures at `tests/test_engine_end_work_1080.py:596`, `:620`, `:649`; expected string at `tests/test_engine_end_work_1080.py:92` conflicts with live constant at `serve/kanban/src/owlbear_kanban/agent_view.py:46`. |
| 2 | architect | Tighten the task test plan so AC1 and AC5 require discriminating proof of config-derived success progression and no `AgentView` masking, not just compatibility on the stock config. | `tests/test_end_work_success_1336.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/agent_view.py` | Task tests at `tests/test_end_work_success_1336.py:138`, `:185`, `:223`, `:239`, `:255` pass against the stock order only; pass-through is only code-inspected at `serve/kanban/src/owlbear_kanban/agent_view.py:1177-1184`. |

### Reflection
- Broad lifecycle gates in kanban currently include unrelated guidance-string debt, so a separating run is necessary before assigning blame to a narrow fix task.
- Without commit-diff access, TestFromAC immutability checks need an explicit confidence deduction rather than a false claim of proof.
- Exact-string guidance tests can make adjacent lifecycle suites red even when the task-local behavioral change is correct.
[[2026-05-04]]


## Architecture Review — Re-scope (Cycle 2)

### Reviewer Deductions Addressed

| Deduction | Root cause | Fix |
|-----------|-----------|-----|
| AC1 proof lax — stock config only | Tests use default 6-status board; a hardcoded sequence would also pass | AC1 refined: require ≥1 test with non-stock config |
| AC3 proof lax — `done` hardcode risk | Tests only exercise `done` as terminal | AC3 refined: require ≥1 test with custom terminal status |
| AC5 code-inspection only | No discriminating test through AgentView | AC5 refined: require one AgentView success-advancement test |
| AC7 red on unrelated debt | `test_engine_end_work_1080.py` guidance-string mismatch is #1339's domain | AC7 re-scoped to task-owned suites |

### Refined Acceptance Criteria

1. Raw `KanbanEngine.end_work(task_id, outcome="success")` derives next status from `config.pipeline.statuses` when no explicit `move_to` is supplied. **Test-plan requirement**: at least one test uses a non-stock config (e.g., 3-status board `alpha → beta → gamma`) to prove advancement reads from config, not a hardcoded sequence. (td:2)
2. Raw success no longer moves tasks to `research` by default. (td:1)
3. Success from the terminal status archives the task with `archival_reason="completed"` and `archival_refs=[]`. **Test-plan requirement**: at least one terminal-archive test uses a custom config where the terminal status is NOT `done` (proving terminal detection reads from config). (td:2)
4. Explicit `move_to` behavior remains available for non-success outcomes where currently supported, especially `reject`. (td:1)
5. `AgentView.end_work(outcome="success")` advances identically to raw engine — one discriminating test through AgentView proves no masking layer alters success behavior. (td:1)
6. `tests/test_end_work_success_1336.py` is corrected so terminal success expects archive behavior, not an error. (td:0)
7. Task-owned test suites pass: `tests/test_end_work_success_1336.py`, `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_activity_session.py`. Known-unrelated guidance-string failures in `test_engine_end_work_1080.py` are excluded (covered by #1339). (td:0)

### Test-Writer Guidance (updated)

- Add ≥1 custom-config test for AC1: define a 3-status board (e.g., `alpha, beta, gamma`) and verify success from `alpha` → `beta`, `beta` → `gamma`.
- Add ≥1 custom-config terminal test for AC3: use a board where `gamma` is terminal; verify success from `gamma` archives with `archival_reason="completed"`.
- Add 1 AgentView integration test for AC5: instantiate AgentView, call `end_work(outcome="success")` from a mid-pipeline status, verify advancement matches raw engine behavior.
- Existing tests for AC1–AC4 remain valid; new tests supplement them.

### Architecture Notes

- Engine code at `serve/kanban/src/owlbear_kanban/engine.py:1514-1540` already reads `self._config.pipeline.statuses` — the implementation is correct. The refinement is purely about test discriminability.
- `AgentView.end_work()` at `serve/kanban/src/owlbear_kanban/agent_view.py:1177-1184` passes `move_to=move_to` (defaults to `None` in AgentView signature). With engine default now also `None`, no masking occurs — but a test must prove this.
- Guidance-string debt (`_BLOCK_AR_HINT` vs test expectation) is task #1339 AC7.

### Verdict: APPROVE (re-scoped)

AC is now precise and discriminating. Test-plan requirements ensure reviewer can verify config-derived behavior without ambiguity. No split needed — all concerns are one logical domain (engine success-path contract).

[[2026-05-04]]
Architecture re-review complete. Refined AC1/AC3/AC5/AC7 to address reviewer's proof-quality deductions: (1) AC1/AC3 now require non-stock config tests to discriminate config-derived logic from hardcoded sequences; (2) AC5 now requires one discriminating AgentView integration test; (3) AC7 re-scoped to task-owned suites, excluding guidance-string debt already covered by #1339. Verdict: APPROVE.
[[2026-05-04]]
## Test-Writer Notes
- Retry (cycle 2): added 5 discriminating tests for reviewer AC1/AC3/AC5 proof-quality gaps. All pass against current implementation.
- Builder skip: test-only retry, all 15 tests green.
- Test file: `tests/test_end_work_success_1336.py`
- New classes added:
  - `TestFromAC_CustomConfigAdvancement` — 2 tests (AC1 discriminating: non-standard status order `in-progress→backlog→review`; stock-order code would advance `in-progress→review`, not `→backlog`)
  - `TestFromAC_CustomTerminalArchive` — 2 tests (AC3 discriminating: terminal=`review` not `done`; hardcoded `done` check would fail)
  - `TestFromAC_AgentViewNoMasking` — 1 test (AC5: AgentView result equals raw engine result from same status)
- Total: 15 tests (10 prior + 5 new), all PASS
- Ruff: clean

AC coverage:
| AC | Tests | Notes |
|----|-------|-------|
| AC1 (td:2) | 5+2=7 tests | 2 new with non-stock config discriminate against hardcoded sequence |
| AC2 (td:1) | 1 test | Negative assertion still passes |
| AC3 (td:2) | 3+2=5 tests | 2 new with non-done terminal discriminate against hardcoded `done` |
| AC4 (td:1) | 1 test | Unchanged |
| AC5 (td:1) | 1 new test | AgentView integration proves no masking layer |
| AC6 (td:0) | N/A — meta-AC |  |
| AC7 (td:0) | N/A — re-scoped to task-owned suites (builder responsibility) |  |
[[2026-05-04]]
## Builder Notes
- Implementation: no source changes required in this cycle. Verified live behavior already matches refined AC (raw engine default move_to=None, config-derived advancement, terminal success archive path).
- Files changed: none.
- Tests: 64 passed, 0 failed, 0 skipped (quality-runner scoped run on task-owned suites).
  - tests/test_end_work_success_1336.py
  - serve/kanban/tests/test_engine_end_work_1077.py
  - tests/test_engine_activity_session.py
- Lint: clean on serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/agent_view.py, tests/test_end_work_success_1336.py.
- Coverage: owlbear_kanban.engine 46% in scoped run (informational; no touched module this cycle).
- Evidence summary: AC1-AC5 behavior present in current code paths and discriminating tests; AC7 task-owned suites pass.

### Reflection
- Problem faced: task is a test-only retry cycle where implementation was already correct, so RED->GREEN implementation delta was empty.
- Workaround applied: collected fresh quality-runner evidence to ensure routing can proceed without speculative edits.
- Pattern discovered: when architect re-scopes AC to task-owned suites, builder closeout can be verification-only with zero-diff source state.
- Quality gap: module-level coverage remains low in narrow scoped measurement due large module surface vs focused task scope.
[[2026-05-04]]
## Review Evidence

### Test Results
- `quality-runner` scoped run: 64 passed, 0 failed, 0 skipped.
- Executed suites:
  - `tests/test_end_work_success_1336.py`
  - `serve/kanban/tests/test_engine_end_work_1077.py`
  - `tests/test_engine_activity_session.py`
- No task-owned runtime failures were observed in this cycle.

### Lint Results
- `ruff`: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/agent_view.py`, and `tests/test_end_work_success_1336.py`.

### Coverage
- Informational only: scoped report showed overall 39%, with `owlbear_kanban.engine=46%` and `owlbear_kanban.agent_view=26%`.
- This did not drive the verdict because the cycle is test-only, there is no source diff in the builder notes, and the available report is module-level rather than diff-scoped.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Raw `KanbanEngine.end_work(..., outcome="success")` derives next status from `config.pipeline.statuses` when no explicit `move_to` is supplied; at least one test uses a non-stock config. | Raw engine success path is config-driven in `serve/kanban/src/owlbear_kanban/engine.py:1532-1540`; custom-config discriminators in `tests/test_end_work_success_1336.py:422` and `tests/test_end_work_success_1336.py:439` prove advancement on a non-stock status order. | PASS |
| 2. Raw success no longer moves tasks to `research` by default. | Raw signature now defaults `move_to` to `None` in `serve/kanban/src/owlbear_kanban/engine.py:1559-1566`; negative regression remains in `tests/test_end_work_success_1336.py:360`. | PASS |
| 3. Success from the terminal status archives the task with `archival_reason="completed"` and `archival_refs=[]`; at least one terminal-archive test uses a custom terminal status. | Terminal branch sets `archival_reason` and clears refs in `serve/kanban/src/owlbear_kanban/engine.py:1534-1537`. Custom-terminal tests at `tests/test_end_work_success_1336.py:469` and `tests/test_end_work_success_1336.py:487` prove custom-terminal archive behavior, and adjacent wrapper regression at `serve/kanban/tests/test_engine_end_work_1077.py:209-227` asserts `archival_refs == []`. But the task-owned helper hardcodes `archival_refs: []` in `tests/test_end_work_success_1336.py:81` and `tests/test_end_work_success_1336.py:101`, `_write_task` cannot seed non-empty refs in `tests/test_end_work_success_1336.py:117`, and raw engine `edit_task` can persist live refs via `serve/kanban/src/owlbear_kanban/engine.py:1162-1163`. Removing the clear at `serve/kanban/src/owlbear_kanban/engine.py:1537` would likely stay green, so the `archival_refs=[]` part of AC3 remains under-proven. | FAIL (proof gap) |
| 4. Explicit `move_to` behavior remains available for non-success outcomes where currently supported, especially `reject`. | Raw reject branch preserves explicit `move_to` in `serve/kanban/src/owlbear_kanban/engine.py:1548-1555`; adjacent regressions in `serve/kanban/tests/test_engine_end_work_1077.py:256` and `serve/kanban/tests/test_engine_end_work_1077.py:438` cover explicit archive and missing-`move_to` validation through the supported wrapper path. | PASS |
| 5. `AgentView.end_work(outcome="success")` advances identically to raw engine; one discriminating wrapper test proves no masking. | `AgentView.end_work` forwards directly in `serve/kanban/src/owlbear_kanban/agent_view.py:1177-1185`; wrapper-vs-raw comparison in `tests/test_end_work_success_1336.py:525-545` would fail if a masking layer changed success behavior. | PASS |
| 6. `tests/test_end_work_success_1336.py` is corrected so terminal success expects archive behavior, not an error. | Terminal-success expectations are positive archive assertions in `tests/test_end_work_success_1336.py:274`, `tests/test_end_work_success_1336.py:290`, and `tests/test_end_work_success_1336.py:306`. | PASS |
| 7. Task-owned suites pass: `tests/test_end_work_success_1336.py`, `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_activity_session.py`. | `quality-runner` scoped run: 64 passed, 0 failed, 0 skipped across the three task-owned suites. | PASS |

### Additional Review Findings
- `code-reader` found no security or data-safety issue in the reviewed engine/wrapper paths.
- No visible weakening or removal of `TestFromAC_*` assertions was found in the current snapshot.
- Dirty-tree / commit-diff provenance could not be independently verified in this tool surface, so immutability confidence is slightly reduced.
- Existing `## Review Evidence` sections before this review: 1. This is a second review failure, so backlog routing applies even though the remaining issue is proof quality rather than runtime breakage.

### Deductions
- AC3 still has a false-green path: the suite proves archive behavior, but not that terminal success normalizes a pre-existing non-empty raw-engine `archival_refs` state to `[]`.
- The task-local fixtures mask this because they always start with `archival_refs: []`.
- The remaining gap is test-proof quality, not implementation correctness; the live engine behavior appears correct.
- Git/dirty-tree verification was unavailable here, so provenance confidence takes a small deduction.

### Verdict
- `FAIL` with confidence `0.88`.
- Runtime evidence is clean, but the gate is not met because AC3's `archival_refs=[]` contract is still not discriminatingly proven against reachable raw-engine state.
- Action: reject to `backlog` under the second-review-failure loop-breaker and test-quality routing rules.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Refine AC3 / test plan to state whether raw-engine terminal success must normalize pre-existing live `archival_refs` to `[]`; if yes, require a discriminating test seeded from a non-empty raw-engine state. | `tests/test_end_work_success_1336.py`, `serve/kanban/src/owlbear_kanban/engine.py` | Task helper hardcodes empty refs at `tests/test_end_work_success_1336.py:81`, `:101`, and cannot seed refs at `:117`; raw engine can persist live refs at `serve/kanban/src/owlbear_kanban/engine.py:1162-1163`; terminal clear happens at `serve/kanban/src/owlbear_kanban/engine.py:1537`. |

### Reflection
- The narrowed task now passes all runtime gates; the remaining blocker is purely proof quality.
- Exact-field contracts like `archival_refs=[]` need a non-default starting state, otherwise default fixtures can hide regressions.
- On looped review tasks, green scoped runs do not eliminate the need for mutation-style assertion checks.
[[2026-05-04]]

## Architecture Review — Re-scope (Cycle 3)

### Reviewer Deduction Addressed

| Deduction | Root cause | Fix |
|-----------|-----------|-----|
| AC3 `archival_refs=[]` not discriminatingly proven | Task fixtures always seed empty refs; removing the `record.archival_refs = []` line would stay green | AC3 refined: require one test that seeds non-empty refs before terminal success |

### Refined AC3

3. Success from the terminal status archives the task with `archival_reason="completed"` and normalizes `archival_refs` to `[]` even if the task previously had non-empty refs (via raw `edit_task`). **Test-plan requirement**: at least one terminal-archive test seeds `archival_refs=[<non-empty>]` via engine `edit_task` before calling terminal success, then asserts `archival_refs == []`. (td:2)

### Architecture Notes

- `edit_task` at `serve/kanban/src/owlbear_kanban/engine.py:1162-1163` can set `archival_refs` to any `list[int]` on a live task.
- Terminal success branch at `serve/kanban/src/owlbear_kanban/engine.py:1537` unconditionally sets `record.archival_refs = []` — this normalization is intentional (completed tasks have no outstanding references).
- The discriminating test must: (1) create a task at terminal status, (2) call `edit_task` to set `archival_refs=[100, 200]`, (3) call `end_work(outcome="success")`, (4) assert archived task has `archival_refs == []`.
- All other AC lines (1, 2, 4, 5, 6, 7) remain unchanged from cycle 2.

### Test-Writer Guidance (cycle 3 delta)

- Add 1 discriminating test for AC3: seed non-empty `archival_refs` on a terminal-status task via `engine.edit_task(task_id, archival_refs=[100, 200])`, then call `end_work(outcome="success")` and assert the archived task has `archival_refs == []`.
- Existing 15 tests remain valid; this adds 1 supplemental test.

### Verdict: APPROVE (re-scoped)

AC3 is now precise and discriminating. The single remaining reviewer gap is addressed by requiring a seeded-refs normalization test. No split needed — this is still one logical domain (engine success-path contract).

[[2026-05-04]]
Architecture re-review (cycle 3) complete. Refined AC3 to require discriminating normalization test: seed non-empty archival_refs via edit_task before terminal success, assert cleared to []. Single remaining reviewer gap addressed. All other AC lines unchanged from cycle 2. Verdict: APPROVE.
[[2026-05-04]]
## Test-Writer Notes
- Retry (cycle 3): added 1 discriminating test for reviewer AC3 proof-quality gap. Test passes against current implementation.
- Builder skip: test-only retry, all 16 tests green.
- Test file: `tests/test_end_work_success_1336.py`
- New test: `TestFromAC_SuccessAtTerminalStatus.test_success_at_terminal_normalizes_nonempty_archival_refs_to_empty`
- Technique: seeds `archival_refs=[100, 200]` via `engine.edit_task` before terminal success; asserts `result.archival_refs == []`. Removing the `record.archival_refs = []` normalization line would break this test.
- Total: 16 tests (15 prior + 1 new), all PASS
- Ruff: clean

AC coverage:
| AC | Tests | Notes |
|----|-------|-------|
| AC1 (td:2) | 7 tests | Custom-config discriminators confirm config-derived advancement |
| AC2 (td:1) | 1 test | Negative assertion passes |
| AC3 (td:2) | 5+1=6 tests | New test discriminates archival_refs normalization with seeded non-empty state |
| AC4 (td:1) | 1 test | Unchanged |
| AC5 (td:1) | 1 test | AgentView integration, no masking |
| AC6 (td:0) | N/A — meta-AC |  |
| AC7 (td:0) | N/A — task-owned suites pass |  |
[[2026-05-04]]
## Builder Notes
- Implementation: no source edits required in this cycle; verified existing engine and AgentView behavior matches refined AC.
- Files changed: none.
- Tests: 65 passed, 0 failed, 0 skipped.
  - tests/test_end_work_success_1336.py
  - serve/kanban/tests/test_engine_end_work_1077.py
  - tests/test_engine_activity_session.py
- Lint: clean (ruff on serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/agent_view.py, tests/test_end_work_success_1336.py).
- Coverage: overall 40%; owlbear_kanban.engine 50%; owlbear_kanban.agent_view 26% (informational for verification-only cycle).
- Evidence summary: AC1-AC5 validated by task-owned TestFromAC coverage and current runtime behavior; AC7 task-owned suites pass.

### Reflection
- Problem faced: this was a verification-only retry cycle with no implementation delta.
- Workaround applied: used a strict task-scoped quality-runner pass to avoid unrelated-suite noise.
- Pattern discovered: for test-only retry cycles, a fresh scoped quality gate is sufficient to route forward when implementation is unchanged.
[[2026-05-05]]
## Review Evidence

### Test Results
- `quality-runner` scoped run: 65 passed, 0 failed, 0 skipped.
- Executed suites:
  - `tests/test_end_work_success_1336.py`
  - `serve/kanban/tests/test_engine_end_work_1077.py`
  - `tests/test_engine_activity_session.py`
- No environment, plugin, or execution issues were reported.

### Lint Results
- `ruff`: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/agent_view.py`, `tests/test_end_work_success_1336.py`, `serve/kanban/tests/test_engine_end_work_1077.py`, and `tests/test_engine_activity_session.py`.
- Editor diagnostics: `get_errors` reported no errors in the same scoped files.

### Coverage
- Informational only: overall 40%; `owlbear_kanban.engine` 50%; `owlbear_kanban.agent_view` 26%.
- This remains module-level rather than diff-scoped, and there is no source diff in the latest builder cycle.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. Raw `KanbanEngine.end_work(task_id, outcome="success")` derives next status from `config.pipeline.statuses` when no explicit `move_to` is supplied; at least one test uses a non-stock config. | Success branch advances by config order in `serve/kanban/src/owlbear_kanban/engine.py:1534-1540`. Non-stock discriminators in `tests/test_end_work_success_1336.py:443-455` and `tests/test_end_work_success_1336.py:460-471` prove `in-progress -> backlog` and `backlog -> review` on a custom 3-status board, which would fail on a hardcoded stock sequence. | PASS |
| 2. Raw success no longer moves tasks to `research` by default. | Raw engine now defaults `move_to` to `None` in `serve/kanban/src/owlbear_kanban/engine.py:1566`. Negative regression at `tests/test_end_work_success_1336.py:381-392`, plus the exact-value AC1 advancement tests, prove success no longer falls back to `research`. | PASS |
| 3. Success from the terminal status archives the task with `archival_reason="completed"` and normalizes `archival_refs` to `[]` even if the task previously had non-empty refs via raw `edit_task`. | Terminal archive branch sets `archival_reason` and clears refs in `serve/kanban/src/owlbear_kanban/engine.py:1534-1537`. The discriminating seeded-refs test in `tests/test_end_work_success_1336.py:326-342` seeds `[100, 200]` via `engine.edit_task` at `tests/test_end_work_success_1336.py:338` and then asserts `archival_refs == []` at `tests/test_end_work_success_1336.py:342`. Stock-terminal archive assertions remain exact at `tests/test_end_work_success_1336.py:285`, `tests/test_end_work_success_1336.py:301`, and `tests/test_end_work_success_1336.py:317-319`, and custom-terminal archive assertions at `tests/test_end_work_success_1336.py:503` and `tests/test_end_work_success_1336.py:521-523` prove terminal detection is config-driven rather than hardcoded to `done`. | PASS |
| 4. Explicit `move_to` behavior remains available for non-success outcomes where currently supported, especially `reject`. | Reject handling remains in `serve/kanban/src/owlbear_kanban/engine.py:1548-1555`. Supported wrapper regressions at `serve/kanban/tests/test_engine_end_work_1077.py:246`, `serve/kanban/tests/test_engine_end_work_1077.py:256-278`, and `serve/kanban/tests/test_engine_end_work_1077.py:438-452` prove explicit reject `move_to` flows and required validation remain intact. | PASS |
| 5. `AgentView.end_work(outcome="success")` advances identically to raw engine; one discriminating wrapper test proves no masking layer alters success behavior. | `AgentView` delegates directly to `engine.end_work(...)` in `serve/kanban/src/owlbear_kanban/agent_view.py:1177-1184`. The comparison test at `tests/test_end_work_success_1336.py:546-566` drives raw engine and wrapper independently and asserts identical resulting status at `tests/test_end_work_success_1336.py:566`. | PASS |
| 6. `tests/test_end_work_success_1336.py` is corrected so terminal success expects archive behavior, not an error. | Terminal-success expectations are now positive archive assertions in `tests/test_end_work_success_1336.py:285`, `tests/test_end_work_success_1336.py:301`, and `tests/test_end_work_success_1336.py:317-319`. No remaining terminal-error expectation was found in the file. | PASS |
| 7. Task-owned suites pass: `tests/test_end_work_success_1336.py`, `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_activity_session.py`. | `quality-runner` scoped run completed cleanly: 65 passed, 0 failed, 0 skipped across the three task-owned suites. | PASS |

### Additional Review Findings
- `code-reader` found no security or data-safety issue in the reviewed engine and `AgentView` success/reject paths.
- Current snapshot shows no visible weakening or removal of `TestFromAC_*` assertions.
- Existing `## Review Evidence` sections before this review: 2. This cycle closes the remaining proof gap from the prior review rather than changing runtime behavior.
- Git-log evidence confirms task-related committed test-writer retries for `#1336` in `.git/logs/HEAD:1845`, `.git/logs/HEAD:1863`, and `.git/logs/HEAD:1896`.

### Deductions
- `tests/test_end_work_success_1336.py:423` (`test_reject_without_move_to_does_not_go_to_research`) is a lax negative assertion for a non-AC behavior; it would false-green on an incorrect non-`research` status.
- This is non-blocking because the refined AC4 is about explicit `move_to` behavior, and that contract is discriminatingly proven elsewhere in the wrapper suite.
- Full dirty-tree and exact commit-diff verification were not available in this tool surface, so provenance confidence takes a small deduction despite the git-log evidence above.

### Verdict
- `PASS` with confidence `0.94`.
- The prior AC3 false-green risk is closed by the seeded non-empty `archival_refs` discriminator, and all task-owned runtime gates are green.
- Action: advance to `docs`.
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/kanban/README.md:43` describes `end_work` briefly ("Finalise a work session: append timestamped note and apply outcome"); description remains accurate after move_to default change. No prose update needed. |
| 2 | Module docstrings | Yes | N/A | `engine.py` `end_work` docstring already accurate: Note section says success advances by config sequence; move_to described as optional for reject — no stale "research" content. `agent_view.py` docstring accurate: move_to "Forbidden on success." No updates needed. |
| 3 | External attribution | No | N/A | No external sources used. |
| 4 | Research doc | No | N/A | No research phase for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) — footer updated from `(0c497432)` to `(5c71fc13)`. `share/diagrams/mcp-topology.excalidraw` (describes: `serve/kanban/src/**`) — footer updated from `(12c2add1)` to `(5c71fc13)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request. |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Docstring verified accurate — no edit needed |
| `serve/kanban/src/owlbear_kanban/agent_view.py` | IN (docstrings) | Docstring verified accurate — no edit needed |
| `tests/test_end_work_success_1336.py` | OUT | Test file — no doc action |
| `serve/kanban/tests/test_engine_end_work_1077.py` | OUT | Test file — no doc action |
| `tests/test_engine_activity_session.py` | OUT | Test file — no doc action |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated to 2026-05-05 (5c71fc13) |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated to 2026-05-05 (5c71fc13) |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer hash updated
- `share/diagrams/mcp-topology.excalidraw` — footer hash updated

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/1336-pytest.txt`
- `.owlbear/scratch/1336-ruff.txt`
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Raw success derives next status from config | engine.py:1528 reads config.pipeline.statuses; custom-config discriminators at test:443,460 | PASS |
| 2. No default to research | Signature at engine.py:1566 has move_to=None | PASS |
| 3. Terminal archives with archival_reason/refs | engine.py:1534-1537; seeded-refs discriminator at test:326-342 | PASS |
| 4. Explicit move_to for reject | Reject branch at engine.py:1548-1555; wrapper regressions in 1077 suite | PASS |
| 5. AgentView no masking | agent_view.py:1177-1184 pass-through; comparison test at test:546-566 | PASS |
| 6. Test file corrected | Terminal assertions at test:285,301,317 expect archive not error | PASS |
| 7. Task-owned suites pass | quality-runner: 65 passed, 0 failed in scoped suites | PASS |

### Test Results
- Full suite: 4384 passed, 250 failed (all pre-existing unrelated debt), 5 skipped
- Task-owned (16 tests): ALL PASS
- ruff: clean

### Architect Quality: 4/5
Initial AC was reasonable and testable. Required 2 re-scoping cycles for proof-quality discriminators (custom config tests, seeded-refs normalization). Responsive to reviewer feedback. Minor gap: initial test-plan requirements could have been more discriminating upfront.

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 pass) = 0
- Lint violations: 0 = 0
- AC quality (4/5, not <=3): 0
- Missing reviewer evidence: 0 (detailed, present) = 0
- Full-suite task-scope failures: 0 = 0
- Background noise (250 pre-existing failures reduce cross-task regression signal): -0.02

### Confidence: 0.98
### Action: archive

### Commit Integrity
- 4 commits verified via git log --grep=1336:
  - 81f7f7bd test: add failing tests (test-writer)
  - d87750c5 test: correct end_work success/terminal tests (test-writer)
  - 267fbf36 test: add AC3 archival_refs normalization discriminator (test-writer)
  - c9ba8481 docs: update diagram footers (doc-writer)
- No engine.py changes committed (confirmed: builder found default already correct)