# Cooperative Pipeline Cancellation via asyncio.Event

**Task:** #733 — Research: Cooperative pipeline cancellation via asyncio.Event
**Date:** 2026-03-20
**Source:** #597 edgequake-research §3.4

## 1. Context and Question

OwlBear already has host-level cancellation via `shutdown_event` in `channel_loop`, `poll_loop`, and `HeartbeatRunner.run()`. The gap is operation-level cancellation inside knowledge pipelines that may keep processing sources, pages, chunks, or background enrichment work after the caller wants to stop.

| Area | Current primitive | Current state | Recommendation |
|------|-------------------|---------------|----------------|
| `channel_loop`, `poll_loop`, `HeartbeatRunner.run()` | Shared `shutdown_event` polled in loop conditions | Already cooperative | Keep as the baseline |
| `ConsolidationService.schedule_periodic()` | Daemon cancels the task directly on shutdown | Adequate for a timer loop | No separate operation event needed now |
| `RefreshOrchestrator.refresh_all()` and `_ingest_items()` | Sequential `for` loops over sources/items | No cancel seam | Add per-operation signal |
| `crawl_and_ingest()` | Sequential `for page in crawl_result.pages` loop | No cancel seam | Thread the same signal through crawl ingest |
| `IngestPipeline._run_extract()` | Sequential `for chunk in chunks` loop over LLM extraction | No cancel seam | Check signal before each chunk |
| `BookmarkPipeline.process()` | Long multi-stage operation: extract -> evaluate -> ingest -> store | No stage-boundary cancel seam | Check signal between stages |
| `GraphEnricher` background tasks | `asyncio.create_task()` plus tracked set, but no public cancel/drain API | Background work can outlive caller | Pass a linked signal and add explicit drain/cancel |

## 2. Sources Studied

| Source | URL | Relevance | What it established |
|--------|-----|-----------|---------------------|
| Python asyncio `Event` docs | <https://docs.python.org/3/library/asyncio-sync.html#event> | .90 | `Event` is a lightweight cooperative signal with `set()`, `wait()`, and `is_set()`; good fit for polling loop boundaries |
| Python asyncio task cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | .95 | `Task.cancel()` raises `CancelledError` at the next await; hard interruption remains distinct from event polling |
| AnyIO cancellation docs | <https://anyio.readthedocs.io/en/stable/cancellation.html> | .75 | Cancel scopes are stronger but change semantics from asyncio edge cancellation to level cancellation |
| .NET cancellation token docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | .90 | One token per cancelable operation and linked parent/child cancellation are the right prior art for daemon + per-operation composition |
| Existing OwlBear EdgeQuake research | `docs/research/edgequake.md` | .70 | The prior OwlBear research already identified work-item-boundary cancellation as the transferable pattern |

## 3. Analysis

### 3.1 Extend `shutdown_event` or add a per-operation signal?

| Option | Granularity | Composability | API ergonomics outside daemon | Risk | Verdict |
|--------|-------------|---------------|-------------------------------|------|---------|
| Reuse daemon `shutdown_event` everywhere | Coarse: one process-wide signal | Poor for concurrent refresh/bookmark runs | Forces memory/tool layers to know daemon lifetime | One cancel request can stop unrelated work | Reject |
| Separate per-operation event and compose with `shutdown_event` when available | Fine: one signal per refresh/bookmark/ingest request | Good: caller and daemon can both participate | Works in toolsets, tests, scripts, and daemon | Small plumbing cost across call stack | Recommend |
| Adopt AnyIO cancel scopes | Strongest blocking-await cancellation | Good, but with different semantics | Requires broader runtime and dependency change | Overkill for an asyncio-only codebase | Not now |

Two important consequences follow from the sources:

1. `asyncio.Event` is a boundary signal, not a hard-stop primitive. It is ideal for "stop before starting the next source/page/chunk/stage" checks, but it does not interrupt an arbitrary in-flight await.
2. OwlBear should keep using `Task.cancel()` or `asyncio.timeout()` for hard teardown paths such as stale-task cleanup and daemon shutdown. The new event should complement that, not replace it.

