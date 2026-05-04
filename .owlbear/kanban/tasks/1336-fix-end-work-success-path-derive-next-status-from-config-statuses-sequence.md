---
id: 1336
title: Fix raw engine end_work success default and terminal archive contract
status: in-progress
priority: critical
created: 2026-05-04T15:00:05.698435+00:00
updated: 2026-05-04T21:21:13.158641+00:00
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