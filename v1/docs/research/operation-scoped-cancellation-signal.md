# Operation-Scoped Cancellation Signal for Knowledge Pipelines

> **Owning task:** #870 - Implement operation-scoped cancellation signal for knowledge pipelines
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

Task #733 established that OwlBear's long-running knowledge loops need a cooperative cancellation seam. Task #870 is the implementation follow-up: choose the smallest viable cancellation abstraction, decide where it lives, decide how far daemon-shutdown composition should reach, and keep the work aligned with the existing knowledge-pipeline test seams.

Current codebase observations:

| Area | Current state | Consequence |
| ---- | ------------- | ----------- |
| `RefreshOrchestrator.refresh_all()` / `_ingest_items()` | Sequential loops over sources and items with no cancel check | Refresh keeps starting new work after caller intent changes |
| `crawl_and_ingest()` | Sequential loop over crawled pages | Crawl ingest cannot stop at page boundaries |
| `IngestPipeline._run_extract()` | Sequential extraction loop over chunks | Extraction cannot exit between chunks |
| `BookmarkPipeline.process()` | Multi-stage flow: extract -> evaluate -> ingest -> store | No stage-boundary early exit |
| `daemon.py` + `HeartbeatRunner` | Process-level `shutdown_event` already exists | Daemon shutdown is solved at loop level, not inside knowledge pipelines |
| `RetrospectiveHook` | Direct daemon-owned `ingest_text()` caller | This is the concrete current place to compose daemon shutdown |
| `OwlBearDeps` / tool bootstrap | No shutdown-aware dependency surface | Agent-turn tool calls cannot currently link daemon shutdown without a separate runtime task |

## 2. Sources Studied

| Source | URL | Relevance | What it established |
| ------ | --- | --------- | ------------------- |
| Python asyncio `Event` docs | <https://docs.python.org/3/library/asyncio-sync.html#event> | .95 | `Event` gives lightweight `is_set()` / `wait()` semantics suitable for cooperative boundary checks |
| Python asyncio task-cancellation docs | <https://docs.python.org/3/library/asyncio-task.html#task-cancellation> | .95 | `Task.cancel()` injects `CancelledError`; caught cancellation should usually be re-raised |
| AnyIO cancellation docs | <https://anyio.readthedocs.io/en/stable/cancellation.html> | .80 | AnyIO uses level cancellation and cancel scopes, which is materially different from OwlBear's asyncio model |
| .NET cancellation-token docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | .90 | One token per cancelable operation, polling at work boundaries, and linked parent/child cancellation are strong prior art |
| OwlBear codebase: `refresh.py`, `ingest.py`, `bookmark_pipeline.py`, `integration.py`, `daemon.py`, `retrospective_hook.py`, `core/deps.py` | local code | .95 | Confirms the exact loop boundaries, current shutdown behavior, and the missing daemon-to-tool dependency seam |

## 3. Analysis

### 3.1 Cancellation API shape

| Option | Composition | Layering fit | Evidence | Verdict |
| ------ | ----------- | ------------ | -------- | ------- |
| Pass raw `asyncio.Event` everywhere | Can combine only by teaching every caller about multiple events | Leaks concrete event ownership across layers | asyncio `Event` docs + current codebase | Reject |
| Small `CancelSignal` protocol plus linked adapter with `is_set()` | One signal per operation; callers can compose multiple sources once | Keeps memory layer daemon-agnostic and call sites simple | .NET linked-token guidance + asyncio `Event` polling | Recommend |
| Rich token API with callbacks / AnyIO cancel scopes | Powerful, but broader semantics and more surface area than current need | Pulls OwlBear toward a different cancellation model | AnyIO docs + asyncio cancellation docs | Not now |

Recommendation: use a tiny protocol-backed abstraction with `is_set()` only for #870. `wait()` is not required for the current work because OwlBear's gaps are all "before starting the next unit of work" boundaries, and .NET's polling guidance plus asyncio `Event.is_set()` are enough for that shape.

### 3.2 Placement

