# Graph-Augmented Retrieval (bge-m3 + Neighbor Expansion)

> **Owning task:** #234 — Research: Graph-augmented retrieval (bge-m3 + neighbor expansion)
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear's knowledge pipeline serves a mixed-domain corpus: ~35% detail-oriented text (ISO norms, internal policies, laws), ~50% technical docs, ~15% general info. Current retrieval: dense embedding (bge-small-en-v1.5 via FastEmbed ONNX) → sqlite-vec similarity search → optional bge-reranker-v2-m3 cross-encoder reranking. The prior research (#232) recommends adding SPLADE++ sparse retrieval with RRF fusion.

**Question**: After vector+sparse retrieval finds relevant chunks, can we enrich the result set by traversing the knowledge graph and including neighboring entities/edges? Does bge-m3 (dense+sparse+ColBERT from one model) simplify the embedding stack enough to justify replacing FastEmbed?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Microsoft GraphRAG — Local Search | microsoft.github.io/graphrag/query/local_search | .95 | Entity-based reasoning: embed query → find entities → fan out to neighbors, relationships, community reports, text units → prioritize → fill context window |
| neo4j-graphrag-python `VectorCypherRetriever` | neo4j.com/developer-blog/graph-traversal-graphrag-python-package | .90 | Vector search → Cypher traversal from matched nodes → collect neighbor data → merge into context |
| BGE-M3 paper (Chen et al. 2024) | arxiv.org/abs/2402.03216 | .90 | Single model: dense (1024-d) + sparse (lexical weights) + ColBERT; 8192 tokens; multilingual; MIT license |
| FastEmbed supported models (Qdrant) | qdrant.github.io/fastembed/examples/Supported_Models | .95 | bge-m3 NOT in FastEmbed model list (no ONNX export for multi-vector); only dense/sparse/ColBERT separately |
| BAAI/bge-m3 HuggingFace model card | huggingface.co/BAAI/bge-m3 | .85 | Usage via `BGEM3FlagModel`; requires `FlagEmbedding` (PyTorch); FP16 2.2 GB; model dim 1024 |
| LightRAG (HKUDS) | github.com/HKUDS/LightRAG | .75 | Graph-augmented retrieval: entity extraction → graph storage → query-time entity matching + neighbor expansion → LLM generation |
| nano-graphrag | github.com/gusye1234/nano-graphrag | .70 | Minimal GraphRAG (~1100 LOC): community detection + neighbor traversal at query time |
| OwlBear dual-embedding-rrf.md | docs/research/dual-embedding-rrf.md | .90 | Current dual-embedding + RRF recommendation (Option B: bge-small + SPLADE++) |
| OwlBear retrieve-rerank.md | docs/research/retrieve-rerank.md §3.6 | .85 | Failure mode analysis: cross-references, policy lookups — graph expansion directly addresses these |
| OwlBear knowledge-graph.md | docs/research/knowledge-graph.md | .80 | Current architecture: SQLite + sqlite-vec + FastEmbed; GraphStore entities/edges/documents |

## 3. Analysis

### 3.1 Architecture Variants — Comparison

| Variant | How it works | Complexity | Benefit | Fit for OwlBear |
|---------|-------------|------------|---------|-----------------|
| **Pre-retrieval expansion** | Vector search → get entity IDs → traverse graph 1-2 hops → append neighbor text to context | Low | Direct, predictable, composable with existing reranker | **Best (.85)** |
| **Post-retrieval expansion** | LLM generates initial answer → identify gaps → query graph to fill → re-generate | High | Can fill specific gaps | Overkill for MVP; doubles LLM calls |
| **Graph-guided retrieval** | Use graph structure (PageRank, centrality) to weight/filter vector search results | Medium | Prioritizes well-connected entities | Requires precomputed graph metrics; premature |
| **Community-based (MS GraphRAG)** | Leiden clustering → community summaries → query community reports | Very High | Holistic corpus understanding | Requires LLM-generated summaries per community; expensive, server-oriented |

**Verdict**: Pre-retrieval expansion is the KISS choice. It's a single additional step after vector search, requires no precomputed graph metrics, and integrates cleanly with the existing pipeline.

### 3.2 Pre-retrieval Expansion — Architecture

