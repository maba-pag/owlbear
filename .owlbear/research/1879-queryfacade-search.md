# QueryFacade — search implementation

> **Owning task:** #1879 — Knowledge: QueryFacade — search
> **Date:** 2026-05-26 **Status:** Complete

## 1. Context and Question

How should `QueryFacade.search(QueryRequest) -> QueryResult` compose the existing ContentStore and GraphStore protocols to deliver unified vector+graph search with provenance?

Key constraints: CP16 (graph_hops = TraversalQuery.max_hops), D53 (scope filters Content only, graph global), R44 (exact_text from chunk.text).

## 2. Sources Studied

| Source | URL/Path | Relevance |
|--------|----------|-----------|
| QueryFacade protocol | `serve/knowledge/src/owlbear_knowledge/protocols/query.py` | 1.0 — authoritative contract |
| ContentStore impl | `serve/knowledge/src/owlbear_knowledge/stores/content.py` | 0.9 — search interface |
| GraphStore impl | `serve/knowledge/src/owlbear_knowledge/stores/graph.py` | 0.9 — claims_for_chunk + traverse |
| Legacy GraphAugmentedRetriever | `serve/knowledge/src/owlbear_knowledge/retrieval.py` | 0.7 — prior art in-codebase |
| NN-ALT/graph-rag | `github.com/NN-ALT/graph-rag` (retrieval/hybrid.py) | 0.6 — same pattern externally |
| Microsoft GraphRAG architecture | graphrag.com, microsoft/graphrag | 0.5 — industry-standard graph RAG |

## 3. Analysis

### 3.1 Search Flow

```
QueryRequest
  │
  ├─ Content.search(text, scopes, source_ids) → ContentSearchResult[]
  │     │
  │     ├─ For each result chunk: Graph.claims_for_chunk(chunk.id) → entity_ids
  │     │
  │     └─ Deduplicate entity_ids; filter by entity_types
  │
  ├─ (if include_graph=True)
  │     │
  │     └─ For each seed entity_id:
  │           Graph.traverse(entity_id, max_hops=graph_hops, relation_types)
  │           → merge TraversalResult[]
  │
  └─ Assemble:
        - search_results from ContentStore results
        - graph_context from merged traversal
        - provenance from chunk + document metadata
```

### 3.2 Seed Selection Strategy

| Option | Description | Pro | Con | Confidence |
|--------|-------------|-----|-----|------------|
| A: All unique entities | claims_for_chunk for all search chunks, traverse all | Complete coverage | More graph calls | 0.85 |
| B: Top-N entities by score | Traverse only entities from top-scoring chunks | Bounded cost | May miss relevant graph paths | 0.55 |
| C: Single best entity | Traverse from highest-score chunk's entity | Cheapest | Incomplete expansion | 0.30 |

**Recommendation: A.** For laptop-resident personal KB, search returns max 10 chunks × ~2 entities = ~20 seeds. Graph.traverse is a SQLite BFS — negligible cost per call. Complexity budgeting is premature optimisation.

### 3.3 Provenance Assembly

All data available from existing protocol surface without new queries:
- `chunk_id`, `document_id`, `source_id`, `section_path` → from `ContentSearchResult.chunk`
- `exact_text` → from `chunk.text` (R44 — not a separate column)
- `title`, `uri` → from `Content.get_document(document_id)` (batch by deduplicating doc IDs)
- `score` → from `ContentSearchResult.score`

### 3.4 Merging Multiple Traversal Results

When multiple seed entities produce overlapping graphs, merge by:
1. Collect all entities and edges from all traversal results
2. Deduplicate by ID (entity.id, edge.id)
3. Wrap in single `TraversalResult(entities=..., edges=...)`

### 3.5 entity_types Filtering

Protocol note: "entity_types and relation_types on QueryRequest filter the graph expansion, not the content search."

- `entity_types`: filter seed entities — only traverse from entities matching the requested types. Requires `Graph.get_entity(id)` to check type before traversal.
- `relation_types`: passed directly to `TraversalQuery.relation_types`.

### 3.6 Async Design

- `QueryFacade.search` is `async def` (protocol declaration)
- `ContentStore.search` is `async def` — awaited
- `GraphStore.claims_for_chunk`, `traverse`, `get_entity` are sync — called normally from async context (no threading needed; SQLite is in-process)

## 4. Recommendation

**Implement option A** (traverse all unique seed entities) with batch-optimised provenance resolution. Confidence: **0.85**.

The implementation is a straightforward composition: `await Content.search()` → `claims_for_chunk` per result → filter seeds → `traverse` per seed → merge → assemble provenance → return `QueryResult`.

No external dependencies. No new tables. Constructor injection of `ContentStore` + `GraphStore` (already specified in task body). Single module `query_facade.py`.

Challenge: FALLBACK — trivial composition task, no design divergence.

## 5. Follow-up Tasks

None needed — task is self-contained. AC is clear and implementation proceeds to backlog.
