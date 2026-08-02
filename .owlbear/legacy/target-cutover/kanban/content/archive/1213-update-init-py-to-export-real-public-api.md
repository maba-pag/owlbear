---
id: 1213
title: Update __init__.py to export real public API
status: archived
priority: medium
created: 2026-04-30 15:29:15.233442+00:00
updated: 2026-05-03T23:10:24.219584+00:00
tags:
- audit-kanban
- api
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Update __init__.py to export the real public API surface from owlbear_kanban.

## Files
- serve/kanban/src/owlbear_kanban/__init__.py

## Change
Add AgentView, ValidationError, NotFoundError, ConcurrencyError, CorruptionError to __all__ with corresponding imports.

NOTE: CockpitView lives in owlbear_cockpit (serve/cockpit/), NOT in owlbear_kanban. It must NOT be re-exported here — that would create an upward dependency violation.

## AC
- [ ] __all__ adds exactly: AgentView, ValidationError, NotFoundError, ConcurrencyError, CorruptionError (td:1)
- [ ] `from owlbear_kanban import AgentView` resolves without error (td:1)
- [ ] `from owlbear_kanban import ValidationError, NotFoundError, ConcurrencyError, CorruptionError` resolves without error (td:1)
- [ ] No import of owlbear_cockpit or serve/cockpit in serve/kanban (td:1)
- [ ] Existing exports (KanbanEngine, WorkSession, Task, TaskSummary, BoardConfig, pick_dispatchable) unchanged (td:1)

## Finding: 3.4

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: export surface of one package |
| Interface clarity | PASS | Exact symbols enumerated in AC |
| Dependency correctness | PASS | Removed stale dep on deleted #1212; no remaining deps |
| Module layering | PASS | All exported symbols originate within serve/kanban/; CockpitView removed (lives in owlbear_cockpit) |
| TDD compliance | PASS | Test-writer will create import-assertion tests |
| KISS/YAGNI | PASS | Minimal change — add imports and __all__ entries |
| Premise challenge | PASS | Consumers currently use submodule imports (owlbear_kanban.errors.X); root-level re-export is standard Python API hygiene |
| Pattern consistency | PASS | Follows existing __init__.py pattern of explicit __all__ |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | kanban engine domain only |

### Challenge Results
- Challenger: SKIPPED — all td:1 (mechanical exports), low architectural risk
- Architect response: N/A

### Test Depth
- Max depth: 1
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Removed CockpitView (layering violation — belongs to owlbear_cockpit, not owlbear_kanban). Removed stale dependency on deleted #1212. Tightened AC to enumerate exact symbols and added guard AC against upward imports.

[[2026-05-03]]
Architecture review complete. Corrected layering violation (CockpitView belongs to owlbear_cockpit, not owlbear_kanban), removed stale dep #1212, tightened AC to enumerate exact export symbols. All criteria pass. Advancing to todo.
[[2026-05-03]]
## Test-Writer Notes
- Test file: `tests/test_init_exports_1213.py`
- Class: `TestFromAC_KanbanInitExports`
- Total: 12 tests, all FAIL (RED confirmed)
- Lint: clean (ruff exit 0)

### Tests by category
| Category | Count | Tests |
|----------|-------|-------|
| AC1 — new symbols in `__all__` | 6 | `test_agentview_in_dunder_all`, `test_validationerror_in_dunder_all`, `test_notfounderror_in_dunder_all`, `test_concurrencyerror_in_dunder_all`, `test_corruptionerror_in_dunder_all`, `test_dunder_all_new_additions_are_exactly_five_symbols` |
| AC2 — AgentView importable | 2 | `test_agentview_importable_from_root`, `test_agentview_is_a_class` |
| AC3 — error classes importable | 4 | `test_validationerror_importable_from_root`, `test_notfounderror_importable_from_root`, `test_concurrencyerror_importable_from_root`, `test_corruptionerror_importable_from_root` |

