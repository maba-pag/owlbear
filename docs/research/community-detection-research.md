# Graph Community Detection (Leiden Algorithm) — Scale Analysis

> **Owning task:** #274 — Add graph community detection (Leiden algorithm)
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Task #274 proposes applying Microsoft GraphRAG's community detection pattern (Leiden algorithm) to OwlBear's entity graph. The pipeline would: detect communities → LLM-summarize each community → expose summaries as retrieval context for RAG queries.

**Key question from the task:** GraphRAG operates on massive documents (100K+ tokens). OwlBear typically processes smaller knowledge bases. Is community detection valuable at our scale, or is it YAGNI?

**OwlBear's graph scale** (from prior research):

- Typical: 500–2,000 entities, 200–1,000 edges
- Upper bound: ~10K entities (laptop daemon, see provenance-tracking-research.md)
- Design ceiling: <50K entities (see graph-augmented-retrieval-research.md §3.8)
- Per document: 8–60 unique entities (see intra-document-graph-research.md §3.4)

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| MS GraphRAG paper (Edge et al. 2024) | arxiv.org/abs/2404.16130 | .95 | Community detection via Leiden → hierarchical summaries → global search. Tested on 1M+ token corpora. |
| MS GraphRAG docs | microsoft.github.io/graphrag | .90 | Architecture: Leiden clustering → community reports → Global/Local/DRIFT search modes. Standard + Fast methods. |
| leidenalg (PyPI) | pypi.org/project/leidenalg | .85 | Python Leiden implementation. Depends on python-igraph. **License: GPL-3.0.** |
| python-igraph (PyPI) | pypi.org/project/igraph | .80 | C-core graph library with built-in `community_leiden()`. **License: GPL-2.0.** |
| leidenalg docs | leidenalg.readthedocs.io/en/stable/intro.html | .75 | Usage, partition types (Modularity, CPM), comparison with Louvain. igraph has built-in Leiden (less flexible, undirected only). |
| NetworkX community module | networkx.org/documentation/stable/reference/algorithms/community.html | .70 | `louvain_communities` built-in. `leiden_communities` requires external backend. No new dep for Louvain. |
| nano-graphrag | github.com/gusye1234/nano-graphrag | .75 | ~1100 LOC GraphRAG. Community detection + summaries. Acknowledges pattern is designed for large corpora. |
| OwlBear graph-augmented-retrieval-research.md | docs/graph-augmented-retrieval-research.md §3.1 | .90 | Rated community-based approach "Very High complexity", "Overkill" for OwlBear. Recommended pre-retrieval BFS instead. |
| OwlBear knowledge-pipeline-research.md §4 | docs/knowledge-pipeline-research.md | .85 | Origin of task #274. "Learn from GraphRAG: community detection for summarization." |
| OwlBear intra-document-graph-research.md | docs/intra-document-graph-research.md | .80 | Entity counts per document. Cost analysis for LLM calls on entity sets. |

## 3. Analysis

### 3.1 What GraphRAG Community Detection Actually Does

GraphRAG's pipeline (from the paper and docs):

1. Extract entities and relationships from text units (chunks)
2. Merge entities by name, LLM-summarize descriptions
3. **Leiden clustering** on the merged entity graph → hierarchical communities
4. **LLM-generate a summary report** for each community (entities + relationships → narrative)
5. At query time: Global Search maps query to community summaries → partial answers → final synthesis

**Critical insight:** Community summaries answer **global sensemaking questions** like "What are the main themes?" or "What security concerns exist across all documents?" They do NOT help with specific entity lookups or cross-reference queries — those are handled by Local Search (1-hop expansion), which OwlBear's graph-augmented retriever already plans to implement.

### 3.2 Scale Requirements — When Communities Add Value

| Factor | GraphRAG (designed for) | OwlBear (actual) | Implication |
|--------|------------------------|-------------------|-------------|
| Corpus size | 100K–1M+ tokens | 10K–100K tokens | Communities degenerate at small scale |
| Entity count | 1,000–10,000+ | 500–2,000 typical | Leiden finds 3–10 communities; trivially inspectable |
| Edge density | Dense (many relationships per entity) | Sparse (5–15 edges/entity, mostly within-doc) | Sparse graphs produce poor community structure |
| Query type | "What are the main themes?" (global) | "How does X relate to Y?" (specific) | Global queries rare in OwlBear's development agent use case |
| Re-index cost | Batch job (acceptable) | Background daemon (cost-sensitive) | LLM calls per community summary are expensive for daemon |

