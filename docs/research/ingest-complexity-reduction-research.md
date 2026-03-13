# Reduce ingest.py Complexity After Pipeline Refactor

> **Owning task:** #517 — Reduce ingest.py complexity after pipeline refactor
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`ingest.py` is 799 lines. `IngestPipeline` handles 5 distinct responsibilities: data models, document CRUD + status tracking, storage writes, graph enrichment scheduling, and orchestration. The AC requires `ingest.py < 500 lines`. The question: what is the cleanest decomposition that achieves this while preserving the existing public API?

## 2. Sources Studied

| Source | URL | Relevance | What we studied |
|--------|-----|-----------|-----------------|
| LlamaIndex IngestionPipeline | [pipeline.py](https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/ingestion/pipeline.py) | .90 | Orchestrator-only pattern; docstore handles status/dedup separately; transformations as composable stages |
| Haystack Pipelines | [Haystack docs](https://docs.haystack.deepset.ai/docs/pipelines) | .80 | Directed graph of separate Component classes; pipeline is routing/orchestration only; each stage is a standalone class |
| Python Patterns: Composition over Inheritance | [python-patterns.guide](https://python-patterns.guide/gang-of-four/composition-over-inheritance/) | .75 | SRP via composition; delegate distinct concerns to separate objects; orchestrator composes helpers at runtime |
| OwlBear `intake.py` (existing) | `src/owlbear/memory/knowledge/intake.py` | .85 | Precedent: intake reading already extracted to its own module; validates pattern of pulling stages out |

## 3. Analysis

### Current responsibility map (799 lines total)

| Group | Responsibility | Methods | Lines | SRP violation? |
|-------|---------------|---------|-------|----------------|
| A | Data models | `DocumentStatus`, `IngestResult`, `compute_content_hash` | 95 | No (but DocumentStatus belongs with its CRUD) |
| B | Document CRUD + status | `find_status_by_source`, `check_content_changed`, `delete_document_data`, `_set_status`, `_insert_document`, `_update_content_hash` | 158 | Yes — DB layer mixed into orchestrator |
| C | Storage writes | `_store_chunks`, `_store_embeddings`, `_store_extractions`, `_store_entity_embeddings` | 108 | Yes — storage details in orchestrator |
| D | Graph enrichment | `_schedule_graph_enrichment`, `_enrich_graph`, `_schedule_inter_doc_enrichment`, `_enrich_inter_doc_graph` | 109 | Yes — background task management in orchestrator |
| E | Orchestration | `__init__`, `ingest`, `ingest_text`, `_ingest_from_intake`, `_read_source`, `_run_embed`, `_run_extract`, `_process_results` | 329 | No — this is the core purpose |

### Extraction options

| Criterion | Option A: 2 modules (.85) | Option B: 3 modules (.65) | Option C: 1 module (.50) |
|-----------|--------------------------|--------------------------|--------------------------|
| New files | `document_store.py` (B+C), `enrichment.py` (D) | `document_store.py` (B), `ingest_store.py` (C), `enrichment.py` (D) | `enrichment.py` (D) only |
| Resulting ingest.py | ~350 lines | ~340 lines | ~660 lines |
| Meets AC (<500) | Yes | Yes | **No** |
| KISS | High — 2 new files | Medium — 3 new files, B+C always coupled | High — 1 file |
| YAGNI | Good — B+C used together | Bad — splitting B/C adds indirection with no benefit | Good |
| Circular deps | None | None | N/A |
| Test impact | Moderate — update imports in ~6 test files | More — 3 new modules to test | Low |
| Aligns with #566 | Yes — modules ready for future `knowledge/pipeline/` sub-package | Yes | Partially |

### Dependency analysis (no circular risks)

`document_store.py` needs: `sqlite3.Connection`, `VectorStoreProtocol` (from protocol.py), `GraphStore` (from graph.py), `IntakeResult` (from intake.py), `Chunk` (from chunker.py), `HybridEmbedding` (from protocol.py), `ExtractionResult` (from extractor.py). All leaf modules.

`enrichment.py` needs: `IntraDocGraphBuilder` (from graph_builder.py), `InterDocGraphBuilder` (from inter_doc_graph_builder.py), `GraphStore` (from graph.py), `sqlite3.Connection`. All leaf modules.

Neither imports from `ingest.py`. No cycles.

### Precedent validation

Both LlamaIndex and Haystack confirm: pipelines should be orchestration-only, with document management/storage delegated to separate stores. LlamaIndex's `docstore` is a direct analogue to our proposed `DocumentStore`. The existing `intake.py` extraction in our codebase already followed this pattern successfully.

## 4. Recommendation (.85 confidence)

**Option A: Two new modules.**

1. **`document_store.py`** (~280 lines) — `DocumentStore` class containing all document CRUD, status tracking, chunk/embedding/extraction storage, and content hashing. Includes `DocumentStatus` model and `compute_content_hash`.

2. **`enrichment.py`** (~150 lines) — `GraphEnricher` class containing background task scheduling for intra-doc and inter-doc graph enrichment. Owns `_background_tasks` set.

3. **`ingest.py`** (~350 lines) — `IngestPipeline` retains `IngestResult` model, `__init__` (now taking `DocumentStore` + `GraphEnricher`), `ingest`, `ingest_text`, `_ingest_from_intake`, `_run_embed`, `_run_extract`, `_process_results`. Pure orchestration.

**Risk:** The `_process_results` method calls both storage writes and logging. After extraction, it will call `self._store.store_embeddings(...)` etc. — a thin delegation layer. Acceptable: ~5 LOC overhead for clear SRP.

**Task #516 synergy:** Extracting enrichment to its own class makes the semaphore addition (task #516) cleaner — the semaphore lives in `GraphEnricher.__init__`.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Extract DocumentStore from IngestPipeline to document_store.py" --priority needed --tags "modularity,knowledge,phase-10" --body "Move document CRUD, status tracking, chunk/embedding/extraction storage, and content hashing from IngestPipeline to a new DocumentStore class in document_store.py. Move DocumentStatus model and compute_content_hash. IngestPipeline takes DocumentStore in __init__. See docs/ingest-complexity-reduction-research.md S4. AC: document_store.py exists with all storage/CRUD methods; IngestPipeline delegates to it; all tests pass; ruff clean."

kanban\kanban-md.exe create "Extract GraphEnricher from IngestPipeline to enrichment.py" --priority needed --tags "modularity,knowledge,phase-10" --body "Move graph enrichment scheduling (_schedule_graph_enrichment, _enrich_graph, _schedule_inter_doc_enrichment, _enrich_inter_doc_graph) and _background_tasks set from IngestPipeline to a new GraphEnricher class in enrichment.py. IngestPipeline takes GraphEnricher in __init__. See docs/ingest-complexity-reduction-research.md S4. AC: enrichment.py exists; IngestPipeline delegates enrichment; ingest.py < 500 lines; all tests pass; ruff clean. Depends on DocumentStore extraction."

kanban\kanban-md.exe create "Update knowledge __init__.py re-exports after ingest split" --priority important --tags "modularity,knowledge,phase-10" --body "After DocumentStore and GraphEnricher extraction, update knowledge/__init__.py to re-export DocumentStore, GraphEnricher, DocumentStatus, compute_content_hash from their new modules. Verify all external import paths still work. See docs/ingest-complexity-reduction-research.md S4. AC: __init__.py exports updated; no import errors across codebase; ruff clean."
```

## 6. Research Checklist

- [x] **Theoretical validity** — SRP extraction of a god-class into orchestrator + stores is a textbook decomposition pattern
- [x] **Prior art** — LlamaIndex (docstore separation) and Haystack (component-based pipeline) both confirm orchestrator-only pipelines
- [x] **Technical feasibility** — Dependency analysis shows zero circular imports; all extracted modules depend only on leaf modules
- [x] **Architecture fit** — Follows existing `intake.py` extraction precedent; complements task #566 (sub-packages); enables task #516 (semaphore)
- [x] **Implementation approach** — Composition over inheritance; `IngestPipeline` takes `DocumentStore` and `GraphEnricher` in `__init__`; delegate don't inherit
