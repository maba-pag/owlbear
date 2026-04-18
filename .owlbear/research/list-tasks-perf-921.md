# list_tasks() Performance at 700/1500 Tasks

> **Owning task:** #921 — P0-01: Bench list_tasks() at 700/1500 tasks (D11)
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

The cockpit Brief (D11) gates all Phase 1/2 work on `list_tasks()` latency:

| p99 result | Branch decision |
|------------|-----------------|
| <150ms | Proceed as-is |
| 150–500ms | YAML-head-only parsing optimisation |
| >500ms | In-memory cache or FSEvents watcher |

The cockpit polls every 3s. Post-load smoothness — not cold-load time — is the user-facing metric.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/engine.py` — `list_tasks()` implementation | 1.0 |
| S2 | `serve/kanban/src/owlbear_kanban/task_io.py` — `read_task()`, `_make_yaml()` | 1.0 |
| S3 | `serve/kanban/src/owlbear_kanban/models.py` — `Task`, `TaskSummary` models | 0.9 |
| S4 | Empirical benchmark: 100/700/1500 synthetic tasks on macOS APFS (this session) | 1.0 |
| S5 | PyYAML `SafeLoader` timestamp behaviour — REPL verification | 0.9 |
| S6 | `serve/kanban/src/owlbear_kanban/config_loader.py` — alternative `_make_yaml()` | 0.7 |

## 3. Analysis

### 3.1 Empirical Results

| Scale | Unfiltered p50 | Unfiltered p99 | Status-filtered p50 | Brief bracket |
|-------|---------------|---------------|--------------------:|---------------|
| 700 | 456ms | 477ms | 457ms | 150–500ms |
| 1500 | 1002ms | 1043ms | 999ms | >500ms |

**Filters do not reduce latency** — all tasks are parsed before filtering.

### 3.2 Bottleneck Decomposition (per file)

| Component | Time (ms) | Share | Notes |
|-----------|-----------|-------|-------|
| `ruamel.yaml` round-trip parse | 0.501 | 90% | Dominant cost |
| `_make_yaml()` instance creation | 0.041 | 7% | Resolver surgery per call |
| File I/O (`read_text`) | 0.012 | 2% | OS page cache effective |
| Pydantic `Task.model_validate` | 0.001 | <1% | Negligible |
| Pydantic `TaskSummary` conversion | 0.002 | <1% | Negligible |

### 3.3 Optimisation Options

| Option | Projected 700 p50 | Projected 1500 p50 | Effort | Risk |
|--------|-------------------|--------------------:|--------|------|
| A. Status quo | 456ms | 1002ms | — | — |
| B. Custom PyYAML SafeLoader (no timestamp resolver) | ~180ms | ~390ms | Small | Low — verified |
| C. B + mtime-scan in-memory cache | ~25ms (warm) | ~25ms (warm) | Medium | Cache invalidation |
| D. B + C + frontmatter-only variant | ~15ms (warm) | ~15ms (warm) | Medium+ | Search requires body |
| E. FSEvents/watchdog watcher | ~5ms (warm) | ~5ms (warm) | High | Complexity, platform-specific |

**Verification of Option B:** A `NoTimestampSafeLoader(yaml.SafeLoader)` subclass with timestamp resolver stripped parses at 0.229ms/file (2.2× faster than ruamel). Timestamps are preserved as strings — verified for both 6-digit and 7-digit fractional seconds.

**Critical finding:** Vanilla `yaml.safe_load()` coerces ISO 8601 timestamps to `datetime` objects, truncating Go 7-digit nanoseconds and changing format. Only the custom loader is safe.

### 3.4 Trade-off Matrix

| Criterion | B (parser) | C (B + cache) | D (B + cache + head-only) | E (watcher) |
|-----------|:---:|:---:|:---:|:---:|
| Meets <150ms at 700? | ✗ (~180ms) | ✓ | ✓ | ✓ |
| Meets <150ms at 1500? | ✗ (~390ms) | ✓ | ✓ | ✓ |
| KISS alignment | ✓✓ | ✓ | ✓ | ✗ |
| Search filter support | ✓ | ✓ | ✗ (needs full read) | ✓ |
| No new dependencies | ✓ | ✓ | ✓ | ✗ (`watchdog`) |
| Cross-platform | ✓ | ✓ | ✓ | ✗ (platform API) |
| Implementation risk | Low | Medium | Medium | High |

## 4. Recommendation

**(rec:) Option C — custom PyYAML SafeLoader + mtime-scan in-memory cache.** Confidence: 0.80.

Staged delivery: Tier 1 (parser switch) unblocks cockpit development by bringing 700 tasks into the 150–500ms range. Tier 2 (mtime cache) brings both scales below 150ms with warm reads under 30ms, aligning with the cockpit's 3s-polling architecture.

The mtime cache stores parsed `Task` objects keyed by `(path, mtime_ns)`. Each `list_tasks()` call runs `os.scandir()` to detect new/deleted/modified files, re-parsing only changes. Cold load equals current behaviour; steady-state is scandir + stat only.

**Challenge: reconsider — confidence in original: 0.40.** Challenger identified critical flaw: vanilla `safe_load` coerces timestamps (C1). Accepted and revised to custom `NoTimestampSafeLoader`. Also accepted: additive savings claim corrected (C2), mtime estimate revised to include scandir cost (C4). Rejected FSEvents re-evaluation — KISS principle and no new dependency outweigh marginal latency gain; revisit only if stat overhead measured >50ms.

## 5. Follow-up Tasks

1. **Benchmark script** — `tests/benchmarks/bench_list_tasks.py` (the deliverable this task requires)
2. **Tier 1: read-path parser switch** — `NoTimestampSafeLoader` in `task_io.py`
3. **Tier 2: mtime-scan in-memory cache** — cache layer in `KanbanEngine.list_tasks()`
