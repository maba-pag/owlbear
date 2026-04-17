# Extend mtime cache to show_task() and _find_task_path()

> **Owning task:** #943 — Extend mtime cache to show_task() and _find_task_path()
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

The #942 mtime cache optimized `list_tasks()` with `_task_cache: dict[str, tuple[int, Task]]`. Two adjacent methods still bypass the cache:

1. `show_task()` — does `glob() + read_task()` for tasks already cached
2. `_find_task_path()` — does `glob(f"{task_id}-*.md")` on every write op (edit, move, claim, release, end_work)

**Question:** How to extend the existing cache to benefit these methods with minimal complexity?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` (L135, L235-270, L307-320, L877-890) | 1.0 | Cache structure, show_task, _find_task_path implementations |
| 2 | `serve/kanban/tests/test_mtime_cache_942.py` | 0.9 | Existing test patterns, AC coverage model |
| 3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (L155-175) | 0.7 | MCP usage pattern for show_task |
| 4 | Challenger review of this research | 0.9 | Identified dead archive dispatch, stat failure gaps |

## 3. Analysis

### Options Evaluated

| Criterion | A: Linear scan of cache | B: Single `_id_to_filename` dict |
|-----------|------------------------|----------------------------------|
| Lookup | O(n) scan of dict values | O(1) dict lookup |
| New structures | 0 | 1 dict (rebuilt, not maintained) |
| Added lines | ~0 in list_tasks, ~15 in show/find | ~4 in list_tasks, ~8 in show/find |
| Invalidation | None (uses existing cache) | None — rebuilt from scratch each scandir |
| Error handling | Multi-path: scan + stat + fallback | Simple: dict miss → glob fallback |
| KISS alignment | Medium (hidden complexity in control flow) | High (explicit mapping, clean fallback) |

### Key Design Decisions

1. **`show_task()` validates mtime via `stat()`** — prevents stale reads after writes. On `stat()` failure (file moved/deleted): evict entry from both `_task_cache` and `_id_to_filename`, fall through to glob.

2. **`_find_task_path()` only uses `_task_cache`** — no archive dispatch. All 5 callers pass `_tasks_dir`. Archive dispatch is YAGNI.

3. **Fallback trigger: "not found in dict"** — covers both cold cache (dict empty) and warm cache miss (task created externally since last `list_tasks()`).

4. **TOCTOU risk unchanged** — same window as existing `list_tasks()` cache. No stronger guarantee claimed.

## 4. Recommendation (confidence: 0.85)

**Option B: Single `_id_to_filename` dict rebuilt in `list_tasks()`.**

Implementation:
- Add `self._id_to_filename: dict[int, str] = {}` to `__init__`
- Rebuild in `list_tasks()`: `self._id_to_filename = {task.id: name for name, (_, task) in cache.items()}`
- Clear in `refresh_config()`: `self._id_to_filename = {}`
- `show_task()`: lookup id → filename → cache hit → stat validate → return or re-read → glob fallback
- `_find_task_path()`: lookup id → filename → return `search_dir / filename` → glob fallback

Challenge: reconsider — original confidence 0.60. Revised after addressing C1-C5: archive dispatch dropped, stat failure specified, fallback clarified, Option B re-evaluated as rebuilt dict.

### Test plan (minimum)

1. `show_task()` cache hit — returns cached Task without glob
2. `show_task()` stat-stale — re-reads and updates cache entry
3. `show_task()` stat-missing (archived) — evicts, falls to glob
4. `show_task()` cold cache — falls to glob
5. `_find_task_path()` cache hit — returns path without glob
6. `_find_task_path()` cold cache — falls to glob
7. `_find_task_path()` post-create warm miss — falls to glob, finds new file
8. `refresh_config()` clears `_id_to_filename`

## 5. Follow-up Tasks

See kanban — tasks created at `research` status.
