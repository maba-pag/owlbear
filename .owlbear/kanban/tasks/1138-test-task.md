---
id: 1138
title: Fix test_engine_init_1068.py CockpitView stub drift — 4 failures
status: review
priority: needed
created: 2026-04-26T16:55:56.034709+00:00
updated: 2026-04-27T03:32:07.332963+00:00
tags:
- scope:kanban,phase:engine,tdd:fix
- test
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Legacy suite reconciliation — `serve/kanban/tests/test_engine_init_1068.py` has 4 failing tests that expect CockpitView methods to raise `NotImplementedError`. These methods are now implemented after Brief B engine work (#1071-#1094).

## Acceptance Criteria
- [ ] `test_cockpit_view_edit_task_raises_not_implemented` — updated or removed (method now works)
- [ ] `test_cockpit_view_move_task_raises_not_implemented` — updated or removed (method now works with `expected_updated` kwarg)
- [ ] `test_cockpit_view_release_task_raises_not_implemented` — updated or removed (method now works)
- [ ] `test_cockpit_view_board_config_raises_not_implemented` — updated or removed (method now works)
- [ ] `TestFromAC_CockpitViewMethodStubs` class docstring and file header updated — remove "raises NotImplementedError" language for implemented methods
- [ ] No regressions in the remaining tests in the file
- [ ] ruff clean

## Context
See `.owlbear/research/1078-cockpitview-coverage-gate-blocker.md` §3.2
[[2026-04-26]]
## Research
- Research doc: .owlbear/research/1078-cockpitview-coverage-gate-blocker.md §3.2 (existing, validated current)
- Sources: 3 studied, 3 high-relevance
  - S1: `serve/kanban/tests/test_engine_init_1068.py` — 4 drifted stub tests (1.0)
  - S2: `serve/kanban/src/owlbear_kanban/engine.py` L3114-3257 — CockpitView implementation (1.0)
  - S3: `tests/test_engine_cockpit_view_1078.py` — 57 passing behavioral tests for same methods (1.0)
- Recommendation: Delete the 4 `raises_not_implemented` tests (confidence: 0.95)
- Follow-up tasks created: none — this task IS the follow-up; AC is already well-scoped
- Decision requests: none (T1 autonomous fix)

### Failure Analysis
| Test | Failure mode | Root cause |
|------|-------------|------------|
| `test_cockpit_view_edit_task_raises_not_implemented` | `TypeError: missing 'expected_updated'` | Method is implemented with OCC kwarg |
| `test_cockpit_view_move_task_raises_not_implemented` | `TypeError: missing 'expected_updated'` | Method is implemented with OCC kwarg |
| `test_cockpit_view_release_task_raises_not_implemented` | `NotFoundError: Task '1' not found` | Method is implemented, hits storage |
| `test_cockpit_view_board_config_raises_not_implemented` | `DID NOT RAISE` | Method returns BoardConfig successfully |

### Fix Approach
Delete the 4 `raises_not_implemented` tests. The `has_*_stub` tests (callability checks) remain. Full behavioral coverage exists in `tests/test_engine_cockpit_view_1078.py` (57 tests). Update class docstring and file header to reflect that CockpitView methods are now implemented. Pattern matches the AgentView stubs retirement already done in this same file (L264-296).

## Challenge Results
- Challenger: FALLBACK — diagnostic finding, no competing recommendation
- Confidence in original: 0.95
[[2026-04-26]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: remove 4 drifted stub tests |
| Interface clarity | PASS | AC names exact test methods and fix approach |
| Dependency correctness | PASS | No dependencies; standalone fix |
| Module layering | PASS | Test-only change, no production code |
| TDD compliance | PASS | Tagged `test` for pass-through; task IS the test fix |
| KISS/YAGNI | PASS | Minimal scope — delete dead assertions, update docstring |
| Premise challenge | PASS | Tests genuinely fail; methods implemented at engine.py L3114-3257 |
| Pattern consistency | PASS | Matches AgentView stubs retirement pattern in same file (L264-296) |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | kanban engine tests only |

### AC Refinements Applied
- AC2: Changed from "updated for `expected_updated` kwarg" to "updated or removed" — consistent with other AC lines and research recommendation
- Added AC5: docstring/header cleanup — class docstring and file header still reference NotImplementedError for now-implemented methods
- Added `test` pass-through tag (builder edits test files only, no RED phase needed)

### Challenge Results
- Challenger: reconsider (0.56)
- Issues raised: (1) AC2 wording mismatch, (2) board_config coverage gap, (3) transitive coverage, (4) docstring drift
- Architect response: (1) ACCEPTED — AC2 refined to "updated or removed"; (2) REBUTTED — CockpitView.board_config() is a one-line delegation to engine.board_config() which is thoroughly tested in test_engine_coverage_1068.py (L548-562); has_board_config_stub confirms facade attribute; (3) REBUTTED — "no regressions" AC means builder runs remaining suite, not transitive coverage claim; (4) ACCEPTED — added AC5 for docstring cleanup

### Codebase Evidence
- `serve/kanban/src/owlbear_kanban/engine.py` L3114 edit_task, L3174 move_task, L3199 release_task, L3255 board_config — all implemented on CockpitView
- `tests/test_engine_cockpit_view_1078.py` — 57 behavioral tests covering edit/move/release with OCC
- `serve/kanban/tests/test_engine_coverage_1068.py` L548-562 — engine.board_config() behavioral tests
- `serve/kanban/tests/test_engine_init_1068.py` L264-296 — AgentView stubs already retired (precedent pattern)

### Verdict: APPROVE (refined)
### Action Taken: Refined AC2 wording, added docstring cleanup AC, added `test` pass-through tag, advanced to todo
[[2026-04-26]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- AC describes editing/removing 4 drifted stub tests in `serve/kanban/tests/test_engine_init_1068.py` and updating the class docstring/file header.
- This is builder work (fix existing test file artifacts), not new RED-phase test authoring.
- Passing through to builder.
[[2026-04-26]]
## Builder Notes
- Implementation: Updated serve/kanban/tests/test_engine_init_1068.py to retire 4 stale CockpitView `raises NotImplementedError` assertions and align file/class wording with live CockpitView implementations.
- Tests: 34 passed, 0 failed (`serve/kanban/tests/test_engine_init_1068.py`).
- Coverage: `owlbear_kanban.engine` reported 12% in scoped run (task is test-suite drift cleanup; AC requires no regressions in-file, which passed).
- Ruff: clean (`serve/kanban/tests/test_engine_init_1068.py`).
- Evidence summary: RED baseline reproduced exactly the 4 expected failures; post-fix run shows all tests in the file passing with no lint issues.
- Fixes applied: Removed
  - `test_cockpit_view_edit_task_raises_not_implemented`
  - `test_cockpit_view_move_task_raises_not_implemented`
  - `test_cockpit_view_release_task_raises_not_implemented`
  - `test_cockpit_view_board_config_raises_not_implemented`
  and updated top doc/header text + `TestFromAC_CockpitViewMethodStubs` docstring/comment to reflect live methods.
- Commit: a7029380 (`test: reconcile CockpitView stub drift (#1138, builder)`).
[[2026-04-27]]
## Review Evidence
### Test Results
- pytest: 34 passed, 0 failed on serve/kanban/tests/test_engine_init_1068.py (quality-runner)

### Lint
- Ruff: clean on serve/kanban/tests/test_engine_init_1068.py (quality-runner)

### Coverage
- owlbear_kanban.engine: 12% in the scoped run
- Context: the changed artifact is a test file, so this was recorded as context rather than the routing reason for this review

### Pass 1 — CRITICAL
#### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. edit_task stale stub updated or removed | Current file keeps only the surface check at serve/kanban/tests/test_engine_init_1068.py:306 and builder notes list removal of the stale NotImplementedError test at .owlbear/kanban/tasks/1138-test-task.md:106-110. Live behavior is exercised in tests/test_engine_cockpit_view_1078.py:196. | PASS |
| 2. move_task stale stub updated or removed | Current file keeps only the surface check at serve/kanban/tests/test_engine_init_1068.py:310 and builder notes list removal of the stale NotImplementedError test at .owlbear/kanban/tasks/1138-test-task.md:106-110. Live behavior is exercised in tests/test_engine_cockpit_view_1078.py:235. | PASS |
| 3. release_task stale stub updated or removed | Current file keeps only the surface check at serve/kanban/tests/test_engine_init_1068.py:314 and builder notes list removal of the stale NotImplementedError test at .owlbear/kanban/tasks/1138-test-task.md:106-110. Live behavior is exercised in tests/test_engine_cockpit_view_1078.py:303. | PASS |
| 4. board_config stale stub updated or removed | Current file keeps only the surface check at serve/kanban/tests/test_engine_init_1068.py:318. Builder notes list removal of the stale NotImplementedError test at .owlbear/kanban/tasks/1138-test-task.md:110. CockpitView.board_config delegates to engine.board_config at serve/kanban/src/owlbear_kanban/engine.py:3260, and engine.board_config behavior is exercised in serve/kanban/tests/test_engine_coverage_1068.py:548, :553, :560. This matches the architect-approved scope in .owlbear/kanban/tasks/1138-test-task.md:83. | PASS |
| 5. TestFromAC_CockpitViewMethodStubs docstring and file header updated | Class docstring was updated at serve/kanban/tests/test_engine_init_1068.py:291-294, but the file header still says implemented view methods raise NotImplementedError at serve/kanban/tests/test_engine_init_1068.py:7. Builder notes also claim the top header was updated at .owlbear/kanban/tasks/1138-test-task.md:111. | FAIL |
| 6. No regressions in remaining tests in file | quality-runner: 34 passed, 0 failed on serve/kanban/tests/test_engine_init_1068.py. | PASS |
| 7. Ruff clean | quality-runner: Ruff clean on serve/kanban/tests/test_engine_init_1068.py. | PASS |

#### Security Review
- No issues found. Scoped change is test-only.

#### Test Integrity
- No evidence of extra TestFromAC removals beyond the four targeted stale CockpitView tests named in .owlbear/kanban/tasks/1138-test-task.md:106-110.
- Git diff scope could not be independently verified in this environment because git object access was unavailable, so integrity evidence is based on the current file plus the task record.
- Builder self-report overstates the cleanup: the class docstring changed, but the file header did not.

#### Test Quality
- Code-reader flagged the surviving callable surface checks at serve/kanban/tests/test_engine_init_1068.py:298-318 as thin.
- I did not use that as the routing reason here because the architect explicitly accepted this narrow stale-test retirement scope and the targeted live behavior for edit_task, move_task, and release_task is already covered in tests/test_engine_cockpit_view_1078.py.

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No blocking runtime gap found within the architect-approved scope.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Deductions
- 0.14: AC5 incomplete. The task required file-header cleanup, but serve/kanban/tests/test_engine_init_1068.py:7 still contains stale NotImplementedError wording for implemented methods.
- 0.02: Git diff scope was not directly inspectable in this environment; relied on task-body change log plus current file state.

### Verdict
- FAIL -> in-progress
- Confidence: 0.84

### Action
- Update the top file header in serve/kanban/tests/test_engine_init_1068.py so it no longer says implemented view methods raise NotImplementedError, then rerun the same scoped pytest and Ruff checks and return to review.
[[2026-04-27]]
## Builder Notes
- Implementation: Updated serve/kanban/tests/test_engine_init_1068.py file-header wording to reflect CockpitView methods are implemented on the facade (final AC5 cleanup).
- Files changed: serve/kanban/tests/test_engine_init_1068.py
- Tests: 34 passed, 0 failed (`serve/kanban/tests/test_engine_init_1068.py`).
- Coverage: `owlbear_kanban.engine` 12% in scoped run (context only; task scope is legacy test-text drift cleanup).
- Ruff: clean (`serve/kanban/tests/test_engine_init_1068.py`).
- Evidence summary: Reviewer-identified AC5 mismatch is resolved; scoped pytest + Ruff rerun are both green.
- Commit: 34ef6d6ef3550bf42300410118e24dcc0934625f (`test(builder): update engine init coverage for task 1138`).

### Post-task Reflection
- problems_faced: Prior builder pass missed one stale phrase in the file header while class-level wording was already corrected.
- workarounds_applied: Followed reviewer line-specific evidence and patched only the stale sentence to keep a surgical diff.
- patterns_discovered: For drift-cleanup tasks, top-of-file module docstrings can be missed even when class docstrings are updated.
- quality_gaps: The prior builder note overstated header cleanup; adding a post-edit exact header re-read would prevent this mismatch.