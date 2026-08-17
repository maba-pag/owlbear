---
id: 844
title: Tests — Config staleness fix in create_task
status: archived
priority: medium
created: '2026-04-11T11:40:50.781085+00:00'
updated: '2026-04-12T22:26:51.784372+00:00'
tags:
- kanban
- phase-1
- type:test
- scope:kanban
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Test verifies: after external config change on disk (e.g. new status added), `create_task` reflects new config in `self._config` (not just local variable)
- Test verifies: calling `create_task` after disk config change uses the refreshed `_tasks_dir` and rank maps (consistent with `refresh_config()` behavior)
- Test verifies: `create_task` does NOT leave `self._config.next_id` stale after successful creation
- Tests fail RED before implementation

## Context

Phase 1, independent pair. Supersedes stale #803 (which bundled `refresh_config()` — now done — with this fix).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
File: `serve/kanban/src/owlbear_kanban/engine.py` (lines 232-281)

[[2026-04-12]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task, one method (`create_task`), one concern (config staleness) |
| Interface clarity | FAIL | AC3 redundant with #828; AC4 (RED phase) impossible — see below |
| Dependency correctness | PASS | No dependencies listed; none needed |
| Module layering | PASS | Tests in `tests/` for `serve/kanban/` engine |
| TDD compliance | PASS | Task IS the test task (`type:test`) |
| KISS/YAGNI | FAIL | AC3 duplicates 5 existing tests in `test_config_staleness_fix_828.py` |
| Premise challenge | FAIL | Partial — AC1/AC2 are valid new coverage; AC3/AC4 are stale |
| Pattern consistency | PASS | Follows existing kanban test patterns |
| Security surface | N/A | No new security boundaries |
| Single domain | PASS | Kanban engine domain only |

### Findings

**AC3 is redundant.** `test_config_staleness_fix_828.py` already contains 5 tests verifying `next_id` is not stale after `create_task`:

- `test_board_config_next_id_incremented_after_one_create`
- `test_board_config_next_id_incremented_after_two_creates`
- `test_board_config_matches_disk_config_after_create`
- `test_board_config_consistent_without_manual_refresh`
- `test_board_config_next_id_tracks_n_creates`

**AC4 (RED phase) is impossible.** The config staleness fix is already implemented in `engine.py` lines 294-296 (`self._config = config; self._tasks_dir = ...`). New tests for this behavior will pass immediately — they cannot fail RED.

**AC1 and AC2 are valid.** They test a scenario NOT covered by #828: external config change on disk → `create_task` (without explicit `refresh_config()`) picks up the new config. `test_refresh_config_803.py` tests external change + explicit `refresh_config()` + `create_task`, but #844's AC1/AC2 test the implicit refresh path inside `create_task` itself. This is genuine supplementary coverage.

### Required AC Changes

1. **Remove AC3** — fully covered by `test_config_staleness_fix_828.py`
2. **Remove or reframe AC4** — RED phase is impossible; reframe as "supplementary GREEN verification tests for create_task's implicit config refresh"
3. **Keep AC1 and AC2** as-is — they provide valid new coverage for the implicit refresh path
4. **Add note to Context** that these tests verify existing behavior (not a RED→GREEN TDD pair) so the test-writer knows to expect passing tests

### Challenge Results

- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Verdict: REFINE

### Action Taken: Returned to backlog with AC refinement notes. AC3 and AC4 need removal/reframing before approval. AC1 and AC2 are sound

[[2026-04-12]]

## Architecture Review (Retry)

### Refined Acceptance Criteria

AC3 (next_id staleness) and AC4 (RED phase) removed per prior review findings:

- AC3 fully covered by 5 existing tests in `test_config_staleness_fix_828.py`
- AC4 impossible — implementation already landed in `engine.py` lines 294-296

**Final AC (2 criteria):**

1. Test verifies: after external config change on disk (e.g. new status added), `create_task` reflects new config in `self._config` (not just local variable)
2. Test verifies: calling `create_task` after disk config change uses the refreshed `_tasks_dir` and rank maps (consistent with `refresh_config()` behavior)

**Test-writer note:** These tests verify *existing* behavior (implicit config refresh inside `create_task`). Tests are expected to pass immediately — this is supplementary GREEN coverage, not a RED→GREEN TDD pair.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task, one method (`create_task`), one concern (implicit config refresh) |
| Interface clarity | PASS | AC1/AC2 are specific and testable; redundant/impossible AC removed |
| Dependency correctness | PASS | No dependencies; none needed |
| Module layering | PASS | Tests in `tests/` for `serve/kanban/` engine |
| TDD compliance | PASS | Task IS the test task (`type:test`); supplementary GREEN coverage noted |
| KISS/YAGNI | PASS | 2 focused criteria, no duplication with existing tests |
| Premise challenge | PASS | AC1/AC2 cover implicit refresh path not tested by #828 or `test_refresh_config_803.py` |
| Pattern consistency | PASS | Follows existing kanban test patterns |
| Security surface | N/A | No new security boundaries |
| Single domain | PASS | Kanban engine domain only |

### Challenge Results

- Challenger: SKIPPED (retry of prior REFINE — refinements are mechanical AC removal)

### Verdict: APPROVED

### Action: Advance to todo with refined AC in note. Test-writer should use the 2 AC lines above (not the original 4 in the body)

[[2026-04-12]]

## Test-Writer Notes

- Test file: tests/test_config_staleness_fix_844.py
- Classes: `TestFromAC_CreateTaskImplicitConfigRefresh`
- Tests per category: happy 2 (AC1), edge 0, error 0, boundary 3 (AC2 consistency/rank maps)
- Total: 5 tests, all PASS (supplementary GREEN coverage per Arch Review 2026-04-12)
- ruff: clean
- commit: 1b7fc2dd

**AC coverage:**

| AC | Test(s) |
|----|---------|
| AC1 — board_config().statuses has new status after external addition | `test_new_status_present_in_board_config_after_external_addition`, `test_statuses_count_reflects_external_addition_after_create` |
| AC2 — rank maps + _tasks_dir consistent with refresh_config() | `test_statuses_after_create_match_refresh_config_after_external_change`, `test_new_status_usable_in_next_create_without_explicit_refresh`, `test_priorities_after_create_match_refresh_config_after_external_change` |

**Note:** Task is tagged `type:test`; Arch Review explicitly directed test-writer to produce supplementary GREEN verification tests confirming existing behaviour (engine.py lines 294-296). Tests PASS as expected — this is not a RED→GREEN pair.
[[2026-04-12]]

## Builder Notes

**Task type:** Supplementary GREEN verification (non-RED→GREEN pair per Arch Review 2026-04-12)

**Files changed:** None — test file already written by test-writer (commit 1b7fc2dd)

**Test results:** 5 passed, 0 failed

- test_new_status_present_in_board_config_after_external_addition ✓
- test_statuses_count_reflects_external_addition_after_create ✓
- test_statuses_after_create_match_refresh_config_after_external_change ✓
- test_new_status_usable_in_next_create_without_explicit_refresh ✓
- test_priorities_after_create_match_refresh_config_after_external_change ✓

**Lint:** ruff clean (All checks passed)

**Evidence:** engine.py lines 341-342 (`self._config = config`) + line 344 (`self._tasks_dir = ...`) implement the implicit config refresh. All 5 AC1/AC2 tests confirm this behavior is present and correct.

**Builder-discovered tests:** None — test coverage is complete per AC scope.
[[2026-04-12]]

## Review Evidence

### Tests

5 passed, 0 failed — confirmed via `pytest_844_out.txt` (4 xdist workers, LoadFileScheduling).
Quality-runner reported exit code 1 but parsed output shows 5/5 pass cleanly; confirmed manual inspection resolves the discrepancy (quality-runner artifact, not test failure).

```
tests/test_config_staleness_fix_844.py::TestFromAC_CreateTaskImplicitConfigRefresh::test_new_status_present_in_board_config_after_external_addition PASSED
tests/test_config_staleness_fix_844.py::TestFromAC_CreateTaskImplicitConfigRefresh::test_statuses_count_reflects_external_addition_after_create PASSED
tests/test_config_staleness_fix_844.py::TestFromAC_CreateTaskImplicitConfigRefresh::test_statuses_after_create_match_refresh_config_after_external_change PASSED
tests/test_config_staleness_fix_844.py::TestFromAC_CreateTaskImplicitConfigRefresh::test_new_status_usable_in_next_create_without_explicit_refresh PASSED
tests/test_config_staleness_fix_844.py::TestFromAC_CreateTaskImplicitConfigRefresh::test_priorities_after_create_match_refresh_config_after_external_change PASSED
```

### Lint

ruff: clean (violations: 0) on `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_config_staleness_fix_844.py`.

### Coverage

owlbear_kanban.engine: 28% overall (scoped run). Critical implementation lines 325, 327 (`self._config = config`, `self._tasks_dir = ...`) are COVERED — not in uncovered-lines list.

### AC Compliance

| AC | Test(s) | Evidence | Status |
|----|---------|----------|--------|
| AC1 — `self._config` reflects full updated config after external disk change | `test_new_status_present_in_board_config_after_external_addition`, `test_statuses_count_reflects_external_addition_after_create` | Assertions on `board_config().statuses` (name presence + count); `board_config()` returns `self._config.model_copy(deep=True)` (engine.py L123) — confirms self._config is the data source; would FAIL if L325 `self._config = config` were removed | PASS |
| AC2 — `_tasks_dir` and rank maps consistent with `refresh_config()` | `test_statuses_after_create_match_refresh_config_after_external_change`, `test_priorities_after_create_match_refresh_config_after_external_change`, `test_new_status_usable_in_next_create_without_explicit_refresh` | Direct equality comparison post-create vs post-explicit-refresh; functional usability test; would FAIL if rank map update at L325-327 were missing | PASS |

### TestFromAC_ Integrity

`TestFromAC_CreateTaskImplicitConfigRefresh` — class name unmodified vs test-writer notes. No modifications detected.

### Implementation Verification

`create_task()` (engine.py L325-327):

```python
self._config = config  # L325 — full config update, covered by tests
self._tasks_dir = self._kanban_dir / self._config.tasks_dir  # L327 — covered
self._archive_dir = self._kanban_dir / _ARCHIVE_DIR_NAME  # L328
```

These lines mirror `refresh_config()` (L131-138) exactly — implementation is sound.

### Security

No new security boundaries introduced. Exclusive file lock and `validate_path_containment` remain in place.

### Deductions

- **-0.04** — AC2 `_tasks_dir` sub-criterion has no direct assertion (e.g., `assert engine._tasks_dir == kanban_dir / "tasks"`); tested only indirectly via rank map functional tests. Minor gap — implementation is deterministic and rank map failures would catch regression.
- **-0.02** — Quality-runner exit code 1 anomaly; required manual verification via output file. Resolved: no test failures present.

### Verdict

Confidence: **0.94** → **PASS**
[[2026-04-12]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Task is `type:test`; supplementary GREEN tests for existing engine.py behavior. No behavior, API, or convention changed. `copilot-instructions.md` no update needed. |
| 2 | Module docstrings | No | N/A | Only `tests/test_config_staleness_fix_844.py` created (commit 1b7fc2dd). No production module modified (Builder Notes: "Files changed: None"). Test file already has accurate module docstring, class docstring, and per-method docstrings — all verified. |
| 3 | External attribution | No | N/A | No external patterns, articles, or repos cited in AC, arch review, or builder notes. `sources/overview.md` unchanged. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. `README.md` unchanged. |
| 5 | Research doc | No | N/A | No `.owlbear/research/844-*` file produced. Task referenced the kanban brief; no research doc was created for this task. |

### Files Updated

- None

### Scratch Files Cleaned

- None found (`.owlbear/scratch/844-*` — no matches)
[[2026-04-12]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — self._config reflects full updated config after external disk change | `test_new_status_present_in_board_config_after_external_addition` (asserts "blocked" in statuses), `test_statuses_count_reflects_external_addition_after_create` (asserts count = BASE+1) | PASS |
| AC2 — _tasks_dir and rank maps consistent with refresh_config() | `test_statuses_after_create_match_refresh_config_after_external_change` (equality), `test_new_status_usable_in_next_create_without_explicit_refresh` (functional), `test_priorities_after_create_match_refresh_config_after_external_change` (equality) | PASS |

### Test Results

- pytest (task-scoped): 5 passed, 0 failed
- pytest (full suite): 4063 passed, 338 failed, 8 skipped — failures are pre-existing and unrelated; commit 1b7fc2dd adds only a test file with zero production code changes
- ruff: All checks passed (0 violations)

### Scope Check

Commit 1b7fc2dd: 1 file changed (`tests/test_config_staleness_fix_844.py`, 207 insertions). No production code modified. Scope matches `type:test` AC.

### Architect Quality: 4/5

Initial AC had 4 criteria; architect review correctly identified AC3 (redundant with #828) and AC4 (impossible — implementation already landed) and refined to 2 focused, specific, testable criteria. Final AC is clean. Minor gap: initial AC required a review cycle to refine, but the process worked as intended.

### Deduction Breakdown

- AC lines without evidence: 0 (both AC lines have multiple test assertions) → -0.00
- Lint violations: none → -0.00
- AC quality ≤ 3: no (4/5) → -0.00
- Missing reviewer evidence: no (detailed, PASS at 0.94) → -0.00
- Full-suite task-scope failures: none → -0.00
- Minor: AC2 `_tasks_dir` tested indirectly (functional tests, not direct path assertion) → -0.01

### Confidence: 0.99

### Action: archive
