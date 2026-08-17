---
id: 945
title: Tests for show_task() and _find_task_path() cache integration (TDD RED)
status: archived
priority: medium
created: 2026-04-17T22:57:35.601340+00:00
updated: 2026-04-18T00:05:12.871324+00:00
tags:
- engine
- cockpit
- phase-0
- type:test
parent: 920
depends_on:
- 943
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Write failing tests for #943 — extending mtime cache to show_task() and_find_task_path().

## Acceptance Criteria

- [ ] Test: show_task() cache hit — returns cached Task without glob syscall
- [ ] Test: show_task() stat-stale — re-reads file and updates cache entry
- [ ] Test: show_task() stat-missing (file archived/deleted) — evicts stale entry, falls to glob
- [ ] Test: show_task() cold cache — falls to glob (current behavior)
- [ ] Test: _find_task_path() cache hit — returns path without glob
- [ ] Test: _find_task_path() cold cache — falls to glob (current behavior)
- [ ] Test: _find_task_path() warm miss (new file created since last list_tasks) — falls to glob
- [ ] Test: refresh_config() clears_id_to_filename dict
- [ ] All tests FAIL (RED phase)

## Files

- `serve/kanban/tests/test_show_find_cache_943.py` (new)

## Context

See `.owlbear/research/extend-mtime-cache-943.md` for approach. Uses single `_id_to_filename` dict rebuilt in `list_tasks()`. Extend patterns from `test_mtime_cache_942.py`.
[[2026-04-17]]

## Research

**Finding: Task already fulfilled.** All 9 ACs are covered by existing tests in `serve/kanban/tests/test_idtofilename_cache_943.py` (25 tests, all GREEN). The tests were written under #943 using the filename `test_idtofilename_cache_943.py` instead of the AC-specified `test_show_find_cache_943.py`. The implementation is live in `engine.py` — `_id_to_filename` is initialized in `__init__`, rebuilt in `list_tasks()`, cleared in `refresh_config()`, and consumed by both `show_task()` and `_find_task_path()`.

- AC mapping: all 8 functional ACs have 1–3 tests each (see task body above)
- AC 9 (all tests FAIL) is N/A — implementation shipped with #943
- Tier: T1 — no decision needed, no follow-up tasks needed
- Confidence: 1.0 — verified by running test suite (25/25 passed in 0.15s)
- Follow-up tasks: none — work is complete
- Decision requests: none

Downstream agents should verify the AC mapping and fast-track through the pipeline. The only discrepancy is the filename (`test_idtofilename_cache_943.py` vs AC-specified `test_show_find_cache_943.py`) — this is cosmetic and not worth a rename.
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: cache integration tests for show_task/find_task_path |
| Interface clarity | PASS | ACs specify exact cache behaviors (hit, miss, stale, eviction) |
| Dependency correctness | PASS | Depends on #943 (archived/done) — dependency fulfilled |
| Module layering | PASS | Tests target `owlbear_kanban.engine` internals correctly |
| TDD compliance | PASS | This IS the test task; implementation shipped with #943 |
| KISS/YAGNI | PASS | 25 focused tests, no over-engineering |
| Premise challenge | PASS | Tests exist at `test_idtofilename_cache_943.py` covering all functional ACs — work already fulfilled under #943. Pipeline pass-through via `type:test` tag is low-cost |
| Pattern consistency | PASS | Follows `test_mtime_cache_942.py` patterns (fixtures, mock patching, board helpers) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | engine/kanban domain only |

### AC Assessment