```
User Query
    │
    ▼
┌────────────────────────┐
│ 1. Embed + Search      │ dense vec0 MATCH + sparse SPLADE + RRF
│    VectorStore          │ (as designed in #232 dual-embedding)
└──────────┬─────────────┘
           │ top_k candidate IDs (entity or chunk IDs)
           ▼
┌────────────────────────┐
│ 2. Resolve to entities │ chunk → document → linked entities
│    bridge table lookup  │ (embedding_rowid_map → entities table)
└──────────┬─────────────┘
           │ entity IDs (seed set)
           ▼
┌────────────────────────┐
│ 3. Graph traversal     │ BFS from seed entities, 1-2 hops
│    GraphStore.list_edges│ collect neighbor entities + edge metadata
└──────────┬─────────────┘
           │ expanded entity set + relationship descriptions
           ▼
┌────────────────────────┐
│ 4. Assemble context    │ original chunks + neighbor descriptions
│    with budget cap     │ max_expansion_tokens to prevent overflow
└──────────┬─────────────┘
           │ enriched context (fits LLM window)
           ▼
┌────────────────────────┐
│ 5. (Optional) Reranker │ rerank expanded set by relevance
└──────────┬─────────────┘
           │ final results
           ▼
        LLM generation
```

### 3.3 When Graph Augmentation Helps vs. Doesn't

| Scenario | Example | Helps? | Why |
|----------|---------|--------|-----|
| Cross-referencing norms | ISO 27001 §6.1.2 references ISO 31000 | **Yes** | Edge `RELATED_TO` between norm entities provides the cross-reference |
| API → class → function chains | "How does `IngestPipeline` use `EntityExtractor`?" | **Yes** | `DEPENDS_ON`/`IMPORTS` edges connect the chain |
| Policy → regulation mapping | "HR-POL-042 implements GDPR Art. 17" | **Yes** | `IMPLEMENTS` edge directly captures this relationship |
| Standalone articles/slides | "What's the Q3 team update?" | **No** | No meaningful graph connections; plain vector search suffices |
| Highly specific detail lookup | "What is the max timeout in §4.2.1?" | **No** | Answer is within the chunk itself; neighbors add noise |
| Broad conceptual questions | "What security practices do we follow?" | **Maybe** | Graph can connect scattered security-related entities, but community summaries (MS GraphRAG style) would be better — too complex for MVP |

**Rule of thumb**: Graph expansion adds value when the answer requires connecting information across documents/entities. It adds noise when the answer is self-contained in a single chunk.

### 3.4 Traversal Depth Analysis

| Depth | Nodes reached (avg) | Latency (est.) | Context added | Risk |
|-------|---------------------|-----------------|---------------|------|
| 0 (no expansion) | seed set only | 0ms | 0 tokens | Baseline — misses connections |
| **1-hop** | seed + ~5-15 neighbors | ~1-5ms (SQLite) | ~500-2000 tokens | **Sweet spot** — captures direct relationships |
| 2-hop | seed + ~25-100 nodes | ~5-20ms | ~2000-8000 tokens | Risk of context explosion; most 2-hop neighbors are noise |
| 3-hop+ | hundreds of nodes | >50ms | >10K tokens | Almost always too much; "everything connects to everything" |

**Recommendation (.85 confidence)**: Default to **1-hop**, make depth configurable (0-2). Add a `max_expansion_tokens` budget (default ~2000) that caps how many neighbor descriptions get included regardless of depth.

### 3.5 bge-m3 as Embedding Model — Feasibility

| Criterion | bge-m3 via FlagEmbedding | Current (bge-small + SPLADE++) | Winner |
|-----------|--------------------------|-------------------------------|--------|
| Dense + sparse from one model | **Yes** (single encode call) | No (two models, two passes) | bge-m3 |
| FastEmbed support (ONNX) | **No** — not in FastEmbed model list | **Yes** — both models in FastEmbed | Current |
| Dependency | FlagEmbedding → PyTorch (~2 GB) | FastEmbed → ONNX Runtime (~15 MB) | Current |
| Model size (RAM) | ~2.3 GB FP16 | ~600 MB total (67 + 532 MB) | Current |
| Embedding dim | 1024-d (requires schema migration) | 384-d dense (no migration) | Current |
| Max tokens | 8192 | 512 (dense), 512 (sparse) | bge-m3 |
| Throughput (Ryzen 8840U) | ~30 chunks/s (PyTorch CPU) | ~200 chunks/s dense, ~50 sparse | Current |
| ColBERT support | Yes (bonus) | No | bge-m3 |
| KISS alignment | Low (PyTorch dep, schema migration) | **High** | Current |

