# Mtime-Scan In-Memory Cache for list_tasks()

> **Owning task:** #941 — Tier 2: Mtime-scan in-memory cache for list_tasks()
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Research #921 found `list_tasks()` at 1500 tasks takes ~1000ms, 90% in YAML parsing. The Tier 1 parser switch (NoTimestampSafeLoader) reduces this to ~390ms. To meet the cockpit's <50ms warm-read target at 1500 tasks, an mtime-based in-memory cache is needed. What cache structure, invalidation strategy, and integration approach should be used?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/engine.py` — `list_tasks()`, write ops, `_revision` | 1.0 |
| S2 | `serve/kanban/src/owlbear_kanban/task_io.py` — `read_task()`, `write_task()` atomic writes | 1.0 |
| S3 | `serve/kanban/src/owlbear_kanban/models.py` — `Task`, `TaskSummary` schemas | 0.9 |
| S4 | `.owlbear/research/list-tasks-perf-921.md` — empirical benchmarks (research #921) | 1.0 |
| S5 | Python docs `os.scandir()` / `os.DirEntry` / `os.stat_result` | 0.9 |
| S6 | `tests/benchmarks/bench_list_tasks.py` — existing benchmark infrastructure | 0.8 |

## 3. Analysis

### 3.1 Current Hot Path

```
glob("*.md") → read_task(path) × N → filter → sort → TaskSummary conversion
  0.5ms/file YAML parse (90%)     ↑ 0.002ms/task      ↑ 0.002ms/task
```

### 3.2 Cache Design: Simple mtime dict (Option A)

**Cache structure:** `dict[str, tuple[int, Task]]` keyed by filename, valued by `(st_mtime_ns, Task)`.

Two instance-level caches: `_task_cache` (tasks_dir) and `_archive_cache` (archive_dir).

**Algorithm per `list_tasks()` call:**

1. `os.scandir(source_dir)` → iterate DirEntry objects for `.md` files
2. For each entry: `stat = entry.stat()` → if `(entry.name, stat.st_mtime_ns)` matches cache → use cached Task; else `read_task()` → update cache
3. Evict cache entries whose filenames were not seen in scandir (handles deletions)
4. Apply existing filter/sort/convert pipeline on resulting Task list

**Cache invalidation events (all handled by lazy scandir):**

| Event | Detection | Action |
|-------|-----------|--------|
| File modified | `st_mtime_ns` changed | Re-parse |
| File created | Not in cache | Parse + add |
| File deleted | In cache but not in scandir | Evict |
| File moved (archive) | Disappears from source dir | Evict (appears in other cache on next call) |
| `refresh_config()` | `_tasks_dir`/`_archive_dir` may change | Clear both caches |

### 3.3 Key Technical Findings

**`st_mtime_ns` type:** `int`, not `float`. The task AC incorrectly specifies `dict[Path, tuple[float, Task]]` — a `float` cannot represent current epoch nanosecond values without precision loss ($1.74 \times 10^{18} > 2^{53}$). Must be `int`.

**`os.scandir()` on macOS:** `DirEntry.stat()` always requires a system call on Unix. The scandir advantage over `glob()` is avoiding fnmatch overhead and path parsing, not free stat. Each call still costs ~0.01ms × 1500 = ~15ms for stat alone.

**Atomic writes:** `write_task()` uses `tempfile.mkstemp()` + `Path.replace()`. The replacement updates the target's mtime to the current time, which the cache detects correctly on next scandir.

**Lazy vs proactive invalidation:** Engine write operations (create, edit, move, claim, release, end_work) write files that `list_tasks()` will re-stat on the next poll. Proactive cache updates are unnecessary and would add complexity — especially for `move_task()`/`end_work()` where `_move_file()` shells out to `git mv`. Lazy scandir-driven invalidation is correct and simpler.

### 3.4 Revised Latency Estimate

| Component | Time at 1500 tasks | Notes |
|-----------|--------------------:|-------|
| `os.scandir()` + `DirEntry.stat()` × 1500 | ~15ms | 1 syscall per file on macOS |
| Cache lookup + dict operations | ~2ms | Hash lookups, set comparison for eviction |
| Filter passes (up to 6) | ~2ms | List comprehensions over cached objects |
| Sort | ~1ms | Depends on sort field |
| `TaskSummary.model_validate(t.model_dump())` × N | ~3ms | Pydantic conversion for returned tasks |
| **Total warm read** | **~23–35ms** | Varies by filter selectivity |

Conservative estimate: **~35ms** p50 warm read. Comfortably under 50ms AC threshold.

### 3.5 Comparison: Alternative Approaches

| Criterion | A: Simple mtime dict | B: Cache class | C: read_task-level cache |
|-----------|:---:|:---:|:---:|
| Lines of code | ~30 | ~50 | ~20 (but module-level state) |
| KISS alignment | ✓✓ | ✓ | ✓ (concerns: shared mutable state) |
| Testability | ✓ (engine integration tests) | ✓✓ (unit tests on class) | ✓ (needs careful isolation) |
| Benefits `show_task()` | ✗ | ✗ | ✓ |
| No shared state | ✓ (per-instance) | ✓ (per-instance) | ✗ (module-level) |
| Eviction clarity | ✓ (scandir-driven) | ✓ | ✗ (needs TTL or explicit clear) |

### 3.6 Memory Footprint

1500 cached `Task` objects with full markdown bodies: estimated ~7.5MB (5KB avg body × 1500). Acceptable for the cockpit's single-process architecture. No memory bound needed for current scale.

## 4. Recommendation

**(rec:) Option A — Simple mtime dict with lazy scandir invalidation.** Confidence: 0.82.

Corrections to task AC before implementation:
1. Cache type must be `dict[str, tuple[int, Task]]` (not `dict[Path, tuple[float, Task]]`)
2. Remove claim that scandir provides "stat() already cached" on Unix
3. Add `refresh_config()` cache-clear requirement
4. State explicitly that invalidation is lazy (scandir-driven, no proactive updates)

**Decomposition:** Single task — the cache is ~30 LOC of changes to `list_tasks()` plus ~5 LOC for `refresh_config()` and `__init__`. No separate infrastructure task needed.

**Challenge: reconsider — confidence in original: 0.60.** Challenger identified 6 concerns: (C1) AC type bug — `float` cannot hold `st_mtime_ns`, accepted and corrected; (C2) 25ms estimate excluded post-cache overhead, revised to ~35ms; (C3) `refresh_config()` orphans caches, added cache-clear; (C4) scandir stat claim wrong on macOS, corrected; (C5) lazy vs proactive eviction ambiguity, clarified; (C6) non-existent `archive_dir` guard, noted. All accepted. Blind spots noted: `show_task()` cache and `_find_task_path()` optimization deferred as separate tasks.

## 5. Follow-up Tasks

1. **Implement mtime cache in `KanbanEngine.list_tasks()`** — corrected AC (see §4), ~35 LOC, benchmark verification
2. **Extend cache to `show_task()` and `_find_task_path()`** — adjacent optimization, defer to separate task
