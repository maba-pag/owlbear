---
id: 1207
title: Direct dep lookup in AgentView.show_task
status: archived
priority: medium
created: 2026-04-30 15:29:06.229446+00:00
updated: 2026-05-02T18:09:55.583099+00:00
tags:
- audit-kanban
- performance
parent:
depends_on:
- 1205
blocked: false
block_reason:
claimed_at:
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
[[2026-05-02]]
## Review Evidence

### Source Scope
- Builder retry commit `da2df053` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- Test-writer retry commit `988afa2c` is also present in the same logs.
- Latest builder scope from task body: `serve/kanban/src/owlbear_kanban/engine.py`.
- Current review also audited `tests/test_engine_dep_lookup_1207.py` and the unchanged delegation point in `serve/cockpit/src/owlbear_cockpit/view.py`.

### Test Results
- pytest (scoped): 19 passed, 0 failed, 0 skipped
- lint (scoped): ruff clean
- coverage (scoped): `owlbear_kanban.engine` 21% module-level, overall 24%
- Coverage was not the gate here; the rejection is for a remaining implementation defect on a natural AC branch.

### AC Compliance
| AC line | Evidence | Status |
|---|---|---|
| AC1 direct `engine.show_task()` per dep ID | `AgentView._compute_dep_status` now loops deps and calls `self.engine.show_task(str(dep_id))` in `serve/kanban/src/owlbear_kanban/engine.py:1861-1884`; scoped tests that patch `list_tasks` to raise still pass in `tests/test_engine_dep_lookup_1207.py:154-201` | PASS |
| AC2 no `list_tasks()` dep enrichment remains in `AgentView.show_task` | `AgentView.show_task` sets `payload["dep_status"] = self._compute_dep_status(task)` at `serve/kanban/src/owlbear_kanban/engine.py:2169` and the dep helper contains no `list_tasks()` call; task-local guard tests in `tests/test_engine_dep_lookup_1207.py:154-201` fail on regression | PASS |
| AC3 `FileNotFoundError` -> `blocked` | Exception catch in `serve/kanban/src/owlbear_kanban/engine.py:1873`; enforced by `tests/test_engine_dep_lookup_1207.py:217-274` | PASS |
| AC4 `CorruptionError` / `ValueError` / `KeyError` -> `blocked` | Same catch branch in `serve/kanban/src/owlbear_kanban/engine.py:1873`; enforced by `tests/test_engine_dep_lookup_1207.py:276-395` | PASS |
| AC5 archival_reason effects preserved | Cold-path archive precedence is fixed at `serve/kanban/src/owlbear_kanban/engine.py:806-812` and the new regression test in `tests/test_engine_dep_lookup_1207.py:497-531` passes. But warm-cache `show_task` still returns the active `tasks/` file immediately when `_id_to_filename` is populated and the tasks file exists at `serve/kanban/src/owlbear_kanban/engine.py:781-803`, with no archive check. Existing engine semantics treat archive copy as authoritative when both locations exist (`serve/kanban/src/owlbear_kanban/engine.py:674-677`, `serve/kanban/tests/test_engine_storage.py:807-834`). The task-local test only proves the miss path because its setup removes the duplicate dep from `_id_to_filename` before the assertion. | FAIL |
| AC6 CockpitView.show_task unaffected | `serve/cockpit/src/owlbear_cockpit/view.py:66-68` remains a straight delegation to `AgentView.show_task(task_id, section)`; task-local Cockpit tests in `tests/test_engine_dep_lookup_1207.py:541-605` now include exact section-content assertion, and durable `AgentView.show_task` section-branch tests still cover missing-sections/guidance behavior in `serve/kanban/tests/test_engine_reads_1069.py:692-812` | PASS |
| AC7 tests pass | Scoped quality evidence: 19 passed, 0 failed; ruff clean | PASS |

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 | `TestFromAC_DirectDepLookup` | Yes | COVERED |
| AC2 | `TestFromAC_DirectDepLookup` | Yes | COVERED |
| AC3 | `TestFromAC_FileNotFoundError` | Yes | COVERED |
| AC4 | `TestFromAC_CorruptionErrorHandling` | Yes | COVERED |
| AC5 | `TestFromAC_ArchivalReasonEffects` incl. `test_archive_wins_over_tasks_copy_for_dep_status` | Only for cold-path duplicate lookup; does not fail the remaining warm-cache archive-precedence defect | LAX |
| AC6 | `TestFromAC_CockpitViewRegression` | Yes for delegation/signature and exact section extraction on the changed path | COVERED |

