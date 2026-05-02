---
id: 1207
title: Direct dep lookup in AgentView.show_task
status: review
priority: needed
created: 2026-04-30 15:29:06.229446+00:00
updated: 2026-05-02T15:56:37.625345+00:00
tags:
- audit-kanban
- performance
parent:
depends_on:
- 1205
blocked: false
block_reason:
claimed_at: 2026-05-02T15:56:37.625345+00:00
archival_reason:
archival_refs: []
---

## Objective
Replace O(N) list_tasks calls with O(D) direct lookups for dependencies.

## Files
- engine.py (AgentView.show_task, AgentView._compute_dep_status)

## Change
Replace two `list_tasks()` calls in `AgentView.show_task` with direct `engine.show_task()` lookups for each dependency ID. O(D) where D ≈ 2-5, instead of O(N) where N ≈ 250.

The `_compute_dep_status` method signature should change to perform direct lookups internally (it is only called from `AgentView.show_task` — safe to refactor). Alternatively, inline the logic. Builder's choice.

## AC
- [ ] AgentView.show_task resolves dependency status via direct engine.show_task() per dep ID, not list_tasks() (td:2)
- [ ] No full list_tasks() call remains in AgentView.show_task for dependency enrichment (td:1)
- [ ] When engine.show_task() raises FileNotFoundError for a dep ID, dep_status treats it as 'blocked' — matching current semantics (td:2)
- [ ] When engine.show_task() raises CorruptionError, ValueError, or KeyError for a dep ID, treat as missing (dep_status 'blocked') — matching current list_tasks skip-on-corruption behavior (td:2)
- [ ] Archived dependency archival_reason effects preserved: dropped/wontfix → blocked, deprecated/duplicate → redirect, else → ok (via existing _dep_effect_from_archival_reason) (td:2)
- [ ] CockpitView.show_task (delegates to AgentView.show_task) unaffected — no API change (td:1)
- [ ] Tests pass (td:0)

## Architecture Notes
- `AgentView._compute_dep_status` (line 1861) is only called from `AgentView.show_task` — safe to change signature
- `CockpitView._compute_dep_status` (line 550) is separate and NOT touched
- `CockpitView.show_task` delegates to `AgentView.show_task` (view.py:68) — consumer impact is implicit
- Existing pattern: `_task_exists` (line 1896) already uses `engine.show_task()` with FileNotFoundError
- Current corruption handling in list_tasks: archive corrupt files → archival_reason=None → effect "ok"; active corrupt files → skipped → not in active_ids → "blocked" if also not in archive
- For direct lookups: catch (FileNotFoundError, CorruptionError, ValueError, KeyError) uniformly → treat as missing → "blocked"
- Performance note: engine.show_task uses _id_to_filename index when warm (common case); cold fallback is per-dep glob which is still fewer ops than 2 full directory scans

## Finding: 5.2

[[2026-05-02]]
## Architecture Review

**Verdict:** APPROVED → todo

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| Direct engine.show_task() per dep ID (td:2) | Verifiable, core change | Added — replaces original vague line |
| No list_tasks() for dep enrichment (td:1) | Verifiable by inspection | Kept from original |
| FileNotFoundError → 'blocked' (td:2) | Matches current semantics (dep not in either set) | Tightened from vague "correct behavior" |
| CorruptionError/ValueError/KeyError → 'blocked' (td:2) | **NEW** — challenger identified critical gap: list_tasks catches these, engine.show_task does not | Added to prevent corruption regression |
| Archival reason effects preserved (td:2) | Tests dropped/wontfix→blocked, deprecated/duplicate→redirect, else→ok | Added for completeness |
| CockpitView unaffected (td:1) | CockpitView.show_task delegates to AgentView.show_task (view.py:68) — no API change | Added per challenger finding |
| Tests pass (td:0) | Standard gate | Kept |

### Architecture Notes
- Single responsibility: pure performance refactoring of one private codepath
- _compute_dep_status only called from AgentView.show_task — safe to refactor or inline
- CockpitView._compute_dep_status (line 550) is separate, not touched
- Follows existing _task_exists pattern (line 1896) for engine.show_task + FileNotFoundError
- Dep #1205 archived (done)

### Challenger Results
- Challenger flagged corruption-handling regression (critical) — addressed by adding AC4
- Challenger flagged CockpitView consumer impact — addressed by adding AC6
- Challenger flagged cold-engine performance caveat — noted in Architecture Notes (warm case is the common case; cold fallback still cheaper than 2 full scans)
- Challenger flagged dep-status duplication risk with CockpitView — acknowledged but out of scope (handled by #1211 consolidation task)
- Overall challenger confidence: 0.57 → addressed all critical/moderate concerns, retaining APPROVE
[[2026-05-02]]
## Test-Writer Notes
- Test file: tests/test_engine_dep_lookup_1207.py
- Classes: TestFromAC_DirectDepLookup, TestFromAC_FileNotFoundError, TestFromAC_CorruptionErrorHandling, TestFromAC_ArchivalReasonEffects, TestFromAC_CockpitViewRegression
- Tests per category: happy 6, edge 3, error 6, boundary 2
- Total: 17 tests, all FAIL
- ruff: clean

### AC Coverage

| AC line | Tests |
|---------|-------|
| Direct engine.show_task() per dep (AC1, td:2) | test_no_list_tasks_for_active_dep, test_no_list_tasks_for_archived_completed_dep |
| No list_tasks() for dep enrichment (AC2, td:1) | test_no_list_tasks_for_task_with_no_deps (+ all _raise_list_tasks_called tests) |
| FileNotFoundError → blocked (AC3, td:2) | test_file_not_found_dep_returns_blocked, test_one_missing_dep_blocks_even_with_active_other_dep |
| CorruptionError/ValueError/KeyError → blocked (AC4, td:2) | test_corruption_error_for_active_dep_returns_blocked, test_corruption_error_for_archived_dep_overrides_archival_reason, test_value_error_from_show_task_returns_blocked, test_key_error_from_show_task_returns_blocked |
| Archival reason effects preserved (AC5, td:2) | test_archived_dropped/wontfix/deprecated/duplicate/completed + test_blocked_beats_redirect_for_mixed_deps |
| CockpitView unaffected (AC6, td:1) | test_cockpit_view_show_task_returns_show_task_response, test_cockpit_view_show_task_accepts_section_parameter |

### Failure modes
- AC1/AC2/AC5/AC6 tests: NotImplementedError (list_tasks called in current impl)
- AC3/AC4 tests: AssertionError (current impl returns 'ok' via list_tasks; new code must return 'blocked' via direct show_task exceptions)
[[2026-05-02]]
## Builder Notes
- Implementation: updated AgentView dependency enrichment in serve/kanban/src/owlbear_kanban/engine.py to use direct per-dependency `engine.show_task()` lookups instead of `list_tasks()` scans.
- Behavior: `_compute_dep_status` now catches `FileNotFoundError`, `CorruptionError`, `ValueError`, and `KeyError` during dep lookup and returns `blocked`; archived dependency effects still map through `_dep_effect_from_archival_reason` (dropped/wontfix -> blocked, deprecated/duplicate -> redirect, else ok).
- API compatibility: `AgentView.show_task` signature unchanged; `CockpitView.show_task` delegation path unchanged.
- Tests: task-scoped suite `tests/test_engine_dep_lookup_1207.py` -> 17 passed, 0 failed.
- Lint: ruff clean for `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_dep_lookup_1207.py`.
- Coverage: scoped report for `owlbear_kanban.engine` in task run reported 21% (large pre-existing module; changed path exercised by 17 AC tests).
- Module-level durable file: `tests/test_engine.py` not present, so module-level durable rerun was skipped.
- Commit: `98a75e57` (`perf: direct dep lookup for dep status (#1207, builder)`).

## Post-task Reflection
- Problem faced: previous implementation used full `list_tasks()` scans in `AgentView.show_task`, which was both slower and incompatible with AC guard tests that forbid list scan usage.
- Workaround applied: moved dependency status resolution to direct `show_task` calls per dependency ID and consolidated missing/corrupt dep exceptions into a single blocked-path behavior.
- Pattern discovered: for dep/status enrichment in this engine, direct lookup with conservative exception handling is safer than list-scan-derived set membership when corruption/race behavior is under test.
- Quality gap observed: module-level coverage percentage for `engine.py` remains low in scoped runs because the file is very large; task-focused tests still provide strong path coverage for the modified logic.
[[2026-05-02]]
## Review Evidence

### Source Scope
- Builder commit `98a75e57` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- Changed-file scope was reconstructed from the task body and builder notes, then verified in the current tree:
  - `serve/kanban/src/owlbear_kanban/engine.py`
  - `tests/test_engine_dep_lookup_1207.py`

### Test Results
- pytest (scoped): 17 passed, 0 failed, 0 skipped
- lint (scoped): ruff clean
- coverage (scoped): `owlbear_kanban.engine` 21% module-level, overall 23%
- Coverage was not used as a hard gate here because the changed path is narrow and the task-specific path is exercised; the rejection is proof-quality based.

### AC Compliance
| AC line | Evidence | Status |
|---|---|---|
| AC1 direct `engine.show_task()` per dep ID | `AgentView.show_task` computes `dep_status` via `self._compute_dep_status(task)` at `serve/kanban/src/owlbear_kanban/engine.py:2169`; the direct lookup loop uses `self.engine.show_task(str(dep_id))` at `serve/kanban/src/owlbear_kanban/engine.py:1872`; task tests patch `list_tasks` to raise and still pass at `tests/test_engine_dep_lookup_1207.py:167`, `:180`, `:200` | PASS |
| AC2 no `list_tasks()` dep enrichment remains in `AgentView.show_task` | Same implementation path and `list_tasks`-raising task tests above | PASS |
| AC3 `FileNotFoundError` -> `blocked` | Catch branch at `serve/kanban/src/owlbear_kanban/engine.py:1873`; tests assert blocked at `tests/test_engine_dep_lookup_1207.py:238`, `:262` | PASS |
| AC4 `CorruptionError`/`ValueError`/`KeyError` -> `blocked` | Same catch branch; tests assert blocked at `tests/test_engine_dep_lookup_1207.py:303`, `:340`, `:362`, `:383` | PASS |
| AC5 archived dependency archival_reason effects preserved | Archive-only fixtures pass at `tests/test_engine_dep_lookup_1207.py:426-492` and helper mapping remains at `serve/kanban/src/owlbear_kanban/engine.py:1854-1860`, but task proof does not cover established archive-wins duplicate-location semantics from `serve/kanban/src/owlbear_kanban/engine.py:674` and `serve/kanban/tests/test_engine_coverage_1068.py:1603-1617`; the new direct lookup path now depends on `engine.show_task()` at `serve/kanban/src/owlbear_kanban/engine.py:1872`, whose cold lookup checks `tasks/` before `archive/` at `serve/kanban/src/owlbear_kanban/engine.py:806-810` | FAIL |
| AC6 CockpitView.show_task unaffected | Signature/delegation is unchanged at `serve/cockpit/src/owlbear_cockpit/view.py:66-68`; task tests confirm return type and active-dep path at `tests/test_engine_dep_lookup_1207.py:520-523`, but the `section=` regression check only asserts `resp.body is not None` at `tests/test_engine_dep_lookup_1207.py:545`, which would not fail if section extraction returned the wrong content | PASS with proof gap |
| AC7 tests pass | Scoped quality-runner run: 17 passed, 0 failed; ruff clean | PASS |

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 | `test_no_list_tasks_for_active_dep`, `test_no_list_tasks_for_archived_completed_dep` | Yes for remaining `list_tasks()` dependency enrichment | COVERED |
| AC2 | `test_no_list_tasks_for_task_with_no_deps` plus the `list_tasks`-raising fixtures | Yes | COVERED |
| AC3 | `test_file_not_found_dep_returns_blocked`, `test_one_missing_dep_blocks_even_with_active_other_dep` | Yes | COVERED |
| AC4 | Four exception-injection tests | Yes | COVERED |
| AC5 | Archival-reason tests | Only for archive-only fixtures; no proof for the archive-wins duplicate-location branch | LAX |
| AC6 | Cockpit regression tests | Return-type/delegation checks fail on obvious API breaks, but the `section=` proof is non-discriminating because `assert resp.body is not None` still passes on wrong extracted content | LAX |

#### Security Review
- No security issues found in the changed path.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions were evident in the current task test file.
- Historical immutability versus the original test-writer commit could not be fully proven without diff access; small confidence deduction applied.

#### Test Quality
- Assertion specificity is mostly strong, but AC6 has one lax assertion: `assert resp.body is not None` at `tests/test_engine_dep_lookup_1207.py:545`.
- That assertion does not prove the `section=` path still returns the correct extracted content; it only proves the body is non-null.

#### Significant Untested Paths
- I verified and rejected one earlier concern: invalid-status targeted reads still hard-raise `CorruptionError` in existing repo tests (`tests/test_storage_1205.py:194-208`, `serve/kanban/tests/test_corruption.py:935-948`), so invalid status is **not** part of this rejection.
- The remaining unproven branch is archive-wins duplicate-location behavior. Existing engine semantics establish that an archive copy takes precedence over a tasks copy (`serve/kanban/src/owlbear_kanban/engine.py:674`, `serve/kanban/tests/test_engine_coverage_1068.py:1603-1617`). No task-scoped test covers that branch.

### Deductions
- -0.06 AC5 proof gap / possible archive-precedence regression
- -0.04 AC6 lax `section=` assertion
- -0.03 TestFromAC immutability not fully provable without commit diff access

### Verdict
- FAIL -> todo
- Confidence: 0.87

### Required Follow-up
- Add a discriminating AC5 test covering duplicate-location archive-wins behavior for a dependency ID present in both `tasks/` and `archive/`.
- Strengthen the AC6 `section=` regression test to assert the extracted section content, not just non-null body.
- Re-run the scoped task suite and lint.
[[2026-05-02]]
## Test-Writer Notes
- Retry: added 2 tests for reviewer gaps (archive-wins AC5, section-content AC6).
- Test file: tests/test_engine_dep_lookup_1207.py
- Classes: TestFromAC_ArchivalReasonEffects (added test_archive_wins_over_tasks_copy_for_dep_status), TestFromAC_CockpitViewRegression (added test_cockpit_view_show_task_section_extracts_correct_content)
- Prior 17 tests: all PASS
- New tests: 1 FAIL (archive-wins), 1 PASS (section-content — impl already correct)
- ruff: clean
- Commit: 988afa2c

### AC Coverage (retry gaps)
| Gap | Test | Status |
|-----|------|--------|
| AC5 archive-wins duplicate-location | test_archive_wins_over_tasks_copy_for_dep_status | FAIL — builder regression confirmed: engine.show_task cold-path returns tasks/ copy instead of archive/ copy; dep in both tasks/ and archive/ yields 'ok' instead of 'blocked' |
| AC6 section= content assertion | test_cockpit_view_show_task_section_extracts_correct_content | PASS — impl already extracts correct content; assert resp.body == "content here\n\n" passes |

### Builder action required
- Fix archive-wins regression in _compute_dep_status: when engine.show_task returns a non-archived task for a dep that has an archive copy, the archive copy must take precedence. Consider checking archive dir directly after active lookup, or check dep_task.status and fall back to archive lookup if dep is in tasks/ but archive copy exists (mirroring AC-C19 mode 7 semantics).
[[2026-05-02]]
## Builder Notes
- Implementation: updated `show_task` cold-path lookup precedence in `serve/kanban/src/owlbear_kanban/engine.py` so archive matches are resolved before tasks matches; kept `AgentView._compute_dep_status` on direct per-dependency `engine.show_task()` lookups with existing blocked-on-exception behavior.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`.
- Fix applied: archive-wins duplicate-location semantics are now preserved for dependency enrichment when an ID exists in both `tasks/` and `archive/`.
- API compatibility: `AgentView.show_task` and `CockpitView.show_task` signatures/return types unchanged.
- Tests (scoped): `tests/test_engine_dep_lookup_1207.py` -> 19 passed, 0 failed, 0 skipped.
- Lint (scoped): ruff clean for `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_dep_lookup_1207.py`.
- Coverage (scoped): `owlbear_kanban.engine` 21% (module is large; task path exercised by AC test suite).
- Durable module-level check: `uv run pytest tests/test_engine.py -q --tb=short` produced no collected tests; skipped per workflow.
- Commit: `da2df053` (`fix: preserve archive-wins dep lookup semantics (#1207, builder)`).
- Evidence summary: previously failing `TestFromAC_ArchivalReasonEffects::test_archive_wins_over_tasks_copy_for_dep_status` now passes; all task-scoped TestFromAC coverage is GREEN with no lint violations.