### AC Coverage
| AC line | Covered? | Notes |
|---------|----------|-------|
| AC1: `__all__` adds exactly the 5 new symbols | YES | 6 tests |
| AC2: `from owlbear_kanban import AgentView` resolves | YES | 2 tests |
| AC3: error classes importable from root | YES | 4 tests |
| AC4: no owlbear_cockpit import in serve/kanban | PRE-SATISFIED | grep confirms zero matches; no failing test possible — excluded per RED rule |
| AC5: existing exports unchanged | PRE-SATISFIED | `__all__` already has all 6 existing symbols; no failing test possible — regression guarded implicitly by `test_dunder_all_new_additions_are_exactly_five_symbols` |
[[2026-05-03]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/__init__.py to re-export `AgentView` (from `engine`) and `ValidationError`, `NotFoundError`, `ConcurrencyError`, `CorruptionError` (from `errors`), and added the same five symbols to `__all__`.
- Files changed: 1 source file (`serve/kanban/src/owlbear_kanban/__init__.py`).
- Tests: 12/12 `TestFromAC_KanbanInitExports` passed (`tests/test_init_exports_1213.py`).
- Coverage: touched module `owlbear_kanban.__init__` at 100% (6/6). Overall package coverage in scoped run is lower because only task-targeted tests were executed.
- ruff: clean for `serve/kanban/src/owlbear_kanban/` and `tests/test_init_exports_1213.py`.
- AC4 dependency guard: verified no `owlbear_cockpit`/`serve/cockpit` imports under `serve/kanban/src/**`.
- Commit: `7c6c010d` (`feat: export kanban root API symbols (#1213, builder)`).

## Post-task Reflection
- Problem faced: locating `AgentView` required confirming its defining module because there is no standalone `views.py`.
- Workaround applied: resolved via symbol search and imported `AgentView` directly from `owlbear_kanban.engine` to keep imports local and layered.
- Pattern discovered: `owlbear_kanban.errors` intentionally supports lazy `CorruptionError` resolution via module `__getattr__`, so root import from `errors` remains safe.
- Quality gap: AC4 wording says "in serve/kanban" broadly; practical enforcement for layering should target `serve/kanban/src/**` (tests may intentionally import cockpit views).
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped pytest: 12 passed, 0 failed, 0 skipped

### Lint
- quality-runner scoped ruff: clean

### Coverage
- `owlbear_kanban.__init__`: 100% (6 statements, 0 missed)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC1: `__all__` adds exactly AgentView, ValidationError, NotFoundError, ConcurrencyError, CorruptionError | `test_agentview_in_dunder_all`, `test_validationerror_in_dunder_all`, `test_notfounderror_in_dunder_all`, `test_concurrencyerror_in_dunder_all`, `test_corruptionerror_in_dunder_all`, `test_dunder_all_new_additions_are_exactly_five_symbols` | Yes | COVERED |
| AC2: `from owlbear_kanban import AgentView` resolves without error | `test_agentview_importable_from_root`, `test_agentview_is_a_class` | Yes for missing or broken root export | COVERED |
| AC3: `from owlbear_kanban import ValidationError, NotFoundError, ConcurrencyError, CorruptionError` resolves without error | `test_validationerror_importable_from_root`, `test_notfounderror_importable_from_root`, `test_concurrencyerror_importable_from_root`, `test_corruptionerror_importable_from_root` | Yes for missing or broken root exports | COVERED |
| AC4: No import of `owlbear_cockpit` or `serve/cockpit` in `serve/kanban` | none; test file header explicitly excludes AC4 as “pre-satisfied” | No | MISSING |
| AC5: Existing exports (`KanbanEngine`, `WorkSession`, `Task`, `TaskSummary`, `BoardConfig`, `pick_dispatchable`) unchanged | none; `test_dunder_all_new_additions_are_exactly_five_symbols` is the nearest check | No. That test computes `set(__all__) - existing`, so removing an existing export would still leave the assertion green. | MISSING |

#### Security Review
- No issues in the builder diff. Commit `7c6c010d` changes only `serve/kanban/src/owlbear_kanban/__init__.py` and adds local re-exports only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_KanbanInitExports` in `tests/test_init_exports_1213.py` | No builder changes. `git diff --name-only 7c6c010d~1 7c6c010d` shows only `serve/kanban/src/owlbear_kanban/__init__.py`. | PRESERVED |

#### Test Quality
- AC1 to AC3 assertions are adequate for the stated smoke-contract.
- AC4 and AC5 have no executable `TestFromAC` proof. The suite header marks both as pre-satisfied instead of enforcing them.

#### Data Safety
- No issues in this change.

#### Implementation-Aware Test Gap Analysis
- Current implementation is correct for the intended narrow change: `serve/kanban/src/owlbear_kanban/__init__.py` imports `AgentView` from `engine`, imports `ValidationError`, `NotFoundError`, `ConcurrencyError`, and `CorruptionError` from `errors`, and exports the five new names while retaining the prior symbols in `__all__`.
- AC4 is structurally defective as written. A repo search over the declared surface finds an existing cockpit import at `serve/kanban/tests/test_engine_pick_tasks_1074.py:18` (`from owlbear_cockpit.view import CockpitView`). So the literal AC text “No import ... in serve/kanban” is already false unless the architect narrows the contract to source code only.
- AC5 is not proven by the RED suite. The only set-based regression test checks the new additions only; it does not fail if an existing export disappears.

#### Builder Process Quality
- CLEAN. One builder cycle. No prior `## Review Evidence` sections found in the task file.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/__init__.py:19-30`; `tests/test_init_exports_1213.py:28-66`; quality-runner scoped pytest green | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/__init__.py:10`; `serve/kanban/src/owlbear_kanban/engine.py:1782`; `tests/test_init_exports_1213.py:70-80`; quality-runner scoped pytest green | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/__init__.py:11-16`; `serve/kanban/src/owlbear_kanban/errors.py:79-87`; `serve/kanban/src/owlbear_kanban/errors.py:103-105`; `tests/test_init_exports_1213.py:84-102`; quality-runner scoped pytest green | PASS |
| AC4 | `tests/test_init_exports_1213.py:9-10` explicitly excludes proof; repo search finds `serve/kanban/tests/test_engine_pick_tasks_1074.py:18` importing `owlbear_cockpit` | FAIL |
| AC5 | `tests/test_init_exports_1213.py:11-13` explicitly excludes proof; `tests/test_init_exports_1213.py:48-66` does not fail if an existing export is removed; current source still retains them at `serve/kanban/src/owlbear_kanban/__init__.py:21-30` | FAIL |

### Deductions
- AC4 contract wording is broader than the implementable source-layering requirement and is false on the current repo state.
- AC5 lacks executable regression proof.

### Verdict
- FAIL. Confidence: 0.82.

### Action
- Rejecting to backlog for architect rework. Refine AC4 to the intended surface explicitly, then require executable proof for AC4 and AC5 before the task returns to review.
[[2026-05-03]]

[[2026-05-04]]
## Architecture Re-Review (Cycle 2)

### Reason for return
Reviewer rejected: AC4 wording is broader than the intended layering constraint (test files legitimately import `owlbear_cockpit` for integration), and AC5 has no executable regression test.

### Refined AC
Replacing AC4 and AC5 with testable versions:

- AC4 (was): "No import of owlbear_cockpit or serve/cockpit in serve/kanban"
- AC4 (now): "No import of `owlbear_cockpit` in any `.py` file under `serve/kanban/src/` (test files excluded)" (td:1)
- AC5 (was): "Existing exports (KanbanEngine, WorkSession, Task, TaskSummary, BoardConfig, pick_dispatchable) unchanged"
- AC5 (now): "All 6 pre-existing symbols (`KanbanEngine`, `WorkSession`, `Task`, `TaskSummary`, `BoardConfig`, `pick_dispatchable`) remain in `__all__` and each resolves via `from owlbear_kanban import X` without error" (td:1)

### Evaluation
| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS — still one concern: export surface |
| Interface clarity | PASS — AC4/AC5 now testable with clear scope |
| TDD compliance | PASS — test-writer will add 2 missing proofs |
| KISS/YAGNI | PASS — no scope creep |

### Challenge Results
- Challenger: SKIPPED — mechanical AC refinement, no architectural change from approved design

### Test Depth
- All lines td:1 (unchanged)
- Test-writer: PROCEED (add tests for refined AC4 and AC5 only; AC1-AC3 tests already pass)

### Verdict: APPROVE
Refined AC4 and AC5 to be testable. Implementation already correct per commit `7c6c010d`. Test-writer needs to add executable proof for the two refined lines.
[[2026-05-03]]
Architecture re-review complete (cycle 2). Refined AC4 scope to `serve/kanban/src/` only (excluding test files) and AC5 to require explicit per-symbol import verification. Implementation unchanged — test-writer needs to add 2 missing executable proofs for the refined AC lines.
[[2026-05-03]]
## Test-Writer Notes
- Retry: added 13 tests for reviewer-cited AC4 and AC5 gaps. All 25 tests pass against current impl.
- Builder skip: test-only retry, all tests green.

### Test file
`tests/test_init_exports_1213.py` — class `TestFromAC_KanbanInitExports`

### New tests added (13)
| Category | Count | Tests |
|----------|-------|-------|
| AC4 — no cockpit import in src | 1 | `test_no_owlbear_cockpit_import_in_src` |
| AC5 — existing symbols in `__all__` | 6 | `test_kanbanengine_in_dunder_all`, `test_worksession_in_dunder_all`, `test_task_in_dunder_all`, `test_tasksummary_in_dunder_all`, `test_boardconfig_in_dunder_all`, `test_pick_dispatchable_in_dunder_all` |
| AC5 — existing symbols importable | 6 | `test_kanbanengine_importable_from_root`, `test_worksession_importable_from_root`, `test_task_importable_from_root`, `test_tasksummary_importable_from_root`, `test_boardconfig_importable_from_root`, `test_pick_dispatchable_importable_from_root` |

### Run result
- pytest: 25 passed, 0 failed (all 25 green — implementation already satisfies refined AC4 and AC5)
- ruff: clean (exit 0)

### AC Coverage (full)
| AC line | Covered? | Notes |
|---------|----------|-------|
| AC1: `__all__` adds exactly the 5 new symbols | YES | 6 tests (unchanged) |
| AC2: `from owlbear_kanban import AgentView` resolves | YES | 2 tests (unchanged) |
| AC3: error classes importable from root | YES | 4 tests (unchanged) |
| AC4 (refined): no `owlbear_cockpit` in `serve/kanban/src/` | YES | 1 new test — walks src/ via rglob |
| AC5 (refined): all 6 pre-existing symbols in `__all__` and importable | YES | 12 new tests — per-symbol `__all__` + importability |

### Direct-to-review rationale
Reviewer Required Follow-up was test-proof gaps only; implementation unchanged since commit `7c6c010d`. All new tests pass. No builder work needed.
[[2026-05-03]]
## Builder Notes
- Implementation status: no additional source edits required in this cycle; existing implementation in `serve/kanban/src/owlbear_kanban/__init__.py` already satisfies refined AC1-AC5.
- Tests: 25/25 passed in scoped run (`tests/test_init_exports_1213.py`), 0 failed, 0 skipped.
- Coverage: `owlbear_kanban.__init__` at 100% in scoped verification.
- Lint: ruff clean for `serve/kanban/src/owlbear_kanban/` and `tests/test_init_exports_1213.py`.
- Evidence summary: quality-runner scoped gate confirms refined AC4/AC5 proofs are now executable and green.

## Post-task Reflection
- Problem faced: task had prior implementation and prior review-loop history, so this cycle required gate confirmation rather than new code.
- Workaround applied: used a fresh quality-runner scoped pass to produce canonical evidence under current task state.
- Pattern discovered: builder-skip on test-only retry is valid when reviewer follow-up is proof-only and green is reconfirmed.
- Quality gap: none found in scoped task targets for this cycle.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped pytest: 25 passed, 0 failed, 0 skipped on current workspace state

### Lint
- quality-runner scoped ruff: clean

### Coverage
- `owlbear_kanban.__init__`: 100%
- overall scoped run: 16% (task-scoped run; informational only)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC1: `__all__` adds exactly AgentView, ValidationError, NotFoundError, ConcurrencyError, CorruptionError | `test_agentview_in_dunder_all`, `test_validationerror_in_dunder_all`, `test_notfounderror_in_dunder_all`, `test_concurrencyerror_in_dunder_all`, `test_corruptionerror_in_dunder_all`, `test_dunder_all_new_additions_are_exactly_five_symbols` | Yes | COVERED (local only) |
| AC2: `from owlbear_kanban import AgentView` resolves without error | `test_agentview_importable_from_root`, `test_agentview_is_a_class` | Yes | COVERED (local only) |
| AC3: `from owlbear_kanban import ValidationError, NotFoundError, ConcurrencyError, CorruptionError` resolves without error | `test_validationerror_importable_from_root`, `test_notfounderror_importable_from_root`, `test_concurrencyerror_importable_from_root`, `test_corruptionerror_importable_from_root` | Yes | COVERED (local only) |
| AC4 (refined): no `owlbear_cockpit` import under `serve/kanban/src/` | `test_no_owlbear_cockpit_import_in_src` | Yes | COVERED (local only) |
| AC5 (refined): all 6 pre-existing symbols remain in `__all__` and resolve from root | `test_kanbanengine_in_dunder_all`, `test_worksession_in_dunder_all`, `test_task_in_dunder_all`, `test_tasksummary_in_dunder_all`, `test_boardconfig_in_dunder_all`, `test_pick_dispatchable_in_dunder_all`, plus the six `*_importable_from_root` tests | Yes | COVERED (local only) |

#### Security Review
- No security issues in the committed source. `serve/kanban/src/owlbear_kanban/__init__.py:9-30` imports only local kanban symbols and exposes the intended names.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_KanbanInitExports` retry suite in `tests/test_init_exports_1213.py` | Retry added AC4/AC5 proof locally, but the file is not committed: `git status --porcelain -- tests/test_init_exports_1213.py` returns `?? tests/test_init_exports_1213.py`; `git ls-files --error-unmatch tests/test_init_exports_1213.py` fails; `git log -- tests/test_init_exports_1213.py` returns no commits; `git diff --name-status 7c6c010d..HEAD -- tests/test_init_exports_1213.py serve/kanban/src/owlbear_kanban/__init__.py` is empty. | FAIL — the green scoped run proves only local workspace state, not the repo deliverable. |

#### Test Quality
- The local retry assertions are adequate for the refined AC: `tests/test_init_exports_1213.py:108-116` enforces the src-only cockpit-import ban and `tests/test_init_exports_1213.py:120-174` enforces retention/importability of the six existing exports.
- Review cannot accept those proofs because the task-local `TestFromAC` file is absent from HEAD.

#### Data Safety
- No issues.

#### Implementation-Aware Test Gap Analysis
- Current committed source satisfies the refined contract: `serve/kanban/src/owlbear_kanban/__init__.py:9-30` re-exports the five new symbols and retains the six pre-existing symbols in `__all__`.
- A scoped search over `serve/kanban/src/**/*.py` found no `owlbear_cockpit` or `serve/cockpit` matches, so refined AC4 holds in the current workspace.
- The blocking issue is deliverable integrity, not implementation behavior.

#### Builder Process Quality
- FAIL (loop-breaker). The task markdown already contains one prior `## Review Evidence` section at `.owlbear/kanban/tasks/1213-update-init-py-to-export-real-public-api.md:106`, so this is the second review cycle. The retry still advanced to review without committing the new task test artifact, violating the commit gate on a repeat cycle.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/__init__.py:19-30`; local task tests at `tests/test_init_exports_1213.py:30-68`; quality-runner green | PASS (workspace) |
| AC2 | `serve/kanban/src/owlbear_kanban/__init__.py:10`; local task tests at `tests/test_init_exports_1213.py:72-82`; quality-runner green | PASS (workspace) |
| AC3 | `serve/kanban/src/owlbear_kanban/__init__.py:11-16`; local task tests at `tests/test_init_exports_1213.py:86-104`; quality-runner green | PASS (workspace) |
| AC4 (refined) | scoped search over `serve/kanban/src/**/*.py` found no `owlbear_cockpit` matches; local task test at `tests/test_init_exports_1213.py:108-116`; quality-runner green | PASS (workspace) |
| AC5 (refined) | `serve/kanban/src/owlbear_kanban/__init__.py:19-30`; local task tests at `tests/test_init_exports_1213.py:120-174`; quality-runner green | PASS (workspace) |

### Deductions
- `tests/test_init_exports_1213.py` is untracked and absent from HEAD, so the scoped green run is not reviewable deliverable evidence.
- This is the second review cycle, so the repeat failure routes to `backlog` under the loop-breaker rule.

### Verdict
- FAIL. Confidence: 0.79.

### Action
- Rejecting to `backlog`. The next cycle must commit the task test file before advancing, then rerun the scoped gate.
[[2026-05-03]]
## Architecture Review (Cycle 3)

### Reason for return
Reviewer rejected cycle 2: implementation and tests are correct but `tests/test_init_exports_1213.py` was never committed — untracked file, absent from HEAD. Process failure, not architectural.

### Evaluation
AC1-AC5 (refined) remain sound. No architectural change needed. Implementation at commit `7c6c010d` is correct. Test suite (25 tests) exists locally and passes.

### Action Required
**Builder must commit the existing test file** `tests/test_init_exports_1213.py` alongside any needed source verification. This is the ONLY remaining gap.

### Test Depth
- All lines td:1 (unchanged)
- Test-writer: SKIP — tests already written and green (`tests/test_init_exports_1213.py`, 25 tests)
- Builder: commit the untracked test file, run scoped gate, confirm HEAD contains both source and test artifacts

### Challenge Results
- Challenger: SKIPPED — no architectural change from prior approved design; process-only fix

### Verdict: APPROVE
[[2026-05-03]]
## Test-Writer Notes
- Retry cycle (Cycle 3): test file `tests/test_init_exports_1213.py` already contains 25 tests covering all AC lines (AC1–AC5 refined), all passing.
- Reviewer blocker was uncommitted test file (process failure), not missing coverage.
- No new tests added — all AC gaps filled in prior retry; tests clean against current impl.
- Passing through to builder: commit `tests/test_init_exports_1213.py`, run scoped gate, confirm HEAD contains both source and test artifacts.

### Run result
- pytest: 25 passed, 0 failed (all green — implementation satisfies refined AC4 and AC5)
- ruff: clean (exit 0)
- File status: `?? tests/test_init_exports_1213.py` (untracked — builder must `git add` and commit)
[[2026-05-03]]
## Builder Notes
- Implementation: no source changes required in this cycle; existing implementation in serve/kanban/src/owlbear_kanban/__init__.py already satisfied AC1-AC5.
- Commit fix applied: added and committed missing task test artifact tests/test_init_exports_1213.py (commit 587e4487).
- Tests: 25 passed, 0 failed, 0 skipped (scoped pytest on tests/test_init_exports_1213.py).
- Coverage: owlbear_kanban.__init__ at 100% in scoped run.
- ruff: clean for serve/kanban/src/owlbear_kanban/ and tests/test_init_exports_1213.py.
- Evidence summary: reviewer blocker was untracked test file; this cycle resolves deliverable-integrity by committing exactly that file and re-verifying scoped quality gate.

## Post-task Reflection
- Problem faced: repeated review loop was process-only (artifact tracking), not behavior.
- Workaround applied: enforced single-file staging check before commit to prevent unrelated index bleed.
- Pattern discovered: in retry cycles, deliverable integrity (tracked/committed tests) must be explicitly re-verified even when runtime quality is green.
- Quality gap: none found in task-scoped source/tests after commit.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped pytest: 25 passed, 0 failed, 0 skipped on `tests/test_init_exports_1213.py`

### Lint
- quality-runner scoped ruff: clean for `serve/kanban/src/owlbear_kanban/` and `tests/test_init_exports_1213.py`
- editor diagnostics: no errors in `serve/kanban/src/owlbear_kanban/__init__.py` or `tests/test_init_exports_1213.py`

### Coverage
- `owlbear_kanban.__init__`: 100% (6 statements, 0 missed)
- overall scoped run: 16% (informational only; diff-scoped gate is satisfied by the touched module)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC1: `__all__` adds exactly `AgentView`, `ValidationError`, `NotFoundError`, `ConcurrencyError`, `CorruptionError` | `test_agentview_in_dunder_all`, `test_validationerror_in_dunder_all`, `test_notfounderror_in_dunder_all`, `test_concurrencyerror_in_dunder_all`, `test_corruptionerror_in_dunder_all`, `test_dunder_all_new_additions_are_exactly_five_symbols` | Yes. Removing any named addition or adding an unexpected new export changes the asserted set. | COVERED |
| AC2: `from owlbear_kanban import AgentView` resolves without error | `test_agentview_importable_from_root`, `test_agentview_is_a_class` | Yes for a missing or broken root export; td:1 smoke proof is adequate for the literal import-resolution contract. | COVERED |
| AC3: `from owlbear_kanban import ValidationError, NotFoundError, ConcurrencyError, CorruptionError` resolves without error | `test_validationerror_importable_from_root`, `test_notfounderror_importable_from_root`, `test_concurrencyerror_importable_from_root`, `test_corruptionerror_importable_from_root` | Yes for missing or broken root exports; td:1 smoke proof is adequate for the literal import-resolution contract. | COVERED |
| AC4 (refined): no import of `owlbear_cockpit` in any `.py` file under `serve/kanban/src/` | `test_no_owlbear_cockpit_import_in_src` | Yes. Any occurrence under `serve/kanban/src/**/*.py` populates `violations` and fails the test. | COVERED |
| AC5 (refined): all 6 pre-existing symbols remain in `__all__` and each resolves from package root | `test_kanbanengine_in_dunder_all`, `test_worksession_in_dunder_all`, `test_task_in_dunder_all`, `test_tasksummary_in_dunder_all`, `test_boardconfig_in_dunder_all`, `test_pick_dispatchable_in_dunder_all`, and the six `*_importable_from_root` tests | Yes. Removing any retained export or breaking its root binding fails the matching membership/importability assertion. | COVERED |

#### Security Review
- No issues. The committed source surface is limited to local imports and `__all__` wiring in `serve/kanban/src/owlbear_kanban/__init__.py:9-30`.
- Direct search over `serve/kanban/src/**/*.py` found no `owlbear_cockpit` or `serve/cockpit` matches.
- No new dependencies, secrets, shell execution, deserialization, or boundary validation changes were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_KanbanInitExports` in `tests/test_init_exports_1213.py` | Commit `7c6c010d` changes only `serve/kanban/src/owlbear_kanban/__init__.py`. Commit `587e4487` adds only `tests/test_init_exports_1213.py`, which is now tracked in HEAD. The committed file contains the same 25 tests named in the preceding Test-Writer Notes for AC1-AC5. | PRESERVED |

#### Test Quality
- STRONG for AC1 and AC5: exact membership checks plus per-symbol root-resolution checks would fail on missing exports.
- ADEQUATE for AC2 and AC3: the assertions target the literal td:1 smoke contract of root-level resolution without error.
- ADEQUATE for AC4: the scan test is stricter than a pure import-AST check but not false-green, and the independent repo search is also clean.
- No WEAK dimensions found. Negative-path coverage is not materially applicable to this static export task.

#### Data Safety
- No issues. The change is static import/export wiring only.

#### Implementation-Aware Test Gap Analysis
- No significant untested paths remain in the touched code. `serve/kanban/src/owlbear_kanban/__init__.py:9-30` contains only import wiring and the exported symbol list.
- `AgentView` is defined at `serve/kanban/src/owlbear_kanban/engine.py:1782` and is re-exported from `__init__.py:10`.
- `ValidationError`, `NotFoundError`, and `ConcurrencyError` are defined at `serve/kanban/src/owlbear_kanban/errors.py:79`, `:83`, and `:87` and re-exported from `__init__.py:11-16`.
- `CorruptionError` is surfaced through `serve/kanban/src/owlbear_kanban/errors.py:103` and resolves to `serve/kanban/src/owlbear_kanban/corruption.py:83`; the green import tests prove the root re-export works in the current snapshot.

#### Necessity Check
- Skipped. No new dependency, integration, tool, or external capability was added.

#### Builder Process Quality
- FRICTION, resolved. Prior review sections exist in this task, but the retry path varied approach (initial source implementation, test-proof retry, then artifact-commit fix) and the current cycle closes the specific deliverable-integrity gap previously noted by committing `tests/test_init_exports_1213.py` in `587e4487`.
- Not a LOOP: the earlier failures were corrected with a distinct process fix and the current deliverable is now reviewable from HEAD.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/__init__.py:19-30`; `tests/test_init_exports_1213.py:30-68`; quality-runner pytest green | AC1 symbol-membership and exact-addition tests | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/__init__.py:10`; `serve/kanban/src/owlbear_kanban/engine.py:1782`; `tests/test_init_exports_1213.py:72-82`; quality-runner pytest green | `test_agentview_importable_from_root`, `test_agentview_is_a_class` | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/__init__.py:11-16`; `serve/kanban/src/owlbear_kanban/errors.py:79-87`; `serve/kanban/src/owlbear_kanban/errors.py:103`; `serve/kanban/src/owlbear_kanban/corruption.py:83`; `tests/test_init_exports_1213.py:86-104`; quality-runner pytest green | four `*_importable_from_root` tests | PASS |
| AC4 (refined) | `tests/test_init_exports_1213.py:108-116`; direct search over `serve/kanban/src/**/*.py` found no matches for `owlbear_cockpit|serve/cockpit`; quality-runner pytest green | `test_no_owlbear_cockpit_import_in_src` | PASS |
| AC5 (refined) | `serve/kanban/src/owlbear_kanban/__init__.py:19-30`; `tests/test_init_exports_1213.py:120-174`; quality-runner pytest green | six `*_in_dunder_all` tests plus six `*_importable_from_root` tests | PASS |

### Deductions
- Small confidence deduction: TestFromAC immutability for the committed test artifact is reconstructed from commit ownership plus the prior test-writer handoff, because the committed baseline for `tests/test_init_exports_1213.py` begins only in this cycle.

### Verdict
- PASS. Confidence: 0.95.

### Action
- Advancing to docs.

## Review Reflection
- Problem faced: the current green snapshot spans two builder commits, so ownership had to be reconstructed across both `7c6c010d` and `587e4487` before trusting the scoped run.
- Workaround applied: verified HEAD contains both deliverables with `git show --name-only` on both commits and `git ls-files --error-unmatch tests/test_init_exports_1213.py`.
- Pattern discovered: a test-only retry is passable once the task test artifact is actually committed; prior local-green evidence alone is not reviewable deliverable proof.
- Quality gap: no remaining AC or deliverable-integrity gaps found in the current snapshot.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | serve/kanban/README.md import example is illustrative (not exhaustive); does not enumerate __all__ — no update needed |
| 2 | Module docstrings | Yes | Updated | __init__.py docstring now includes "error classes" — commit 4b7c06db |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research phase |
| 5 | Diagram maintenance (describes match) | Yes | Updated | kanban.excalidraw and mcp-topology.excalidraw both match serve/kanban/src/**; footers updated to 2026-05-04 (587e4487) — commit 4b7c06db |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/src/owlbear_kanban/__init__.py | IN (docstrings) | Updated docstring |
| tests/test_init_exports_1213.py | OUT (test file) | N/A |
| share/diagrams/kanban.excalidraw | IN (diagram) | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- serve/kanban/src/owlbear_kanban/__init__.py (docstring: added "error classes")
- share/diagrams/kanban.excalidraw (footer: 2026-05-04 (587e4487))
- share/diagrams/mcp-topology.excalidraw (footer: 2026-05-04 (587e4487))

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1213-* scratch files found)
[[2026-05-03]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: __all__ adds exactly 5 new symbols | serve/kanban/src/owlbear_kanban/__init__.py:19-30 (direct read); 25/25 tests green | PASS |
| AC2: AgentView importable from root | __init__.py:10 imports from engine; test_agentview_importable_from_root green | PASS |
| AC3: Error classes importable from root | __init__.py:11-16 imports from errors; 4 importability tests green | PASS |
| AC4 (refined): No owlbear_cockpit in serve/kanban/src/ | test_no_owlbear_cockpit_import_in_src green; reviewer confirmed clean search | PASS |
| AC5 (refined): 6 pre-existing symbols remain in __all__ and importable | __init__.py:19-30 retains all 6; 12 new tests green | PASS |

### Test Results
- pytest full suite: 772 passed, 20 failed (all failures in unrelated tasks: 1234, 1195, 1015), 4 skipped. Zero failures in task scope.
- vitest full suite: 13 failures (tasks 966, 1278 context issues). Zero in task scope.
- ruff: 1 T201 violation outside task scope
- eslint: 1 config issue outside task scope

### Architect Quality: 3/5
Original AC4 and AC5 were too broad/untestable, causing 2 reviewer bounces. Architect self-corrected effectively in cycle 2 re-review with properly scoped, testable refinements.

### Deduction Breakdown
- Start: 1.00
- AC quality score 3 (less than or equal to 3): -0.03
- No AC lines without evidence: -0.00
- No task-scope lint violations: -0.00
- No task-scope test failures: -0.00
- Reviewer evidence present and detailed: -0.00

### Confidence: 0.97
### Action: Archive