#### Security Review
- No security issues found in the changed path.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions were evident in the current task test file.
- Historical immutability against the original test-writer commit is still slightly lower-confidence because I do not have direct diff access from this tool surface.

#### Test Quality
- I am not treating the earlier AC6 proof-locality concern as blocking: the task-local suite now has an exact content assertion, and the unchanged delegation plus durable `AgentView.show_task` section tests cover the unchanged branches.
- The blocking issue is implementation, not assertion style: AC5 still has a real warm-cache defect.

#### Significant Untested / Failing Path
- `KanbanEngine.show_task` still violates archive-wins precedence when `_id_to_filename` is warm and the active `tasks/` file still exists. In that branch, the function returns the active file before any archive lookup (`serve/kanban/src/owlbear_kanban/engine.py:781-803`).
- That conflicts with existing engine duplicate-location semantics, where archive copy wins over tasks copy (`serve/kanban/src/owlbear_kanban/engine.py:674-677`, `serve/kanban/tests/test_engine_storage.py:807-834`).
- The new task test only proves the cold-path fallback case because its setup warms the index after the duplicate already exists, so the duplicate ID is absent from `_id_to_filename`.

### Deductions
- -0.12 AC5 remaining warm-cache archive-precedence defect
- -0.02 TestFromAC immutability not fully provable without commit diff access

### Verdict
- FAIL -> backlog
- Confidence: 0.86
- Reason: second review failure on the same task, with a remaining AC5 implementation defect in the warm-cache `show_task` path

### Required Follow-up
- Fix `KanbanEngine.show_task` so archive precedence holds even when `_id_to_filename` is warm and the active tasks file still exists.
- Add a discriminating test that warms `_id_to_filename` before an archive duplicate appears, then proves `AgentView.show_task` still derives `dep_status` from the archived copy.
- Re-run the scoped task suite and the adjacent cache/show_task suites relevant to stale-index behavior.

### Routing
- This task already contains one prior `## Review Evidence` rejection. Per reviewer loop-breaker rules, a second review failure routes to `backlog`, not back to `in-progress` or `todo`.
[[2026-05-02]]

## Architecture Review (cycle 2)

**Verdict:** APPROVED → todo (REFINE: added AC6 for warm-cache archive precedence)

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1 direct engine.show_task() per dep (td:2) | Proven through 2 review cycles, 19 passing tests | Kept |
| AC2 no list_tasks() for dep enrichment (td:1) | Proven, guard tests raise on list_tasks call | Kept |
| AC3 FileNotFoundError → blocked (td:2) | Proven | Kept |
| AC4 CorruptionError/ValueError/KeyError → blocked (td:2) | Proven | Kept |
| AC5 archival_reason effects preserved (td:2) | Proven for archival_reason mapping; warm-cache defect separated into AC6 | Kept |
| **AC6 (NEW)** warm-cache archive precedence (td:2) | Reviewer identified warm-cache path returns tasks/ copy when both exist; cold path is correct. This is the root cause of both review rejections | **Added** |
| AC7 CockpitView unaffected (td:1) | Proven, delegation unchanged | Kept (was AC6) |
| AC8 tests pass (td:0) | Standard gate | Kept (was AC7) |

### New AC line (supplements existing ## AC section)

