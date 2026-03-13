# Ingest Background Task Concurrency Limit

> **Owning task:** #516 — Add concurrency limit to ingest background tasks
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`IngestPipeline` fires background `asyncio.Task`s via `create_task()` at two sites:

- `_schedule_graph_enrichment` — intra-document graph building (L467)
- `_schedule_inter_doc_enrichment` — cross-document edge inference (L538)

Tasks are tracked in `_background_tasks: set[asyncio.Task]` with `add_done_callback(discard)` — the standard fire-and-forget pattern from Python docs. However, bulk ingest scenarios (file globs, URL lists via `RefreshOrchestrator._ingest_items`, or repeated `KnowledgeToolset.ingest_document` calls) can spawn unbounded concurrent background tasks. Each ingest can produce up to 2 background tasks, so N documents = up to 2N concurrent graph-enrichment tasks competing for LLM API calls and CPU.

**Question:** What is the simplest, KISS-aligned approach to bound background task concurrency?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python docs — asyncio.Semaphore | <https://docs.python.org/3/library/asyncio-sync.html#semaphore> | 1.0 |
| 2 | Python docs — asyncio.TaskGroup | <https://docs.python.org/3/library/asyncio-task.html#task-groups> | 0.7 |
| 3 | SuperFastPython — Asyncio Semaphore | <https://superfastpython.com/asyncio-semaphore/> | 0.8 |
| 4 | Python docs — create_task fire-and-forget | <https://docs.python.org/3/library/asyncio-task.html#creating-tasks> | 0.9 |

## 3. Analysis

### Approach comparison

| Criterion | A: `asyncio.Semaphore` | B: `asyncio.TaskGroup` | C: Bounded queue + worker |
|-----------|----------------------|----------------------|--------------------------|
| Complexity | ~10 LOC | ~30 LOC (restructure) | ~50 LOC (new class) |
| Stdlib only | Yes | Yes | Yes |
| Fire-and-forget compat | Yes — wrap body in `async with sem` | No — TaskGroup awaits all tasks on exit | Yes but overkill |
| Configurable limit | Trivial — `Semaphore(N)` | Not directly | Yes |
| KISS alignment | High | Medium | Low |
| Backpressure | Natural — tasks block on acquire | N/A — different model | Natural |
| Existing pattern change | Minimal — add sem.acquire inside schedule methods | Major — requires restructuring lifecycle | Major |
| Risk | Low — well-understood primitive | Medium — TaskGroup cancels all on error | Medium — more moving parts |

### Why not TaskGroup?

`TaskGroup` is designed for structured concurrency where you **await all tasks before proceeding**. Our background tasks are intentionally fire-and-forget — the ingest pipeline returns `IngestResult` immediately while enrichment runs asynchronously. TaskGroup would either block the ingest call until enrichment completes (breaking the current non-blocking design) or require a separate long-lived TaskGroup managed elsewhere (unnecessary complexity).

### Why not a bounded queue + worker pool?

A producer-consumer queue with N worker coroutines is the textbook solution for high-throughput job systems. But our background tasks are simple, the volume is moderate (each ingest = at most 2 tasks), and the current fire-and-forget pattern works well. A queue adds a lifecycle to manage (start workers, drain on shutdown, handle errors). YAGNI for this use case.

## 4. Recommendation (.90 confidence)

**Approach A: `asyncio.Semaphore`** — wrap background task bodies with a shared semaphore.

### Implementation sketch

1. Add `ingest_bg_concurrency` config field (default `5`, range 1–50).
2. Create `self._bg_semaphore = asyncio.Semaphore(limit)` in `IngestPipeline.__init__`.
3. In `_enrich_graph` and `_enrich_inter_doc_graph`, wrap the body:

```python
async def _enrich_graph(self, document_id, entities, scope):
    async with self._bg_semaphore:
        # existing enrichment logic
```

4. No changes to `_schedule_graph_enrichment` or `_schedule_inter_doc_enrichment` — tasks are still created via `create_task()` and tracked in `_background_tasks`. The semaphore simply gates execution.

### Why this works

- Tasks are created immediately (no change to fire-and-forget pattern).
- Tasks that exceed the limit **queue up** on the semaphore — they don't get cancelled or dropped.
- The semaphore is per-`IngestPipeline` instance (one per daemon) — natural scope.
- Default of 5 allows reasonable parallelism while preventing unbounded resource consumption.
- Zero new dependencies, ~10 LOC change.

### Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Semaphore starvation if one task hangs | Combine with `asyncio.timeout()` (separate task #515 addresses intake timeouts) |
| Config value too low throttles throughput | Default 5 is generous; configurable for tuning |
| Semaphore created before event loop | Created in `__init__` — safe since Python 3.10 removed loop binding |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement asyncio.Semaphore concurrency limit for ingest background tasks" --priority needed --tags "resilience,knowledge,phase-9" --body "Add _bg_semaphore to IngestPipeline.__init__ (configured via ingest_bg_concurrency setting, default 5). Wrap _enrich_graph and _enrich_inter_doc_graph bodies with async with self._bg_semaphore. Add ingest_bg_concurrency field to OwlBearSettings (int, default 5, range 1-50). Thread config value through bootstrap into IngestPipeline constructor. See docs/research/ingest-concurrency-limit.md. AC: (1) Semaphore limits concurrent background enrichment tasks to configured value. (2) Config field exists with validation. (3) Existing fire-and-forget pattern preserved. (4) Tests verify semaphore bounds concurrency."

kanban\kanban-md.exe create "Add tests for ingest background task concurrency limit" --priority needed --tags "test,resilience,knowledge,phase-9" --body "Unit tests for the semaphore-bounded background tasks in IngestPipeline. Test cases: (1) With limit=2 and 5 concurrent ingests, at most 2 enrichment tasks run simultaneously. (2) All tasks eventually complete (no drops). (3) Config validation rejects 0 and negative values. (4) Default config value is 5. See docs/research/ingest-concurrency-limit.md."
```
