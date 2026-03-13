# Inter-Document Graph Builder Research

> **Owning task:** #256 — Research: Inter-document graph builder
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

After intra-document graph building (task #255) discovers cross-chunk relationships within a single document, the next step is cross-document connections: given entities from document A and document B, ask the LLM "how are these related?" and create inter-document edges.

**Core challenge:** With N documents × M entities per document, naive pairwise comparison yields O(N²×M²) entity pairs — computationally intractable. The research question is: what pre-filtering strategy reduces candidate pairs to a manageable count while preserving high-quality cross-document relationships?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Microsoft GraphRAG paper | <https://arxiv.org/abs/2404.16130> | .95 | LLM-extracted entity KG → Leiden community detection → community summaries; entity merging by exact name match; 1M tokens → ~8K–15K entities |
| GraphRAG indexing dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow/> | .90 | 6-phase pipeline: chunk → extract → summarize → community detect → summarize communities → embed |
| OwlBear IntraDocGraphBuilder | `src/owlbear/memory/knowledge/graph_builder.py` | .95 | Pattern to follow: PydanticAI Agent, batch threshold of 80, entity_type batching, edge stamping |
| OwlBear entity embeddings | `src/owlbear/memory/knowledge/ingest.py` (L714-729) | .90 | Entity descriptions already embedded via BGE-M3 and stored in Qdrant with `embedding_type='entity'` |
| Graph-augmented retrieval research | `docs/graph-augmented-retrieval-impl-research.md` | .85 | Dual-path retrieval (document + entity vectors) already designed; entity embeddings searchable |
| Neo4j entity resolution (Senzing) | <https://neo4j.com/developer-blog/entity-resolved-knowledge-graphs/> | .60 | Entity deduplication across datasets; different use case (record linkage vs. relationship inference) |

## 3. Analysis

### 3.1 Scaling Analysis

For a corpus of N documents with M entities each:

| Metric | Formula | N=50, M=20 | N=200, M=30 | N=500, M=40 |
|--------|---------|------------|-------------|-------------|
| Total entities | N × M | 1,000 | 6,000 | 20,000 |
| Naive cross-doc pairs | ~(NM)²/2 | 500K | 18M | 200M |
| Embedding pre-filter (K=10/entity) | N × M × K | 10K | 60K | 200K |
| LLM calls (batch_size=40) | filtered_pairs / 40 | 250 | 1,500 | 5,000 |

**Key insight:** Embedding pre-filtering reduces pairs by 50×–1000× while preserving the most semantically relevant candidates. At 200K filtered pairs with batch size 40, that's ~5,000 LLM calls — expensive for a single run but tractable as a background job.

### 3.2 Approach Comparison

| Criterion | A: Name-match merge (.60) | B: Embedding-only edges (.65) | C: LLM + embedding pre-filter (.85) | D: Full community detection (.70) |
|-----------|---------------------------|-------------------------------|--------------------------------------|-----------------------------------|
| How it works | Merge entities with identical names across docs (GraphRAG approach) | Create edges when cosine > threshold, no LLM | Use embeddings to find K candidates per entity, LLM infers relationships | Leiden on full graph, then LLM summarizes communities |
| LLM calls | 0 (merge only) | 0 | N×M×K / batch_size | N×M / chunk_size + community count |
| Edge quality | High precision (same name = same entity) but low recall | Medium (semantic similarity ≠ meaningful relationship) | High (LLM validates semantic relationship) | High for community structure, indirect for edges |
| Handles different names | No | Yes (embedding similarity) | Yes | Partially (needs edges first) |
| Complexity | Low (~50 LOC) | Low (~80 LOC) | Medium (~200 LOC) | High (Leiden dependency, community pipeline) |
| KISS score | High | High | Medium | Low |
| YAGNI risk | Low | Low | Low | High (community summaries not needed yet) |

### 3.3 Pre-Filtering Strategy (Approach C Detail)

The recommended approach uses existing infrastructure:

1. **For each entity**, query Qdrant with `search_similar(entity_embedding, top_k=K, embedding_type='entity')` — already supported by `QdrantVectorStore`
2. **Filter results** to entities from *other* documents (skip same-document pairs — already covered by intra-doc builder)
3. **Apply cosine threshold** (e.g., 0.70) to prune weak matches
4. **Group candidates into batches** of ~40 entity pairs per LLM call
5. **LLM infers relationships** using `RelationType` enum, same as `IntraDocGraphBuilder`
6. **Stamp edges** with `weight=0.4` (slightly lower than intra-doc's 0.5) and `metadata={"source": "inter_doc_inference"}`

**Why this works:** Entity embeddings are already in Qdrant (stored during ingestion in `_store_entity_embeddings()`). The `search_similar()` method supports `embedding_type` filtering and scope filtering. No new infrastructure needed.

### 3.4 Architecture Fit

| Question | Answer |
|----------|--------|
| Separate module or extension? | **Separate class** `InterDocGraphBuilder` in new file `inter_doc_graph_builder.py`, following `IntraDocGraphBuilder` pattern |
| When to run? | **Incremental per new document** — after intra-doc build completes, find cross-doc links for the new doc's entities. Optional full-corpus batch mode for initial bootstrap. |
| Scope-aware? | Yes — use scope filtering from `VectorStoreProtocol.search_similar(scopes=...)` to restrict matches within project scope |
| Background job? | Yes — inter-doc building should be async, non-blocking. Can be deferred or run at lower priority than intra-doc. |
| Quality validation? | Confidence threshold on LLM output; edge weight reflects certainty; metadata tracks source doc pair for auditability |

### 3.5 Design: InterDocGraphBuilder

Follow the `IntraDocGraphBuilder` pattern exactly:

- **Constructor:** Takes `model` (str | Model) and `vector_store` (VectorStoreProtocol)
- **Main method:** `async def build(entities, scope, document_id) -> GraphBuildResult`
- **Pre-filter:** Query Qdrant for similar entities from other documents
- **Batching:** Group entity pairs into batches of ~40, one LLM call each
- **System prompt:** Modified to say "entities from different documents" instead of "single document"
- **Edge stamping:** `weight=0.4`, `metadata={"source": "inter_doc_inference", "doc_pair": [doc_a, doc_b]}`
- **Error handling:** Same try/except pattern with logging, skip failed batches

New compared to intra-doc:

- Takes `vector_store` dependency for embedding similarity queries
- Cross-document filtering (exclude same-document entities from candidates)
- Entity pair deduplication (don't re-infer existing inter-doc edges)
- Configurable `top_k` and `cosine_threshold` parameters

## 4. Recommendation (.85 confidence)

**Approach C: LLM inference with embedding pre-filter.** This is the right balance of quality and cost:

- **Leverages existing infrastructure** — entity embeddings already in Qdrant, `search_similar()` already supports `embedding_type='entity'` filtering
- **Follows established pattern** — mirrors `IntraDocGraphBuilder` closely, minimal new concepts
- **KISS-aligned** — no community detection libraries, no new data structures, just entity pairing + LLM
- **Incremental** — runs per new document, not full-corpus rebuilds

**Risks and mitigations:**

- *LLM cost at scale:* Mitigate with aggressive cosine threshold (0.70+) and rate limiting
- *Hallucinated edges:* Mitigate with LLM prompt engineering ("only propose strongly implied relationships"), low default weight (0.4), and confidence gating
- *Stale edges after document deletion:* Mitigate by cascading entity deletion (already in `GraphStore.delete_entity()`) and adding inter-doc edge cleanup to document removal pipeline

**Not recommended yet:**

- Community detection (Leiden) is powerful but adds `graspologic` dependency, significant complexity, and solves a problem we don't have yet (global sensemaking queries). YAGNI — revisit if/when OwlBear needs global summarization.
- Name-match merging misses entities with different names for the same concept (e.g., "Pydantic validation" vs "schema validation").

## 5. Follow-up Tasks

### Implementation tasks (ordered by dependency)

1. **InterDocGraphBuilder core class** — The main builder following IntraDocGraphBuilder pattern
2. **Embedding pre-filter** — Query similar entities from other docs via Qdrant
3. **Integration into ingestion pipeline** — Hook inter-doc build into `_store_results()` after intra-doc
4. **Edge deduplication** — Skip entity pairs that already have inter-doc edges
5. **Tests** — Unit tests for pre-filter, builder, and integration tests for the pipeline

### Kanban commands

```powershell
kanban\kanban-md.exe create "Implement InterDocGraphBuilder core class" --priority important --tags "phase-9,knowledge-graph,agent" --body "## Context`nFollows IntraDocGraphBuilder pattern from graph_builder.py. See docs/inter-document-graph-builder-research.md for design.`n`n## Acceptance Criteria`n- [ ] New file src/owlbear/memory/knowledge/inter_doc_graph_builder.py`n- [ ] InterDocGraphBuilder class with PydanticAI Agent[None, ExtractionResult]`n- [ ] Constructor takes model + VectorStoreProtocol`n- [ ] build() method: pre-filter via embeddings, batch entity pairs, LLM inference`n- [ ] Edge stamping: weight=0.4, metadata={'source': 'inter_doc_inference', 'doc_pair': [a, b]}`n- [ ] Configurable top_k (default 10) and cosine_threshold (default 0.70)`n- [ ] System prompt adapted for cross-document relationship inference`n- [ ] Error handling: skip failed batches with logging`n`nDepends on #255 (intra-document graph builder)"

kanban\kanban-md.exe create "Unit tests for InterDocGraphBuilder" --priority important --tags "phase-9,knowledge-graph,test" --body "## Context`nTDD tests for InterDocGraphBuilder. Write before implementation.`n`n## Acceptance Criteria`n- [ ] test_inter_doc_graph_builder.py in tests/`n- [ ] Test embedding pre-filter returns only cross-document entities`n- [ ] Test cosine threshold filtering`n- [ ] Test batch grouping of entity pairs`n- [ ] Test edge stamping (weight=0.4, inter_doc metadata)`n- [ ] Test error handling (failed LLM call skips batch)`n- [ ] Test deduplication (existing inter-doc edges skipped)`n- [ ] Mock VectorStoreProtocol and PydanticAI agent`n- [ ] >= 90% coverage"

kanban\kanban-md.exe create "Integrate InterDocGraphBuilder into ingestion pipeline" --priority important --tags "phase-9,knowledge-graph" --body "## Context`nHook InterDocGraphBuilder into the ingestion pipeline after intra-doc graph building completes.`n`n## Acceptance Criteria`n- [ ] After _store_results() runs intra-doc builder, trigger inter-doc builder for new doc's entities`n- [ ] Inter-doc build runs async (non-blocking to ingestion)`n- [ ] Skip inter-doc build if fewer than 2 documents in scope`n- [ ] Add config toggle to enable/disable inter-doc building`n- [ ] Integration test: ingest 2 docs, verify cross-doc edges created`n`nDepends on InterDocGraphBuilder core class task"
```

## 6. Sources Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Microsoft GraphRAG | <https://arxiv.org/abs/2404.16130> | Entity merging by name match, Leiden community detection, community summarization pipeline, scaling data (~8K–15K entities per 1M tokens) | `docs/inter-document-graph-builder-research.md` (comparison analysis, scaling reference) | 2026-02-28 |
| GraphRAG Indexing Dataflow | <https://microsoft.github.io/graphrag/index/default_dataflow/> | 6-phase pipeline (chunk → extract → graph → community → summarize → embed), entity/relationship summarization pattern | `docs/inter-document-graph-builder-research.md` (pipeline comparison) | 2026-02-28 |