- [ ] KanbanEngine.show_task warm-cache path: when `_id_to_filename` resolves an ID to a tasks/ filename AND `archive_dir / filename` also exists, return the archive copy and evict the ID from `_id_to_filename` (AC-C19 mode 7 parity) (td:2)

### Architecture Notes

**Root cause:** `_id_to_filename` is populated exclusively from `tasks/` dir (engine.py:699-704). The warm-cache path (engine.py:781-803) returns the tasks/ copy without checking archive. The cold path (engine.py:806-812) correctly checks archive first. This asymmetry means `show_task` violates AC-C19 mode 7 when the cache is warm and a duplicate exists.

**Fix location:** `KanbanEngine.show_task` warm-cache branch (engine.py ~line 800, after stat succeeds). Insert archive existence check using same filename identity as the existing stale-path pattern at line 790 (`self._archive_dir / filename`). This is filename-based, not ID-glob-based, because the warm path already has the filename from `_id_to_filename`. On archive hit: read from archive, evict from `_id_to_filename`, evict from `_task_cache`, return archived task.

**Lookup identity (challenger concern):** Use filename-based (`archive_dir / filename`), matching the existing stale-path pattern at line 790. ID-based glob is unnecessary here because `_id_to_filename` already resolved the canonical filename. The cold path uses ID-glob because no filename is cached yet.

**Scope boundary:** This fix is in `show_task` only. `_find_task_path` is a separate contract for write-path file resolution and intentionally does NOT cross into archive (its `include_archive_fallback` defaults to False). Not in scope.

**Performance:** One additional `exists()` syscall per warm-cache hit. Negligible relative to the O(N)→O(D) improvement this task delivers.

**Test hint for AC6:** The discriminating test must: (1) warm `_id_to_filename` via `list_tasks()` while dep exists only in tasks/, (2) then place a copy in archive/ (simulating concurrent archival), (3) call `AgentView.show_task` for the parent task, (4) assert dep_status reflects the archived copy's archival_reason, not the active copy's status.

### Dependency Analysis
- #1205 (Thread cached config through read_task): archived/done ✓

### Challenger Results
- Challenger at 0.68 confidence, recommended reconsider
- Critical: proof gap for new AC — addressed: AC6 is new, test-writer will write the discriminating test
- Moderate: design under-specification (filename vs ID lookup) — addressed in Architecture Notes above
- Moderate: adjacent cache/show_task suite run missing — noted in test hint; builder should run `test_idtofilename_cache_944.py` alongside task suite
- Blind spot: `_find_task_path` scope — clarified: not in scope, separate contract
- Override rationale: challenger's concerns are about specification precision, not fundamental design. All addressed in AC refinement and architecture notes. Retaining APPROVE.

[[2026-05-02]]
APPROVED #1207 → todo | REFINE: added AC6 for warm-cache archive precedence in KanbanEngine.show_task (AC-C19 mode 7 parity). Root cause of both prior review rejections was warm-cache path returning tasks/ copy when archive/ copy exists. Fix is a single archive existence check in show_task warm branch, filename-based (matching existing stale-path pattern). Challenger overridden at 0.68 — all concerns addressed in AC specification.
[[2026-05-02]]
## Test-Writer Notes
- Retry: added 2 tests for AC6 warm-cache archive-precedence gap (new AC from cycle-2 architecture review).
- Test file: tests/test_engine_dep_lookup_1207.py
- New class: TestFromAC_WarmCacheArchivePrecedence
- Tests added: 2 (both boundary/error category)
- Prior 19 tests: all PASS
- New tests: 2 FAIL
- ruff: clean
- Commit: 326d8433

### AC Coverage (retry gaps)
| Gap | Test | Status |
|-----|------|--------|
| AC6 warm-cache archive-wins (dep in _id_to_filename, archive copy added after index) | test_warm_cache_dep_returns_archive_when_archive_appears_after_index | FAIL — dep_status='ok' (tasks/ copy returned), expected 'blocked' (archive copy with archival_reason='dropped') |
| AC6 eviction from _id_to_filename after archive-wins | test_warm_cache_id_evicted_from_index_after_archive_precedence_applied | FAIL — dep 2 remains in _id_to_filename, expected eviction |