**bge-m3 verdict (.40 confidence against, .60 for future)**: bge-m3 is technically superior (single model, 3 retrieval modes, 8192 tokens) but **violates KISS and YAGNI** today. Adding PyTorch as a dependency for the embedding model contradicts the lightweight/ONNX-first decision made in #50. The correct path: implement graph-augmented retrieval with the current embedding stack (bge-small + SPLADE++), then evaluate bge-m3 as a future upgrade when/if we move to Qdrant (#236) which has native multi-vector support.

**FastEmbed bge-m3 status**: Confirmed NOT supported. The FastEmbed supported models page lists 24 dense models (up to `intfloat/multilingual-e5-large`), 4 sparse models (BM25, BM42, SPLADE++), and 3 late-interaction models (ColBERT variants) — bge-m3 is absent from all three lists. The bge-m3 model requires `FlagEmbedding.BGEM3FlagModel` which depends on PyTorch.

### 3.6 Integration with Current OwlBear Architecture

**What exists today** (from codebase analysis):

- `GraphStore.list_edges(source_id=X)` — returns all outgoing edges from entity X
- `GraphStore.list_edges(target_id=X)` — returns all incoming edges to entity X
- `GraphStore.get_entity(id)` — fetch entity by ID
- `VectorStore.search_similar()` — dense search with optional reranker
- `embedding_rowid_map` bridge table — maps entity/document IDs to vec0 rowids
- No existing neighbor traversal or graph expansion function

**What needs to be built**:

1. **`GraphStore.get_neighbors(entity_id, depth=1, max_nodes=20)`** — BFS traversal returning neighbor entities + edges. ~30 LOC. Uses existing `list_edges` + `get_entity`.

2. **`GraphAugmentedRetriever` class** — orchestrates: vector search → resolve entity IDs → graph expansion → assemble context. ~80-100 LOC.

3. **Entity-chunk linkage** — Currently, chunks are linked to documents (via `chunks.document_id`), and entities are extracted from chunks (via `extractor.py`). But there's no explicit `chunk_id → entity_id` mapping in the schema. The `embedding_rowid_map` links `entity_or_document_id` to vec0 rowids, but expanding from a chunk result to its entities requires an intermediate lookup. Options:
   - (a) Add `chunk_id` column to entities table (simple, ~5 LOC migration)
   - (b) Create `chunk_entity_map` junction table (normalized, more flexible)
   - (c) Store entity IDs in chunk metadata JSON (denormalized, no schema change)

   Recommendation: **(a)** — add `chunk_id` to entities table. Simplest, enables direct `chunk → entities → neighbors` traversal.

### 3.7 Context Window Budget Management

The critical risk of graph expansion is context explosion. Mitigation strategy:

```python
# Pseudocode for budget-aware expansion
def expand_with_budget(
    seed_entities: list[Entity],
    graph: GraphStore,
    max_tokens: int = 2000,  # budget for expansion text
    max_depth: int = 1,
    max_neighbors: int = 20,
) -> list[str]:
    """BFS expansion with token budget."""
    visited: set[str] = {e.id for e in seed_entities}
    expansion_texts: list[str] = []
    token_count = 0
    queue = [(e, 0) for e in seed_entities]  # (entity, depth)

    while queue and token_count < max_tokens:
        entity, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        edges = graph.list_edges(source_id=entity.id)
        for edge in edges[:max_neighbors]:
            if edge.target_id in visited:
                continue
            visited.add(edge.target_id)
            neighbor = graph.get_entity(edge.target_id)
            if neighbor:
                text = f"{entity.name} --[{edge.relation}]--> {neighbor.name}: {neighbor.description}"
                tokens = len(text.split()) * 1.3  # rough token estimate
                if token_count + tokens > max_tokens:
                    break
                expansion_texts.append(text)
                token_count += tokens
                queue.append((neighbor, depth + 1))

    return expansion_texts
```

### 3.8 Prior Art Comparison — Graph-Augmented RAG Systems

