# Source-Aware Candidate Filtering in InterDocGraphBuilder

> **Owning task:** #863 — P3-02: Source-aware candidate filtering in InterDocGraphBuilder
> **Date:** 2026-04-14 **Status:** Complete

## 1. Context and Question

InterDocGraphBuilder filters candidates by `document_id` but not by `source_id`. Brief Outcome 4 requires cross-*source* linking (e.g., SharePoint security policy → Confluence implementation guide). The builder should prioritize cross-source pairs and include source metadata in edge stamps.

**Research questions:**
1. What is the most KISS-aligned approach for joining entities to their document's `source_id`?
2. How should cross-source prioritization work within the existing batching flow?
3. What metadata should edges carry, given no existing `doc_pair` field?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | `inter_doc_graph_builder.py` (codebase) | .95 | Current `_collect_candidates()`: filters by `document_id`, no source awareness |
| 2 | `models.py` (codebase) | .90 | `Entity.document_id` → `Document.source_id` chain; no `source_id` on Entity |
| 3 | `graph_store.py` (codebase) | .90 | `get_document(doc_id)` returns `Document` with `source_id`; PK lookup, cheap |
| 4 | 772 research doc (codebase) | .85 | Gap G3 analysis; confirmed source-level filtering is medium severity |
| 5 | Kumar et al. (2025) — arxiv:2503.07993 | .70 | Enterprise KG integrating emails, calendars, docs via LLM; cross-source by design, entity matching via embedding + LLM mapper |
| 6 | Saeedi et al. (2020) — ESWC | .65 | Incremental multi-source entity resolution for KG completion; optimized entity-to-cluster assignment across sources |

## 3. Analysis

### 3.1 Current Data Model

```
Entity.document_id → Document.id → Document.source_id → KnowledgeSource.id
```

Entity has no direct `source_id`. Two-hop lookup is required: entity → document → source.

### 3.2 AC Discrepancy: `doc_pair` Does Not Exist

AC3 says "alongside existing `doc_pair`". Grep confirms: **no `doc_pair` metadata exists anywhere in the codebase.** Edge metadata currently only contains `source: "inter_doc_inference"` (set by `_stamp_inter_edge`). Both `doc_pair` and `source_pair` must be added fresh.

### 3.3 Dependency Context

- **#862 (prompt fix) is blocked** — LLMExtractor removed (pydantic-ai dropped). The `StructuredExtractor` protocol exists but has no production implementation. InterDocGraphBuilder has no production call site.
- This task (#863) is independent of the extractor mechanism — source-aware filtering happens *before* LLM calls. Implementation is valid even without a working extractor.
- All Phase 3 tasks carry the `deferred` tag — gated on real corporate ingestion.

### 3.4 Implementation Options

| Criterion | A: Direct doc lookup (.85) | B: Batch SQL method (.75) | C: Entity model change (.40) |
|-----------|---------------------------|---------------------------|------------------------------|
| Approach | `graph_store.get_document(doc_id)` per unique doc_id | New `GraphStore.get_source_ids(doc_ids)` method | Add `source_id` to Entity model |
| LOC estimate | ~30 | ~45 | ~100+ schema migration |
| Interface changes | None | New GraphStore method | Schema v10 + model change |
| DB calls | N (≤ unique doc_ids, typically < 10 per batch) | 1 SQL query | 0 (already on entity) |
| KISS | High | Medium | Low — over-engineering |
| YAGNI risk | Low | Medium — premature for unused builder | High — schema change for deferred feature |
| Performance at scale | Adequate (SQLite PK lookups ~μs each) | Slightly better at 100+ docs | Best — no lookups |

### 3.5 Prioritization Strategy

Two viable approaches for cross-source prioritization:

| Strategy | How | Pro | Con |
|----------|-----|-----|-----|
| **Sort-first** | Partition candidates into cross-source and same-source-cross-doc, return cross-source first | Simple, LLM sees cross-source pairs in early batches | All candidates still processed |
| **Weight-boost** | Give cross-source edges a +0.1 weight boost after stamping | Results carry signal of cross-source origin | Conflates weight semantics |

**Recommendation: Sort-first.** KISS, no semantic changes to edge weights. The LLM processes cross-source pairs in priority batches. Downstream consumers can also filter by `source_pair` metadata.

### 3.6 Edge Metadata Stamping

After extractor returns edges, each edge's `source_id`/`target_id` point at entity IDs. Since `entity_by_id` and `doc_to_source` maps are available in `build()`, metadata enrichment is straightforward:

```python
# Pseudocode — per returned edge:
src_entity = entity_by_id[edge.source_id]
tgt_entity = entity_by_id[edge.target_id]
doc_pair = sorted([src_entity.document_id, tgt_entity.document_id])
source_pair = sorted([doc_to_source.get(src_entity.document_id), doc_to_source.get(tgt_entity.document_id)])
```

Both `doc_pair` and `source_pair` are sorted lists for stable dedup/comparison.

## 4. Recommendation (confidence: .82)

**Option A: Direct document lookup with sort-first prioritization.**

- Pre-compute `doc_to_source: dict[str, str | None]` from unique `document_id` values via `graph_store.get_document()` at start of `build()`
- In `_collect_candidates()`, partition results: cross-source pairs first, then same-source cross-doc pairs
- In `build()`, after edge stamping, enrich metadata with `doc_pair` and `source_pair`
- ~30 LOC change, zero interface additions, zero schema changes

**Risks:**
1. Entities with `document_id=None` or documents with `source_id=None` — mitigation: treat as "unknown" source, never prioritize as cross-source
2. `get_document()` returns `None` for orphaned document_ids — mitigation: skip or treat as unknown

Challenge: FALLBACK — challenger subagent not available in agent list.

## 5. Follow-up Tasks

No additional follow-up tasks needed. #863's AC is self-contained and concrete. Implementation covers all four AC items:
1. `_collect_candidates()` joins via `get_document()` to resolve `source_id`
2. Cross-source pairs prioritized via sort-first partition
3. Metadata stamped with `source_pair` and `doc_pair`
4. Tests cover filtering and metadata
