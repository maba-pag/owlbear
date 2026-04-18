# Mtime Cache Implementation — Validation Research

> **Owning task:** #942 — Implement mtime-scan cache in KanbanEngine.list_tasks()
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #942 is the implementation follow-up from research #941. This validation confirms the AC is correct against the current codebase and incorporates challenger feedback.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `.owlbear/research/mtime-cache-941.md` — original research | 1.0 |
| S2 | `serve/kanban/src/owlbear_kanban/engine.py` — current `list_tasks()` at L231 | 1.0 |
| S3 | `serve/kanban/src/owlbear_kanban/task_io.py` — `read_task()`, `write_task()` | 1.0 |
| S4 | `tests/benchmarks/bench_list_tasks.py` — benchmark infrastructure | 0.9 |
| S5 | Benchmark run (this session): 1500 tasks p50=408ms, p99=453ms | 1.0 |
| S6 | `serve/kanban/src/owlbear_kanban/dispatch.py` — `pick_dispatchable()` | 0.7 |

## 3. Analysis

### 3.1 Baseline Established

| Scale | Cold | p50 | p99 |
|------:|-----:|----:|----:|
| 700 | 190ms | 185ms | 192ms |
| 1500 | 401ms | 408ms | 453ms |

Target: warm p99 <50ms at 1500 tasks. Current is ~9× over target. Cache is required.

### 3.2 AC Validation Against Current Code

| AC Item | Verified | Notes |
|---------|:--------:|-------|
| `__init__` two caches: `dict[str, tuple[int, Task]]` | ✓ | No existing cache attrs. `int` for `st_mtime_ns` correct |
| `os.scandir()` + `st_mtime_ns` | ✓ | Replaces `glob("*.md")` at engine.py L231 |
| Only modified/new files re-parsed | ✓ | Cache miss → `read_task()` → insert |
| Eviction for deleted files | ✓ | Set difference on filenames |
| `refresh_config()` clears caches | ✓ | Currently no cache; clear needed at L176 |
| Non-existent `archive_dir` | ⚠ | `os.scandir()` raises `FileNotFoundError` (unlike `glob()` which returns empty). Guard required |
| `revision` orthogonal | ✓ | Write ops increment revision independently |
| Lazy invalidation | ✓ | `write_task()` atomic replace updates mtime naturally |

### 3.3 Challenger Findings (6 concerns)

| ID | Concern | Disposition |
|----|---------|-------------|
| C1 | Race: file deleted between scandir and read_task | **Accept.** Add `FileNotFoundError` to suppress + evict entry |
| C2 | Archive cache population unstated | **Accept.** Explicitly state: scandir hit + cache miss → read → insert |
| C3 | `st_mtime_ns` precision on HFS+ | **Reject.** APFS is standard since 2017; HFS+ edge case not worth designing around |
| C4 | `pick_dispatchable()` bypasses cache | **Noted, out of scope.** Task #942 targets `list_tasks()` only. Separate optimisation path |
| C5 | Benchmark conflates OS page-cache warm vs app-cache warm | **Accept.** Benchmark needs cache-hit scenario (same engine, second call) |
| C6 | ~35 LOC excludes tests | **Accept.** Implementation ~35 LOC; tests additional. AC already lists test files |

Challenger also suggested caching at `read_task()` level (Option C from research #941). **Rejected**: module-level shared state, unclear eviction, incompatible with per-instance lifecycle. Task #943 already exists for `show_task()`/`_find_task_path()` extension.

### 3.4 AC Corrections for Implementation

1. Guard `os.scandir()` with `FileNotFoundError` handler for non-existent dirs (return empty list)
2. Add `FileNotFoundError` to suppress when `read_task()` fails for a file seen in scandir (evict cache entry)
3. Benchmark: add a "cache-hit" scenario measuring second+ call on same engine instance
4. Ensure cache miss path (new file in scandir, not in cache) explicitly reads and inserts

## 4. Recommendation

**Proceed with implementation as specified.** AC is accurate with the 4 minor corrections above. No design changes needed. Confidence: 0.85.

**Challenge: reconsider — confidence in original: 0.55.** Six concerns raised; 3 accepted (race condition guard, benchmark scenario, archive cache miss path), 2 noted out-of-scope, 1 rejected (HFS+ edge case). All accepted items are minor implementation details, not design changes.

## 5. Follow-up Tasks

No new follow-up tasks needed. Existing task #943 covers `show_task()`/`_find_task_path()` extension.