| Option | Benefit | Risk | Verdict |
| ------ | ------- | ---- | ------- |
| `src/owlbear/memory/cancellation.py` | Reusable across future memory subsystems | Prematurely creates a memory-wide API with only knowledge callers today | Defer |
| `src/owlbear/memory/knowledge/cancellation.py` | Keeps scope local to the only proven users | If other subsystems adopt it later, module may need promotion | Recommend |

Current users are all knowledge-specific, so `owlbear.memory.knowledge` is the KISS/YAGNI-aligned home now.

### 3.3 Scope of daemon-shutdown composition

| Option | Covers AC4? | Code touched | Evidence | Verdict |
| ------ | ----------- | ------------ | -------- | ------- |
| Ignore daemon composition until later | No | Smallest | Task #870 AC + current daemon behavior | Reject |
| Compose in direct daemon-owned knowledge callers only | Yes, for the concrete current callers | Retrospective hook plus future similar hooks | `daemon.py` + `retrospective_hook.py` + `core/deps.py` | Recommend for #870 |
| Expose daemon shutdown throughout agent deps and tool bootstrap now | More complete for agent-turn tool calls | Cross-cutting runtime change beyond the pipeline seam | `core/agent.py` + `core/deps.py` + bootstrap code | Follow-up task |

The key codebase fact is that daemon shutdown is not available in `OwlBearDeps` or tool bootstrap today. That makes broad agent-turn composition real work, not a small kwarg thread-through. The concrete current daemon-owned ingest caller is `RetrospectiveHook`; it should be the first AC4 target. Broader propagation should stay separate so #870 remains atomic.

### 3.4 Testing strategy

| Test target | Existing seam | What to add |
| ----------- | ------------- | ----------- |
| `RefreshOrchestrator.refresh_all()` / `_ingest_items()` | `tests/test_refresh_orchestrator.py` already covers ordering and partial failure | Early exit before the next source or item |
| `crawl_and_ingest()` | `tests/test_crawl_integration.py` already mocks crawler + `ingest_text()` | Stop before the next page when cancel is set |
| `BookmarkPipeline.process()` | `tests/test_bookmark_pipeline.py` already isolates stage behavior | Stage-boundary exit before evaluate / ingest / store |
| `IngestPipeline._run_extract()` | `tests/test_knowledge_ingest.py` already exercises enrichment-trigger behavior | Chunk-boundary exit and preserved outer `CancelledError` semantics |

## 4. Recommendation (.89 confidence)

Implement #870 as a knowledge-local cooperative boundary signal:

- Add a tiny `CancelSignal` protocol and linked adapter under `src/owlbear/memory/knowledge/`.
- Thread an optional `cancel` argument through `RefreshOrchestrator`, `crawl_and_ingest()`, `IngestPipeline`, and `BookmarkPipeline`.
- Check `cancel.is_set()` before each next source, item, page, chunk, or bookmark stage.
- Return partial work or skipped outcomes for cooperative exits, but never swallow outer `asyncio.CancelledError` from task cancellation.
- Satisfy AC4 in the concrete current daemon-owned knowledge caller path first, especially `RetrospectiveHook`.
- Leave `GraphEnricher` cancellation to #871 and regression depth to #872.
- Do not expand #870 to thread daemon shutdown through every agent tool call; that broader runtime seam is tracked separately as #877.

## 5. Follow-up Tasks

1. **#871 - Manage GraphEnricher background-task cancellation and draining**
   Priority rationale: needed to prevent orphaned enrichment work once upstream cancellation exists.
   Depends on: #870.
   One-line AC: accept the signal in enrichment scheduling and expose public cancel/drain behavior.

2. **#872 - Add cooperative cancellation regression coverage for knowledge pipelines**
   Priority rationale: cancellation behavior is subtle and easy to regress.
   Depends on: #870 and #871.
   One-line AC: cover refresh/item boundaries, extraction or bookmark stage boundaries, and daemon-linked entry points.

3. **#877 - Expose daemon shutdown to tool-invoked knowledge cancellation**
   Priority rationale: current agent turns have no shutdown-aware dependency surface, so daemon stop cannot yet link into tool-invoked knowledge work.
   Depends on: #870.
   One-line AC: add a runtime shutdown dependency at the agent/bootstrap boundary and wire knowledge tool entry points to compose it with per-operation cancellation.