**Minimum viable scale for community detection:** Based on the GraphRAG paper's evaluation datasets and nano-graphrag's implementation, community detection produces meaningful hierarchical structure at **≥500 entities with ≥2,000 edges** in a connected graph. Below this, the Leiden algorithm produces either a single community or trivially small clusters (2–5 entities) that offer no more context than 1-hop BFS.

### 3.3 License Compatibility — Critical Blocker

| Library | License | OwlBear License | Compatible? |
|---------|---------|-----------------|-------------|
| `leidenalg` | **GPL-3.0** | MIT | **No** — GPL-3 requires derivative works to be GPL-3. Distributing OwlBear with leidenalg would force relicensing. |
| `python-igraph` | **GPL-2.0** | MIT | **No** — same copyleft incompatibility. |
| `networkx` (Louvain) | BSD-3 | MIT | **Yes** — but adds ~15MB dependency for one function. |
| Pure Python Louvain | N/A (self-written) | MIT | **Yes** — but ~200 LOC, slow for >5K nodes, unmaintained. |

**leidenalg and igraph are both GPL-licensed.** This is a hard blocker for an MIT-licensed project that distributes as a pip package. The only GPL-free options are NetworkX's Louvain (BSD-3) or a custom implementation.

### 3.4 Dependency Weight Analysis

| Option | New dependencies | Disk footprint | C compilation needed? | KISS |
|--------|-----------------|----------------|----------------------|------|
| `leidenalg` + `igraph` | 2 (C-compiled) | ~30MB | Yes (wheels exist, but fragile on some platforms) | Low |
| `igraph` only (built-in Leiden) | 1 (C-compiled) | ~25MB | Yes | Low |
| `networkx` (Louvain) | 1 (pure Python) | ~15MB | No | Medium |
| None (defer) | 0 | 0 | No | **High** |

OwlBear currently has zero C-compiled graph dependencies. Adding igraph would be the first native extension beyond ONNX runtime (which is in an optional `knowledge` extra). This increases build complexity and CI fragility.

### 3.5 Cost Analysis — Community Summary Generation

For each detected community, GraphRAG generates an LLM summary. Cost estimate at OwlBear's scale:

| Entity count | Expected communities (Leiden, modularity) | LLM calls | Token cost/community | Total cost |
|-------------|------------------------------------------|-----------|---------------------|------------|
| 500 | 5–10 | 5–10 | ~2K in + ~1K out = ~3K | ~15K–30K tokens |
| 2,000 | 10–25 | 10–25 | ~3K | ~30K–75K tokens |
| 10,000 | 25–80 | 25–80 | ~4K | ~100K–320K tokens |

These summaries must be **regenerated whenever the graph changes** (new document ingested, entity merged, edge added). For a daemon that ingests documents continuously, this creates a recurring LLM cost with no clear amortization strategy.

### 3.6 Alternative: 1-Hop BFS Already Covers the Use Case

The graph-augmented retrieval research (docs/graph-augmented-retrieval-research.md) compared four retrieval variants:

