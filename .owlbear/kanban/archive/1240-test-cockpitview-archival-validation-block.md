---
id: 1240
title: 'Test: CockpitView archival validation block'
status: archived
priority: medium
created: 2026-05-01T03:07:52.852822+00:00
updated: 2026-05-01T08:08:18.348749+00:00
tags:
- scope:backend
parent: 1238
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `CockpitView.move_task` with `status="archived"` and `archival_reason=None` raises `ERR_ARCHIVAL_REASON_REQUIRED` (422)
- `CockpitView.move_task` with `reason="completed"` and non-empty `archival_refs` raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="dropped"` and non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="wontfix"` and non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="deprecated"` and empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED`
- `CockpitView.move_task` with `reason="duplicate"` and empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED`
- `CockpitView.move_task` with `reason="completed"` when `task.status != "done"` raises `ERR_COMPLETED_REQUIRES_DONE`
- `CockpitView.move_task` raises a 422 error when any ref ID does not exist on the board
- `CockpitView.move_task` raises a 422 error when `archival_refs` contains the task's own ID (self-reference)
- `CockpitView.move_task` raises a 422 error when `archival_refs` creates a dependency cycle
- Valid archival (e.g., `reason="completed"`, task `status == "done"`, empty refs) succeeds and persists both fields

## In Scope

- All validation paths in `CockpitView.move_task` for the `status == "archived"` case

## Out of Scope

- Non-archival moves (plain status changes)
- `MoveRequest`/route layer (B1+B2 task #1239)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B3
[[2026-05-01]]
## Test-Writer Notes
- Test file: tests/test_cockpit_view_1240.py
- Classes: TestFromAC_CockpitViewArchivalValidation
- Tests per category:
  - Error paths (validation rejects invalid input): 10
  - Happy path (AC11): SKIPPED — engine pass-through already satisfies valid archival; no RED test possible per w-tdd-red §5
- Total: 10 tests, all FAIL (DID NOT RAISE ValidationError)
- Lint: clean (ruff exit 0)

### AC coverage table

| AC line | Test method |
|---|---|
| AC1: reason=None → ERR_ARCHIVAL_REASON_REQUIRED | test_archive_without_reason_raises_archival_reason_required |
| AC2: completed + refs → ERR_ARCHIVAL_REFS_FORBIDDEN | test_archive_completed_with_refs_raises_archival_refs_forbidden |
| AC3: dropped + refs → ERR_ARCHIVAL_REFS_FORBIDDEN | test_archive_dropped_with_refs_raises_archival_refs_forbidden |
| AC4: wontfix + refs → ERR_ARCHIVAL_REFS_FORBIDDEN | test_archive_wontfix_with_refs_raises_archival_refs_forbidden |
| AC5: deprecated + empty refs → ERR_ARCHIVAL_REFS_REQUIRED | test_archive_deprecated_without_refs_raises_archival_refs_required |
| AC6: duplicate + empty refs → ERR_ARCHIVAL_REFS_REQUIRED | test_archive_duplicate_without_refs_raises_archival_refs_required |
| AC7: completed + task.status != done → ERR_COMPLETED_REQUIRES_DONE | test_archive_completed_from_non_done_status_raises_completed_requires_done |
| AC8: non-existent ref → ERR_ARCHIVAL_REF_MISSING | test_archive_with_nonexistent_ref_raises_archival_ref_missing |
| AC9: self-reference → ERR_ARCHIVAL_REF_SELF | test_archive_with_self_ref_raises_archival_ref_self |
| AC10: cycle → ERR_ARCHIVAL_REF_CYCLE | test_archive_with_cyclic_refs_raises_archival_ref_cycle |
| AC11: valid archival persists fields | SKIPPED — passes at RED (engine already handles) |

### Failure reason
All 10 tests fail with "DID NOT RAISE ValidationError" — CockpitView.move_task currently delegates directly to KanbanEngine.move_task with no validation block. The engine stores archival_reason/archival_refs unconditionally without any reason/refs/cycle checks.
[[2026-05-01]]
## Builder Notes
- Implementation: Added archival validation block in `serve/cockpit/src/owlbear_cockpit/view.py` for `CockpitView.move_task` when `status == "archived"`.
- Validation enforced: `ERR_ARCHIVAL_REASON_REQUIRED`, `ERR_ARCHIVAL_REASON_INVALID`, `ERR_ARCHIVAL_REFS_REQUIRED`, `ERR_ARCHIVAL_REFS_FORBIDDEN`, `ERR_COMPLETED_REQUIRES_DONE`, `ERR_ARCHIVAL_REF_MISSING`, `ERR_ARCHIVAL_REF_SELF`, `ERR_ARCHIVAL_REF_CYCLE`.
- Approach: Performed pre-validation in cockpit view before delegating to engine move, reusing same rule set as engine AgentView behavior while keeping OCC delegation unchanged.
- Files changed: `serve/cockpit/src/owlbear_cockpit/view.py`.
- Tests: `tests/test_cockpit_view_1240.py` -> 10 passed, 0 failed.
- Lint: ruff clean on touched source + task test file.
- Coverage: quality-runner reports `owlbear_cockpit` not tracked by current coverage source package config in scoped mode.
- Commit: `0f890cc5` (`feat: add cockpit archival validation block (#1240, builder)`).

## Post-task Reflection
- Private helper access (`engine.agent_view()._validate_move_archival_for_archive`) triggered `SLF001`; cockpit view now uses local equivalent helper methods.
- Canonical archival validation parity was preserved by mirroring engine rule order and error codes.
- Cycle detection and ref-existence checks were implemented using public `show_task` reads to avoid private API coupling.
- Coverage instrumentation for cockpit module is still not configured for module-level percentages in current scoped quality-runner output.

[[2026-05-01]]
## Review Evidence
### Changed Scope
- Builder commit confirmed in git log: `0f890cc5769ef63c257945e85c3660a0fb3defa5`.
- Builder-scoped source file from task body and live inspection: `serve/cockpit/src/owlbear_cockpit/view.py`.
- Task-owned suite reviewed: `tests/test_cockpit_view_1240.py`.
- First review failure: no prior `## Review Evidence` section exists in the task file.

### Test Results
- pytest: 10 passed, 0 failed (`quality-runner`, scoped to `tests/test_cockpit_view_1240.py`).

### Lint
- ruff: clean (`serve/cockpit/src/owlbear_cockpit/view.py`, `tests/test_cockpit_view_1240.py`).

### Coverage
- `owlbear_cockpit.view`: 46% overall (module-level only in scoped quality-runner output).
- Informational only: the module figure is not a direct gate, but the low value is consistent with the missing success-path proof described below.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1: `status="archived"` + `archival_reason=None` raises `ERR_ARCHIVAL_REASON_REQUIRED` | `test_archive_without_reason_raises_archival_reason_required` (`tests/test_cockpit_view_1240.py:126`, assert at `:140`) | Yes. `CockpitView` raises that code at `serve/cockpit/src/owlbear_cockpit/view.py:120`. | COVERED |
| AC2: `reason="completed"` + non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN` | `test_archive_completed_with_refs_raises_archival_refs_forbidden` (`tests/test_cockpit_view_1240.py:144`, assert at `:162`) | Yes. Forbidden-refs branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:140`. | COVERED |
| AC3: `reason="dropped"` + non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN` | `test_archive_dropped_with_refs_raises_archival_refs_forbidden` (`tests/test_cockpit_view_1240.py:164`, assert at `:181`) | Yes. Same branch at `serve/cockpit/src/owlbear_cockpit/view.py:140`. | COVERED |
| AC4: `reason="wontfix"` + non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN` | `test_archive_wontfix_with_refs_raises_archival_refs_forbidden` (`tests/test_cockpit_view_1240.py:183`, assert at `:200`) | Yes. Same branch at `serve/cockpit/src/owlbear_cockpit/view.py:140`. | COVERED |
| AC5: `reason="deprecated"` + empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED` | `test_archive_deprecated_without_refs_raises_archival_refs_required` (`tests/test_cockpit_view_1240.py:204`, assert at `:222`) | Yes. Required-refs branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:133`. | COVERED |
| AC6: `reason="duplicate"` + empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED` | `test_archive_duplicate_without_refs_raises_archival_refs_required` (`tests/test_cockpit_view_1240.py:224`, assert at `:242`) | Yes. Same branch at `serve/cockpit/src/owlbear_cockpit/view.py:133`. | COVERED |
| AC7: `reason="completed"` when task status is not `done` raises `ERR_COMPLETED_REQUIRES_DONE` | `test_archive_completed_from_non_done_status_raises_completed_requires_done` (`tests/test_cockpit_view_1240.py:246`, assert at `:264`) | Yes. Completed-from-non-terminal branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:147`. | COVERED |
| AC8: non-existent archival ref raises validation error | `test_archive_with_nonexistent_ref_raises_archival_ref_missing` (`tests/test_cockpit_view_1240.py:268`, assert at `:286`) | Yes. Missing-ref branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:160`. | COVERED |
| AC9: self-reference raises validation error | `test_archive_with_self_ref_raises_archival_ref_self` (`tests/test_cockpit_view_1240.py:290`, assert at `:308`) | Yes. Self-ref branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:153`. | COVERED |
| AC10: cycle raises validation error | `test_archive_with_cyclic_refs_raises_archival_ref_cycle` (`tests/test_cockpit_view_1240.py:312`, assert at `:350`) | Yes. Cycle branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:165`. | COVERED |
| AC11: valid archival on a `done` task with `reason="completed"` and empty refs succeeds and persists both fields | None. The task-owned suite explicitly marks AC11 `SKIPPED` in the file header (`tests/test_cockpit_view_1240.py:17-18`) and the `TestFromAC_CockpitViewArchivalValidation` class (`:121-350`) contains no success-path method. | No. If the valid-archival path regressed, this task-owned suite would stay green because it never asserts a successful cockpit move or persisted fields. | MISSING |

#### Security Review
- No hardcoded secrets, injection sinks, path traversal, unsafe deserialization, or new dependency surface in the changed scope.

#### Test Integrity
| Original Test Set | Change Made | Assessment |
|---|---|---|
| `TestFromAC_CockpitViewArchivalValidation` | No weakening detected from the live file versus the Test-Writer note inventory: the same 10 error-path methods are present under the same class, and builder notes scope changes to `serve/cockpit/src/owlbear_cockpit/view.py` only. | PRESERVED |

#### Test Quality
| Dimension | Status | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Each task-owned test asserts an exact `ValidationError.code` at `tests/test_cockpit_view_1240.py:140, :162, :181, :200, :222, :242, :264, :286, :308, :350`. |
| Negative / error-path coverage | STRONG | AC1-AC10 are all represented by task-owned rejecting-path tests. |
| Manual mutation reasoning | ADEQUATE | Flipping any of the existing validation branches would fail the mapped tests, but removing the valid-success delegate/persistence path would not be caught because AC11 is untested. |
| Test independence | ADEQUATE | Fixtures isolate the board per test, and the cycle case builds its own fresh board. |
| Descriptive names | STRONG | Each method names the exact archival rule under test. |

#### Data Safety
- No issue found in the changed scope. Validation is local and ref existence/cycle checks use read-only task lookups.

#### Implementation-Aware Test Gaps
- Significant untested path: the explicit success criterion for valid archival.
- `CockpitView.move_task()` validates archived moves and then delegates the success path to `self.engine.move_task(...)` at `serve/cockpit/src/owlbear_cockpit/view.py:245-255`.
- The engine persists both fields on archived moves at `serve/kanban/src/owlbear_kanban/engine.py:1131`, `:1136`, and `:1137`.
- But the task-owned cockpit suite never exercises that success path; AC11 is explicitly skipped at `tests/test_cockpit_view_1240.py:17-18`.
- Because AC11 is part of the binding task contract and brief (`.owlbear/briefs/draft-archival-ux/brief.md:188`), this is a blocking test gap.

#### Necessity Check
- Skip: no new dependency, integration, tool, or external capability.

#### Builder Process Quality
- CLEAN: one `## Builder Notes` section in the task body, no prior review section, no loop pattern.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:120`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:140`. | `test_archive_without_reason_raises_archival_reason_required` | PASS |
| AC2 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:140`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:162`. | `test_archive_completed_with_refs_raises_archival_refs_forbidden` | PASS |
| AC3 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:140`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:181`. | `test_archive_dropped_with_refs_raises_archival_refs_forbidden` | PASS |
| AC4 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:140`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:200`. | `test_archive_wontfix_with_refs_raises_archival_refs_forbidden` | PASS |
| AC5 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:133`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:222`. | `test_archive_deprecated_without_refs_raises_archival_refs_required` | PASS |
| AC6 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:133`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:242`. | `test_archive_duplicate_without_refs_raises_archival_refs_required` | PASS |
| AC7 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:147`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:264`. | `test_archive_completed_from_non_done_status_raises_completed_requires_done` | PASS |
| AC8 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:160`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:286`. | `test_archive_with_nonexistent_ref_raises_archival_ref_missing` | PASS |
| AC9 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:153`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:308`. | `test_archive_with_self_ref_raises_archival_ref_self` | PASS |
| AC10 | Validation branch exists at `serve/cockpit/src/owlbear_cockpit/view.py:165`; scoped pytest passed the exact-code assertion at `tests/test_cockpit_view_1240.py:350`. | `test_archive_with_cyclic_refs_raises_archival_ref_cycle` | PASS |
| AC11 | The live implementation appears to support the path (`serve/cockpit/src/owlbear_cockpit/view.py:245-255` delegates after validation; `serve/kanban/src/owlbear_kanban/engine.py:1131`, `:1136-1137` persist the fields), but the task-owned cockpit suite explicitly skips this AC at `tests/test_cockpit_view_1240.py:17-18` and contains no success-path test in `:121-350`. | None | FAIL |

### Deductions
- -0.12: AC11 is an explicit task and brief requirement, but the task-owned `TestFromAC_*` suite has no executable proof for it.
- -0.03: module-level coverage for `owlbear_cockpit.view` remains low and is directionally consistent with the missing success-path coverage, even though whole-module coverage is not the gate.

### Verdict
- FAIL -> `todo`
- Confidence: `0.85`
- Reason: test gap only. The cockpit implementation appears to cover the valid archival path, but the task-owned suite explicitly omits AC11, so the review gate cannot pass.

### Required Follow-up
- Add a task-owned cockpit success-path test for AC11 in `tests/test_cockpit_view_1240.py`.
- The test should call `CockpitView.move_task()` on a `done` task with `status="archived"`, `archival_reason="completed"`, and `archival_refs=[]`, then assert both the returned response and a fresh reload persist `archival_reason == "completed"` and `archival_refs == []`.
- Re-run scoped review evidence after that proof is added.

## Post-task Reflection
- Error-path-heavy task suites can still miss an explicit happy-path AC; review has to check the task-owned proof matrix, not just green counts.
- Module-level coverage is useful context but not a substitute for AC-bound assertions.
- Routing to `todo` is appropriate here because no implementation defect was demonstrated; the gap is missing executable proof.
[[2026-05-01]]
## Test-Writer Notes
- Retry: added 1 test for reviewer gap (AC11 success path).
- Test file: tests/test_cockpit_view_1240.py
- New method: `test_valid_archival_persists_reason_and_refs` — calls `CockpitView.move_task(1, "archived", archival_reason="completed", archival_refs=[])` on a done task; asserts `response.archival_reason == "completed"`, `response.archival_refs == []`; reloads via `engine.show_task("1")` and asserts both fields persisted.
- All 11 tests pass against current implementation (10 original error-path tests + 1 new success-path test).
- Builder skip: test-only retry, all tests green.
- Lint: ruff clean.
- Commit: a5298f2c
[[2026-05-01]]
## Builder Notes
- Scope: Test-only retry handoff from test-writer; no implementation changes required in this builder pass.
- Files changed in this pass: none.
- Validation status: Existing implementation in serve/cockpit/src/owlbear_cockpit/view.py already satisfies AC path exercised by retry test.
- Tests: quality-runner scoped run on tests/test_cockpit_view_1240.py -> 11 passed, 0 failed, 0 skipped.
- Lint: quality-runner ruff scoped to serve/cockpit/src/owlbear_cockpit/view.py and tests/test_cockpit_view_1240.py -> clean.
- Coverage: quality-runner report does not include owlbear_cockpit package in configured source packages; no task-local regression indicated.
- Evidence summary: AC11 success-path proof added by test-writer retry is now passing against current implementation; builder gate satisfied without additional code edits.

## Post-task Reflection
- Test-only retries after reviewer proof gaps can often pass straight through builder when implementation is already correct.
- Running a fresh scoped quality-runner check prevents stale assumptions from prior review cycles.
- Coverage package configuration gaps are orthogonal to task correctness but worth tracking separately.
[[2026-05-01]]
## Review Evidence
### Changed Scope
- Prior implementation commit confirmed in `.git/logs/refs/heads/dev:1156`: `0f890cc5769ef63c257945e85c3660a0fb3defa5`.
- Retry test commit confirmed in `.git/logs/refs/heads/dev:1177`: `a5298f2cb72eaeb9d1ae2cfe6643f3de8433cb58`.
- Live files reviewed: `serve/cockpit/src/owlbear_cockpit/view.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_cockpit_view_1240.py`, `.owlbear/briefs/draft-archival-ux/brief.md`.
- This is the second review pass. The prior review gap was AC11 proof; the retry added a task-owned success-path test at `tests/test_cockpit_view_1240.py:353-377`.

### Test Results
- `quality-runner` scoped run: 11 passed, 0 failed, 0 skipped for `tests/test_cockpit_view_1240.py`.

### Lint
- `quality-runner` scoped ruff on `serve/cockpit/src/owlbear_cockpit/view.py` and `tests/test_cockpit_view_1240.py`: clean.

### Coverage
- `quality-runner` reported no per-module coverage entry for `owlbear_cockpit.view`.
- Informational only: workspace coverage config in `pyproject.toml:153-164` tracks `owlbear`, `owlbear_kanban`, `owlbear_orchestrator`, `owlbear_knowledge`, `owlbear_mcp_*`, `owlbear_browser`, and `owlbear_tools`, but not `owlbear_cockpit`, so scoped cockpit percentages are suppressed.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1: archived with `archival_reason=None` raises `ERR_ARCHIVAL_REASON_REQUIRED` | `test_archive_without_reason_raises_archival_reason_required` at `tests/test_cockpit_view_1240.py:125` with exact code assertion at `:139` | Yes. Validation branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:120`. | COVERED |
| AC2: `completed` with non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN` | `test_archive_completed_with_refs_raises_archival_refs_forbidden` at `tests/test_cockpit_view_1240.py:143` with exact code assertion at `:161` | Yes. Forbidden-refs branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:140`. | COVERED |
| AC3: `dropped` with non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN` | `test_archive_dropped_with_refs_raises_archival_refs_forbidden` at `tests/test_cockpit_view_1240.py:163` with exact code assertion at `:180` | Yes. Same branch at `serve/cockpit/src/owlbear_cockpit/view.py:140`. | COVERED |
| AC4: `wontfix` with non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN` | `test_archive_wontfix_with_refs_raises_archival_refs_forbidden` at `tests/test_cockpit_view_1240.py:182` with exact code assertion at `:199` | Yes. Same branch at `serve/cockpit/src/owlbear_cockpit/view.py:140`. | COVERED |
| AC5: `deprecated` with empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED` | `test_archive_deprecated_without_refs_raises_archival_refs_required` at `tests/test_cockpit_view_1240.py:203` with exact code assertion at `:221` | Yes. Required-refs branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:133`. | COVERED |
| AC6: `duplicate` with empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED` | `test_archive_duplicate_without_refs_raises_archival_refs_required` at `tests/test_cockpit_view_1240.py:223` with exact code assertion at `:241` | Yes. Same branch at `serve/cockpit/src/owlbear_cockpit/view.py:133`. | COVERED |
| AC7: `completed` on non-`done` task raises `ERR_COMPLETED_REQUIRES_DONE` | `test_archive_completed_from_non_done_status_raises_completed_requires_done` at `tests/test_cockpit_view_1240.py:245` with exact code assertion at `:263` | Yes. Terminal-status gate raises at `serve/cockpit/src/owlbear_cockpit/view.py:147`. | COVERED |
| AC8: non-existent ref raises validation error | `test_archive_with_nonexistent_ref_raises_archival_ref_missing` at `tests/test_cockpit_view_1240.py:267` with exact code assertion at `:285` | Yes. Missing-ref branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:160`. | COVERED |
| AC9: self-reference raises validation error | `test_archive_with_self_ref_raises_archival_ref_self` at `tests/test_cockpit_view_1240.py:289` with exact code assertion at `:307` | Yes. Self-ref branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:153`. | COVERED |
| AC10: cycle raises validation error | `test_archive_with_cyclic_refs_raises_archival_ref_cycle` at `tests/test_cockpit_view_1240.py:311` with exact code assertion at `:349` | Yes. Cycle branch raises at `serve/cockpit/src/owlbear_cockpit/view.py:165`. | COVERED |
| AC11: valid archival succeeds and persists both fields | `test_valid_archival_persists_reason_and_refs` at `tests/test_cockpit_view_1240.py:353`; call at `:364`; exact response assertions at `:371-372`; reload assertions at `:375-377` | Yes. `CockpitView.move_task()` validates and delegates at `serve/cockpit/src/owlbear_cockpit/view.py:248-269`; engine persistence happens at `serve/kanban/src/owlbear_kanban/engine.py:1128-1132`; the test would fail on exception, wrong response fields, or wrong persisted fields. | COVERED |

#### Security Review
- No hardcoded secrets, injection sinks, path traversal, unsafe deserialization, or dependency additions in reviewed scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_CockpitViewArchivalValidation` at `tests/test_cockpit_view_1240.py:120` | Original AC1-AC10 exact-code assertions are still present at `tests/test_cockpit_view_1240.py:139, 161, 180, 199, 221, 241, 263, 285, 307, 349`. Retry adds AC11 success-path proof at `:353-377`. | STRENGTHENED |

#### Test Quality
| Dimension | Status | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Error-path tests assert exact `ValidationError.code`; AC11 asserts exact persisted values on both response and fresh reload. |
| Negative / error-path coverage | STRONG | AC1-AC10 each have their own rejecting-path test. |
| Manual mutation reasoning | STRONG | Flipping any guarded error code or removing success-path persistence would fail task-owned assertions. |
| Test independence | ADEQUATE | Fixtures create isolated boards; cycle case builds its own fresh board. |
| Descriptive names | STRONG | Method names map directly to archival rules and the success path. |

#### Data Safety
- No issue found. Validation performs read-only board lookups before delegation and does not widen mutation scope.

#### Implementation-Aware Test Gaps
- No blocking gap remains. The prior AC11 gap is closed by the retry test at `tests/test_cockpit_view_1240.py:353-377`.

#### Necessity Check
- Skip. No new dependency, integration, tool, or external capability.

#### Builder Process Quality
- CLEAN. One implementation pass plus one test-only retry confirmation; no repeated implementation loop and no weakened tests.

### Pass 2 - INFORMATIONAL
- Scoped cockpit coverage percentages remain unavailable until `owlbear_cockpit` is added to workspace `source_pkgs` or reviewed via explicit cockpit coverage instrumentation. This did not block AC proof here.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/src/owlbear_cockpit/view.py:120` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:139`. | `test_archive_without_reason_raises_archival_reason_required` | PASS |
| AC2 | `serve/cockpit/src/owlbear_cockpit/view.py:140` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:161`. | `test_archive_completed_with_refs_raises_archival_refs_forbidden` | PASS |
| AC3 | `serve/cockpit/src/owlbear_cockpit/view.py:140` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:180`. | `test_archive_dropped_with_refs_raises_archival_refs_forbidden` | PASS |
| AC4 | `serve/cockpit/src/owlbear_cockpit/view.py:140` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:199`. | `test_archive_wontfix_with_refs_raises_archival_refs_forbidden` | PASS |
| AC5 | `serve/cockpit/src/owlbear_cockpit/view.py:133` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:221`. | `test_archive_deprecated_without_refs_raises_archival_refs_required` | PASS |
| AC6 | `serve/cockpit/src/owlbear_cockpit/view.py:133` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:241`. | `test_archive_duplicate_without_refs_raises_archival_refs_required` | PASS |
| AC7 | `serve/cockpit/src/owlbear_cockpit/view.py:147` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:263`. | `test_archive_completed_from_non_done_status_raises_completed_requires_done` | PASS |
| AC8 | `serve/cockpit/src/owlbear_cockpit/view.py:160` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:285`. | `test_archive_with_nonexistent_ref_raises_archival_ref_missing` | PASS |
| AC9 | `serve/cockpit/src/owlbear_cockpit/view.py:153` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:307`. | `test_archive_with_self_ref_raises_archival_ref_self` | PASS |
| AC10 | `serve/cockpit/src/owlbear_cockpit/view.py:165` and passing exact-code assertion at `tests/test_cockpit_view_1240.py:349`. | `test_archive_with_cyclic_refs_raises_archival_ref_cycle` | PASS |
| AC11 | Brief authority at `.owlbear/briefs/draft-archival-ux/brief.md:186`; cockpit validation and delegation at `serve/cockpit/src/owlbear_cockpit/view.py:248-269`; engine persistence at `serve/kanban/src/owlbear_kanban/engine.py:1128-1132`; passing exact response and reload assertions at `tests/test_cockpit_view_1240.py:371-377`. | `test_valid_archival_persists_reason_and_refs` | PASS |

### Deductions
- -0.03: workspace coverage configuration still does not emit cockpit module percentages in scoped runs, so confidence rests on line-level AC proof plus green task-owned tests rather than a tracked cockpit coverage percentage.

### Verdict
- PASS. Advance to docs.
- Confidence: `0.95`
- Reason: the retry closed the only prior review gap, all 11 AC lines now have executable proof, and independent scoped test and lint checks are clean.

## Post-task Reflection
- A second review pass should re-check the exact prior gap first; here the AC11 proof was added cleanly without introducing new weakness.
- For cockpit review tasks, line-level AC evidence is more reliable than scoped coverage percentages until `owlbear_cockpit` is included in workspace coverage tracking.
- Test-only retries can pass review cleanly when the new proof is task-owned and strengthens the existing `TestFromAC_*` suite.
[[2026-05-01]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `CockpitView.move_task` validation is internal logic; cockpit README facade table lists the route but does not describe validation rules — no prose accuracy gap. |
| 2 | Module docstrings | Yes | Verified | All public methods in `serve/cockpit/src/owlbear_cockpit/view.py` have accurate docstrings: `list_tasks`, `show_task`, `edit_task`, `move_task`, `release_task`, `sweep`. Private helpers `_has_archival_cycle` and `_validate_move_archival_for_archive` are out of scope (private). |
| 3 | External attribution | No | N/A | No external patterns cited in task body or review evidence. |
| 4 | Research doc | No | N/A | No research doc produced or referenced. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/src/**`; footer updated from `c9ac7a5d` → `276c941d` (HEAD at gate time). Committed `bf303697`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/src/owlbear_cockpit/view.py` | IN (docstrings) | Verified — no updates needed |
| `tests/test_cockpit_view_1240.py` | OUT | N/A |
| `share/diagrams/cockpit.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer stamped `2026-05-01 (276c941d)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1240-*` files found)
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---|---|---|
| AC1: archived + reason=None raises ERR_ARCHIVAL_REASON_REQUIRED | view.py:120 + test assertion at test_cockpit_view_1240.py:139 | PASS |
| AC2: completed + refs raises ERR_ARCHIVAL_REFS_FORBIDDEN | view.py:140 + test assertion at :161 | PASS |
| AC3: dropped + refs raises ERR_ARCHIVAL_REFS_FORBIDDEN | view.py:140 + test assertion at :180 | PASS |
| AC4: wontfix + refs raises ERR_ARCHIVAL_REFS_FORBIDDEN | view.py:140 + test assertion at :199 | PASS |
| AC5: deprecated + empty refs raises ERR_ARCHIVAL_REFS_REQUIRED | view.py:133 + test assertion at :221 | PASS |
| AC6: duplicate + empty refs raises ERR_ARCHIVAL_REFS_REQUIRED | view.py:133 + test assertion at :241 | PASS |
| AC7: completed + not done raises ERR_COMPLETED_REQUIRES_DONE | view.py:147 + test assertion at :263 | PASS |
| AC8: non-existent ref raises validation error | view.py:160 + test assertion at :285 | PASS |
| AC9: self-reference raises validation error | view.py:153 + test assertion at :307 | PASS |
| AC10: cycle raises validation error | view.py:165 + test assertion at :349 | PASS |
| AC11: valid archival succeeds and persists | view.py:248-269 + engine:1128-1132 + test assertions at :371-377 | PASS |

### Test Results
- pytest (full suite): 3425 passed, 105 failed, 4 skipped. All 105 failures are outside task scope (engine, frontend build, E2E, timestamp tests). Task-owned suite: 11/11 passed.
- ruff (full): 4 violations, all outside task scope (knowledge, mcp-memory, orchestrator).

### Reviewer Evidence
Two review passes. First pass identified AC11 gap (confidence 0.85, FAIL). Retry added success-path test. Second pass: all 11 AC lines PASS, confidence 0.95. Detailed, thorough.

### Upstream Commits
- 2e707acb (builder, on dev; originally 0f890cc5, rebased by CI)
- a5298f2c (test-writer retry, AC11)
- bf303697 (doc-writer diagram footer)

### Architect Quality: 5/5
All 11 AC lines are specific with exact error codes, conditions, and reasons. Edge cases covered (self-ref, cycles, ref existence). Happy path AC11 explicitly included. Clean implementation path.

### Deduction Breakdown
- No deductions. All 11 AC lines have specific evidence. Lint clean in scope. Reviewer evidence present and detailed. No task-scope test failures. AC quality 5/5.

### Confidence: 1.00
### Action: archive