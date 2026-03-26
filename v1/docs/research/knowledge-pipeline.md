# Adopt Existing Knowledge Pipeline vs Build Custom

> **Owning task:** #262 — Research: Adopt existing knowledge pipeline vs build custom
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

Before executing 14 implementation tasks (#247–#259, #261) that evolve our custom knowledge pipeline, we must evaluate whether an existing OSS framework should replace or augment it. Our pipeline currently covers: intake → chunk → embed → extract entities → graph store → vector search → rerank. The question: is that worth maintaining, or should a mature framework own it?

**Our constraints:** Python 3.12, Qdrant local (dense+sparse+ColBERT via bge-m3), PydanticAI agents, CPU-only laptop daemon, 16 GB RAM, embedded process (not a server), scope-filtered retrieval.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| LlamaIndex | github.com/run-llama/llama_index | .75 | Full RAG framework; `llama-index-vector-stores-qdrant` integration; PropertyGraphIndex for KG |
| Cognee | github.com/topoteretes/cognee | .80 | Purpose-built KG+vector memory engine; analysed via `--depth 1` clone |
| Microsoft GraphRAG | github.com/microsoft/graphrag | .60 | Graph enrichment, community detection; batch-oriented, LLM-heavy |
| txtai | github.com/neuml/txtai | .50 | All-in-one embeddings + graph; own vector backends, single developer |
| Haystack (deepset) | github.com/deepset-ai/haystack | .70 | Pipeline orchestrator; `qdrant-haystack` integration; no KG support |
| R2R (SciPhi) | github.com/SciPhi-AI/R2R | .30 | Server-based RAG; requires Docker/Postgres; last commit 3 months ago |
| Unstructured.io | github.com/Unstructured-IO/unstructured | .25 | Document parsing only; not a pipeline framework |

## 3. Analysis

### 3.1 Elimination Round

| Candidate | Eliminated? | Reason |
|-----------|-------------|--------|
| R2R | **Yes** | Server architecture (RESTful API + Docker + Postgres). Incompatible with embedded laptop daemon. Last commit 3 months ago — development stalled. |
| Unstructured.io | **Yes** | Document processing only. Doesn't address vector search, graph, entity extraction, or pipeline orchestration. Could supplement intake but can't replace pipeline. |
| txtai | **Yes** | Bus factor ~1 (21 contributors, 1 active). No Qdrant support (own ANN backends: faiss, hnswlib). Graph is NetworkX-based similarity edges, not LLM-extracted entities. |

### 3.2 Deep Comparison — Top 4

| Criterion | LlamaIndex (.55) | Cognee (.50) | GraphRAG (.40) | Haystack (.60) |
|-----------|-------------------|--------------|----------------|----------------|
| **1. Qdrant + bge-m3** | Has `qdrant` integration. Hybrid sparse+dense via Qdrant's API. Custom embedding model feasible via HuggingFace integration. | **No Qdrant adapter.** Uses LanceDB/ChromaDB/PgVector only. Would require writing a custom VectorDBInterface adapter (~200 LOC). | v3 modular packages but designed for OpenAI embeddings. Custom embedding providers possible but undocumented path. | Has `qdrant-haystack` integration. Supports sparse embedding components. Custom HF models work. |
| **2. Knowledge graph** | PropertyGraphIndex: LLM-based entity/rel extraction, graph storage in Neo4j/Nebula. Good but couples to their index abstraction. | **Strongest KG**: Kuzu embedded graph DB, entity extraction via LLM (instructor), ontology resolution, graph traversal, memify algorithms. | **Core feature**: community detection, hierarchical summaries, global search. Best graph analysis — but batch-only, no incremental. | **None.** Pipeline orchestrator only. No built-in entity extraction or graph storage. |
| **3. Doc management** | SimpleDirectoryReader + Storage Context. Basic persistence. No content hashing or delta re-ingest. | Document chunking, status tracking, ingestion pipeline. Uses SQLAlchemy for document registry. Closest to what we need. | Basic batch indexing. Not designed for incremental updates. | DocumentStore abstraction with metadata filtering. Write/update semantics. Decent. |
| **4. Extensibility** | 300+ integration packages. Can plug in custom LLMs, embeddings, vector stores. But: framework lock-in — must conform to their abstractions (Nodes, ServiceContext, etc). | Modular task pipelines. EmbeddingEngine is a Protocol (extensible). But: tightly coupled internal infrastructure (own FastAPI server, SQLAlchemy, Alembic migrations). | CLI-driven. Not designed as embeddable library. Extension requires forking their pipeline code. | **Best**: clean Component protocol, pipeline validation, easy to write custom components. Designed for composition. |
| **5. Weight** | **Heaviest.** `llama-index-core` alone: tiktoken, nltk, node_parser, hundreds of transitive deps. Full install ~500 MB. | **Heavy.** 60+ core deps: openai, litellm, lancedb, kuzu, fastembed, fastapi, sqlalchemy, tiktoken, onnxruntime, uvicorn, gunicorn, mistralai, networkx. | Moderate. pandas, LLM API calls. But indexing is extremely expensive (many LLM calls per document). | **Lightest of top 4.** Core `haystack-ai` is lean. Integrations are separate pip packages. ~50 MB core. |
| **6. API quality** | Good Pydantic models. But: deep inheritance chains, implicit globals (Settings), complex node system. | Top-level clean (`cognee.add/cognify/search`). Internals: complex, many layers of abstraction, inconsistent naming. | CLI-first. Python API exists but secondary. Not designed as library. | Good typed API. Component protocol is clean. Pydantic serialization for pipeline configs. |
| **7. Community** | 47.3k ★, 1816 contributors, weekly releases. Very healthy. | 12.6k ★, 118 contributors, active. Growing but smaller. | 31.1k ★, 65 contributors, MS-backed. Healthy but narrow focus. | 24.3k ★, 335 contributors, 212 releases. Very healthy. Used by Apple, Meta, Netflix. |
| **8. What we'd lose** | PydanticAI integration (their agents ≠ ours). Scope system. Fine-grained Qdrant hybrid search control. Custom temporal decay. | Qdrant support. PydanticAI agents. Our scope system. Custom bge-m3 hybrid. | Incremental ingestion. Embedded operation. Cost control. | Entity extraction. Graph store. Still need to build half the pipeline. |
| **9. What we'd gain** | PropertyGraphIndex. Document readers for 100+ formats. Community-maintained integrations. | Ontology resolution. Memory algorithms (memify). Graph traversal patterns. Temporal awareness. 30+ data source connectors. | Community detection. Global search. Hierarchical summaries. | Pipeline validation. Component reusability. Battle-tested DocumentStore. |

### 3.3 Critical Blockers

1. **No framework supports Qdrant hybrid search (dense+sparse+ColBERT) with bge-m3 out of the box.** LlamaIndex and Haystack have Qdrant integrations, but they don't expose Qdrant's prefetch+fusion API for triple-mode hybrid search that tasks #249–#250 implement.

2. **No framework integrates with PydanticAI agents.** All use their own LLM abstraction layers (LlamaIndex: llms module; Cognee: litellm/instructor; Haystack: generators; GraphRAG: OpenAI). Replacing our `EntityExtractor` (which uses `pydantic_ai.Agent[None, ExtractionResult]`) would mean abandoning PydanticAI structured output.

3. **Dependency weight violates KISS.** Our current pipeline is ~1500 LOC across 10 files with 5 direct dependencies (pydantic, pydantic-ai, sqlite-vec, fastembed, httpx). Cognee has 60+ core deps. LlamaIndex has hundreds. This is a laptop daemon, not a cloud service.

4. **Scope system is custom to OwlBear.** Our per-agent, per-project scope filtering is threaded through every layer (schema, graph store, vector store, ingest pipeline). No framework has this concept.

## 4. Recommendation (.85 confidence): Learn and Build

**Decision: Learn and build.** No framework fits our stack. The gap between what they offer and what we need would cost more to bridge than continuing with our custom pipeline.

**Rationale:**

- Our pipeline is already well-structured (Protocol-based providers, Pydantic models, clean separation)
- We're 70% done — tasks #247–#251 migrate to Qdrant+bge-m3, which is our biggest missing piece
- The remaining tasks (#253–#259) add document management, graph builders, and retrieval — all achievable in ~1500 LOC
- Adopting any framework would add 50–500 MB of dependencies for marginal gain
- Every framework would require custom adapters for our Qdrant hybrid search + PydanticAI agents + scope system
- Total cost of adoption: rewrite adapters (~2 weeks) + dependency maintenance (ongoing) + lose fine-grained control

**What to learn from each framework (apply to our code):**

| Framework | Pattern to adopt | Apply where |
|-----------|-----------------|-------------|
| Cognee | Provenance tracking on DataPoints (source_pipeline, source_task) | `IngestResult` model — add pipeline provenance |
| Cognee | Ontology-constrained entity types (resolve against schema) | `EntityExtractor` — add optional ontology validation |
| GraphRAG | Community detection on entity graph (Leiden algorithm) | New task: graph community detection for summarization |
| GraphRAG | Hierarchical summaries per community | New task: community-level context for RAG |
| Haystack | Component protocol with typed inputs/outputs | Already have via `EmbeddingProvider`/`RerankerProvider` protocols — extend pattern |
| txtai | Config-driven graph building (automatic edge creation from embedding similarity) | `GraphStore` — add embedding-similarity edges alongside LLM-extracted edges |

## 5. Impact on Tasks #247–#259, #261

| Task | Status | Impact |
|------|--------|--------|
| #247 VectorStoreProtocol | ideation | **Survives.** Our Protocol approach is validated by Cognee (EmbeddingEngine), Haystack (Component), and txtai. |
| #248 BgeM3EmbeddingProvider | ideation | **Survives.** No framework provides bge-m3 triple-mode (dense+sparse+ColBERT) natively. |
| #249 QdrantVectorStore | ideation | **Survives.** Only LlamaIndex/Haystack have Qdrant integrations, but neither supports our hybrid search mode. |
| #250 Wire Qdrant+BgeM3 | ideation | **Survives.** Custom wiring is necessary regardless of framework choice. |
| #251 Remove sqlite-vec | ideation | **Survives.** Migration path is our own. |
| #252 Benchmark hybrid search | ideation | **Survives.** Framework-agnostic benchmark. |
| #253 Content hashing/delta | ideation | **Survives.** Cognee has this but we can't adopt Cognee. Learn from their approach (document status table is similar to ours). |
| #254 Source registry/scheduling | ideation | **Survives.** No framework provides this at our level of customization. |
| #255 Intra-doc graph builder | ideation | **Survives + enhanced.** Incorporate GraphRAG's entity extraction patterns. |
| #256 Inter-doc graph builder | ideation | **Survives + enhanced.** Add community detection pattern from GraphRAG. |
| #258 Graph-augmented retrieval | ideation | **Survives + enhanced.** Apply graph traversal patterns from Cognee. |
| #259 Knowledge pipeline module | ideation | **Survives.** Our modular approach is correct — this task finalizes the clean API. |
| #261 BgeM3 idle-timeout | ideation | **Survives.** Framework-agnostic model lifecycle management. |

**All 14 tasks survive. None become redundant.**

## 6. Follow-up Tasks

Two new tasks derived from this research (patterns to adopt):

```
kanban\kanban-md.exe create "Add graph community detection (Leiden algorithm)" --priority important --tags "phase-9,knowledge-graph" --body "Apply GraphRAG's community detection pattern to our entity graph. Use python-igraph or leidenalg to detect communities in the knowledge graph and generate community summaries. See docs/research/knowledge-pipeline.md §4. AC: - [ ] Implement community detection on GraphStore entities - [ ] Generate per-community summaries via PydanticAI agent - [ ] Expose communities as retrieval context for RAG queries"

kanban\kanban-md.exe create "Add provenance tracking to IngestResult" --priority nice-to-have --tags "phase-9,knowledge-graph" --body "Apply Cognee's provenance tracking pattern: stamp each entity and edge with source_pipeline and source_task metadata. See docs/research/knowledge-pipeline.md §4. AC: - [ ] Add source_pipeline and source_task fields to Entity/Edge metadata - [ ] IngestPipeline stamps provenance on all extracted entities - [ ] Provenance queryable via GraphStore.list_entities filter"
```

Confirm proceed with custom build for #247–#259, #261 — move task #262 to review.
