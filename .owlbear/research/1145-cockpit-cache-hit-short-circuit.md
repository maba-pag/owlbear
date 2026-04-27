# Restore Cockpit Cache-Hit Short-Circuit for list_tasks

> **Owning task:** #1145 — Restore cockpit cache-hit short-circuit for list_tasks
> **Date:** 2026-04-27  **Status:** Complete

## 1. Context and Question

The #1082 route rewrite replaced the mtime-gated `adapter.list_tasks()` call in `GET /api/tasks` with unconditional `view.list_tasks()` delegation. The `MtimeScanCache` is still injected as a dependency but unused in the route body. The 930 durable test `test_engine_list_tasks_not_called_on_cache_hit` fails because `engine.list_tasks()` is now called on every request regardless of file changes.

**Question:** What is the correct approach to restore the cache short-circuit while preserving the Brief B `CockpitView` delegation?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/cockpit/src/owlbear_cockpit/routes/read.py` (current) | Live code | 0.95 — shows unused `_cache` param |
| Git `b582a3e3:routes/read.py` (pre-#1082) | History | 0.95 — shows original cache-gated pattern |
| `serve/cockpit/src/owlbear_cockpit/cache.py` | Live code | 0.90 — `MtimeScanCache` with `has_changed()` + `tasks` property |
| `tests/test_cockpit_read_api_930.py` L451–480 | Durable test | 0.90 — documents expected behavior |
| `serve/kanban/src/owlbear_kanban/engine.py` L3124–3165 | Live code | 0.80 — `CockpitView.list_tasks()` → `AgentView.list_tasks()` chain |
| `.owlbear/research/1144-cockpit-durable-reconciliation.md` | Research | 0.70 — identified this as separate follow-up |

## 3. Analysis

### Call Chain (current, broken)

```
Route list_tasks() → view.list_tasks() → CockpitView.list_tasks()
  → engine.agent_view().list_tasks() → AgentView.list_tasks()
  → engine.list_tasks()  ← called every request
```

### Call Chain (old, working)

```
Route list_tasks() → cache.has_changed()?
  YES → adapter.list_tasks(engine) → engine.list_tasks()
        cache.tasks = result
  NO  → skip engine call
  → filter cache.tasks in Python → return
```

### Implementation Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A: Route-level cache gate** | Restore `has_changed()` check in route, cache full unfiltered `view.list_tasks()`, filter in Python | Simple, matches old pattern, KISS | Duplicates 4 trivial filter lines |
| **B: CockpitView cache-aware** | Add caching inside `CockpitView` | Cleaner encapsulation | Violates package boundary (kanban pkg shouldn't know cockpit cache) |
| **C: Caching proxy dependency** | Wrap view in a caching DI wrapper | Clean architecture | Over-engineering for 1 endpoint, YAGNI |

### Recommendation: Option A (confidence: 0.90)

Restore the cache gate in the route. The 4 Python filter lines (`status`, `priority`, `tag`, `blocked`) are trivial and identical to the pre-#1082 pattern. The `MtimeScanCache` class already has the `has_changed()` + `tasks` property API designed for this exact use case.

Pattern:
1. `cache.has_changed()` → on True: call `view.list_tasks()` (unfiltered), store `response.tasks` in `cache.tasks`
2. On False: use `cache.tasks` directly (no engine call)
3. Apply 4 filters in Python on the cached list
4. Return `ListTasksResponse(tasks=filtered, guidance=[], missing_ids=None)`

### Monkeypatch Compatibility

The test monkeypatches `engine.list_tasks`. The call chain reaches `engine.list_tasks()` via `AgentView.list_tasks()` → `self.engine.list_tasks()` where `self.engine` is the same instance. The monkeypatch intercepts correctly. The cache gate prevents reaching this call on cache hit.

## 4. Recommendation

**Option A — Route-level cache gate.** Confidence: 0.90.

Challenge: FALLBACK — trivial T1 bug fix restoring prior behavior, challenger skipped per w-research Step 3.5 (skip for trivial research).

## 5. Follow-up Tasks

| Task | Status | Priority |
|------|--------|----------|
| Implement cache-hit short-circuit in `routes/read.py` | backlog (advance #1145) | nice-to-have |