| System | Graph Backend | Expansion Strategy | Depth | Context Management | Complexity |
|--------|--------------|-------------------|-------|-------------------|------------|
| **MS GraphRAG Local Search** | In-memory (Parquet) | Entity embedding → neighbors + community reports + text units → prioritize by relevance | 1-hop + community | Token-budget priority queue | Very High |
| **neo4j-graphrag VectorCypherRetriever** | Neo4j (server) | Vector search → Cypher traversal query (user-defined) → collect neighbor properties | User-defined | Cypher query limits | Medium |
| **LightRAG** | networkx (in-memory) | Entity extraction → neighbor lookup → combine with chunk text | 1-hop | Max context parameter | Medium |
| **nano-graphrag** | networkx (in-memory) | Community detection → community summaries → entity-level expansion | 1-hop + community | Token budget | Low-Medium |
| **OwlBear (proposed)** | SQLite (on-disk) | Vector+sparse search → entity resolution → BFS expansion → budget cap | 1-hop (configurable) | `max_expansion_tokens` | **Low** |

**Key insight from prior art**: Every production system implements a token budget / priority mechanism. Unbounded expansion universally leads to context pollution. MS GraphRAG's approach (priority queue ranked by relevance to query) is the gold standard, but overkill for our scale. A simpler budget-capped BFS is sufficient for <50K entities.

### 3.9 Complexity vs. Benefit — Is Graph Expansion Worth It?

| Approach | Lines of Code | New Dependencies | Benefit | Verdict |
|----------|--------------|-----------------|---------|---------|
| Just retrieve more chunks (top_k=20 → 50) | 0 | 0 | More recall, but more noise; reranker sorts it out | Works for simple queries, fails for cross-references |
| **Graph expansion (1-hop)** | ~130 LOC | 0 | Structured context about entity relationships; directly surfaces cross-references | **Best ROI** for our corpus mix |
| Full MS GraphRAG (communities) | ~2000+ LOC | Community detection lib | Holistic corpus understanding | Overkill — we don't need global summaries |
| bge-m3 + graph expansion | ~130 LOC + ~200 migration | PyTorch (~2 GB) | Better embeddings + graph context | Deferred — violates KISS today |

**The simpler alternative (just retrieve more chunks)** fails specifically for the ~35% regulatory/legal text where cross-references and inter-document relationships are critical. Graph expansion adds ~130 LOC with zero new dependencies and directly addresses the identified failure modes from #233 research (§3.6).

## 4. Recommendation (.80 confidence)

**Implement pre-retrieval graph expansion (1-hop BFS, budget-capped) with the current embedding stack.** Defer bge-m3 to a future task.

### What to build

1. `GraphStore.get_neighbors()` — BFS traversal from seed entities
2. `GraphAugmentedRetriever` — orchestrator class composing vector search + graph expansion
3. Schema migration: add `chunk_id` column to `entities` table for chunk-entity linkage
4. Budget-capped expansion with configurable `max_depth` (default 1) and `max_expansion_tokens` (default 2000)

### What NOT to build (YAGNI)

- Community detection / Leiden clustering
- Graph-guided vector weighting
- bge-m3 integration (defer to post-Qdrant migration)
- ColBERT late-interaction scoring

### Configuration

| Parameter | Default | Range | Rationale |
|-----------|---------|-------|-----------|
| `expansion_depth` | 1 | 0-2 | 1-hop covers direct relationships; 2-hop only for debugging |
| `max_expansion_tokens` | 2000 | 500-5000 | ~2000 tokens = ~5-10 neighbor descriptions; fits in 8K-32K context |
| `max_neighbors_per_entity` | 10 | 5-50 | Prevents hub entities from dominating |
| `expansion_enabled` | `True` | bool | Kill switch for A/B testing |

### Risk and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hub entity explosion (one entity with 100+ edges) | Medium | High noise | `max_neighbors_per_entity` cap; sort edges by weight desc |
| Chunk-entity linkage gap (entities not linked to source chunks) | High today | No expansion possible | Schema migration adding `chunk_id` to entities |
| Graph expansion adds irrelevant context | Low-Medium | Slightly worse answers | Budget cap + optional reranking of expanded set |
| Performance regression at scale | Low (<50K entities) | Slow queries | SQLite indexes on edges(source_id), edges(target_id); ~1-5ms for 1-hop |

