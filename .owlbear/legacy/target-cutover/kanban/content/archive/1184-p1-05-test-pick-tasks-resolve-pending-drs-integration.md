---
id: 1184
title: 'P1-05: Test pick_tasks resolve_pending_drs integration'
status: archived
priority: medium
created: 2026-04-30T00:51:47.776679+00:00
updated: 2026-04-30T02:26:53.493343+00:00
tags:
- phase-1
- scope:kanban
- type:test
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test that `pick_tasks` calls `resolve_pending_drs` before task selection logic (td:1)
- Test that resolve exceptions do NOT propagate to `pick_tasks` caller (try/except wrapping) (td:1)
- Test that resolved DRs are processed before task filtering occurs (td:2)
- Test pick_tasks still functions correctly when no pending DRs exist (td:1)
- Test pick_tasks still functions correctly when pending/ directory doesn't exist (td:1)

## Scope

- IN: integration test for resolve call within pick_tasks flow
- OUT: decisions.py unit tests (covered by #1180), MCP layer

Brief: see parent #1179

[[2026-04-30]]
## Research
- Research doc: .owlbear/research/pick-tasks-resolve-integration-testing.md
- Sources: 5 studied, 5 high-relevance (all codebase/brief — no external sources needed)
- Recommendation: 5 tests using monkeypatch on `decisions.resolve_pending_drs`; mock at module function level, not private method (confidence: .90)
- Follow-up tasks created: none (this IS the test task)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — test specification task with clear established patterns; no design decision to challenge
- Key findings: existing test_engine_pick_tasks_1074.py establishes all patterns needed (tmp_path boards, _make_board helpers); mock target is `owlbear_kanban.decisions.resolve_pending_drs`; test file goes at `tests/test_pick_tasks_resolve_1184.py`

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only the pick_tasks/resolve_pending_drs integration contract |
| Interface clarity | PASS | Each AC line maps to one test method; mock target specified in research |
| Dependency correctness | PASS | No deps needed — mocks the not-yet-existing function |
| Module layering | PASS | Tests in `tests/`, mock at module boundary |
| TDD compliance | PASS | This IS the test task (RED phase for #1185) |
| KISS/YAGNI | PASS | 5 tests for 5 AC lines, no extra abstractions |
| Premise challenge | PASS | Tests define contract for #1185 implementation |
| Pattern consistency | PASS | Follows test_engine_pick_tasks_1074.py patterns (tmp_path, _make_board) |
| Security surface | N/A | Test file only |
| Single domain | PASS | kanban engine domain |

### Challenge Results
- Challenger: FALLBACK — test specification with clear established patterns; accepted
- Architect response: accepted

### Test Depth
- Max depth: 2 (AC3 requires ordering proof via side-effect mutation)
- Test-writer: SKIP (type:test tag — pass-through)

### Verdict: APPROVE
### Action Taken: AC annotated with test depths; advanced to todo
[[2026-04-30]]
Architecture review complete. All 10 criteria pass. AC lines annotated with test depths (max td:2 on ordering proof). type:test tag confirmed for test-writer pass-through. Mock strategy at module boundary (owlbear_kanban.decisions.resolve_pending_drs) is correct — tests the actual try/except contract, not a pass-through mock.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_pick_tasks_resolve_1184.py
- Classes: TestFromAC_PickTasksResolveIntegration
- Tests per category: happy 2, edge 1, error 1, boundary 1
- Total: 5 tests, all FAIL (AssertionError: resolve_pending_drs called 0 times / ordering assertion)
- ruff: clean

### AC Coverage

| AC | Test | Failure mode |
|----|------|-------------|
| pick_tasks calls resolve_pending_drs before selection (td:1) | test_resolve_pending_drs_is_called | assert_called_once_with(engine) — called 0 times |
| Exceptions do NOT propagate to caller (td:1) | test_resolve_exceptions_do_not_propagate | assert_called_once_with(engine) — called 0 times |
| Resolved DRs processed before filtering (td:2) | test_resolve_runs_before_task_filtering | assert 1 in {2} — task 1 not unblocked because resolve never ran |
| Works with no pending DRs (td:1) | test_no_pending_drs_pick_tasks_works | assert_called_once() — called 0 times |
| Works when pending/ dir doesn't exist (td:1) | test_no_decisions_directory_pick_tasks_works | assert_called_once() — called 0 times |

### Mock strategy
- Injects fake `owlbear_kanban.decisions` module via `monkeypatch.setitem(sys.modules, ...)` — works regardless of whether #1185 uses lazy import or module-level import (since decisions.py doesn't exist yet, implementation must use lazy import)
- AC3 ordering proof uses a side-effect closure that rewrites the task file (blocked: true → false) — mtime-based cache picks up the change on the subsequent list_tasks call
[[2026-04-30]]
## Builder Notes
- Implementation: added a pre-filter decision-resolution hook in serve/kanban/src/owlbear_kanban/engine.py within AgentView.pick_tasks.
- Behavior: pick_tasks now lazily imports owlbear_kanban.decisions via importlib, calls resolve_pending_drs(self.engine) before list_tasks filtering, and suppresses resolution/import exceptions so caller behavior remains stable.
- Files changed: serve/kanban/src/owlbear_kanban/engine.py
- Tests (task-scoped): 5 passed, 0 failed in tests/test_pick_tasks_resolve_1184.py (all TestFromAC expectations now green).
- Lint (scoped): clean for serve/kanban/src/owlbear_kanban/engine.py and tests/test_pick_tasks_resolve_1184.py.
- Coverage evidence (scoped run): owlbear_kanban.engine reported 21% due module breadth; task-scoped AC coverage is satisfied by all 5 integration tests passing.
- Regression check: attempted durable pick_tasks suite path tests/test_engine_pick_tasks_1074.py; file does not exist in workspace.
- Commit: fc520d2b with message "feat: resolve DRs before pick_tasks filtering (#1184, builder)".

## Post-task Reflection
- Problem faced: lazy in-function import satisfied behavior but triggered PLC0415 lint.
- Workaround applied: switched to importlib.import_module for lazy resolution without local import statements.
- Pattern discovered: module-level monkeypatch via sys.modules works cleanly with importlib-based lazy hooks and keeps decision integration optional.
- Quality gap: coverage gating on a large monolithic module can under-represent focused behavior changes; task-scoped assertions were used as primary proof.
[[2026-04-30]]
## Review Evidence
### Source Scope
- Builder commit `fc520d2b` is present in `.git/logs/HEAD`.
- Builder notes and the current snapshot scope the production change to `serve/kanban/src/owlbear_kanban/engine.py`.
- No current-signature change is visible on `AgentView.pick_tasks`, so no caller-usage audit was required.

### Test Results
- quality-runner (task-scoped): 5 passed, 0 failed, 0 skipped on `tests/test_pick_tasks_resolve_1184.py`.
- quality-runner (adjacent durable `pick_tasks` suites): 27 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_engine_pick_tasks_1074.py` and `serve/kanban/tests/test_engine_pick_tasks_1076.py`.
- A broader batch that also included `serve/kanban/tests/test_engine_coverage_1068.py` surfaced 6 unrelated baseline failures in claim/release/end_work tests; that run was not used as gate evidence for this `pick_tasks` change.

### Lint
- clean for `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_pick_tasks_resolve_1184.py`.

### Coverage
- task-scoped report: `owlbear_kanban.engine` 21% module coverage, 26% overall.
- Adjacent durable `pick_tasks` rerun reported 29% package-level coverage.
- These module/package numbers are informational only because `engine.py` is a large monolithic module. The changed lines at `serve/kanban/src/owlbear_kanban/engine.py:2323-2325` are directly exercised by the task-owned AC tests.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| `pick_tasks` calls `resolve_pending_drs` before task selection logic | `test_resolve_pending_drs_is_called` + `test_resolve_runs_before_task_filtering` | Yes. Removing the call fails the call assertion at `tests/test_pick_tasks_resolve_1184.py:160`; moving the call below filtering leaves task 1 blocked and fails `tests/test_pick_tasks_resolve_1184.py:217`. | COVERED |
| Resolve exceptions do NOT propagate to the caller | `test_resolve_exceptions_do_not_propagate` | Yes. If the wrapper at `serve/kanban/src/owlbear_kanban/engine.py:2323-2325` did not suppress the exception, the test would not reach the response/assertion path at `tests/test_pick_tasks_resolve_1184.py:182-185`. | COVERED |
| Resolved DRs are processed before task filtering occurs | `test_resolve_runs_before_task_filtering` | Yes. The side-effect unblocks task 1 before `list_tasks(blocked=False, unclaimed=True, ...)` at `serve/kanban/src/owlbear_kanban/engine.py:2327-2330`; if filtering ran first, task 1 would be absent and `tests/test_pick_tasks_resolve_1184.py:217` would fail. | COVERED |
| `pick_tasks` still works when no pending DRs exist | `test_no_pending_drs_pick_tasks_works` | Yes. If the empty-return path broke dispatch, the response/task assertions at `tests/test_pick_tasks_resolve_1184.py:239-241` would fail. | COVERED |
| `pick_tasks` still works when `pending/` doesn't exist | `test_no_decisions_directory_pick_tasks_works` | Yes for this task's integration contract. The task research explicitly defines the strategy as `Board without decisions dir; function handles gracefully | Returns [] or skips` in `.owlbear/research/pick-tasks-resolve-integration-testing.md:29-35`, with resolver internals out of scope for this integration task. The response/task assertions at `tests/test_pick_tasks_resolve_1184.py:256-266` prove the `pick_tasks` boundary continues normally under that setup. | COVERED |

#### Security Review
- No issues found in the scoped production path. The change uses a fixed internal import (`importlib.import_module("owlbear_kanban.decisions")` at `serve/kanban/src/owlbear_kanban/engine.py:2324`) followed by a direct internal call at `serve/kanban/src/owlbear_kanban/engine.py:2325`; no user-controlled shell, SQL, template, or path sink is introduced.

#### Test Integrity
- No evidence of weakened or removed `TestFromAC_*` assertions. The current `TestFromAC_PickTasksResolveIntegration` suite remains intact in `tests/test_pick_tasks_resolve_1184.py:139-266`, and the builder notes scope file changes to `serve/kanban/src/owlbear_kanban/engine.py` only.

#### Test Quality
- Assertion specificity: ADEQUATE. The dedicated AC1 test is only a call check, but the AC3 side-effect test provides the required ordering proof against the real filter boundary.
- Negative/error-path coverage: ADEQUATE. The resolver exception path is exercised by `test_resolve_exceptions_do_not_propagate`, and the no-directory graceful path matches the task's documented mocked-integration strategy.
- Manual mutation reasoning: STRONG. Removing the resolver call, moving it below filtering, or letting exceptions escape would all fail named tests.
- Test independence: STRONG. Each test constructs its own `tmp_path` board.
- Descriptive names: STRONG.

#### Data Safety
- No issues found in the reviewed lines.

#### Implementation-Aware Gap Analysis
- No blocking gap in the changed behavior. The added wrapper and call at `serve/kanban/src/owlbear_kanban/engine.py:2323-2325` are exercised by the task-owned suite.
- Informational only: the import-failure half of the `contextlib.suppress(Exception)` wrapper is not directly asserted by this task's tests. I did not gate on that because the AC and research scope this task to mocked `resolve_pending_drs` integration, not import-error behavior, and the module now exists at `serve/kanban/src/owlbear_kanban/decisions.py`.

#### Builder Process Quality
- CLEAN. One builder attempt, no loop pattern, no repeated retries.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| `pick_tasks` calls `resolve_pending_drs` before task selection logic | `serve/kanban/src/owlbear_kanban/engine.py:2323-2327`; `tests/test_pick_tasks_resolve_1184.py:160`; `tests/test_pick_tasks_resolve_1184.py:217` | `test_resolve_pending_drs_is_called`; `test_resolve_runs_before_task_filtering` | PASS |
| Resolve exceptions do NOT propagate to the caller | `serve/kanban/src/owlbear_kanban/engine.py:2323-2325`; `tests/test_pick_tasks_resolve_1184.py:162-185` | `test_resolve_exceptions_do_not_propagate` | PASS |
| Resolved DRs are processed before task filtering occurs | `serve/kanban/src/owlbear_kanban/engine.py:2325-2330`; `tests/test_pick_tasks_resolve_1184.py:187-217` | `test_resolve_runs_before_task_filtering` | PASS |
| `pick_tasks` still works when no pending DRs exist | `tests/test_pick_tasks_resolve_1184.py:222-241` | `test_no_pending_drs_pick_tasks_works` | PASS |
| `pick_tasks` still works when `pending/` doesn't exist | `.owlbear/research/pick-tasks-resolve-integration-testing.md:29-35`; `tests/test_pick_tasks_resolve_1184.py:243-266` | `test_no_decisions_directory_pick_tasks_works` | PASS |

### Subagent Divergence
- `code-reader` flagged AC5 as missing under a stricter interpretation that required exercising the real `pending/` branch in `decisions.py`.
- I did not adopt that as a blocking finding because this task's own research and scope define AC5 as a mocked integration scenario (`Board without decisions dir; function handles gracefully | Returns [] or skips`), while `decisions.py` internals are handled by task `#1180`/`#1181`.

### Deductions
- `-0.03` low module-level coverage on the monolithic `engine.py`; diff lines were verified manually instead.
- `-0.03` import-failure branch of the suppress wrapper is not directly exercised by this task's tests.
- Confidence: `0.94`

### Verdict
- PASS. The changed `pick_tasks` behavior is exercised by the task-owned suite, adjacent durable `pick_tasks` suites pass, and no weakening, security issue, or AC miss remains after reconciling the task scope with the research contract.

### Action
- Advanced to docs.
[[2026-04-30]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/kanban/README.md` L71: "four-step pipeline" → "five-step pipeline" with resolve step prepended |
| 2 | Module docstrings | Yes | Updated | `engine.py` `pick_tasks` docstring: "Runs a four-step pipeline" → "Runs a five-step pipeline", added step 1 (Resolve), renumbered 2–5 |
| 3 | External attribution | No | N/A | Task body: "5 high-relevance (all codebase/brief — no external sources needed)" |
| 4 | Research doc | Yes | Verified | `.owlbear/research/pick-tasks-resolve-integration-testing.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `kanban.excalidraw` (describes: `serve/kanban/src/**`) and `mcp-topology.excalidraw` (describes: `serve/kanban/src/**`) — both footers updated to `Last verified: 2026-04-30 (1745b261)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/src/owlbear_kanban/engine.py | IN (docstring) | Updated docstring |
| tests/test_pick_tasks_resolve_1184.py | OUT (test file) | N/A |
| .owlbear/research/pick-tasks-resolve-integration-testing.md | IN (research doc) | Verified — exists and linked |
| share/diagrams/kanban.excalidraw | IN (diagram) | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- serve/kanban/README.md — "four-step" → "five-step", resolve step added
- serve/kanban/src/owlbear_kanban/engine.py — pick_tasks docstring updated
- share/diagrams/kanban.excalidraw — footer: Last verified: 2026-04-30 (1745b261)
- share/diagrams/mcp-topology.excalidraw — footer: Last verified: 2026-04-30 (1745b261)

Commit: 92e522e1

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (`.owlbear/scratch/1184-*` — no matches)
[[2026-04-30]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| pick_tasks calls resolve_pending_drs before selection | engine.py:2326-2328 (importlib call before list_tasks at L2330); test_resolve_pending_drs_is_called PASS | PASS |
| Resolve exceptions do NOT propagate to caller | engine.py:2326 contextlib.suppress(Exception) wraps both import+call; test_resolve_exceptions_do_not_propagate PASS | PASS |
| Resolved DRs processed before task filtering | engine.py:2326-2330 (resolve call precedes list_tasks); test_resolve_runs_before_task_filtering side-effect ordering proof PASS | PASS |
| pick_tasks works with no pending DRs | test_no_pending_drs_pick_tasks_works PASS (empty-return path verified) | PASS |
| pick_tasks works when pending/ dir missing | test_no_decisions_directory_pick_tasks_works PASS (mocked graceful skip) | PASS |

### Test Results
- pytest (task-scoped): 32 passed, 0 failed (5 task-owned + 27 adjacent durable pick_tasks suites)
- pytest (full suite): 3251 passed, 75 failed (all failures in unrelated modules: coverage_1068 baseline, cockpit, knowledge)
- ruff (task scope): clean

### Reviewer Evidence
- Present and detailed: Pass 1 CRITICAL section with AC compliance table, security review, test integrity, test quality, gap analysis. PASS verdict at 0.94. Trusted.

### Commit Integrity
- 3a622c34 test-writer (RED)
- fc520d2b builder (GREEN)
- 92e522e1 doc-writer (docs)
All three commits verified via git log.

### Architect Quality: 4/5
AC lines specific and independently testable. Test-depth annotations present. Clear scope boundary (integration task vs. unit task #1180). Minor gap: import-failure scenario not explicitly called out as AC but adequately covered by suppress semantics.

### Deduction Breakdown
- AC lines without evidence: 0 (all 5 have test + code evidence)
- Lint violations in scope: 0
- AC quality <= 3: no (score 4)
- Missing reviewer evidence: no
- Full-suite failures in task scope: 0
- Import-failure branch lacks dedicated task-owned test: -0.02 (informational, suppress semantics cover it)

### Confidence: 0.98
### Action: archive