| AC | Assessment | Notes |
|----|-----------|-------|
| 1. show_task() cache hit | FULFILLED | 3 tests: no-glob, no-read_task, correct-task |
| 2. show_task() stat-stale | FULFILLED | 2 tests: triggers-reread, updates-cache-entry |
| 3. show_task() stat-missing | FULFILLED (wording imprecise) | 2 tests verify eviction + FileNotFoundError. AC says "falls to glob" but impl raises immediately after eviction — correct for deleted files since glob won't find them either. Minor spec-wording gap, not a bug. |
| 4. show_task() cold cache | FULFILLED | 1 test: glob fallback |
| 5. _find_task_path() cache hit | FULFILLED | 2 tests: no-glob, correct-path |
| 6. _find_task_path() cold cache | FULFILLED | 1 test: glob fallback |
| 7. _find_task_path() warm miss | FULFILLED | 1 test: post-create glob fallback |
| 8. refresh_config() clears dict | FULFILLED | 2 tests: clears + re-warmable |
| 9. All tests FAIL (RED) | N/A | Implementation shipped with #943; tests are GREEN |

### Key Finding

All work completed under #943. Tests live at `serve/kanban/tests/test_idtofilename_cache_943.py` (25 tests, all GREEN). Implementation at `serve/kanban/src/owlbear_kanban/engine.py` lines 137, 186, 274, 335-342, 915-921. Downstream agents should fast-track — nothing to build or test.

### Challenge Results

- Challenger: reconsider (confidence 0.45)
- C1 (AC 3 wording): Accepted as observation — "falls to glob" doesn't match impl (raises). Non-blocking for deleted-file case.
- C2 (pipeline waste): Rebutted — `type:test` pass-through minimizes cost. Direct-archive not available to architect.
- C3/C4 (bookkeeping): Rebutted — minor, downstream handles.
- Architect response: accepted C1 as noted imprecision, rebutted C2-C4, proceeding with APPROVE.

### Verdict: APPROVE

### Action Taken: Advanced to todo. All ACs already fulfilled by #943. Fast-track recommended for downstream agents

[[2026-04-17]]

## Test-Writer Notes

**Verdict: pass-through — all ACs fulfilled pre-pipeline under #943.**

### Test file

`serve/kanban/tests/test_idtofilename_cache_943.py` (exists, 25 tests, all GREEN)

### AC Coverage Table

| AC | Tests | Status |
|----|-------|--------|
| show_task() cache hit — no glob, no read_task | 3 | COVERED |
| show_task() stat-stale — re-reads + updates cache | 2 | COVERED |
| show_task() stat-missing — evicts both caches | 2 | COVERED |
| show_task() cold cache — glob fallback | 1 | COVERED |
| _find_task_path() cache hit — no glob | 2 | COVERED |
| _find_task_path() cold cache — glob fallback | 1 | COVERED |
| _find_task_path() warm miss — glob fallback | 1 | COVERED |
| refresh_config() clears_id_to_filename | 2 | COVERED |
| All tests FAIL (RED) | N/A | Implementation shipped with #943 |

### Categories

- happy: 4 (cache hits, cold fallbacks)
- edge: 7 (stale mtime, warm miss, archived list, non-integer id, search_dir mismatch, lazy invalidation)
- error: 2 (missing file eviction)
- boundary: 2 (init dict state, dict type)
- init/structure: 5 (init checks, key/value types, coverage count)

**Total: 25 tests, all currently PASS** (implementation pre-exists; no new test file needed)

### Note

Tests were written as part of #943 using filename `test_idtofilename_cache_943.py` (not `test_show_find_cache_943.py` as specified in AC). Filename discrepancy is cosmetic — same coverage, no rename needed.
[[2026-04-17]]

## Builder Notes

**Verdict: pass-through — no code changes required.**

All ACs fulfilled pre-pipeline under #943. Tests exist at `serve/kanban/tests/test_idtofilename_cache_943.py`.

### Evidence

- **Tests run:** 25 passed, 0 failed in 0.16s
- **Ruff:** clean (no new code written)
- **Coverage:** N/A — no new implementation
- **Files changed:** none

### AC Coverage (verified GREEN)