## 5. Follow-up Tasks

1. **Add `get_neighbors()` to GraphStore** — BFS traversal returning neighbor entities + connecting edges. Parameters: `entity_id`, `depth` (default 1), `max_nodes` (default 20), `scopes`. TDD. Priority: needed. Tags: phase-9, knowledge-graph, memory. AC: `get_neighbors("X", depth=1)` returns entities connected to X with their edges; respects scope filtering.

2. **Schema migration v4: add `chunk_id` to entities table** — `ALTER TABLE entities ADD COLUMN chunk_id TEXT REFERENCES chunks(id)`. Update `_store_extractions()` in `IngestPipeline` to populate `chunk_id`. TDD. Priority: needed. Tags: phase-9, knowledge-graph. AC: Entity records link back to their source chunk; migration is idempotent.

3. **Implement `GraphAugmentedRetriever`** — New class in `owlbear.memory.knowledge.retrieval` that chains: vector search → entity resolution → graph expansion → budget-capped context assembly. Parameters: `expansion_depth`, `max_expansion_tokens`, `max_neighbors_per_entity`, `expansion_enabled`. TDD. Priority: needed. Tags: phase-9, knowledge-graph, memory. Depends on: tasks 1, 2.

4. **Integration with existing `search_similar()` flow** — Add `graph_expand: bool` parameter to `VectorStore.search_similar()` or create a higher-level `KnowledgeRetriever` that composes VectorStore + GraphStore. Priority: important. Tags: phase-9, knowledge-graph. Depends on: task 3.

5. **Benchmark: graph-augmented vs plain retrieval** — Create test corpus with cross-referencing documents (e.g., ISO norm A references B; API doc references class doc). Measure Recall@10 and answer quality for cross-reference queries with and without graph expansion. Priority: important. Tags: phase-9, test, knowledge-graph. Depends on: task 4.

6. **Evaluate bge-m3 via FlagEmbedding (deferred)** — When/if Qdrant migration (#236) happens, evaluate bge-m3 as single-model replacement for bge-small + SPLADE++. Benchmark memory/latency on Ryzen 8840U. Priority: nice-to-have. Tags: phase-10, embedding, research. AC: Decision doc comparing bge-m3 vs dual-FastEmbed on quality, latency, and resource usage.

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| Microsoft GraphRAG | microsoft.github.io/graphrag/query/local_search | Local Search entity expansion pattern, prioritized context filling | `docs/research/graph-augmented-retrieval.md` (prior art, architecture) | 2026-02-28 |
| neo4j-graphrag-python | github.com/neo4j/neo4j-graphrag-python | VectorCypherRetriever pattern (vector search → graph traversal) | `docs/research/graph-augmented-retrieval.md` (prior art) | 2026-02-28 |
| Neo4j blog — Graph Traversal GraphRAG | neo4j.com/developer-blog/graph-traversal-graphrag-python-package | Vector search + Cypher traversal integration pattern | `docs/research/graph-augmented-retrieval.md` (prior art) | 2026-02-28 |
| BGE-M3 paper (Chen et al. 2024) | arxiv.org/abs/2402.03216 | Multi-functionality embedding analysis (dense+sparse+ColBERT) | `docs/research/graph-augmented-retrieval.md` (bge-m3 analysis) | 2026-02-28 |
| BAAI/bge-m3 HuggingFace | huggingface.co/BAAI/bge-m3 | Model specs, FlagEmbedding usage, MIT license verification | `docs/research/graph-augmented-retrieval.md` (bge-m3 analysis) | 2026-02-28 |
| FastEmbed (Qdrant) | qdrant.github.io/fastembed/examples/Supported_Models | Confirmed bge-m3 not in supported models list | `docs/research/graph-augmented-retrieval.md` (feasibility) | 2026-02-28 |
| LightRAG (HKUDS) | github.com/HKUDS/LightRAG | Graph-augmented retrieval pattern with neighbor expansion | `docs/research/graph-augmented-retrieval.md` (prior art) | 2026-02-28 |
| nano-graphrag | github.com/gusye1234/nano-graphrag | Minimal GraphRAG implementation (~1100 LOC) | `docs/research/graph-augmented-retrieval.md` (prior art) | 2026-02-28 |
