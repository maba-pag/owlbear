# GraphEnricher Background-Task Cancellation and Draining

> **Owning task:** #871 — Manage GraphEnricher background-task cancellation and draining
> **Date:** 2026-03-25 **Status:** Complete

## 1. Context and Question

`GraphEnricher` owns a `_background_tasks` set and `_bg_semaphore` for bounded concurrent graph enrichment. It has **no shutdown flag**, **no cancel/drain API**, and **no way for callers to stop or await pending work**. Background tasks can outlive the caller and the daemon shutdown path. #870 (done) added `CancelSignal`/`LinkedCancelSignal` to upstream pipelines; #871 extends that to the enricher.

**Question:** What API surface and wiring does `GraphEnricher` need to support cooperative cancellation and clean shutdown?

## 2. Sources Studied

| Source | URL | Relevance | What it established |
|--------|-----|-----------|---------------------|
| Python asyncio task cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | .95 | `Task.cancel()` raises `CancelledError` at next await; `asyncio.gather(*tasks, return_exceptions=True)` is the shutdown drain pattern |
| Python asyncio `create_task` strong-ref pattern | <https://docs.python.org/3/library/asyncio-task.html#creating-tasks> | .85 | `background_tasks.add(task)` + `task.add_done_callback(background_tasks.discard)` — already used by GraphEnricher |
| .NET CancellationToken docs (via #733 research) | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | .90 | One token per cancelable operation; check before starting new work |
| OwlBear `HookWorkerSupervisor` (`hook_worker_supervisor.py`) | Internal codebase | .95 | Exact in-codebase pattern: `_shutdown` flag, no-op `schedule()` after shutdown, `shutdown()` cancels + gathers |
| OwlBear cooperative-cancellation research (`docs/research/cooperative-cancellation.md`) | Internal codebase | .90 | Recommends both `CancelSignal` boundary checks and explicit `cancel_pending()`/`drain()` for GraphEnricher |
| OwlBear operation-scoped-cancellation-signal research | Internal codebase | .85 | Confirms GraphEnricher cancellation deferred to #871; depends on #870 signal |

## 3. Analysis

### 3.1 API Shape: Three options

| Option | Description | KISS | Matches HookWorkerSupervisor | Cancel + Drain separation | Risk |
|--------|-------------|------|------------------------------|---------------------------|------|
| A: `shutdown()` only (.80) | Single method: set flag, cancel all, gather. Identical to HookWorkerSupervisor | High | Exact match | No — always cancels | May lose in-flight enrichment results |
| B: `shutdown()` + `drain()` (.85) | `shutdown()` cancels; `drain()` awaits without cancel. Both set `_shutdown` | Medium | Extends pattern | Yes | Slightly more API surface |
| C: Delegate to HookWorkerSupervisor (.60) | Replace enricher's task set with a shared supervisor | Low | N/A — removes ownership | N/A | Breaks enricher's self-contained ownership model |

### 3.2 CancelSignal threading: Two options

| Option | Where CancelSignal is checked | Complexity | Fits existing call chain |
|--------|-------------------------------|------------|--------------------------|
| Per-schedule (.85) | `schedule_*` methods accept optional `cancel` param, check before `create_task` | Low — 2 param additions | Yes — IngestPipeline already has `cancel` |
| Constructor-stored (.70) | Store `cancel` at construction, check in every schedule call | Lower call-site churn | Breaks per-operation signal model from #870 |

### 3.3 Bootstrap wiring gap

Currently `bootstrap/knowledge.py` constructs `GraphEnricher` but does **not** register any cleanup. `HookWorkerSupervisor.shutdown` is registered via `cleanup.append(supervisor.shutdown)` at `bootstrap/__init__.py:153`. The enricher needs the same treatment.

**Options:** (a) Return the enricher from `_build_knowledge()` and register `enricher.shutdown` in `cleanup` at the call site. (b) Accept `cleanup` list in `_build_knowledge()` and append there. Option (b) follows the existing pattern used by `_build_toolsets()` (which accepts `cleanup` and appends `conn.close`).

## 4. Recommendation (.85 confidence)

**Option B + Per-schedule CancelSignal + bootstrap wiring (option b).**

1. **`_shutdown` flag** — checked at the top of both `schedule_*` methods; prevents new task creation after shutdown.
2. **Optional `cancel: CancelSignal | None` parameter** — both `schedule_*` methods accept it, check `cancel.is_set()` before scheduling. `IngestPipeline._ingest_from_intake` passes its own `cancel` through.
3. **`async shutdown()`** — sets `_shutdown`, cancels all tracked tasks, gathers with `return_exceptions=True`. Leaves `_background_tasks` empty. Mirrors `HookWorkerSupervisor.shutdown()`.
4. **`async drain()`** — sets `_shutdown` (no new work), then awaits all tracked tasks **without** cancelling. For graceful shutdown where partial enrichment results are valuable.
5. **Bootstrap wiring** — `_build_knowledge()` registers `enricher.shutdown` in `cleanup` when enricher is not None.
6. **Tests** — cancel signal no-op, shutdown flag no-op, shutdown cancels and empties task set, drain awaits without cancel, bootstrap cleanup registration.

This is the right approach because it matches the established `HookWorkerSupervisor` pattern (KISS), adds the per-operation signal from #870 (composability), and the drain/shutdown split gives callers the choice between graceful completion and fast teardown (practical need).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add shutdown, drain, and CancelSignal to GraphEnricher" --priority nice-to-have --status ideation --tags "scope:core,type:build" --body "Source: #871 research (docs/research/graphenricher-cancellation-draining.md). Depends on: #870 (done).\n\nAC:\n1. Add _shutdown bool flag to GraphEnricher.__init__.\n2. schedule_graph_enrichment and schedule_inter_doc_enrichment accept optional cancel: CancelSignal parameter; return early when _shutdown is True or cancel.is_set().\n3. Add async shutdown() that sets _shutdown, cancels all tracked tasks, gathers with return_exceptions=True, leaves _background_tasks empty.\n4. Add async drain() that sets _shutdown, awaits all tracked tasks without cancelling.\n5. Subsequent schedule_* calls are no-ops after shutdown() or drain().\n6. Preserve existing _background_tasks bookkeeping and _bg_semaphore concurrency." --depends-on 870
```

```
kanban\kanban-md.exe create "Wire GraphEnricher.shutdown into bootstrap cleanup" --priority nice-to-have --status ideation --tags "scope:core,type:build" --body "Source: #871 research (docs/research/graphenricher-cancellation-draining.md).\n\nAC:\n1. bootstrap/knowledge.py registers enricher.shutdown in cleanup list when enricher is not None.\n2. Daemon shutdown path invokes enricher.shutdown via BootstrapResult.cleanup.\n3. No orphaned enrichment tasks after daemon stop." --depends-on 870
```

```
kanban\kanban-md.exe create "Thread CancelSignal from IngestPipeline to GraphEnricher schedule calls" --priority nice-to-have --status ideation --tags "scope:core,type:build" --body "Source: #871 research (docs/research/graphenricher-cancellation-draining.md). Depends on GraphEnricher CancelSignal support.\n\nAC:\n1. IngestPipeline._ingest_from_intake passes its cancel parameter to enricher.schedule_graph_enrichment and enricher.schedule_inter_doc_enrichment.\n2. When cancel is set before enrichment scheduling, no new enrichment tasks are created.\n3. Existing callers that omit cancel continue to work unchanged." --depends-on 870
```

```
kanban\kanban-md.exe create "Add tests for GraphEnricher cancellation and draining" --priority nice-to-have --status ideation --tags "scope:core,type:test" --body "Source: #871 research (docs/research/graphenricher-cancellation-draining.md).\n\nAC:\n1. Test shutdown() cancels tracked tasks and empties _background_tasks set.\n2. Test drain() awaits tasks without cancelling.\n3. Test schedule_* is no-op after shutdown.\n4. Test schedule_* is no-op when cancel signal is set.\n5. Test _shutdown flag prevents new task creation.\n6. Test bootstrap registers enricher.shutdown in cleanup."
```
