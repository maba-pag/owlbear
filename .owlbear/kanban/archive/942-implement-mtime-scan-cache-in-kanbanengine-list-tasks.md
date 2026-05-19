---
id: 942
title: Implement mtime-scan cache in KanbanEngine.list_tasks()
status: archived
priority: needed
created: 2026-04-17T21:13:56.835009+00:00
updated: 2026-04-17T22:49:10.960946+00:00
tags:
- engine
- cockpit
- phase-0
- type:build
parent: 920
depends_on:
- 941
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Add mtime-based in-memory task cache to `KanbanEngine` so `list_tasks()` re-parses only changed files.

## Context

Research #941 (`.owlbear/research/mtime-cache-941.md`) validated the approach and corrected several AC items from the original specification.

## Acceptance Criteria

- [ ] `KanbanEngine.__init__` initializes two caches: `_task_cache: dict[str, tuple[int, Task]]` and `_archive_cache: dict[str, tuple[int, Task]]` (keyed by filename, valued by `(st_mtime_ns, Task)`)
- [ ] `list_tasks()` uses `os.scandir()` + `entry.stat().st_mtime_ns` to detect new/deleted/modified files
- [ ] Only modified/new files are re-parsed; cached `Task` objects returned for unchanged files
- [ ] Cache eviction for deleted files: entries not seen in scandir are removed
- [ ] `refresh_config()` clears both caches (directory paths may change)
- [ ] Non-existent `archive_dir` handled gracefully (empty list, no crash)
- [ ] Engine `revision` counter continues incrementing on writes (cache is orthogonal)
- [ ] Invalidation is lazy (scandir-driven) — write operations do NOT proactively update the cache
- [ ] Cold load latency unchanged from current behavior
- [ ] Warm read p99 <50ms at 1500 tasks (benchmark verification via `tests/benchmarks/bench_list_tasks.py`)

## Design Notes

- Cache type: `dict[str, tuple[int, Task]]` — `str` filename key, `int` st_mtime_ns (NOT float — float truncates at current epoch ns values)
- `os.scandir()` on Unix requires a syscall per `DirEntry.stat()` — not free, but avoids glob fnmatch overhead
- Projected warm-read: ~35ms at 1500 tasks (scandir+stat ~15ms + filter/sort/convert ~20ms)
- `write_task()` uses atomic `tempfile` → `Path.replace()` which updates mtime naturally
- `move_task()` / `end_work()` move files between dirs — lazy eviction handles this correctly
- ~35 LOC total: ~25 in `list_tasks()`, ~5 in `__init__`, ~5 in `refresh_config()`

## Files

