# Graph-Augmented Retrieval — Implementation Design

> **Owning task:** #258 — Research: Graph-augmented retrieval implementation
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Research #234 (docs/research/graph-augmented-retrieval.md) established that pre-retrieval graph expansion (1-hop BFS, budget-capped) is the right approach for OwlBear. This follow-up addresses four open implementation questions:

1. **GraphAugmentedRetriever API** — What's the class interface? How does it compose QdrantVectorStore + GraphStore?
2. **Re-ranking after expansion** — How to score graph-expanded results vs vector results?
3. **Entity embeddings in Qdrant** — Should entities be searched directly? (Answer: they already are stored.)
4. **Quality assessment** — Concrete scenarios where expansion helps vs hurts.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| OwlBear graph-augmented-retrieval.md | docs/research/graph-augmented-retrieval.md | .95 | Prior art analysis, architecture selection, budget strategy |
| MS GraphRAG Local Search | microsoft.github.io/graphrag/query/local_search | .90 | Priority-queue context filling: entities → neighbors → text units → community reports |
| neo4j-graphrag VectorCypherRetriever | neo4j.com/developer-blog/graph-traversal-graphrag-python-package | .85 | Vector search → Cypher traversal; simple composition pattern |
| LightRAG (HKUDS, EMNLP 2025) | github.com/HKUDS/LightRAG | .85 | Token budgets: `max_entity_tokens`, `max_relation_tokens`, `max_total_tokens`; "mix" mode combines KG + vector; reranker recommended for mix queries |
| OwlBear codebase — IngestPipeline._store_entity_embeddings() | src/owlbear/memory/knowledge/ingest.py L715-729 | .95 | Entity descriptions already embedded and stored in Qdrant with `embedding_type='entity'` |
| OwlBear codebase — QdrantVectorStore.search_similar() | src/owlbear/memory/knowledge/qdrant.py L210-290 | .95 | Supports `embedding_type` filter; can search entities separately from documents |
| OwlBear codebase — GraphStore | src/owlbear/memory/knowledge/graph.py | .95 | `list_edges(source_id=X)` + `get_entity(id)` for graph traversal |

## 3. Analysis

### 3.1 Key Discovery: Entity Embeddings Already in Qdrant

`IngestPipeline._store_entity_embeddings()` already embeds entity descriptions via `BgeM3EmbeddingProvider.embed_hybrid()` and stores them in Qdrant with `embedding_type='entity'`. But `KnowledgeToolset._query_knowledge()` only searches `embedding_type="document"`.

**Implication:** We can search entity embeddings directly — no chunk-entity linkage migration (`chunk_id` on entities table) needed for the initial implementation. The dual-path approach:

```
Query → embed
  ├─ search(embedding_type="document", top_k) → document content (existing)
  └─ search(embedding_type="entity", top_k) → seed entity IDs (new)
                                                  └─ get_neighbors(1-hop) → expanded context
```

This is simpler than #234's proposal which required a schema migration to add `chunk_id`. We can defer that migration to a later optimization phase.

### 3.2 GraphAugmentedRetriever — Proposed API

```python
@dataclass(frozen=True)
class RetrievalResult:
    """Single result item from graph-augmented retrieval."""

    entity_or_doc_id: str
    score: float
    content: str
    source: Literal["vector", "graph"]  # provenance


class GraphAugmentedRetriever:
    """Chains vector search → entity resolution → graph expansion → assembly.

    Composes VectorStoreProtocol + GraphStore + optional RerankerProvider.
    """

    def __init__(
        self,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStore,
        embedding_provider: EmbeddingProvider,
        reranker: RerankerProvider | None = None,
        expansion_depth: int = 1,
        max_expansion_tokens: int = 2000,
        max_neighbors_per_entity: int = 10,
        expansion_enabled: bool = True,
    ) -> None: ...

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        scopes: list[str] | None = None,
    ) -> list[RetrievalResult]:
        """Full retrieval pipeline:
        1. Embed query
        2. Search documents (vector) → top_k doc results
        3. Search entities (vector) → top_k entity results
        4. BFS expand from seed entities (if enabled)
        5. Assemble context with token budget
        6. Optional reranking
        """
```

**Design rationale:**

- Separate class (not bolted onto VectorStore or KnowledgeToolset) — KISS, single responsibility
- Takes both stores as dependencies — composition over inheritance
- Returns `list[RetrievalResult]` with provenance — callers know what came from where
- `KnowledgeToolset._query_knowledge()` delegates to this class instead of calling `search_similar()` directly

### 3.3 Re-ranking Strategy — Comparison

| Strategy | How | Complexity | Fit |
|----------|-----|-----------|-----|
| **A. No reranking** — append graph context as-is | Graph results appended after vector results, ordered by edge weight | Trivial | Baseline — no quality guarantee for graph additions |
| **B. Reranker on combined set** (.80) | Merge vector + graph results → pass all through BGE reranker vs query | Low (+1 rerank call) | **Best fit** — reranker already exists; naturally demotes irrelevant neighbors |
| **C. Score blending** | `final_score = α * vector_score + β * edge_weight` | Medium | Requires tuning α/β; scores on different scales |
| **D. MS GraphRAG priority queue** | Rank by: relevance_to_query × entity_degree × freshness | High | Overkill; requires precomputed graph metrics |

**Recommendation (.80 confidence): Strategy B** — Use the existing `BGERerankerProvider` on the combined result set. Flow:

1. Vector search → document results (with scores)
2. Entity search → seed entities → BFS neighbors → format as text passages
3. Combine all passages into a single list
4. `reranker.rerank(query, passages)` → re-sorted by relevance
5. Take top_k from re-sorted list

When no reranker is configured, fall back to **Strategy A** (append graph results, sorted by edge weight descending).

### 3.4 get_neighbors() — BFS Traversal Design

```python
@dataclass(frozen=True)
class NeighborResult:
    """One neighbor entity and the edge connecting it to the seed."""

    entity: Entity
    edge: Edge
    depth: int


def get_neighbors(
    self,
    entity_id: str,
    depth: int = 1,
    max_nodes: int = 20,
    scopes: list[str] | None = None,
) -> list[NeighborResult]:
    """BFS traversal from entity_id, returning neighbor entities + edges.

    Traverses both outgoing and incoming edges (undirected expansion).
    Sorts edges by weight descending to prioritize strongest relationships.
    """
```

Key decisions:

- **Bidirectional:** traverse both `source_id=X` and `target_id=X` edges — entities may be targets of important edges
- **Weight-sorted:** higher-weight edges first → strongest relationships discovered first
- **Scope-filtered:** respects project scoping via `scopes` parameter
- **~30 LOC** — simple BFS using existing `list_edges()` + `get_entity()`

### 3.5 Quality Assessment — When Expansion Helps vs Hurts

**Helps (high-value scenarios):**

| Query type | Example | Why it helps | Expected improvement |
|-----------|---------|--------------|---------------------|
| Cross-document references | "What ISO standards does our security policy reference?" | `RELATED_TO` edges connect policy entity → ISO standard entities across docs | High — surfaces info invisible to vector search |
| Dependency chains | "What does IngestPipeline depend on?" | `DEPENDS_ON`/`IMPORTS` edges chain to EntityExtractor, TextChunker, etc. | High — structured dependency context |
| Implementation mapping | "Which module implements the approval flow?" | `IMPLEMENTS` edges connect abstract concept → concrete class | Medium — shortcuts semantic gap |

**Hurts (noise scenarios):**

| Query type | Example | Why it hurts | Mitigation |
|-----------|---------|--------------|------------|
| Self-contained lookup | "What is the max_tokens default?" | Answer is in one chunk; neighbors add noise | Token budget cap (2000 tokens) limits damage |
| Hub entity queries | "Tell me about Python" | Entity has 100+ edges; expansion explodes | `max_neighbors_per_entity=10` + weight sort |
| Sparse graph | Fresh corpus with few entities extracted | BFS finds nothing; wasted latency | `expansion_enabled` kill switch; ~1ms cost negligible |

**Net assessment (.75 confidence):** For OwlBear's mixed corpus (35% regulatory/legal, 50% technical docs), graph expansion adds value on ~40-50% of queries — specifically those requiring cross-document reasoning. The budget cap + kill switch + reranker ensure it doesn't hurt the other 50-60%.

### 3.6 Integration Path — KnowledgeToolset Changes

Current `_query_knowledge()` flow:

```
embed(query) → search_similar(embedding_type="document") → format results
```

Proposed flow with GraphAugmentedRetriever:

```
retriever.retrieve(query) → format results
```

`KnowledgeToolset.__init__()` gains an optional `retriever: GraphAugmentedRetriever | None` parameter. When provided, `_query_knowledge()` delegates to it. When `None`, falls back to current direct vector search. This preserves backward compatibility.

### 3.7 chunk_id Migration — Deferred

The #234 research recommended adding `chunk_id` to the entities table. With the dual-path approach (entity search + document search), this is no longer needed for the initial implementation. Entity embeddings in Qdrant provide direct entity-level search without chunk resolution.

**Defer to a future task** — only needed if we want finer-grained "which specific chunk mentioned this entity?" traceability. Mark as nice-to-have.

## 4. Recommendation (.80 confidence)

**Build `GraphAugmentedRetriever` with dual-path search (document + entity), 1-hop BFS expansion, budget-capped context, and reranker-based scoring.** Five implementation tasks, zero new dependencies, ~200 LOC total.

### Configuration defaults

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `expansion_depth` | 1 | 1-hop covers direct relationships; 2-hop only for debugging |
| `max_expansion_tokens` | 2000 | ~5-10 neighbor descriptions; fits 8K-32K context |
| `max_neighbors_per_entity` | 10 | Prevents hub explosion; weight-sorted |
| `expansion_enabled` | True | Kill switch for A/B testing |

## 5. Follow-up Tasks

1. **Add `get_neighbors()` to GraphStore** — BFS traversal returning NeighborResult (entity + edge + depth). Bidirectional, weight-sorted, scope-filtered. ~30 LOC. TDD.
2. **Implement `GraphAugmentedRetriever`** — New module `owlbear.memory.knowledge.retrieval`. Dual-path search + BFS expansion + budget cap + optional reranking. ~120 LOC. TDD. Depends on task 1.
3. **Wire `GraphAugmentedRetriever` into `KnowledgeToolset`** — Add optional `retriever` parameter, delegate `_query_knowledge()`. ~20 LOC. TDD. Depends on task 2.
4. **Wire retriever into bootstrap** — Build `GraphAugmentedRetriever` in `_build_knowledge_toolset()`. ~15 LOC. Depends on task 3.
5. **Benchmark: graph-augmented vs plain retrieval** — Test corpus with cross-referencing docs. Measure Recall@10 with/without expansion. Depends on task 4.
6. **(Deferred) Schema v5: add `chunk_id` to entities** — Nice-to-have for chunk-level traceability. Not needed for initial implementation.