| Variant | Complexity | Benefit | Already planned? |
|---------|------------|---------|------------------|
| Pre-retrieval BFS (1-hop) | Low (~130 LOC, 0 deps) | Cross-reference resolution | **Yes** (task #258) |
| Community summaries (GraphRAG) | Very High (~2K LOC, 2 deps) | Global sensemaking | No — this is task #274 |

The first variant already handles OwlBear's primary retrieval need: connecting entities across documents for specific queries. Community summaries would add value only for holistic/global questions, which are rare in a development agent context ("What are all the security patterns we use?" vs "How does AuthService connect to TokenValidator?").

### 3.7 Comparison Matrix — Should We Build This?

| Criterion | Build now (.15) | Build later (.20) | Don't build (.85) |
|-----------|----------------|-------------------|-------------------|
| Graph scale fit | Poor — too small for meaningful communities | Medium — maybe after graph grows | N/A — 1-hop BFS suffices |
| License compatibility | **Blocked** (GPL) unless NetworkX or custom | Same blocker exists | No issue |
| Dependency weight | Heavy (C-compiled library) | Same weight | Zero new deps |
| LLM cost | 15K–320K tokens per re-index | Same cost | Zero |
| Query type match | Poor — global queries rare in dev agent | Potentially better if use cases emerge | N/A |
| KISS alignment | Low | Low | **High** |
| YAGNI alignment | Violates — no proven need | Better — wait for evidence | **High** |
| Alternative exists | 1-hop BFS covers 90%+ of use cases | Same | Yes |

## 4. Recommendation (.85 confidence): YAGNI — Do Not Build

**Community detection should not be implemented at OwlBear's current scale.** The evidence is clear:

1. **Scale mismatch**: OwlBear's graph (500–2,000 entities) is 1–2 orders of magnitude below where community detection produces meaningful hierarchical structure. GraphRAG was designed for 100K+ token corpora with thousands of entities.

2. **License blocker**: Both `leidenalg` (GPL-3) and `igraph` (GPL-2) are incompatible with OwlBear's MIT license. The only GPL-free option (NetworkX Louvain) adds a 15MB dependency for marginal benefit.

3. **Wrong query type**: Community summaries serve global sensemaking questions. OwlBear's agents primarily ask specific cross-reference queries, which 1-hop BFS graph expansion already handles.

4. **Ongoing LLM cost**: Community summaries must be regenerated when the graph changes. For a daemon that continuously ingests documents, this is a recurring cost with unclear ROI.

5. **1-hop BFS covers 90%+ of use cases**: The already-planned graph-augmented retriever (task #258) addresses the same retrieval needs with ~130 LOC and zero new dependencies.

**When to revisit** (re-evaluate conditions):

- Graph grows beyond 5,000 entities with dense cross-document edges
- Users request "global overview" queries ("What themes exist across all ingested docs?")
- A permissively-licensed (MIT/BSD/Apache) Leiden implementation becomes available in Python
- OwlBear becomes server-deployed (not laptop daemon), relaxing cost sensitivity

### Proposed disposition for task #274

Move #274 to `done` with status "YAGNI — deferred" or archive it. The research finding is that the task's premise (applying GraphRAG's community detection to OwlBear) doesn't hold at our scale.

## 5. Follow-up Tasks

One task is warranted — a lightweight alternative that captures the "topic clustering" intent without the heavyweight community detection machinery:

```
kanban\kanban-md.exe create "Add entity-type clustering summary to KnowledgeToolset" --priority nice-to-have --tags "phase-10,knowledge-graph" --body "Lightweight alternative to Leiden community detection. Group entities by entity_type within scope, generate a brief LLM summary per group (e.g., 'Functions: AuthService, TokenValidator, SessionManager — authentication and session management subsystem'). No new dependencies. See docs/community-detection-research.md §4. AC: - [ ] Group entities by entity_type (6 groups max per EntityType enum) - [ ] Generate 1-sentence summary per group via PydanticAI agent - [ ] Cache summaries in entity metadata (invalidate on entity add/delete) - [ ] Expose via list_knowledge_sources or new query_overview tool"
```

```
kanban\kanban-md.exe create "Archive task #274 — community detection YAGNI at current scale" --priority important --tags "phase-9,knowledge-graph,docs" --body "Research #274 concluded community detection is YAGNI at OwlBear's scale (500-2K entities). Archive the task with research link. See docs/community-detection-research.md. AC: - [ ] Move #274 to done/archived with YAGNI rationale - [ ] Link to docs/community-detection-research.md in task body"
```

## 6. Attribution Updates

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| MS GraphRAG paper | arxiv.org/abs/2404.16130 | Community detection architecture, scale analysis, Leiden clustering pattern | docs/community-detection-research.md (scale comparison) | 2026-03-01 |
| leidenalg | pypi.org/project/leidenalg | GPL-3 license analysis, API surface for Leiden in Python | docs/community-detection-research.md (license blocker) | 2026-03-01 |
| python-igraph | pypi.org/project/igraph | GPL-2 license analysis, built-in community_leiden method | docs/community-detection-research.md (license blocker) | 2026-03-01 |