### 3.2 Recommended placement and call flow

- Place the abstraction in `owlbear.memory.knowledge` or `owlbear.memory`, not `owlbear.core`; the immediate consumers are knowledge pipelines and `core` should not grow knowledge-specific dependencies.
- Pass the signal per call; do not store a long-lived mutable event on pipeline instances.
- Compose daemon shutdown with operation cancellation by linking both signals when the daemon invokes a pipeline.
- Add signal checks before each new unit of work: source, item, page, chunk, bookmark stage, and background enrichment build.

### 3.3 Interface sketch (.85 confidence)

```python
import asyncio
from typing import Protocol, runtime_checkable


@runtime_checkable
class CancelSignal(Protocol):
    def is_set(self) -> bool: ...


class LinkedCancelSignal:
    def __init__(self, *events: asyncio.Event | None) -> None:
        self._events = tuple(event for event in events if event is not None)

    def is_set(self) -> bool:
        return any(event.is_set() for event in self._events)


async def refresh_all(self, scope: str | None = None, cancel: CancelSignal | None = None):
    results = []
    for source in self._store.list_enabled(scope):
        if cancel and cancel.is_set():
            break
        results.append(await self.refresh(source, cancel=cancel))
    return results


async def process(self, url: str, ..., cancel: CancelSignal | None = None):
    if cancel and cancel.is_set():
        return BookmarkResult(url=url, skipped_reason="Cancelled")
    content = await self._web_read(url)
    if cancel and cancel.is_set():
        return BookmarkResult(url=url, skipped_reason="Cancelled")
    ...


linked = LinkedCancelSignal(operation_cancel, shutdown_event)
await orchestrator.refresh_all(scope, cancel=linked)
```

`GraphEnricher` should use the same signal but also expose a public `cancel_pending()` or `drain()` method. Today it tracks background tasks in a private set, which keeps them alive correctly, but gives callers no way to wait for or stop pending enrichment work explicitly.

## 4. Recommendation (.85 confidence)

Use a separate optional per-operation cancellation signal, backed by `asyncio.Event` semantics, and compose it with daemon `shutdown_event` where a pipeline runs under daemon control.

This is the best fit because:

- It matches the .NET model of one token per cancelable operation, which avoids leaking process-lifetime concerns into every library API.
- It preserves OwlBear's current asyncio model instead of importing AnyIO's different cancellation semantics.
- It fits OwlBear's actual work shape: long sequential loops over sources, pages, and chunks where cooperative boundary checks are enough.
- It keeps hard interruption available for stale tasks and shutdown via existing `Task.cancel()` paths.

Implementation policy:

- Event for cooperative early exit at work-item boundaries.
- `Task.cancel()` or timeout for forced interruption of a blocked await.
- Partial results or "Cancelled" outcomes for cooperative exits; do not swallow `CancelledError` when the outer task itself is cancelled.

## 5. Follow-up Tasks

1. **Implement operation-scoped cancellation signal in knowledge pipelines**
   Priority rationale: `nice-to-have` quality improvement that closes the main gap without changing user-visible behavior.
   Depends on: none.
   One-line AC: Add an optional cancel signal through `RefreshOrchestrator`, `crawl_and_ingest()`, `IngestPipeline`, and `BookmarkPipeline`, with checks before each new source, page, chunk, or stage.

2. **Manage `GraphEnricher` background-task cancellation explicitly**
   Priority rationale: `nice-to-have`, but required to avoid orphaned enrichment work once cancellation is introduced upstream.
   Depends on: Task 1.
   One-line AC: `GraphEnricher` accepts the linked signal and exposes a public cancel/drain path used during shutdown and caller cleanup.

3. **Add cooperative cancellation regression tests**
   Priority rationale: `nice-to-have`; the behavior is subtle and easy to regress.
   Depends on: Tasks 1 and 2.
   One-line AC: Tests cover early exit in refresh, bookmark/ingest extraction, and daemon-shutdown composition, with no swallowed `CancelledError`.
