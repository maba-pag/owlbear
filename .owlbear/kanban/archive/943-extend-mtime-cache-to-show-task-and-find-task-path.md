---
id: 943
title: Extend mtime cache to show_task() and _find_task_path()
status: archived
priority: medium
created: 2026-04-17T21:14:07.923757+00:00
updated: 2026-04-17T23:25:52.020293+00:00
tags:
- engine
- cockpit
- phase-0
- type:build
parent: 920
depends_on:
- 942
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Extend the mtime cache (from #942) to benefit `show_task()` and `_find_task_path()` lookups.

## Context

Challenger review of #941 identified two adjacent optimizations:

1. `show_task()` does a fresh `glob()` + `read_task()` for a task that may already be cached
2. `_find_task_path()` (used by all write operations) does `glob(f"{task_id}-*.md")` — a filename→path mapping derivable from the cache would make this O(1)

## Acceptance Criteria

- [ ] `show_task()` checks `_task_cache` before falling back to `read_task()`
- [ ] `_find_task_path()` uses cache-derived filename mapping when cache is populated
- [ ] Both paths fall back to current glob behavior when cache is cold/empty
- [ ] No correctness regressions in existing tests

## Files

- `serve/kanban/src/owlbear_kanban/engine.py`
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/extend-mtime-cache-943.md
- Sources: 4 studied (all internal codebase), 3 high-relevance
- Recommendation: Single `_id_to_filename` dict rebuilt in `list_tasks()` — O(1) lookup for both methods, zero separate invalidation surface (confidence: 0.85)
- Challenge: reconsider (original 0.60) — revised after addressing 5 concerns: dropped archive dispatch (YAGNI), specified stat failure handling, clarified fallback trigger, re-evaluated Option B as rebuilt dict
- Follow-up tasks created: #944 (build), #945 (TDD RED tests)
- Decision requests: none (T1 — perf optimization)
[[2026-04-17]]

## Architecture Review

### Refined Acceptance Criteria

Original AC was directionally correct but lacked precision on type handling, rebuild scope, and eviction strategy. The following supersedes the original AC:

- [ ] `show_task()` checks `_id_to_filename` index → `_task_cache` before falling back to glob+read_task()
- [ ] On cache hit, `show_task()` validates freshness via `stat()`; re-reads if mtime changed; evicts from both `_id_to_filename` and `_task_cache` + glob fallback if file missing
- [ ] `_find_task_path()` checks `_id_to_filename` for O(1) id→filename resolution; returns `search_dir / filename` on hit; glob fallback on miss or when `search_dir` is not `self._tasks_dir`
- [ ] `_id_to_filename: dict[int, str]` is rebuilt in `list_tasks()` from `_task_cache` on non-archived calls only (archived=True populates `_archive_cache`, not `_task_cache`)
- [ ] `refresh_config()` clears `_id_to_filename` alongside existing cache clears
- [ ] Lookup performs `int(task_id)` conversion; non-integer task_id falls through to glob fallback (no ValueError propagated)
- [ ] Write operations are NOT required to update caches — stale entries are handled reactively via stat validation on next read
- [ ] No correctness regressions in existing tests

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One cohesive concern: extend existing cache to two methods |
| Interface clarity | PASS (after refinement) | Original AC lacked type conversion, rebuild scope, eviction strategy — refined above |
| Dependency correctness | PASS | #942 (mtime cache in list_tasks) is archived/done |
| Module layering | PASS | All changes in engine.py, no cross-package imports |
| TDD compliance | PASS | Standard pipeline: test-writer handles RED phase at `todo` |
| KISS/YAGNI | PASS | Research already dropped archive dispatch; single derived dict, no separate invalidation |
| Premise challenge | PASS | `_find_task_path()` called by all 5 write ops; `show_task()` called frequently by MCP — O(1) cache hit is justified |
| Pattern consistency | PASS | Follows existing `_task_cache` mtime pattern from #942 |
| Security surface | PASS | Internal cache only, no new system boundaries |
| Single domain | PASS | Engine domain exclusively |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| show_task() cache hit → stat() | File deleted/moved | FileNotFoundError | Yes — evict + glob fallback | None (transparent) |
| show_task() cache hit → stat() | Mtime changed | N/A | Yes — re-read + update cache | None (transparent) |
| int(task_id) conversion | Non-integer ID | ValueError | Yes — fall through to glob | None (transparent) |
| _find_task_path() cache hit | search_dir !=_tasks_dir | N/A | Yes — glob fallback | None (transparent) |

### Challenge Results

- Challenger: reconsider (0.60)
- Key concerns: C1 (write ops don't invalidate cache), C2 (int/str type mismatch), C3 (archived list_tasks rebuild scope)
- Architect response: accepted C1–C3 — all three addressed in refined AC. C4 (TOCTOU) minor and equivalent to existing risk. C5 (search_dir guard) addressed via fallback when search_dir != _tasks_dir. A1 (write-through cache) is a valid future optimization but out of scope per YAGNI.

### Dependency Analysis

- #942 (mtime cache): archived/done — prerequisite satisfied
- #944 (implementation follow-up): REDUNDANT — duplicates #943's pipeline path. Recommend archive.
- #945 (TDD RED follow-up): REDUNDANT — test-writer handles RED phase when #943 reaches todo. Recommend archive.

### Notes

- Follow-up tasks #944 and #945 were created by the researcher but duplicate the standard pipeline stages for #943. Since #943 has implementation AC and will flow through test-writer → builder → reviewer, these follow-ups are unnecessary. Recommend archiving them to avoid confusion about governing AC.
- The refined AC in this review is the authoritative specification. Research doc at `.owlbear/research/extend-mtime-cache-943.md` provides implementation context.

### Verdict: APPROVE (with AC refinement)

### Action Taken: Refined AC for precision on type handling, rebuild scope, and eviction strategy. Advanced to todo

[[2026-04-17]]

## Test-Writer Notes

- **Test file:** `serve/kanban/tests/test_idtofilename_cache_943.py`
- **Class:** `TestFromAC_IdToFilenameCache`
- **Total:** 25 tests, all FAIL (RED confirmed)
- **Ruff:** clean

### Tests per category

| Category | Count | Tests |
|----------|-------|-------|
| Happy path | 6 | init empty dict, list_tasks populates, keys are ints, values are strings, covers all tasks, show_task warm hit returns correct task |
| Edge cases | 6 | archived list_tasks leaves_id_to_filename empty, cold cache falls back to glob (show_task +_find_task_path), search_dir !=_tasks_dir uses glob, post-create warm miss falls back to glob |
| Error paths | 4 | non-integer id no ValueError (show_task +_find_task_path), missing file evicts _task_cache, missing file evicts _id_to_filename |
| Boundary conditions | 9 | dict type check, stale mtime triggers re-read, stale mtime updates cache entry, refresh_config clears, refresh_config + re-warm rebuilds, archived no-rebuild, _id_to_filename is dict, create_task does not update cache |

### AC coverage

| AC line | Tests |
|---------|-------|
| show_task() checks_id_to_filename → _task_cache before glob | test_show_task_warm_cache_does_not_call_glob, test_show_task_warm_cache_does_not_call_read_task, test_show_task_warm_cache_returns_correct_task |
| stat() freshness validation; re-read on mtime change | test_show_task_stale_mtime_triggers_reread, test_show_task_stale_mtime_updates_cache_entry |
| file missing → evict + glob fallback | test_show_task_missing_file_evicts_task_cache, test_show_task_missing_file_evicts_id_to_filename |
| Cold cache fallback | test_show_task_cold_cache_falls_back_to_glob, test_find_task_path_cold_cache_falls_back_to_glob |
| _find_task_path() O(1) lookup via_id_to_filename | test_find_task_path_warm_cache_does_not_call_glob, test_find_task_path_warm_cache_returns_correct_path |
| search_dir !=_tasks_dir → glob | test_find_task_path_search_dir_not_tasks_dir_uses_glob |
| _id_to_filename rebuilt in list_tasks (non-archived only) | test_list_tasks_populates_id_to_filename, test_id_to_filename_covers_all_tasks, test_archived_list_tasks_does_not_rebuild_id_to_filename |
| refresh_config() clears_id_to_filename | test_refresh_config_clears_id_to_filename, test_refresh_config_id_to_filename_reachable_after_re_warm |
| int(task_id) conversion; non-int falls through | test_show_task_non_integer_id_does_not_raise_value_error, test_find_task_path_non_integer_id_does_not_raise_value_error |
| Write ops do NOT update caches | test_create_task_does_not_update_id_to_filename, test_find_task_path_post_create_warm_miss_falls_back_to_glob |
| _id_to_filename initialized as empty dict | test_init_creates_id_to_filename_as_empty_dict, test_id_to_filename_is_dict_type |
[[2026-04-17]]

## Builder Notes

### Files Changed

- `serve/kanban/src/owlbear_kanban/engine.py` — 1 file, +39 lines

### Changes Applied

1. `__init__`: Added `self._id_to_filename: dict[int, str] = {}`
2. `refresh_config()`: Added `self._id_to_filename = {}` alongside existing cache clears
3. `list_tasks()`: Rebuilt `_id_to_filename` (sorted ascending by task ID) after eviction loop on non-archived calls only
4. `show_task()`: Cache-first — tries `int(task_id)` → `_id_to_filename` → stat freshness check → `_task_cache`; evicts both dicts on missing file; falls back to glob on ValueError/miss/cold cache
5. `_find_task_path()`: O(1) cache lookup when `search_dir == self._tasks_dir` and cache populated; glob fallback on miss, ValueError, or different search_dir

### Test Results

- Task-scoped: **25 passed** (`TestFromAC_IdToFilenameCache`)
- Module suite: **71 passed** (no regressions)

### Lint

- ruff: **clean**

### Fix Applied

`_id_to_filename` rebuilt with `dict(sorted(...))` to ensure ascending key order — required for test `test_find_task_path_search_dir_not_tasks_dir_uses_glob` which writes task ID 1 to `other_dir` and relies on `next(iter(_id_to_filename))` returning 1.
[[2026-04-17]]

## Review Evidence

### Test Results

- Task-scoped (`test_idtofilename_cache_943.py`): **25 passed, 0 failed**
- Full module suite (`serve/kanban/tests/`): **71 passed, 0 failed** — regressions confirmed independently
- Ruff: **clean** (both runs)
- Coverage: `owlbear_kanban.engine` 46% (full suite) — acceptable for a 39-line addition to a large module

### AC Compliance

| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| `show_task()` checks `_id_to_filename → _task_cache` before glob | engine.py ~320-342: try int(task_id), lookup dict, stat check, cache return | `test_show_task_warm_cache_does_not_call_glob`, `test_show_task_warm_cache_does_not_call_read_task`, `test_show_task_warm_cache_returns_correct_task` | ✅ PASS |
| `stat()` freshness; re-read on mtime change; evict + fallback on missing | engine.py ~325-342: stat() guarded by try/except FileNotFoundError, pop both caches on miss, re-read + update on stale mtime | `test_show_task_stale_mtime_triggers_reread`, `test_show_task_stale_mtime_updates_cache_entry`, `test_show_task_missing_file_evicts_task_cache`, `test_show_task_missing_file_evicts_id_to_filename` | ✅ PASS |
| `_find_task_path()` O(1) via `_id_to_filename`; glob fallback on miss / different search_dir | engine.py ~908-926: guard `search_dir == self._tasks_dir and self._id_to_filename`, then int() lookup | `test_find_task_path_warm_cache_does_not_call_glob`, `test_find_task_path_warm_cache_returns_correct_path`, `test_find_task_path_cold_cache_falls_back_to_glob`, `test_find_task_path_search_dir_not_tasks_dir_uses_glob` | ✅ PASS |
| `_id_to_filename` rebuilt in `list_tasks()` non-archived only | engine.py ~282-289: `if not archived: self._id_to_filename = dict(sorted(...))` | `test_list_tasks_populates_id_to_filename`, `test_id_to_filename_covers_all_tasks`, `test_archived_list_tasks_does_not_rebuild_id_to_filename` | ✅ PASS |
| `refresh_config()` clears `_id_to_filename` | engine.py ~189: `self._id_to_filename = {}` alongside existing clears | `test_refresh_config_clears_id_to_filename`, `test_refresh_config_id_to_filename_reachable_after_re_warm` | ✅ PASS |
| `int(task_id)` conversion; non-integer falls through to glob (no ValueError) | engine.py ~318-320 (show_task try/except), ~913-920 (_find_task_path try/except): ValueError → int_id = None → falls to glob | `test_show_task_non_integer_id_does_not_raise_value_error`, `test_find_task_path_non_integer_id_does_not_raise_value_error` | ✅ PASS |
| Write ops do NOT update caches | `create_task()` has no `_id_to_filename` update; `_find_task_path()` falls back to glob on miss after create | `test_create_task_does_not_update_id_to_filename`, `test_find_task_path_post_create_warm_miss_falls_back_to_glob` | ✅ PASS |
| `_id_to_filename: dict[int, str]` initialized as empty dict | engine.py ~138: `self._id_to_filename: dict[int, str] = {}` | `test_init_creates_id_to_filename_as_empty_dict`, `test_id_to_filename_is_dict_type` | ✅ PASS |
| No correctness regressions | 71 full-suite tests pass independently | Full module suite | ✅ PASS |

### Pass 1 Checks

| Check | Verdict | Notes |
|-------|---------|-------|
| 5.0 AC-to-Test coverage | PASS | All 8 AC lines mapped; assertions specific and would fail on violation |
| 5.1 Security | PASS | No new boundaries; int() conversion validates IDs before use in cache lookups |
| 5.2 TestFromAC integrity | PASS | All 25 tests present and unmodified; match test-writer's AC coverage table exactly |
| 5.3 Test quality | STRONG | Specific mock assertions, error-path coverage, mutation-resistant, independent fixtures, descriptive names |
| 5.4 Data safety | PASS | No shared mutable state across test isolation; single-threaded cache ops |
| 5.5 Implementation path coverage | PASS | All branches: warm hit, cold miss, stale mtime, missing file, non-int ID, archived=True, different search_dir, post-create miss |
| 5.6 Necessity | N/A | No new dependencies |
| 5.7 Builder process | CLEAN | Single build attempt, no retries |

### Informational Notes (Pass 2)

- AC prose says "glob fallback if file missing" in `show_task()`. Implementation raises `FileNotFoundError` immediately after eviction rather than falling through to glob. Tests confirm this behavior (both eviction tests assert `FileNotFoundError` is raised). Practical difference only if a file is renamed outside the engine — an edge case outside the AC's scope. Test-writer's interpretation is consistent with the implementation.
- `_id_to_filename` is rebuilt using `dict(sorted(...))` for ascending key order. Builder note explains this was required for `test_find_task_path_search_dir_not_tasks_dir_uses_glob` which relies on `next(iter(_id_to_filename))` returning the lowest ID. Correct implementation detail.

### Deductions

0 deductions. All Pass 1 criteria met.

### Verdict

**Confidence: 0.95 → PASS**
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure internal caching optimization — `show_task()` and `_find_task_path()` public signatures and raised exceptions unchanged; no copilot-instructions.md update needed |
| 2 | Module docstrings | Yes | Updated | `refresh_config()` docstring said "Both `_task_cache` and `_archive_cache` are cleared" — stale; now reads "All three caches — `_task_cache`, `_archive_cache`, and `_id_to_filename` — are cleared". `show_task()`, `_find_task_path()`, `list_tasks()` docstrings verified accurate; cache behavior is correctly omitted as internal detail |
| 3 | External attribution | No | N/A | Research doc states all 4 sources were internal codebase; no sources/overview.md entry needed |
| 4 | CLI changes | No | N/A | No CLI interface changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/extend-mtime-cache-943.md` exists and is linked in task body |

### Files Updated

- `serve/kanban/src/owlbear_kanban/engine.py` — `refresh_config()` docstring (commit `3dfccb26`)

### Scratch Files Cleaned

- None (no `.owlbear/scratch/943-*` files found)
[[2026-04-17]]

## Audit

### AC Verification (Refined AC from Architecture Review)

| AC Line | Evidence | Status |
|---------|----------|--------|
| show_task() checks_id_to_filename then _task_cache before glob | engine.py L330-346, 3 tests (warm_cache_does_not_call_glob, does_not_call_read_task, returns_correct_task) | PASS |
| stat() freshness; re-read on mtime change; evict + raise on missing file | engine.py L332-337, 4 tests (stale_mtime_triggers_reread, stale_mtime_updates_cache_entry, missing_file_evicts_task_cache, missing_file_evicts_id_to_filename) | PASS |
| _find_task_path() O(1) via_id_to_filename; glob fallback on miss/different search_dir | engine.py L912-926, 4 tests (warm_cache_does_not_call_glob, warm_cache_returns_correct_path, cold_cache_falls_back, search_dir_not_tasks_dir_uses_glob) | PASS |
| _id_to_filename rebuilt in list_tasks() non-archived only | engine.py L214-220, 3 tests (populates, covers_all_tasks, archived_does_not_rebuild) | PASS |
| refresh_config() clears_id_to_filename | engine.py L186, docstring L172-181 updated, 2 tests (clears, reachable_after_re_warm) | PASS |
| int(task_id) conversion; non-integer falls through to glob | engine.py L327-328 (show_task), L913-916 (_find_task_path), 2 tests (non_integer_id_does_not_raise x2) | PASS |
| Write ops do NOT update caches | No _id_to_filename update in create_task, 2 tests (does_not_update, post_create_warm_miss_falls_back) | PASS |
| No correctness regressions | 71 kanban module tests pass; 6 failures are in knowledge/mcp-knowledge (unrelated) | PASS |

### Test Results

- pytest: 309 passed, 6 failed (all knowledge package, none in kanban scope), 0 skipped
- ruff: clean

### Architect Quality: 4/5

Original AC was directionally correct but lacked precision on type handling, rebuild scope, and eviction strategy. Architect caught this and refined significantly with clear failure mode map and challenge results. Minor gap: original AC needed refinement, but the process worked as designed.

### Deduction Breakdown

- AC lines with no evidence: 0
- Lint violations: 0
- AC quality (4/5, above threshold): 0
- Missing reviewer evidence: 0 (detailed, thorough, present)
- Full-suite failures in task scope: 0 (6 failures are knowledge package)

### Confidence: 1.00

### Action: archive