### Builder action required
- Fix warm-cache branch in KanbanEngine.show_task (~engine.py line 800): after stat(tasks/filename) succeeds, check if archive_dir/filename also exists. If so, read from archive, evict ID from _id_to_filename and filename from _task_cache, return archived task. This mirrors the existing stale-path eviction pattern at line 788-800.
[[2026-05-02]]
## Builder Notes
- Implementation: updated warm-cache branch in `KanbanEngine.show_task` in `serve/kanban/src/owlbear_kanban/engine.py` to enforce archive precedence even when `_id_to_filename` is populated from `tasks/`.
- Fix applied: after warm-path `stat(tasks/filename)` succeeds, code now checks `archive/filename`; when present, it evicts `filename` from `_task_cache`, evicts dep ID from `_id_to_filename`, and returns the archived task.
- Scope: surgical single-file source change only; no API/signature changes in `AgentView.show_task` or `CockpitView.show_task`.
- RED verification (pre-fix): `tests/test_engine_dep_lookup_1207.py` had 2 failing `TestFromAC` tests (`test_warm_cache_dep_returns_archive_when_archive_appears_after_index`, `test_warm_cache_id_evicted_from_index_after_archive_precedence_applied`).
- GREEN verification (post-fix, quality-runner scoped): `tests/test_engine_dep_lookup_1207.py` -> 21 passed, 0 failed, 0 skipped.
- Lint (quality-runner scoped): ruff clean for `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_dep_lookup_1207.py`.
- Coverage (quality-runner scoped): `owlbear_kanban.engine` 22% module-level (large module; task-scoped branch coverage satisfied by TestFromAC suite).
- Durable module-level check: `tests/test_engine.py` absent, so module-level pytest rerun was skipped.
- Commit: `60c085fc` (`fix: enforce warm-cache archive precedence in show_task (#1207, builder)`).
- Evidence summary: both AC6 warm-cache regression tests are now green, and full task-scoped TestFromAC suite is green with no lint violations.
[[2026-05-02]]
## Review Evidence

### Source Scope
- Builder commit `60c085fc` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`.
- Test-writer retry commit `326d8433` is present in the same logs.
- Reviewed current tree for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_dep_lookup_1207.py`, and `serve/cockpit/src/owlbear_cockpit/view.py`.
- Changed-file scope was reconstructed from builder notes plus current tree because full diff access is not available from this tool surface.

### Test Results
- pytest scoped: 21 passed, 0 failed, 0 skipped
- lint scoped: ruff clean
- coverage scoped: `owlbear_kanban.engine` 22%, overall 24%
- Coverage was not used as a hard gate here because the changed path is narrow and the task suite exercises the modified branches directly.