- `serve/kanban/src/owlbear_kanban/engine.py`
- `tests/benchmarks/bench_list_tasks.py` (add warm-read scenario)
- Tests in `serve/kanban/tests/` or `tests/`
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/mtime-cache-impl-942.md
- Sources: 6 studied, 5 high-relevance (all internal — codebase + benchmark run)
- Recommendation: Proceed with implementation as specified (confidence: 0.85)
- Baseline established: 1500 tasks p50=408ms, p99=453ms (target <50ms warm p99)
- Challenger review: 6 concerns — 3 accepted (race condition guard, benchmark cache-hit scenario, explicit cache-miss path), 2 noted out-of-scope, 1 rejected
- AC corrections: (1) guard os.scandir() for non-existent dirs, (2) suppress FileNotFoundError in read_task race, (3) add cache-hit benchmark scenario, (4) explicit cache-miss-→-read-→-insert path
- Follow-up tasks created: none (existing #943 covers show_task/find_task_path extension)
- Decision requests: none
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: mtime cache for `list_tasks()` |
| Interface clarity | PASS | Data structures, behaviors, and touchpoints fully specified |
| Dependency correctness | PASS | #941 archived (done), no missing deps |
| Module layering | PASS | Changes within `engine.py` only, no cross-package imports |
| TDD compliance | PASS | `type:build` flows through test-writer; test files listed |
| KISS/YAGNI | PASS | ~35 LOC, instance-level cache, no over-engineering |
| Premise challenge | PASS | Benchmark evidence: 408ms p50 at 1500 tasks vs 50ms target |
| Pattern consistency | PASS | Instance-level state (like `_config`, `_revision`), lazy invalidation matches atomic write pattern |
| Security surface | PASS | No new external inputs or boundaries |
| Single domain | PASS | Engine internals only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `os.scandir()` on non-existent `archive_dir` | Dir doesn't exist | FileNotFoundError | AC #6 requires graceful handling | None if handled |
| `read_task()` after scandir | File deleted between scandir and read | FileNotFoundError | **AC addition below** — suppress + evict | None if handled |
| scandir on non-`.md` files | Temp files, `.DS_Store` fed to `read_task()` | ValueError | **AC addition below** — filter `.md` only | Phantom cache entries if unfiltered |

### AC Refinements (binding)

Two AC items added — test-writer and builder must treat these as part of the AC:

1. **Suffix filtering:** `list_tasks()` scandir must filter to `.md` entries only. Non-task files (temp files from `write_task()` using `tempfile.mkstemp`, `.DS_Store`, editor swap files) must be excluded. The current `glob("*.md")` provides this filtering implicitly; `os.scandir()` does not.

2. **Race condition guard:** `FileNotFoundError` during `read_task()` in the scandir loop must be suppressed (file deleted between scandir and read). If the file was in the cache, evict the entry. This extends the existing `contextlib.suppress(ValueError, KeyError)` pattern at `engine.py` L233.

### Challenge Results

- Challenger: reconsider (confidence 0.62)
- 4 concerns raised: C1 (benchmark threshold) — noted, documentation-level verification appropriate for hardware-dependent perf targets; C2 (`.md` suffix filtering) — **accepted**, added as binding AC refinement; C3 (double MCP conversion) — minor, out of scope; C4 (transient archive inconsistency) — minor, eventual consistency correct
- Blind spots on `show_task()`/`sweep()` uncached — explicitly out of scope, #943 covers extension
- Architect response: accepted C2, added 2 binding AC refinements, override on C1 (CI-fragile absolute thresholds)

### Verdict: APPROVE

### Action Taken: Advanced to todo with 2 binding AC refinements (suffix filtering, race condition guard)

[[2026-04-17]]

## Test-Writer Notes

- Test file: serve/kanban/tests/test_mtime_cache_942.py
- Benchmark: tests/benchmarks/bench_list_tasks.py (warm-cache p99 scenario added)
- Classes: TestFromAC_MtimeCache
- Tests per category: happy 7, edge 6, error 4, boundary 4
- Total: 21 unit tests (all FAIL) + 1 benchmark assertion (FAIL, p99 ~450ms vs <50ms target)
- ruff: clean

**AC coverage:**

| AC | Tests |
|----|-------|
| 1. _task_cache/_archive_cache init | test_init_creates_task_cache_as_empty_dict, test_init_creates_archive_cache_as_empty_dict |
| 2. os.scandir + mtime_ns | test_cache_entry_is_int_mtime_ns_task_tuple (verifies int mtime_ns type) |
| 3. Only modified/new re-parsed | test_unchanged_file_not_reparsed_on_warm_call, test_cold_call_populates_task_cache, test_warm_call_returns_same_task_ids, test_modified_file_triggers_reparsing_and_cache_update |
| 4. Deleted file eviction | test_deleted_file_evicted_from_task_cache, test_deleted_file_absent_from_results_after_eviction |
| 5. refresh_config clears caches | test_refresh_config_clears_task_cache, test_refresh_config_clears_archive_cache |
| 6. Non-existent archive_dir graceful | test_nonexistent_archive_dir_returns_empty_list, test_nonexistent_archive_dir_does_not_raise |
| 7. Revision counter orthogonal | test_revision_increments_after_create_with_warm_cache, test_revision_increments_after_edit_with_warm_cache |
| 8. Lazy invalidation | test_edit_does_not_proactively_update_task_cache, test_cache_updated_lazily_on_next_list_tasks |
| 9. Suffix filtering (arch) | test_non_md_files_not_added_to_task_cache, test_non_md_files_not_in_list_tasks_results |
| 10. Race condition guard (arch) | test_race_condition_fileerror_during_read_task_suppressed, test_race_condition_evicts_entry_from_cache_when_file_gone |
| Benchmark p99<50ms | test_warm_cache_p99_under_50ms_at_1500_tasks (bench_list_tasks.py) |

Commit: cc642b4c
[[2026-04-17]]

## Builder Notes

### Status: REJECT → todo (infeasible test assumption)

### Implementation completed (20/21 tests pass, ruff clean)

Files changed:

- `serve/kanban/src/owlbear_kanban/engine.py` — added `import os`; `_task_cache`/`_archive_cache` in `__init__`; cache clear in `refresh_config()`; replaced `source_dir.glob("*.md")` loop with `os.scandir()` + mtime-based cache in `list_tasks()`; added `noqa: PLR0915`

### Test results: 20 passed, 1 failed

| Category | Count |
|----------|-------|
| AC 1 (cache init) | 2 PASS |
| AC 2+3 (warm cache, no re-parse) | 4 PASS |
| AC 4 (deleted file eviction) | 2 PASS |
| AC 5 (refresh_config clears caches) | 2 PASS |
| AC 6 (non-existent archive_dir) | 2 PASS |
| AC 7 (revision orthogonal) | 2 PASS |
| AC 8 (lazy invalidation) | 2 PASS |
| AC 9 (suffix filtering) | 2 PASS |
| AC 10 (race condition) | 1 PASS, **1 FAIL** |

### Failing test: `test_race_condition_evicts_entry_from_cache_when_file_gone`

**Root cause — infeasible test assumption:**

The test patches `owlbear_kanban.engine.read_task` to raise `FileNotFoundError` for `target_name` and then calls `eng.list_tasks()`. For the eviction to occur, `read_task` must be called for `target_name`. With a correct mtime cache this only happens on a **cache miss** (mtime changed or file not in cache). But the test does NOT modify `target_name` between the cold call and the warm call, so `st_mtime_ns` is identical on both scandir passes → cache hit → `read_task` is never called → no eviction.

This directly contradicts `test_unchanged_file_not_reparsed_on_warm_call` (AC 3), which asserts `mock_read.assert_not_called()` for all files with unchanged mtime. Both tests cannot pass simultaneously under the current test setup.

**Fix needed (test-writer rewrites):**

`test_race_condition_evicts_entry_from_cache_when_file_gone` must modify the target file before the patched warm call to change its mtime and trigger a cache miss:

```python
# Force mtime change to trigger cache miss
time.sleep(0.01)
(tasks_dir / target_name).write_bytes((tasks_dir / target_name).read_bytes())
# Now patch read_task: cache miss will call it, which raises FileNotFoundError → evict
with patch("owlbear_kanban.engine.read_task", side_effect=patched_read):
    eng.list_tasks()
assert target_name not in eng._task_cache
```

### Ruff: clean

[[2026-04-17]]

## Test-Writer Notes

- Retry: fixed `test_race_condition_evicts_entry_from_cache_when_file_gone` (builder-rejected)
- Root cause: test patched `read_task` but target file had unchanged mtime → cache hit → `read_task` never called → eviction never triggered
- Fix: added `time.sleep(0.01)` + `target.write_bytes(target.read_bytes())` before the patched call to force an mtime change, ensuring a cache miss that invokes `read_task`, which raises `FileNotFoundError`, triggering eviction
- All 21 existing tests now PASS (builder implementation already correct for 20/21; fixed test verifies the 21st)
- ruff: clean
- Commit: 563b06d5
[[2026-04-17]]

## Builder Notes

### Status: DONE → review

### Files changed

- `serve/kanban/src/owlbear_kanban/engine.py` — added `import os`; `_task_cache`/`_archive_cache` in `__init__`; cache clear in `refresh_config()`; replaced `source_dir.glob("*.md")` loop with `os.scandir()` + mtime-based cache in `list_tasks()`; added `noqa: PLR0915`
- Commit: 5e8e0b16

### Test results: 21 passed, ruff clean

| AC | Tests | Status |
|----|-------|--------|
| 1. _task_cache/_archive_cache init | 2 | PASS |
| 2+3. Warm cache / no re-parse | 4 | PASS |
| 4. Deleted file eviction | 2 | PASS |
| 5. refresh_config clears caches | 2 | PASS |
| 6. Non-existent archive_dir | 2 | PASS |
| 7. Revision orthogonal | 2 | PASS |
| 8. Lazy invalidation | 2 | PASS |
| 9. Suffix filtering (arch) | 2 | PASS |
| 10. Race condition guard (arch) | 2 | PASS |

Previously rejected test `test_race_condition_evicts_entry_from_cache_when_file_gone` fixed by test-writer (forced mtime change via `write_bytes` before patching `read_task`). Implementation was correct throughout.

### Benchmark: test_warm_cache_p99_under_50ms_at_1500_tasks

- Warm p99 = 12.2ms at 1500 tasks (target <50ms) ✓
- Cold load = 405ms (unchanged baseline)

### Lint: ruff clean

[[2026-04-17]]

## Review Evidence

### Test Results

- pytest: 32 passed, 0 failed (21 unit tests in test_mtime_cache_942.py + 11 benchmark parametrizations in bench_list_tasks.py)

### Lint: clean (ruff 0 violations)

### Coverage: owlbear_kanban.engine: 41%

41% on full engine module is expected — test file scopes to new cache code only (list_tasks, **init**, refresh_config). Other engine methods are covered by pre-existing test suite.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 1. _task_cache/_archive_cache init | test_init_creates_task_cache_as_empty_dict, test_init_creates_archive_cache_as_empty_dict | Yes — `== {}` asserts specific type and emptiness | COVERED |
| 2. os.scandir + st_mtime_ns | test_cache_entry_is_int_mtime_ns_task_tuple | Yes — `isinstance(mtime_ns, int)` fails on float truncation | COVERED |
| 3. Only modified/new re-parsed | test_unchanged_file_not_reparsed_on_warm_call (mock_read.assert_not_called), test_modified_file_triggers_reparsing_and_cache_update | Yes — mock catches any spurious re-parse | COVERED |
| 4. Cache eviction (deleted files) | test_deleted_file_evicted_from_task_cache, test_deleted_file_absent_from_results_after_eviction | Yes — explicit `not in` + count checks | COVERED |
| 5. refresh_config clears caches | test_refresh_config_clears_task_cache, test_refresh_config_clears_archive_cache | Yes — `== {}` post-refresh | COVERED |
| 6. Non-existent archive_dir graceful | test_nonexistent_archive_dir_returns_empty_list, test_nonexistent_archive_dir_does_not_raise | Yes — `== []` + pytest.fail on exception | COVERED |
| 7. Revision orthogonal to cache | test_revision_increments_after_create_with_warm_cache, test_revision_increments_after_edit_with_warm_cache | Yes — `== before + 1` assertion | COVERED |
| 8. Lazy invalidation | test_edit_does_not_proactively_update_task_cache, test_cache_updated_lazily_on_next_list_tasks | Yes — old title persists in cache until next list_tasks() | COVERED |
| 9. Suffix filtering (arch binding) | test_non_md_files_not_added_to_task_cache, test_non_md_files_not_in_list_tasks_results | Yes — checks .DS_Store, .tmp, .txt absent from cache and results | COVERED |
| 10. Race condition guard (arch binding) | test_race_condition_fileerror_during_read_task_suppressed, test_race_condition_evicts_entry_from_cache_when_file_gone | Yes — mock raises FNF; test verifies suppression and eviction | COVERED |
| Benchmark p99<50ms | test_warm_cache_p99_under_50ms_at_1500_tasks | Yes — hard `assert p99_ms < 50` | COVERED |

No MISSING entries.

#### Security Review

No issues. os.scandir paths derived from trusted config (self._tasks_dir / self._archive_dir), not user input. entry.name from scandir is filename-only (no traversal). No new dependencies, no hardcoded secrets, no injection surface.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_race_condition_evicts_entry_from_cache_when_file_gone | Test-writer added time.sleep(0.01) + write_bytes() to force mtime change; assertion target_name not in cache preserved | STRENGTHENED — original was logically infeasible under mtime cache; fix makes it reach the tested path |
| All other 20 TestFromAC_MtimeCache tests | No changes | PRESERVED |

No WEAKENED or REMOVED tests.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `== {}`, `assert_not_called()`, `isinstance(mtime_ns, int)`, `== old_title` — no lazy `assert result` patterns |
| Negative/error-path coverage | STRONG | Two tests each for AC 6 (non-existent dir), AC 10 (race), AC 4 (deleted); error paths fully exercised |
| Manual mutation resistance | STRONG | Flip `endswith(".md")` → AC9 fails; remove cache.clear() in refresh_config → AC5 fails; remove eviction loop → AC4 fails |
| Test independence | STRONG | Function-scoped engine fixture; tests creating their own engines use tmp_path |
| Descriptive names | STRONG | All names fully describe the scenario and AC line |

#### Data Safety

No issues. Cache is instance-level (no cross-instance sharing). Race condition explicitly handled. Atomic writes via existing tempfile→replace() unchanged.

#### Implementation-Aware Gaps

All significant new code paths exercised:

- engine.py L210-212: FNF on scandir → tested (AC 6)
- engine.py L214: .md filter → tested (AC 9)
- engine.py L216-217: cache hit → tested (AC 3, `assert_not_called`)
- engine.py L218-226: cache miss → read → update → tested (AC 3, modified file test)
- engine.py L220-222: FNF in read_task → evict → tested (AC 10)
- engine.py L227-228: post-loop eviction → tested (AC 4)
- engine.py L159-160: refresh_config → tested (AC 5)
ValueError/KeyError suppression on read_task (L223-224) is the existing pattern preserved from original code — not a new addition, suppression applies.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | N/A — same implementation, test-writer cycle between passes |
| Assessment | FRICTION — implementation correct on first pass; test infeasibility required test-writer fix |

### Pass 2 — INFORMATIONAL

- None. noqa: PLR0915 on list_tasks justified by function complexity. Hardcoded count `assert len(results) == 3` in test_non_md_files_not_in_list_tasks_results is safe given function-scoped fixture.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Cache init | engine.py L125-126: both caches initialized as `{}` | test_init_creates_*_cache_as_empty_dict | PASS |
| 2. os.scandir + mtime_ns | engine.py L209, L215: `os.scandir(source_dir)`, `entry.stat().st_mtime_ns` | test_cache_entry_is_int_mtime_ns_task_tuple | PASS |
| 3. Only changed files re-parsed | engine.py L216-217 (hit) + L218-226 (miss) | test_unchanged_file_not_reparsed_on_warm_call | PASS |
| 4. Deleted file eviction | engine.py L227-228 | test_deleted_file_evicted_from_task_cache | PASS |
| 5. refresh_config clears caches | engine.py L159-160 | test_refresh_config_clears_task_cache | PASS |
| 6. Non-existent archive_dir graceful | engine.py L210-212 | test_nonexistent_archive_dir_returns_empty_list | PASS |
| 7. Revision orthogonal | write ops in create/edit/move untouched; revision++ at L321,L417 | test_revision_increments_after_*_with_warm_cache | PASS |
| 8. Lazy invalidation | no cache write in edit_task (L388) or any other write op | test_edit_does_not_proactively_update_task_cache | PASS |
| 9. Suffix filtering | engine.py L214: `if not entry.name.endswith(".md"): continue` | test_non_md_files_not_added_to_task_cache | PASS |
| 10. Race condition guard | engine.py L220-222: `except FileNotFoundError: cache.pop(entry.name, None); continue` | test_race_condition_evicts_entry_from_cache_when_file_gone | PASS |
| Benchmark p99<50ms | quality-runner: 32 passed (benchmarks included); bench L175: `assert p99_ms < 50` | test_warm_cache_p99_under_50ms_at_1500_tasks | PASS |

### Confidence: .96

### Verdict: PASS

[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `list_tasks()` signature unchanged; performance-only internal change. `copilot-instructions.md` covers only project identity/branches — no engine internals documented there. |
| 2 | Module docstrings | Yes | Updated | `refresh_config` docstring lacked mention of cache clearing. Updated to note both `_task_cache` and `_archive_cache` are cleared so next `list_tasks()` is a full cold scan. `list_tasks` and class docstrings accurate (cache is transparent to callers). Commit: 3973f5a2. |
| 3 | External attribution | No | N/A | Sources for os.scandir/st_mtime_ns already attributed in `sources/overview.md` under task #941 (research task). No new external sources in #942 implementation. |
| 4 | CLI changes | No | N/A | Pure engine internal change — no CLI surface affected. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/mtime-cache-impl-942.md` exists and is linked in task body. |

### Files Updated

- `serve/kanban/src/owlbear_kanban/engine.py` — `refresh_config` docstring updated (3973f5a2)

### Scratch Files

- No `.owlbear/scratch/942-*` files found.
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. _task_cache/_archive_cache init | engine.py L147-148: both `dict[str, tuple[int, Task]]` = `{}` | PASS |
| 2. os.scandir + st_mtime_ns | engine.py L243: `os.scandir(source_dir)`, L251: `entry.stat().st_mtime_ns` | PASS |
| 3. Only modified/new re-parsed | engine.py L252 cache hit, L254-261 cache miss; reviewer verified mock assertions | PASS |
| 4. Deleted file eviction | engine.py L263-265: post-loop `del cache[name]` for unseen entries | PASS |
| 5. refresh_config clears caches | engine.py L169-170: both caches reset to `{}` | PASS |
| 6. Non-existent archive_dir graceful | engine.py L244-246: `except FileNotFoundError: cache.clear(); return []` | PASS |
| 7. Revision orthogonal | Reviewer verified revision++ at L321,L417 untouched by cache changes | PASS |
| 8. Lazy invalidation | Reviewer verified no cache write in edit_task or other write ops | PASS |
| 9. Suffix filtering (arch binding) | engine.py L248: `if not entry.name.endswith(".md"): continue` — spot-checked | PASS |
| 10. Race condition guard (arch binding) | engine.py L256-257: `except FileNotFoundError: cache.pop(entry.name, None); continue` — spot-checked | PASS |
| Benchmark p99<50ms | Builder reported 12.2ms warm p99; quality-runner 32 benchmarks passed | PASS |

### Test Results

- pytest: 284 passed, 6 failed (all 6 in serve/mcp-knowledge — unrelated to task scope; 0 failures in kanban/benchmark)
- ruff: clean (0 violations)

### Architect Quality: 5/5

Excellent AC: 10 specific verifiable criteria + 2 proactive binding refinements (suffix filtering, race condition guard). Design notes with data structures, LOC estimates, and rationale. Research #941 validated approach upstream. No vague or unverifiable AC lines.

### Deduction Breakdown

- AC lines with no evidence: 0
- Lint violations: 0
- AC quality ≤ 3: no (5/5)
- Missing reviewer evidence: no (detailed PASS at .96)
- Full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive
