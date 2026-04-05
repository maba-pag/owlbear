# Intra-Document Graph Builder

> **Owning task:** #255 — Research: Intra-document graph builder
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear's entity extraction pipeline (`EntityExtractor`) processes each chunk in isolation. A 10-page document split into 8 chunks produces 8 independent subgraphs. The entity deduplicator (`dedup.py`) merges near-identical entity *names* globally, but no step discovers **implicit relationships between entities from different chunks of the same document**.

Example failure: Chunk 2 mentions "AuthService" and chunk 6 mentions "TokenValidator". A human reading the full document sees that AuthService depends on TokenValidator, but no chunk states this directly. An intra-document graph builder would infer that edge.

**Key question:** Does post-hoc, document-level relationship inference improve graph quality enough to justify the LLM cost? What's the simplest approach?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Microsoft GraphRAG (Edge et al. 2024) | arxiv.org/abs/2404.16130 | .95 | Per-TextUnit extraction → merge by name → summarize descriptions → community detection. The "entity & relationship summarization" phase is exactly cross-chunk consolidation. |
| MS GraphRAG Indexing Dataflow | microsoft.github.io/graphrag/index/default_dataflow | .90 | 6-phase pipeline: chunk → extract → summarize → community → embed. Merge step: entities with same name+type are merged by collecting description arrays, then LLM-summarized. |
| LlamaIndex PropertyGraphIndex | developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide | .80 | Per-node extraction with `SimpleLLMPathExtractor` / `SchemaLLMPathExtractor`. No explicit cross-chunk step — relies on graph store upsert-by-name for implicit dedup. |
| LightRAG (Guo et al. 2024) | github.com/HKUDS/LightRAG | .85 | Entity extraction → merge by name → entity merging API. Supports entity merge + relationship regeneration via `merge_entities()` method. Reranker post-retrieval. |
| nano-graphrag | github.com/gusye1234/nano-graphrag | .75 | ~1100 LOC GraphRAG. Same pattern: extract per chunk → merge entities by name → summarize descriptions. Community detection via Leiden on merged graph. |
| OwlBear dedup.py | src/owlbear/memory/knowledge/dedup.py | .90 | Existing fuzzy merge: SequenceMatcher ratio ≥ 0.85 → union-find grouping → pick canonical → redirect edges. Operates globally (not per-document). |

## 3. Analysis

### 3.1 Prior Art Consensus

All studied systems follow the same core pattern:

```
Per-chunk extraction → Entity merge (by name) → Description summarization → (Optional) Community detection
```

None implement a separate "ask LLM to infer new relationships between entities" step. Instead, they consolidate what was *already extracted* but fragmented across chunks. The cross-chunk benefit comes from **merging** and **summarizing**, not from inventing new edges.

This is an important finding: the prior art suggests that entity description summarization (merging fragmented views of the same entity) is more valuable than relationship inference between distinct entities.

### 3.2 Approaches Compared

| Approach | How it works | LLM calls/doc | Token cost (20 entities) | Quality | Complexity | KISS |
|----------|-------------|---------------|--------------------------|---------|------------|------|
| **A. Entity-list relationship inference** | Collect all entities from doc → single LLM call → "what relationships exist?" | 1 | ~2K in + ~1K out = ~3K | Medium — LLM may hallucinate edges without source text context | Low | **Good** |
| **B. Description merge + summarize** (GraphRAG) | Merge entities by name → LLM-summarize descriptions per entity | 1 per merged entity | ~500/entity × ~5 merged = ~2.5K | **High** — consolidates fragmented info | Medium | Good |
| **C. Pairwise entity comparison** | For each entity pair, ask LLM "is there a relationship?" | $\binom{n}{2}$ | 190 calls × ~500 = ~95K for 20 entities | High but insanely expensive | Very high | **Bad** |
| **D. Embedding-similarity edges** | Embed entity descriptions → create edges above cosine threshold | 0 | 0 (CPU only) | **Low** — similarity ≠ relationship; high false positives | Low | Good |
| **E. Hybrid: merge + single inference call** | Dedup → summarize → one LLM call with entity list + doc summary | 1 + merged count | ~4K + ~2.5K merge = ~6.5K | **Highest** — informed inference | Medium | Acceptable |

### 3.3 Recommendation Analysis

**Option C eliminated** — $O(n^2)$ LLM calls is a non-starter for a background enrichment job.

**Option D eliminated** — Cosine similarity between descriptions produces too many false positives (e.g., "AuthService: handles authentication" and "TokenValidator: validates auth tokens" are similar but `RELATED_TO` is vague and unhelpful).

**Option A vs B vs E:**

Option B (GraphRAG pattern) is what every major framework does. But our dedup.py already handles name-based entity merging. What's missing is **description summarization** — when dedup merges two entities, it keeps the longest description rather than summarizing both. This is a simpler fix than building an entirely new graph builder.

Option A (single inference call) addresses the *actual* gap: discovering relationships between *distinct* entities across chunks. This is what the user's request describes.

Option E combines both but adds complexity. Per YAGNI, start with the cheaper approach and measure.

### 3.4 Cost Estimate

Typical OwlBear document profile:

| Doc size | Chunks (1200 tok) | Entities/chunk | Total entities | Unique (post-dedup) |
|----------|-------------------|----------------|----------------|---------------------|
| 2 pages | 2–3 | 5–10 | 10–30 | 8–20 |
| 10 pages | 8–12 | 5–10 | 40–120 | 25–60 |
| 50 pages | 40–60 | 5–10 | 200–600 | 80–200 |

For the single-call approach (Option A), token cost per document:

| Unique entities | Input tokens (entity list) | Output tokens (edges) | Total | Cost @ $0.01/1K |
|-----------------|---------------------------|----------------------|-------|------------------|
| 20 | ~1,500 | ~800 | ~2,300 | $0.023 |
| 60 | ~4,500 | ~2,000 | ~6,500 | $0.065 |
| 200 | ~15,000 | ~5,000 | ~20,000 | $0.200 |

For 200 entities, the entity list alone is ~15K tokens. GPT-4o-mini context is 128K, so it fits. But at 200 entities, the LLM will struggle to reason about all pairwise relationships. A **sliding window** or **entity-type grouping** batching strategy is needed above ~80 entities.

### 3.5 Architecture Gap: Entity Provenance

**Critical prerequisite:** Entities currently have no `document_id` field. The `_store_extractions` method in `ingest.py` stores entities globally — there's no way to query "all entities from document X." Without this, the intra-document graph builder can't collect entities per document.

Solutions:

1. Add `document_id` column to `entities` table (schema v4 migration)
2. Store `document_id` in entity `metadata` dict (no schema change, query via JSON)
3. Create a `document_entities` junction table (most normalized)

Option 2 is simplest (KISS) but makes querying slow (JSON parsing). Option 1 is cleanest and aligns with existing `chunks.document_id` pattern. **Recommend Option 1.**

### 3.6 Hallucination Mitigation

Risk: LLM invents plausible but incorrect edges (e.g., "AuthService DEPENDS_ON DatabasePool" when the document never mentions this).

Mitigations from prior art:

1. **Confidence scoring** (GraphRAG): weight edges from inference lower (0.5 default vs 1.0 for direct extraction)
2. **Constrained relation types**: only allow `RELATED_TO`, `DEPENDS_ON`, `IMPLEMENTS` — the same RelationType enum we already have
3. **Source tagging**: store `metadata.source = "intra_doc_inference"` so hallucinated edges can be identified and pruned
4. **Structured output**: use PydanticAI agent with `ExtractionResult` schema (we already have this)
5. **Verification prompt**: optionally ask "for each proposed edge, cite which entities' descriptions support it"

Recommendation: mitigations 1 + 2 + 3 + 4 (skip 5 per YAGNI, adds a second LLM call).

### 3.7 When to Run

| Trigger | Pros | Cons |
|---------|------|------|
| Immediately after ingestion | Simple, always fresh | Blocks ingestion pipeline, couples tightly |
| **Background job after ingestion** | Non-blocking, can batch multiple docs | Needs scheduling mechanism |
| On-demand (user triggers) | Minimal waste | User must remember to run it |
| Scheduled (periodic) | Catches all new docs | May re-process already-processed docs |

**Recommend: background job after ingestion.** The IngestPipeline returns `IngestResult` with `document_id` — a post-ingestion hook can queue the graph builder. Mark documents as `graph_enriched` in `document_status` to prevent re-processing.

### 3.8 Incremental Updates

When new chunks are added to an existing document (re-ingest): only cross-reference new entities against existing ones for that document. Track which entity pairs have already been evaluated via edge metadata.

## 4. Recommendation (.80 confidence)

**Implement a document-level graph builder using a single LLM call per document** (Option A), with the GraphRAG-style description summarization (Option B) as a separate, simpler task.

### Architecture

New module: `src/owlbear/memory/knowledge/graph_builder.py`

```
class IntraDocGraphBuilder:
    """Discover cross-chunk relationships within a single document."""

    def __init__(self, graph: GraphStore, model: str | Model):
        self._graph = graph
        self._agent = Agent[None, ExtractionResult](model, ...)

    async def build(self, document_id: str, scope: str = "global") -> GraphBuildResult:
        # 1. Collect entities for this document (requires provenance)
        entities = self._graph.list_entities_for_document(document_id)
        if len(entities) < 2:
            return GraphBuildResult(edges_added=0)

        # 2. Build prompt with entity names + descriptions
        prompt = self._build_prompt(entities)

        # 3. LLM inference — structured output
        result = await self._agent.run(prompt)

        # 4. Store edges with low weight + source tag
        edges_added = self._store_edges(result.output, document_id, scope)

        return GraphBuildResult(edges_added=edges_added)
```

### Prerequisite tasks