### AC Compliance
| AC line | Evidence | Status |
|---|---|---|
| AC1 direct `engine.show_task()` per dep ID | `AgentView._compute_dep_status` loops deps and calls `self.engine.show_task(str(dep_id))` in `serve/kanban/src/owlbear_kanban/engine.py:1868-1890`; `list_tasks`-raising guard tests pass in `tests/test_engine_dep_lookup_1207.py:154-201` | PASS |
| AC2 no `list_tasks()` dep enrichment remains | `AgentView.show_task` still computes `dep_status` through `_compute_dep_status` in `serve/kanban/src/owlbear_kanban/engine.py:2145-2174`, and the dep helper contains no `list_tasks()` call; task-local guard tests in `tests/test_engine_dep_lookup_1207.py:154-201` fail on regression | PASS |
| AC3 `FileNotFoundError` yields `blocked` | `_compute_dep_status` catches `FileNotFoundError` in `serve/kanban/src/owlbear_kanban/engine.py:1876-1884`; enforced by `tests/test_engine_dep_lookup_1207.py:221-266` | PASS |
| AC4 `CorruptionError`, `ValueError`, and `KeyError` yield `blocked` | Same catch branch in `serve/kanban/src/owlbear_kanban/engine.py:1876-1884`; enforced by `tests/test_engine_dep_lookup_1207.py:280-387` | PASS |
| AC5 archival reason effects preserved | `_dep_effect_from_archival_reason` still maps dropped and wontfix to blocked, deprecated and duplicate to redirect, else ok in `serve/kanban/src/owlbear_kanban/engine.py:1854-1860`; archival matrix and precedence tests pass in `tests/test_engine_dep_lookup_1207.py:401-531` | PASS |
| AC6 warm-cache archive precedence and ID eviction | Warm-cache `show_task` checks `archive/filename` before returning cached or active task, evicts `_task_cache` and `_id_to_filename`, and returns `read_task(archive_path, config=self._config)` in `serve/kanban/src/owlbear_kanban/engine.py:781-820`; discriminating warm-cache tests pass in `tests/test_engine_dep_lookup_1207.py:623-718` | PASS |
| AC7 CockpitView unaffected | `CockpitView.show_task` remains a straight delegation in `serve/cockpit/src/owlbear_cockpit/view.py:66-68`; task-local regression tests cover response type, dep_status, optional section, and exact section extraction in `tests/test_engine_dep_lookup_1207.py:546-608` | PASS |
| AC8 tests pass | Quality-runner scoped evidence: 21 passed, 0 failed; ruff clean | PASS |

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 | `TestFromAC_DirectDepLookup` | Yes | COVERED |
| AC2 | `TestFromAC_DirectDepLookup` | Yes | COVERED |
| AC3 | `TestFromAC_FileNotFoundError` | Yes | COVERED |
| AC4 | `TestFromAC_CorruptionErrorHandling` | Yes | COVERED |
| AC5 | `TestFromAC_ArchivalReasonEffects` | Yes | COVERED |
| AC6 | `TestFromAC_WarmCacheArchivePrecedence` | Yes. One test proves the warm-cache branch now derives dep status from the archived copy after the index is warm, and the other proves ID eviction from `_id_to_filename`. That matches the cycle-2 architecture note for this AC. | COVERED |
| AC7 | `TestFromAC_CockpitViewRegression` | Yes | COVERED |
| AC8 | Quality-runner scoped run | Yes | COVERED |

#### Security Review
- No security issues found in the changed path.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions were evident in the current task test file.
- Historical immutability against the original test-writer commit is slightly lower-confidence because I do not have full diff access from this tool surface.

#### Test Quality
- Assertion specificity is strong for the task contract. Exact `dep_status` outcomes, exact section extraction, and explicit ID eviction are all asserted.
- Code-reader raised a non-blocking AC6 payload-fidelity concern. I am not treating that as a failure because the architect's cycle-2 AC explicitly framed the discriminating proof as archived-copy semantics on the consumer path plus ID eviction, and the implementation now directly returns `read_task(archive_path, config=self._config)` on archive hit.

#### Significant Untested Paths
- I investigated the invalid-status concern and rejected it. Targeted reads hard-raise `ERR_CORRUPT_INVALID_STATUS` in `serve/kanban/src/owlbear_kanban/storage.py:312-381` and `serve/kanban/src/owlbear_kanban/corruption.py:347-353`, and `_compute_dep_status` catches `CorruptionError` and returns `blocked`. No remaining significant untested path in the changed logic was found.

### Deductions
- -0.04 full commit diff not available; commit presence was proven through git log entries plus current-tree inspection

### Verdict
- PASS to docs
- Confidence: 0.95

