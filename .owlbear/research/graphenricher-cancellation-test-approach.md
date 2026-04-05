# GraphEnricher Cancellation & Draining — Test Approach

> **Owning task:** #1000 — Add tests for GraphEnricher cancellation and draining
> **Date:** 2026-03-25 **Status:** Complete

## 1. Context and Question

Task #1000 asks for TDD RED (failing) tests covering `GraphEnricher` cancellation and draining features defined in #871's AC. `GraphEnricher` currently has no `shutdown()`, `drain()`, `_shutdown` flag, or `CancelSignal` parameter — all tests will fail on current HEAD, satisfying TDD RED.

**Question:** What test patterns, fixtures, markers, and file placement should the test-writer use, and is the AC complete?

## 2. Sources Studied

| Source | URL | Relevance | What it established |
|--------|-----|-----------|---------------------|
| Python asyncio task cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | .95 | `Task.cancel()` raises `CancelledError` at next await; `asyncio.gather(*tasks, return_exceptions=True)` is the shutdown drain idiom |
| Python asyncio `create_task` strong-ref pattern | <https://docs.python.org/3/library/asyncio-task.html#creating-tasks> | .85 | `background_tasks.add(task)` + `task.add_done_callback(background_tasks.discard)` — already used by GraphEnricher |
| OwlBear `test_hook_worker_supervisor.py` | Internal: `tests/test_hook_worker_supervisor.py` | .95 | Exact in-codebase prior art: 5 test classes covering ownership, schedule lifecycle, semaphore bounds, shutdown cancel/drain/empty contract |
| OwlBear `test_enrichment.py` | Internal: `tests/test_enrichment.py` | .90 | Existing GraphEnricher fixtures (`conn`, `mock_graph_store`, `mock_graph_builder`, `enricher`), currently uses `@pytest.mark.anyio` |
| OwlBear `test_bootstrap.py` cleanup tests | Internal: `tests/test_bootstrap.py` L658-720 | .85 | Pattern for testing bootstrap cleanup registration: assert method in `result.cleanup` list |
| OwlBear GraphEnricher cancellation research | Internal: `docs/research/graphenricher-cancellation-draining.md` | .90 | Design: `shutdown()` mirrors HookWorkerSupervisor; `drain()` awaits without cancel; per-schedule `CancelSignal` param |

## 3. Analysis

### 3.1 AC Coverage Mapping

| #1000 AC | Maps to | Implementation task | Verifiable |
|----------|---------|---------------------|------------|
| AC-1: shutdown() cancels + empties | #871 AC-3 | #871 | Yes — `was_cancelled` event + `len(_background_tasks) == 0` |
| AC-2: drain() awaits without cancel | #871 AC-4 | #871 | Yes — task completes normally, no `CancelledError` |
| AC-3: schedule_* no-op after shutdown | #871 AC-5 | #871 | Yes — schedule post-shutdown, assert coroutine didn't run |
| AC-4: schedule_* no-op when cancel set | #871 AC-2 | #871 | Yes — mock `CancelSignal.is_set()` returns True, assert no task created |
| AC-5: _shutdown flag prevents creation | #871 AC-1+2 | #871 | Yes — overlaps with AC-3; tests flag attribute directly |
| AC-6: bootstrap registers cleanup | #998 AC-1 | **#998** (not #871) | Yes — mirror `test_bootstrap.py` cleanup assertion pattern |

**Gap:** AC-6 tests #998's scope, not #871's. The builder of #871 will make AC 1-5 green; #998's builder makes AC-6 green. This cross-dependency should be noted to avoid confusion.

### 3.2 Async Test Marker

| Marker | Used by | Dependency |
|--------|---------|------------|
| `@pytest.mark.anyio` | `test_enrichment.py` | Transitive via httpx (not in pyproject.toml) |
| `@pytest.mark.asyncio(loop_scope="function")` | `test_hook_worker_supervisor.py` | `pytest-asyncio>=0.25.0` (explicit dependency) |

The project declares `asyncio_mode = "strict"` and depends on `pytest-asyncio`. The `@pytest.mark.anyio` usage in `test_enrichment.py` works but relies on a transitive dependency. **New cancellation tests should use `@pytest.mark.asyncio(loop_scope="function")`** to match the HookWorkerSupervisor pattern and the explicit dependency.

### 3.3 Test File Placement

| Option | Pros | Cons |
|--------|------|------|
| Append to `test_enrichment.py` (.75) | All GraphEnricher tests co-located | File already 555 lines; different marker convention |
| New `test_enrichment_cancellation.py` (.85) | Mirrors `test_hook_worker_supervisor.py` separation; clean marker choice; clear ownership (#1000) | One more file |

### 3.4 Test Patterns (from HookWorkerSupervisor)

The test-writer should adopt these patterns verbatim from `test_hook_worker_supervisor.py`:

- **Sync coordination:** `asyncio.Event` pairs (`running`/`release`) for controlling task lifecycle
- **Timeout safety:** `asyncio.wait_for(..., timeout=1.0)` on all event waits
- **Done-callback propagation:** `await asyncio.sleep(0.05)` after task completion
- **Cancel detection:** `try/except CancelledError` with `was_cancelled.set()` + `raise`
- **Empty-set assertion:** `assert len(enricher._background_tasks) == 0` post-shutdown/drain
- **No-op verification:** `ran = asyncio.Event()` in probe coroutine, assert `not ran.is_set()` after schedule

### 3.5 Fixture Requirements

Existing `test_enrichment.py` fixtures (`conn`, `mock_graph_store`, `mock_graph_builder`, `mock_document_store`, `enricher`) are reusable. Additional needs:

- `CancelSignal` mock: `MagicMock(is_set=MagicMock(return_value=True))` or a real `asyncio.Event` wrapper
- Enricher with running tasks: fixture that pre-schedules hanging coroutines for shutdown/drain tests

## 4. Recommendation (.85 confidence)

**Create `tests/test_enrichment_cancellation.py`** with `@pytest.mark.asyncio(loop_scope="function")` marker, adopting HookWorkerSupervisor test patterns.

Structure as 4 test classes:

1. `TestGraphEnricherShutdown` — AC-1, AC-3, AC-5
2. `TestGraphEnricherDrain` — AC-2
3. `TestGraphEnricherCancelSignal` — AC-4
4. `TestGraphEnricherBootstrapCleanup` — AC-6

Risk: AC-6 belongs to #998's implementation scope. The test-writer should add a comment noting this cross-dependency so reviewers understand why it stays red after #871.

## 5. Follow-up Tasks

No new implementation tasks needed — #871, #998, and #999 already cover all implementation work. The sole follow-up action is moving #1000 to backlog for test-writing.

**Dependency note for architect:** #998 should add `depends_on: 1000` since the TDD RED test for its behavior (AC-6) lives in #1000. Currently #998 has no dependency on #1000.
