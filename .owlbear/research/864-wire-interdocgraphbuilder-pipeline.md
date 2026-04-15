# Wire InterDocGraphBuilder into Refresh Pipeline — Research

> **Owning task:** #864 — P3-03: Wire InterDocGraphBuilder into refresh pipeline
> **Date:** 2026-04-14 **Status:** Complete

## 1. Context and Question

InterDocGraphBuilder is production-ready but standalone — no call site in `refresh.py` or `ingest.py`. Gap G6 from #772 research. This research determines WHERE in the pipeline to wire it, HOW to satisfy async/config/guard AC, and surfaces a critical dependency blocker.

## 2. Sources Studied

| Source | Relevance | What |
|--------|-----------|------|
| `inter_doc_graph_builder.py` (codebase) | .95 | DI-based builder: `build(entities, scope)` → `GraphBuildResult` |
| `refresh.py` (codebase) | .95 | `RefreshOrchestrator`: per-source handlers call `pipeline.ingest()` per item |
| `ingest.py` (codebase) | .90 | `IngestPipeline.ingest()`: chunks → embeds → extracts → stores → returns `IngestResult` |
| `graph_store.py` (codebase) | .85 | `list_entities_for_document(doc_id)`, `get_counts() → (docs, entities, edges)` |
| `server.py` (mcp-knowledge) | .85 | Production composition: `RefreshOrchestrator(store, pipeline, workspace_root)` |
| `loader.py` (codebase) | .80 | CLI composition: same DI pattern, no inter-doc wiring |
| #862 task body (kanban) | .90 | P3-01 BLOCKED — LLMExtractor/pydantic-ai removed; no StructuredExtractor impl exists |

## 3. Analysis

### 3.1 Dependency Blocker

`InterDocGraphBuilder.__init__` requires `extractor: StructuredExtractor`. After pydantic-ai removal, **no concrete `StructuredExtractor` implementation exists**. The protocol is defined in `protocol.py` but has zero implementations. #862 (P3-01, prompt fix) is blocked for the same reason. Wiring is a structural task that can proceed (design + tests with mocks), but end-to-end integration requires a `StructuredExtractor` implementation first. The `depends_on` field on #864 is empty — should be `[862, 863]` per #772 review notes.

### 3.2 Wiring Location Comparison

| Criterion | A: RefreshOrchestrator (.82) | B: IngestPipeline (.60) | C: Post-refresh hook (.55) |
|-----------|------------------------------|--------------------------|----------------------------|
| SRP | Orchestrator coordinates multi-step flows — natural fit | IngestPipeline's scope is chunk→extract→store; cross-doc is outside | Good, but batches all docs |
| DI params added | +2 (`inter_doc_builder`, `graph_store`) | +2 (`inter_doc_builder`, `graph_store`) | +2, same |
| Entity access | `graph_store.list_entities_for_document(doc_id)` after ingest | Same — needs graph_store access IngestPipeline doesn't have | Bulk entity fetch |
| Non-blocking (AC2) | `asyncio.create_task()` in handler loop | Same | Natural — runs after handler returns |
| Doc count guard (AC3) | `graph_store.get_counts()[0] >= 2` or scoped `list_documents` | Same | Same |
| Config toggle (AC4) | `inter_doc_builder is None` = disabled (DI pattern) | Same | Same |
| AC1 alignment | Per-document trigger after ingest ✓ | Per-document ✓ | Per-source batch — diverges from AC1 |
| Existing test impact | ~20 RefreshOrchestrator tests need new optional param | ~15 IngestPipeline tests need new param | Same as A |
| Production call sites | 1 (`server.py:192`) | 1 (`server.py:181`) + 1 (`loader.py:252`) | 1 (same as A) |

### 3.3 Wiring Design (Option A — Recommended)

```
RefreshOrchestrator.__init__(
    ...,
    inter_doc_builder: InterDocGraphBuilder | None = None,  # NEW — None = disabled (AC4)
    graph_store: GraphStore | None = None,                  # NEW — entity retrieval
)

_handle_url_list / _handle_file_glob / _handle_authenticated_web:
    for each item:
        ingest_result = pipeline.ingest(intake_result, scope=scope)
        if ingest_result.status == "ok" and self._inter_doc_builder is not None:
            asyncio.create_task(self._run_inter_doc(ingest_result.document_id, scope))
                                                                     # AC2: non-blocking

async _run_inter_doc(self, document_id: str, scope: str) -> None:
    doc_count, _, _ = self._graph_store.get_counts()               # AC3: guard
    if doc_count < 2:
        return
    entities = self._graph_store.list_entities_for_document(document_id)
    result = await self._inter_doc_builder.build(entities, scope)
    for edge in result.edges:
        self._graph_store.insert_edge(edge)                        # persist inter-doc edges
```

### 3.4 Scoped Doc Count

`get_counts()` returns global totals. AC3 says "fewer than 2 documents exist in scope." For scoped check, use `len(graph_store.list_documents(scopes=[scope]))`. This is O(N) but N is small during early Phase 3. Acceptable for now; optimize later if needed.

### 3.5 Edge Storage Gap

`InterDocGraphBuilder.build()` returns `GraphBuildResult(edges=stamped, edges_added=N)` but does NOT persist edges — the caller must store them. The wiring must call `graph_store.insert_edge(edge)` for each returned edge.

### 3.6 Fire-and-Forget Risks

`asyncio.create_task()` without tracking can silently swallow exceptions. Mitigation: add a done-callback that logs failures. Collected tasks should be awaited at end of `_handle_*` method to prevent event-loop cleanup issues.

## 4. Recommendation (confidence: .78)

**Option A: Wire at RefreshOrchestrator level.** Two new optional DI params, one new private async method, `asyncio.create_task` for non-blocking execution, DI-based config toggle (builder=None → disabled).

Confidence reduced from .82 to .78 due to: (1) dependency blocker — #862 blocked, no StructuredExtractor implementation exists; (2) `depends_on` field not set on #864.

Challenge: FALLBACK — challenger subagent not in available roster.

## 5. Follow-up Tasks

1. **#864 itself** — implementation task, stays at research with `deferred` tag until #862 unblocks
2. New: investigate StructuredExtractor replacement strategy (pydantic-ai removal left a gap)
