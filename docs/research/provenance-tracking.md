# Provenance Tracking for Knowledge Graph Entities

> **Owning task:** #275 — Add provenance tracking to IngestResult
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Task #275 asks us to stamp every entity and edge with `source_pipeline` and `source_task` provenance metadata, inspired by Cognee's `DataPoint` provenance pattern. The goal is traceability: when debugging the knowledge graph, we need to know which pipeline step produced each entity/edge.

**Key question:** Add dedicated SQL columns (schema v5) or reuse the existing `metadata` JSON dict?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Cognee DataPoint model | github.com/topoteretes/cognee | .90 | `source_pipeline` / `source_task` on every DataPoint; used for lineage queries |
| OwlBear knowledge-pipeline-research | docs/research/knowledge-pipeline.md §4 | .95 | Original recommendation to adopt this pattern |
| SQLite JSON1 extension | sqlite.org/json1.html | .85 | `json_extract()` for querying inside JSON columns; ships with Python 3.12+ |
| OwlBear Entity/Edge models | src/owlbear/memory/knowledge/models.py | 1.0 | Current state: `metadata: dict[str, Any]` on both models |
| OwlBear IngestPipeline | src/owlbear/memory/knowledge/ingest.py | 1.0 | `_store_extractions()` already stamps scope/document_id via `model_copy` |

## 3. Analysis

### 3.1 Storage Approach

| Criterion | A: Metadata dict (.85) | B: Dedicated columns (.55) |
|-----------|------------------------|---------------------------|
| Schema migration | None needed | v4→v5 migration + ALTER TABLE x2 tables |
| Query filter | `json_extract(metadata, '$.source_pipeline') = ?` | `WHERE source_pipeline = ?` |
| Index support | Not indexable (acceptable at our scale) | Can add B-tree index |
| Code change size | ~30 LOC (ingest.py + graph.py) | ~80 LOC (schema + models + graph + ingest) |
| KISS alignment | High — reuses existing infrastructure | Medium — adds structural complexity |
| Pydantic model change | None — metadata dict already exists | Add 2 fields to Entity + Edge |
| Performance at scale | Fine for <100k entities; `json_extract` is O(n) scan | Better for >100k entities |

**Verdict:** Option A. Our knowledge graph is laptop-scale (<10k entities). The `metadata` dict already exists on both `Entity` and `Edge`. SQLite 3.50.4 (confirmed in our env) supports `json_extract`. No schema migration, no model changes, minimal diff.

### 3.2 Provenance Keys

Following Cognee's naming convention:

| Key | Type | Value | Example |
|-----|------|-------|---------|
| `source_pipeline` | `str` | Pipeline name that produced the entity/edge | `"ingest"`, `"graph_enrichment"` |
| `source_task` | `str` | Specific pipeline step | `"entity_extraction"`, `"intra_doc_graph"` |

### 3.3 Stamp Points in IngestPipeline

| Method | What it stamps | source_task value |
|--------|---------------|-------------------|
| `_store_extractions()` | Entities + edges from LLM extraction | `"entity_extraction"` |
| `_enrich_graph()` | Edges from graph builder | `"graph_enrichment"` |

The `IngestPipeline` constructor gets an optional `pipeline_name: str = "ingest"` parameter. Both stamp points merge `{"source_pipeline": self._pipeline_name, "source_task": "..."}` into the entity/edge metadata dict via `model_copy`.

### 3.4 Query Filter in GraphStore

Add optional `source_pipeline: str | None = None` parameter to `list_entities()`:

```python
if source_pipeline is not None:
    clauses.append("json_extract(metadata, '$.source_pipeline') = ?")
    params.append(source_pipeline)
```

Same pattern for `list_edges()`.

## 4. Recommendation (.90 confidence)

Use the **metadata dict approach** (Option A). Three implementation tasks:

1. **Stamp provenance in IngestPipeline** — Add `pipeline_name` constructor param; stamp `source_pipeline` + `source_task` in `_store_extractions()` and `_enrich_graph()`. ~20 LOC.
2. **Add `source_pipeline` filter to GraphStore** — Add `json_extract` clause to `list_entities()` and `list_edges()`. ~15 LOC.
3. **Add `source_pipeline`/`source_task` to IngestResult** — Expose provenance on the result model for callers. ~5 LOC.

Total: ~40 LOC across 2 files. No schema migration. No model changes. TDD: test the filter with a fixture that inserts entities with/without provenance metadata.

## 5. Follow-up Tasks

Three atomic tasks below. Task 1 is the core implementation; tasks 2–3 are the filter and result model extensions.