1. **Entity provenance** — add `document_id` to entities table or metadata
2. **Description summarization** (separate from this task) — when dedup merges entities, LLM-summarize descriptions instead of picking longest

### Batching for large documents (>80 entities)

Group entities by `entity_type`, run one inference call per group. For a 200-entity document with 6 entity types: ~6 calls × ~3K tokens = ~18K tokens total, well within budget.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add document_id provenance to entities table (schema v4)" --priority needed --tags "phase-9,knowledge-graph,memory" --body "Prerequisite for intra-document graph builder (#255). Add document_id column to entities table with FK to documents(id). Update EntityExtractor + IngestPipeline to stamp document_id during extraction. Add GraphStore.list_entities_for_document(doc_id) query method. See docs/research/intra-document-graph.md §3.5. AC: - [ ] Schema v4 migration adds document_id column to entities - [ ] IngestPipeline._store_extractions stamps document_id - [ ] GraphStore.list_entities_for_document(doc_id) works - [ ] Existing entities get NULL document_id (backward compat) - [ ] Tests for migration and new query method"

kanban\kanban-md.exe create "Implement IntraDocGraphBuilder — cross-chunk relationship inference" --priority needed --tags "phase-9,knowledge-graph,agent" --body "Core intra-document graph builder. After ingestion, collect all entities from a document and ask LLM to infer cross-chunk relationships. Uses PydanticAI structured output. Depends on entity provenance task. See docs/research/intra-document-graph.md §4. AC: - [ ] New module graph_builder.py with IntraDocGraphBuilder class - [ ] PydanticAI agent with ExtractionResult output (reuse existing schema) - [ ] Single LLM call per document (batch by entity_type if >80 entities) - [ ] Edges stored with weight=0.5 and metadata.source='intra_doc_inference' - [ ] Constrained to existing RelationType enum - [ ] Returns GraphBuildResult with edges_added count"

kanban\kanban-md.exe create "Test IntraDocGraphBuilder — cross-chunk inference with mocked agent" --priority needed --tags "phase-9,knowledge-graph,agent,test" --body "TDD tests for IntraDocGraphBuilder. See docs/research/intra-document-graph.md. AC: - [ ] Test with 0, 1, 2, 20 entities (boundary cases) - [ ] Test entity-type batching triggers above 80 entities - [ ] Test edges get weight=0.5 and correct metadata tagging - [ ] Test LLM failure produces empty result (no crash) - [ ] Mock PydanticAI agent (no real LLM calls) - [ ] Test scope passthrough"

kanban\kanban-md.exe create "Wire IntraDocGraphBuilder into IngestPipeline as post-ingestion hook" --priority important --tags "phase-9,knowledge-graph,memory" --body "After IngestPipeline completes successfully, queue the IntraDocGraphBuilder for the ingested document. Non-blocking — run as background task. Track enrichment status in document_status. See docs/research/intra-document-graph.md §3.7. AC: - [ ] IngestPipeline triggers graph builder after successful ingestion - [ ] Runs as asyncio.create_task (non-blocking) - [ ] document_status updated to 'graph_enriched' on completion - [ ] Skips if document already enriched (idempotent) - [ ] Test integration with mocked builder"

kanban\kanban-md.exe create "Add LLM description summarization to entity dedup" --priority important --tags "phase-9,knowledge-graph,agent" --body "Currently dedup picks the longest description when merging entities. Instead, LLM-summarize all descriptions into a single coherent description (GraphRAG pattern). Independent of IntraDocGraphBuilder but complementary. See docs/research/intra-document-graph.md §3.1. AC: - [ ] dedup accepts optional LLM model param - [ ] When model provided: summarize merged descriptions via PydanticAI agent - [ ] When no model: fall back to current longest-wins behavior - [ ] Summary is concise (max ~100 words) - [ ] Test with mocked agent"
```

## 6. Attribution Updates

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Microsoft GraphRAG | arxiv.org/abs/2404.16130 | Entity merge + description summarization pattern; cross-chunk consolidation approach | docs/research/intra-document-graph.md, future graph_builder.py | 2026-02-28 |
| Microsoft GraphRAG Dataflow | microsoft.github.io/graphrag/index/default_dataflow | 6-phase indexing pipeline, entity & relationship summarization architecture | docs/research/intra-document-graph.md | 2026-02-28 |
| LlamaIndex PropertyGraphIndex | developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide | SchemaLLMPathExtractor, constrained entity/relation types, per-node extraction pattern | docs/research/intra-document-graph.md | 2026-02-28 |
| LightRAG | github.com/HKUDS/LightRAG | Entity merging API, reranker integration, workspace-scoped isolation | docs/research/intra-document-graph.md | 2026-02-28 |
| nano-graphrag | github.com/gusye1234/nano-graphrag | Minimal GraphRAG implementation (~1100 LOC), extract-merge-summarize pattern | docs/research/intra-document-graph.md | 2026-02-28 |