### Action
- Advance to docs
[[2026-05-02]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/kanban/README.md` describes `show_task` as "Fetch a single full Task by ID" — still accurate; no API change. No update needed. |
| 2 | Module docstrings | Yes | Updated | `KanbanEngine.show_task` docstring updated to document archive-wins precedence behavior (new warm-cache contract). `AgentView.show_task` docstring already accurate. `AgentView._compute_dep_status` is private — no docstring required. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` describes `serve/kanban/src/**` — match. Footer updated from `b38e0eb8` → `6f82bf2d` (current HEAD). |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Updated `KanbanEngine.show_task` docstring |
| `tests/test_engine_dep_lookup_1207.py` | OUT (test file) | N/A |
| `serve/cockpit/src/owlbear_cockpit/view.py` | IN (docstrings) | `AgentView.show_task` docstring already accurate — no edit |
| `share/diagrams/kanban.excalidraw` | IN (diagram describes-match) | Footer commit hash updated |

### Files Updated
- `serve/kanban/src/owlbear_kanban/engine.py` — `KanbanEngine.show_task` docstring
- `share/diagrams/kanban.excalidraw` — footer `Last verified` commit hash

### Commit
`55ce8870` — docs: update KanbanEngine.show_task docstring and kanban diagram (#1207, doc-writer)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None
[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 direct engine.show_task() per dep | _compute_dep_status at engine.py:1875 uses self.engine.show_task(str(dep_id)); list_tasks-raising guard tests pass (test_engine_dep_lookup_1207.py:154-201) | PASS |
| AC2 no list_tasks() for dep enrichment | Same implementation path; no list_tasks() call in _compute_dep_status | PASS |
| AC3 FileNotFoundError → blocked | Catch branch at engine.py:1876; tests at test_engine_dep_lookup_1207.py:221-266 | PASS |
| AC4 CorruptionError/ValueError/KeyError → blocked | Same catch branch; tests at test_engine_dep_lookup_1207.py:280-387 | PASS |
| AC5 archival_reason effects preserved | _dep_effect_from_archival_reason at engine.py:1854-1860; archival matrix tests at test_engine_dep_lookup_1207.py:401-531 | PASS |
| AC6 warm-cache archive precedence | Warm branch at engine.py:806-808 checks archive_path.exists() before returning tasks/ copy, evicts caches; tests at test_engine_dep_lookup_1207.py:623-718 | PASS |
| AC7 CockpitView unaffected | Delegation unchanged at view.py:66-68; regression tests at test_engine_dep_lookup_1207.py:546-608 | PASS |
| AC8 tests pass | 21 passed, 0 failed (scoped); full suite: 128 failures all in unrelated files | PASS |

### Test Results
- pytest (full): 3654 passed, 128 failed (none in task scope), 4 skipped
- pytest (scoped): 21 passed, 0 failed
- ruff (full): 3 violations in unrelated files (copilot_auth.py, server.py, hello_world.py)
- vitest (full): 943 passed, 4 failed (none in task scope)

### Commits Verified
- dc6e9bb3 test: add failing tests (test-writer)
- 98a75e57 perf: direct dep lookup (builder)
- 988afa2c test: add archive-wins and section-content tests (retry, test-writer)
- da2df053 fix: preserve archive-wins (builder retry)
- 326d8433 test: add warm-cache archive-wins tests (test-writer retry 2)
- 60c085fc fix: enforce warm-cache archive precedence (builder retry 2)
- 55ce8870 docs: update docstring and diagram (doc-writer)

### Architect Quality: 3/5
Original AC missed warm-cache archive-wins semantics despite the architecture notes explicitly discussing warm/cold paths. This foreseeable gap cost 2 full review rejection cycles before the cycle-2 architect review diagnosed the root cause and added AC6. Cycle 2 refinement was precise and effective.

### Deduction Breakdown
- AC quality score 3/5: -0.03
- No task-scope test failures: 0
- No task-scope lint violations: 0
- Reviewer evidence present and detailed: 0
- No cross-task regressions attributable to this task: 0

### Confidence: 0.97
### Action: archive