| AC | Tests | Result |
|----|-------|--------|
| show_task() cache hit — no glob | 3 | PASS |
| show_task() stat-stale — re-reads + updates | 2 | PASS |
| show_task() stat-missing — evicts both caches | 2 | PASS |
| show_task() cold cache — glob fallback | 1 | PASS |
| _find_task_path() cache hit — no glob | 2 | PASS |
| _find_task_path() cold cache — glob fallback | 1 | PASS |
| _find_task_path() warm miss — glob fallback | 2 | PASS |
| refresh_config() clears_id_to_filename | 2 | PASS |

Implementation lives in `serve/kanban/src/owlbear_kanban/engine.py`. Tests use filename `test_idtofilename_cache_943.py` (cosmetic difference from AC-specified name — no rename needed).
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest: 25 passed, 0 failed (0.16s)

### Lint

- ruff: clean

### Coverage

- `owlbear_kanban.engine`: 38% (expected for scoped test file; full suite not in scope for this task)

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage (`TestFromAC_IdToFilenameCache`)

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| show_task() cache hit — no glob, no read_task | test_show_task_warm_cache_does_not_call_glob, _does_not_call_read_task,_returns_correct_task | Yes — mock asserts + task.id check | COVERED |
| show_task() stat-stale — re-reads, updates cache | test_show_task_stale_mtime_triggers_reread, _updates_cache_entry | Yes — status and mtime_ns comparisons | COVERED |
| show_task() stat-missing — evicts + falls to glob | test_show_task_missing_file_evicts_task_cache,_evicts_id_to_filename | Eviction: yes. "Falls to glob": not asserted (impl raises immediately; AC wording acknowledged imprecise by architect) | LAX (no compensating TestBuilderDiscovered) |
| show_task() cold cache — falls to glob | test_show_task_cold_cache_falls_back_to_glob | Yes — task.id == 1 | COVERED |
| _find_task_path() cache hit — no glob | test_find_task_path_warm_cache_does_not_call_glob,_returns_correct_path | Yes — mock assert + path equality | COVERED |
| _find_task_path() cold cache — falls to glob | test_find_task_path_cold_cache_falls_back_to_glob | Yes — result.name.startswith("1-") unambiguous in 3-task board | COVERED |
| _find_task_path() warm miss — falls to glob | test_find_task_path_post_create_warm_miss_falls_back_to_glob | **No — asserts result.exists() only** | **WEAK** |
| refresh_config() clears_id_to_filename | test_refresh_config_clears_id_to_filename, _reachable_after_re_warm | Yes — == {} comparison | COVERED |

**FAIL trigger: AC 7 mapped test has a WEAK assertion.**

`test_find_task_path_post_create_warm_miss_falls_back_to_glob` ([test_idtofilename_cache_943.py:401–409](serve/kanban/tests/test_idtofilename_cache_943.py)):

```python
result = warm_engine._find_task_path(str(new_task.id), warm_engine._tasks_dir)
assert result.exists()
```

If `_find_task_path` returned an existing path for a *different* task, `result.exists()` would still pass. A mutation that returns a wrong-ID path is undetected. Fix: assert `result.name.startswith(str(new_task.id) + "-")` or `result == warm_engine._tasks_dir / expected_filename`.

#### 5.1 Security Review

No issues. Test file uses `tmp_path`; engine cache additions use `int()` conversion before dict lookup; `validate_path_containment` guards all write paths.

#### 5.2 Test Integrity

No builder modifications to `TestFromAC_*` tests detected. `changed_files: []`.

#### 5.3 Test Quality

ADEQUATE overall except one WEAK spot (above, AC 7). All other assertions are specific; error paths covered; test independence strong (all use `tmp_path`); names descriptive.

#### 5.4 Data Safety

`time.sleep(0.01)` for mtime differences at lines 241, 263: potential flakiness on HFS+ or network filesystems (1-second mtime resolution). Matches accepted pattern from `test_mtime_cache_942.py`. Informational only.

#### 5.5 Implementation-Aware Test Gap Analysis

Two gaps noted, both informational given this is a scoped test task:

- `show_task()` warm miss (task created post list_tasks; ID absent from_id_to_filename, cache populated for others) — code path is identical to cold-cache path; exercised indirectly. Low risk.
- `_id_to_filename` populated but `_task_cache` empty simultaneously — reachable via partial cache clear; not directly tested. Low risk.

#### 5.6 Necessity Check

Skipped (no new external dependency).

#### 5.7 Builder Process Quality

1 × `## Builder Notes`, pass-through verdict, no retries. CLEAN.

### Pass 2 — Informational

- `_id_to_filename` rebuild in `list_tasks()` uses `sorted()` unnecessarily (dict lookup order is irrelevant); minor overhead on large boards.
- Test file docstring at line 9 reads "evicts + glob fallback when file missing" — mismatches impl behaviour (raises immediately after eviction). Should read "evicts + raises FileNotFoundError." Cosmetic.

### Deductions

| Finding | Severity | Deduction |
|---|---|---|
| WEAK assertion on AC 7 test (result.exists() only) | FAIL trigger (§5.3) | −0.15 |
| LAX AC 3 (no glob-fallback assertion, no compensating test) | Note (arch-accepted wording imprecision) | −0.05 |

### Verdict

Confidence: **0.80 → FAIL**

Implementation is correct. The sole issue is test quality: the AC 7 test (`test_find_task_path_post_create_warm_miss_falls_back_to_glob`) asserts only `result.exists()`. Strengthen to verify the returned path belongs to the expected task ID.

**Action:** Routed → `todo` (test-writer strengthens weak assertion)

Fix required in `serve/kanban/tests/test_idtofilename_cache_943.py`:

```python
# Replace: assert result.exists()
assert result.name.startswith(str(new_task.id) + "-")
# or:
assert result == warm_engine._tasks_dir / f"{new_task.id}-brand-new-task.md"
```

[[2026-04-17]]

## Test-Writer Notes

### Action taken

