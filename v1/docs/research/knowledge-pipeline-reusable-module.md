# Knowledge Pipeline as Reusable Module

> **Owning task:** #259 — Research: Knowledge pipeline as reusable module
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

OwlBear's knowledge pipeline (`src/owlbear/memory/knowledge/`) implements a full chunk → embed → extract → graph → store → search flow across 14 files / ~2,957 LOC. The question: should this be extracted into a standalone Python package reusable beyond OwlBear?

This is fundamentally a **YAGNI evaluation** — does extraction provide concrete value NOW, or is it speculative future-proofing?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| LlamaIndex Core | <https://pypi.org/project/llama-index-core/> | .90 | Modular core + 200+ integration packages; defines industry-standard abstractions for RAG pipelines |
| Haystack (deepset) | <https://pypi.org/project/haystack-ai/> | .85 | Production-ready AI orchestration framework; pipeline DAGs with explicit component graphs |
| GraphRAG (Microsoft) | <https://pypi.org/project/graphrag/> | .80 | Knowledge graph extraction pipeline for LLMs; research-grade, expensive to run |
| LightRAG (HKU) | <https://pypi.org/project/lightrag-hku/> | .90 | Graph-RAG with entity extraction, BGE-M3 + BGE-reranker, Qdrant backend — closest architectural match to OwlBear's pipeline |

## 3. Analysis

### 3.1 Coupling Assessment

The knowledge pipeline has **zero cross-module imports** — every `from owlbear.*` import references only sibling modules within `owlbear.memory.knowledge`. External consumers are:

| Consumer | Import | Coupling |
|----------|--------|----------|
| `owlbear.tools.knowledge` (KnowledgeToolset) | protocol, graph, ingest, embeddings | Thin adapter — wraps pipeline as PydanticAI tools |
| `owlbear.bootstrap` | All pipeline components | Assembly only — constructs objects, passes to KnowledgeToolset |
| `owlbear.tools.browser.integration` | IngestPipeline, IngestResult | Bridge function — feeds crawled pages to ingest |

**Verdict:** The pipeline is already architecturally isolated. Extraction would require zero refactoring of the pipeline itself — only updating 3 import sites in OwlBear.

### 3.2 External Dependencies

| Dependency | Required? | Modules | Size impact |
|------------|-----------|---------|-------------|
| pydantic | Yes | All models | Already in any modern Python project |
| pydantic-ai | Yes | extractor, graph_builder | **Significant coupling** — LLM extraction uses PydanticAI Agent |
| anyio | Yes | intake (file I/O) | Lightweight |
| httpx | Yes | intake (URL fetch) | Common |
| qdrant-client | Optional | qdrant.py | ~5 MB, behind ImportError guard |
| FlagEmbedding | Optional | embeddings, reranker | ~3 GB model, behind ImportError guard |
| sqlite3 | Stdlib | graph, schema, ingest | Zero-cost |

The **pydantic-ai dependency is the key bottleneck**. `EntityExtractor` and `IntraDocGraphBuilder` use `pydantic_ai.Agent` directly. A truly generic package would need to abstract the LLM layer behind a protocol, which is non-trivial additional work.

### 3.3 Competitor Comparison

| Criterion | OwlBear Pipeline | LightRAG (.90) | LlamaIndex (.70) | Haystack (.75) | GraphRAG (.60) |
|-----------|-----------------|-----------------|-------------------|----------------|----------------|
| LOC (core) | ~3,000 | ~15,000 | ~50,000+ | ~30,000+ | ~20,000+ |
| Graph extraction | PydanticAI Agent | Custom LLM | Via integrations | Via components | Custom LLM |
| Vector backends | Qdrant | Qdrant, Milvus, Faiss, PG, Mongo, Nano | 40+ integrations | 10+ integrations | Custom |
| Embedding models | BGE-M3 only | Configurable | Configurable | Configurable | Configurable |
| Reranking | BGE reranker | Cohere, Jina, Aliyun | Via integrations | Via integrations | N/A |
| Hybrid search | Dense + sparse + ColBERT | Dense + sparse | Via integrations | Via components | Dense only |
| Content hashing | Yes (delta re-ingest) | Yes | Partial | No | No |
| Graph storage | SQLite | NetworkX, Neo4J, PG, Memgraph | Via integrations | Via integrations | Custom |
| Maintenance team | 1 developer | HKU research lab | Company (LlamaIndex Inc) | Company (deepset) | Microsoft |
| Community | 0 external users | 20k+ GitHub stars | 40k+ GitHub stars | 20k+ GitHub stars | 20k+ GitHub stars |

### 3.4 YAGNI Evaluation Matrix

| Factor | Extract Now | Keep In-Tree | Weight |
|--------|------------|--------------|--------|
| External users needing this | 0 | N/A | HIGH |
| Maintenance overhead (CI, releases, versioning) | High | Zero | HIGH |
| Market differentiation vs competitors | None — LightRAG is architecturally identical with more backends | N/A | HIGH |
| Code cleanliness | Already clean (zero coupling) | Already clean | LOW |
| Extraction difficulty if needed later | Trivial (3 import sites to change) | N/A | MEDIUM |
| PydanticAI abstraction cost | ~200 LOC protocol layer needed | Zero | MEDIUM |

## 4. Recommendation (.90 confidence): Keep in-tree

**Do not extract.** The YAGNI case is overwhelming:

1. **Zero external demand.** No users, no community, no market signal. Extracting for hypothetical future users is textbook YAGNI.

2. **Saturated market.** LightRAG alone covers the same pipeline (chunk → embed → extract → graph → store → search) with more backends, more embedding options, and a dedicated research team. LlamaIndex and Haystack are even larger. There is no gap to fill.

3. **Extraction is trivial later.** The pipeline already has zero cross-module coupling. If extraction becomes warranted (e.g., a second project needs it), the effort is: (a) create a `pyproject.toml`, (b) move the directory, (c) update 3 import sites. Estimated effort: 2–4 hours.

4. **PydanticAI coupling is a feature, not a bug.** Within OwlBear, PydanticAI is the agent framework. Abstracting it away for a generic package adds complexity with no current benefit.

5. **Maintenance cost is real.** A separate package means separate CI, versioning, release cadence, compatibility testing, and documentation. For a single consumer, this is pure overhead.

### Architectural Notes for Future Extractability

The pipeline is already in good shape. To keep it extractable with minimal effort:

- **Preserve the zero-coupling invariant.** Never import from `owlbear.*` outside `owlbear.memory.knowledge` within the knowledge package. This is already true today.
- **Keep protocols over concrete types.** `VectorStoreProtocol`, `EmbeddingProvider`, and `RerankerProvider` are already protocol-based — any new component should follow suit.
- **Optional dependencies stay optional.** `qdrant-client` and `FlagEmbedding` are behind `ImportError` guards. Keep this pattern for any new backend.
- **If a second consumer emerges** (another project, a user request), revisit this decision. The extraction criteria would be: (a) a concrete second consumer exists, (b) the consumer needs the pipeline without PydanticAI, (c) the maintenance cost is justified by the user base.

## 5. Follow-up Tasks

One lightweight task to codify the extractability invariant as an automated check, preventing accidental coupling drift.