Pass-through with assertion fix. All 9 ACs already fulfilled by 25 tests in `serve/kanban/tests/test_idtofilename_cache_943.py` (written under #943). Reviewer routed back to strengthen one weak assertion.

### Fix applied

**File:** `serve/kanban/tests/test_idtofilename_cache_943.py`

`test_find_task_path_post_create_warm_miss_falls_back_to_glob` — replaced:

```python
assert result.exists()
```

with:

```python
assert result.name.startswith(str(new_task.id) + "-"), f"expected path for task {new_task.id}, got: {result.name}"
```

This detects mutations that return an existing-but-wrong-ID path. Consistent with existing pattern at line 384 (`assert result.name.startswith("1-")`).

### Test results

- 25 passed, 0 failed (0.10s for targeted run)
- ruff: clean

### AC Coverage Table

| AC | Tests | Status |
|----|-------|--------|
| show_task() cache hit — no glob, no read_task | 3 | COVERED |
| show_task() stat-stale — re-reads + updates cache | 2 | COVERED |
| show_task() stat-missing — evicts both caches | 2 | COVERED |
| show_task() cold cache — glob fallback | 1 | COVERED |
| _find_task_path() cache hit — no glob | 2 | COVERED |
| _find_task_path() cold cache — glob fallback | 1 | COVERED |
| _find_task_path() warm miss — glob fallback (now mutation-detecting) | 1 | COVERED ✓ STRENGTHENED |
| refresh_config() clears_id_to_filename | 2 | COVERED |
| All tests FAIL (RED) | N/A | Pass-through — impl shipped with #943 |

### Total: 25 tests, all PASS (implementation pre-exists from #943)

[[2026-04-17]]

## Builder Notes

**Verdict: pass-through — no code changes required.**

All ACs fulfilled pre-pipeline under #943. Assertion fix applied by test-writer was already in place.

### Evidence

- **Tests run:** 25 passed, 0 failed in 0.16s (`serve/kanban/tests/test_idtofilename_cache_943.py`)
- **Ruff:** clean (no new code written)
- **Coverage:** N/A — no new implementation files
- **Files changed:** none

### AC Coverage (verified GREEN)

| AC | Tests | Result |
|----|-------|--------|
| show_task() cache hit — no glob, no read_task | 3 | PASS |
| show_task() stat-stale — re-reads + updates cache | 2 | PASS |
| show_task() stat-missing — evicts both caches | 2 | PASS |
| show_task() cold cache — glob fallback | 1 | PASS |
| _find_task_path() cache hit — no glob | 2 | PASS |
| _find_task_path() cold cache — glob fallback | 1 | PASS |
| _find_task_path() warm miss — mutation-detecting assertion | 1 | PASS |
| refresh_config() clears_id_to_filename | 2 | PASS |

Reviewer-flagged weak assertion (`result.exists()`) was already strengthened to `result.name.startswith(str(new_task.id) + "-")` by the test-writer pass. Build verified clean.
[[2026-04-18]]

## Review Evidence

### Test Results

- pytest: 25 passed, 0 failed (0.16s) — independent run via quality-runner

### Lint

- ruff: clean

### Coverage

- `owlbear_kanban.engine`: 38% (expected; scoped test file targeting cache paths only)

### AC Compliance Table

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| show_task() cache hit — no glob, no read_task | test_show_task_warm_cache_does_not_call_glob, _does_not_call_read_task,_returns_correct_task | Yes — mock.assert_not_called + task.id check | COVERED |
| show_task() stat-stale — re-reads + updates cache | test_show_task_stale_mtime_triggers_reread, _updates_cache_entry | Yes — status equality + mtime_ns comparison | COVERED |
| show_task() stat-missing — evicts both caches | test_show_task_missing_file_evicts_task_cache,_evicts_id_to_filename | Eviction: yes. "Falls to glob": not asserted (impl raises; arch-accepted wording imprecision from prior cycle) | LAX (arch-accepted) |
| show_task() cold cache — glob fallback | test_show_task_cold_cache_falls_back_to_glob | Yes — task.id == 1 | COVERED |
| _find_task_path() cache hit — no glob | test_find_task_path_warm_cache_does_not_call_glob,_returns_correct_path | Yes — mock.assert_not_called + path equality | COVERED |
| _find_task_path() cold cache — glob fallback | test_find_task_path_cold_cache_falls_back_to_glob | Yes — result.name.startswith("1-") | COVERED |
| _find_task_path() warm miss — glob fallback | test_find_task_path_post_create_warm_miss_falls_back_to_glob | Yes — result.name.startswith(str(new_task.id) + "-") — STRENGTHENED ✓ | COVERED |
| refresh_config() clears_id_to_filename | test_refresh_config_clears_id_to_filename, _reachable_after_re_warm | Yes — == {} equality | COVERED |
| All tests FAIL (RED) | N/A | N/A — implementation shipped with #943 | N/A |

### Test Integrity (5.2)

No TestFromAC_* tests weakened or removed. AC 7 test STRENGTHENED from `result.exists()` to `result.name.startswith(str(new_task.id) + "-")` — previous cycle's WEAK trigger resolved.

### Security (5.1)

No issues. Tests use tmp_path; engine uses int() conversion before dict lookup; validate_path_containment guards write paths.

### Test Quality (5.3)

STRONG overall. Assertion specificity: specific values, mock assertions, dict equality. Error paths covered (FileNotFoundError, ValueError). Test independence: all use tmp_path. Names descriptive.

### Implementation-Aware Gap Analysis (5.5)

- show_task() warm miss (ID absent from_id_to_filename after create): code path identical to cold-cache; indirectly exercised. Low risk.
- `search_dir != _tasks_dir` path: covered by test_find_task_path_search_dir_not_tasks_dir_uses_glob with glob call assertion.

### Informational

- `time.sleep(0.01)` for mtime differences: potential flakiness on HFS+/network filesystems. Accepted pattern matching test_mtime_cache_942.py.
- Test file docstring at line 9 says "evicts + glob fallback when file missing" but impl raises immediately after eviction — cosmetic mismatch, not a defect.

### Deductions

| Finding | Severity | Deduction |
|---|---|---|
| LAX AC 3 (arch-accepted wording imprecision, same from prior cycle) | Note | −0.03 |
| Informational items (sleep flakiness, docstring) | Cosmetic | −0.02 |

### Verdict

Confidence: **0.95 → PASS**

Previous-cycle FAIL trigger (WEAK assertion on AC 7) correctly resolved by test-writer. All 8 functional ACs COVERED with mutation-detecting assertions. Tests pass independently. Lint clean. Implementation verified at engine.py L137, L186, L274-278, L335-342, L915-921.
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure test task — only `test_idtofilename_cache_943.py` assertion strengthened; no application behavior, API, or conventions changed; copilot-instructions.md unchanged |
| 2 | Module docstrings | No | N/A | Only test file modified; test file has module-level docstring (lines 1–13); test file docstring notes "All tests FAIL in RED phase" — reviewer-acknowledged cosmetic note, not a public API docstring |
| 3 | External attribution | No | N/A | No external repos, articles, or patterns referenced in task body, research, or implementation |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/extend-mtime-cache-943.md` exists; linked from task body ("See `.owlbear/research/extend-mtime-cache-943.md` for approach"); no follow-up tasks needed per researcher findings |

### Files Updated

- None

### Scratch Files Cleaned

- None found (`.owlbear/scratch/945-*` — no matches)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| show_task() cache hit | 3 tests: test_show_task_warm_cache_does_not_call_glob, _does_not_call_read_task,_returns_correct_task | PASS |
| show_task() stat-stale | 2 tests: test_show_task_stale_mtime_triggers_reread, _updates_cache_entry | PASS |
| show_task() stat-missing | 2 tests: eviction verified; "falls to glob" wording imprecise (impl raises after eviction) — arch-accepted | PASS (LAX) |
| show_task() cold cache | 1 test: test_show_task_cold_cache_falls_back_to_glob | PASS |
| _find_task_path() cache hit | 2 tests: _does_not_call_glob, _returns_correct_path | PASS |
| _find_task_path() cold cache | 1 test: _falls_back_to_glob | PASS |
| _find_task_path() warm miss | 1 test: _post_create_warm_miss — STRENGTHENED assertion verified at L408: result.name.startswith(str(new_task.id) + "-") | PASS |
| refresh_config() clears dict | 2 tests: _clears_id_to_filename, _reachable_after_re_warm | PASS |
| All tests FAIL (RED) | N/A — implementation shipped with #943; pass-through acknowledged by all agents | N/A |

### Test Results

- pytest: 332 passed, 6 failed (all failures in knowledge package — unrelated to kanban cache scope)
- ruff: clean

### Architect Quality: 4/5

ACs were specific and decomposed well (8 functional ACs covering hit/miss/stale/eviction/clear). Minor imprecision on AC 3 ("falls to glob" vs actual raise-after-eviction behavior). 25 tests emerged naturally. Good edge-case coverage.

### Deduction Breakdown

| Criterion | Deduction |
|-----------|-----------|
| AC 3 wording imprecision (arch-accepted, non-blocking) | -0.01 |
| 6 test failures outside task scope (knowledge pkg, pre-existing) | -0.00 |
| Cannot verify git commit status (no terminal access) | -0.01 |
| Lint violations | -0.00 |
| Missing reviewer evidence | -0.00 |

### Confidence: 0.98

### Action: archive

### Notes

- Reviewer caught WEAK assertion on AC 7 in first cycle (0.80 FAIL), test-writer fixed it, second review confirmed (0.95 PASS). Pipeline self-correction worked correctly.
- All kanban tests pass (25/25 in scoped file, 0 kanban failures in full suite).
- Deliverable file verified on disk: serve/kanban/tests/test_idtofilename_cache_943.py with strengthened assertion at L408.
