# Knowledge Ingestion Pipeline — Document to Graph + Embeddings

> **Owning task:** #133 — Knowledge ingestion pipeline — document to graph+embeddings
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear needs a pipeline that takes documents (files, URLs, text), extracts entities and relations, embeds text chunks, and stores them in the existing knowledge graph + vector DB (SQLite + sqlite-vec). The existing `src/owlbear/memory/knowledge/` package provides CRUD storage (GraphStore, VectorStore, FastEmbedProvider) but has no ingestion pipeline — entities must be inserted manually. This research covers: entity extraction approach, chunking strategy, embedding model strategy (RRF vs rerank vs single), and pipeline architecture.

**Content types:** Technical documentation (~50%), detailed texts like ISO norms/policies/laws (~35%), general information like slides/articles (~15%).

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| LightRAG (HKUDS) | github.com/HKUDS/LightRAG | .90 | Full GraphRAG: LLM entity extraction, async insert, reranker support, 4 storage types, document status tracking |
| nano-graphrag | github.com/gusye1234/nano-graphrag | .85 | Minimal GraphRAG (~1100 LOC): token-based chunking, LLM entity extraction, async pipeline |
| fast-graphrag (Circlemind) | github.com/circlemind-ai/fast-graphrag | .80 | Typed async GraphRAG with PageRank exploration, configurable entity types, domain-aware extraction |
| BGE-M3 (BAAI) | huggingface.co/BAAI/bge-m3 | .85 | Multi-functionality embedding: dense (1024-dim) + sparse (lexical weights) + ColBERT from single model, 8192 token context |
| bge-reranker-v2-m3 (BAAI) | huggingface.co/BAAI/bge-reranker-v2-m3 | .80 | Cross-encoder reranker: 0.6B params, multilingual, sigmoid-normalized relevance scores |
| Azure AI Search — RRF | learn.microsoft.com/azure/search/hybrid-search-ranking | .75 | Reciprocal Rank Fusion algorithm: score = Σ 1/(k + rank_i), weighted fusion, parallel query execution |
| RAG-Fusion | github.com/Raudaschl/rag-fusion | .65 | RRF applied to multi-query retrieval: generate query variants, vector search each, fuse with RRF |
| microsoft/graphrag | github.com/microsoft/graphrag | .60 | Reference GraphRAG implementation: extract → summarize → community detection → query. Heavy, server-oriented |

## 3. Analysis

### 3.1 Entity Extraction — LLM vs Rule-based vs Hybrid

| Criterion | LLM-based (.85) | Rule-based (.50) | Hybrid (.90) |
|-----------|-----------------|-------------------|--------------|
| Accuracy on prose | High — understands context | Low — misses implicit relations | High |
| Accuracy on code | Medium — struggles with syntax | High — AST/regex patterns are precise | High |
| Latency | Slow (~1-5s per chunk) | Fast (< 10ms per chunk) | Medium |
| Cost | LLM API tokens per chunk | Zero | LLM tokens for prose only |
| KISS score | High (one approach) | High (simple patterns) | Medium (two paths) |
| Prior art | LightRAG, nano-graphrag, fast-graphrag all use LLM | spaCy NER, tree-sitter for code | Common in production RAG |

**Recommendation (.85):** **LLM-based extraction as primary path**, with optional rule-based augmentation for code files (AST-parsed function/class/import extraction). All major GraphRAG implementations (LightRAG, nano-graphrag, fast-graphrag, microsoft/graphrag) use LLM-based extraction — this is the proven approach. The extraction prompt is a structured output prompt asking the LLM to return `list[Entity]` and `list[Edge]` from a text chunk. PydanticAI's structured output makes this straightforward.

Rule-based augmentation for code can be deferred (YAGNI) — LLMs handle code descriptions well enough for the MVP. Add tree-sitter later only if LLM extraction quality on code is insufficient.

### 3.2 Chunking Strategy

| Criterion | Fixed token (~512) (.70) | Semantic (paragraph/section) (.80) | Recursive character split (.75) | Sliding window (.65) |
|-----------|--------------------------|------------------------------------|---------------------------------|---------------------|
| Respects boundaries | No — cuts mid-sentence | Yes — splits at headings/paragraphs | Partially — tries separators | No |
| Chunk size control | Exact | Variable (needs min/max clamping) | Good (within tolerance) | Exact |
| Code handling | Poor — splits mid-function | Good if respects code blocks | Medium | Poor |
| Implementation | Simple — count tokens | Medium — detect boundaries | Medium — hierarchical separators | Simple |
| KISS score | High | Medium | Medium | High |

**Recommendation (.80):** **Recursive separator-based chunking** with this separator hierarchy: `\n##` (markdown H2) → `\n###` → `\n\n` (paragraph) → `\n` → ` `. Target **512 tokens** per chunk with **~50 token overlap**. Rationale:

- 512 tokens balances context richness with embedding model capacity (bge-small max 512 tokens, bge-m3 max 8192)
- Recursive splitting respects document structure without requiring complex parsing
- LightRAG recommends top_k=60 chunks and uses 1200-token chunks, but for a laptop system with ~10K documents, 512 is more efficient
- nano-graphrag uses token-based chunking by default with configurable chunk size

For code files, split at function/class boundaries when possible (double newlines work as a heuristic).

### 3.3 Embedding Strategy — RRF vs Retrieve-and-Rerank vs Single

This is the most consequential decision. Three approaches evaluated:

| Criterion | Single embedding (.75) | Retrieve-and-rerank (.85) | RRF dual embeddings (.70) |
|-----------|----------------------|--------------------------|---------------------------|
| **How it works** | One model → one vector table → cosine search | One model → retrieve top-K → cross-encoder reranks | Two representations (dense + sparse) → search each → RRF fuses |
| **Retrieval quality** | Good for semantic similarity | Excellent — cross-encoder sees query+doc together | Very good — combines semantic + keyword matching |
| **Latency (query)** | Fastest (~5ms) | Medium (~50ms retrieve + ~200ms rerank) | Medium (~10ms × 2 searches + merge) |
| **Latency (ingest)** | Fastest (one embed per chunk) | Same as single (rerank only at query time) | 2× embed cost (or BGE-M3 single-model dual output) |
| **Storage** | 1 vector table | 1 vector table (same as single) | 2 vector tables (dense + sparse) |
| **Model size (disk)** | ~33 MB (bge-small) | ~33 MB embed + ~2.2 GB reranker | ~2.2 GB (bge-m3 for both) |
| **Complexity** | Minimal | Medium — add rerank step to query | High — two tables, RRF merge logic, sparse vector format |
| **Laptop-friendliness** | Excellent | Good (reranker fits in RAM) | Medium (bge-m3 is 2.2 GB) |
| **KISS score** | **High** | **Medium** | **Low** |
| **Works with sqlite-vec** | Yes (native) | Yes (embed is same) | Partial — sparse vectors need FTS5 or separate table |

**Key insight from BGE-M3 docs:** BGE-M3 produces dense (1024-dim) + sparse (lexical weights) + ColBERT from a single model pass. This makes RRF conceptually simpler (one model, not two), but requires:

- Storing sparse vectors (not supported by sqlite-vec's vec0 — would need FTS5 or custom sparse table)
- BGE-M3 needs PyTorch/FlagEmbedding (~2 GB deps) vs FastEmbed's ONNX (~15 MB)
- 1024-dim dense embeddings vs current 384-dim schema

**Key insight from bge-reranker-v2-m3:** The reranker is a cross-encoder (0.6B params, ~2.2 GB). It scores (query, passage) pairs directly, so it only runs at query time on top-K candidates — no ingest overhead. LightRAG defaults `enable_rerank=True` and recommends "mix mode" with reranking.

**Recommendation (.80):** **Phased approach — start with single embedding, add reranking later:**

1. **Phase 1 (MVP):** Single embedding with existing bge-small-en-v1.5 (384-dim, FastEmbed ONNX). Already implemented in `embeddings.py`. This is the KISS path.
2. **Phase 2:** Add retrieve-and-rerank. Embed with bge-small, retrieve top-K, rerank with bge-reranker-v2-m3. The reranker adds ~2.2 GB model but dramatically improves precision. Only affects query path — ingestion stays identical.
3. **Phase 3 (if needed):** Switch to BGE-M3 for embeddings + RRF. Only pursue this if Phase 2 precision is insufficient, which is unlikely given LightRAG's success with reranking.

This phased approach respects KISS/YAGNI. The `EmbeddingProvider` protocol already supports swapping models. A `RerankerProvider` protocol can be added cleanly at Phase 2.

### 3.4 Pipeline Architecture

Every GraphRAG implementation follows the same pattern:

| Stage | Input | Output | Async? |
|-------|-------|--------|--------|
| 1. **Intake** | File path / URL / raw text | Raw content string + metadata | Yes (file I/O, HTTP) |
| 2. **Chunk** | Raw content + metadata | List of chunks with source tracking | No (CPU-bound, fast) |
| 3. **Embed** | List of chunk texts | List of embedding vectors | Yes (batched, model inference) |
| 4. **Extract** | List of chunks | Entities + edges per chunk | Yes (LLM calls, parallelizable) |
| 5. **Store** | Entities, edges, chunks, embeddings | Persisted to DB | No (SQLite writes are sync) |
| 6. **Deduplicate** | Stored entities | Merged duplicates | No (string matching) |

**Architecture patterns from prior art:**

- **LightRAG:** `ainsert()` → chunk → embed + extract in parallel → store → build communities. Has document status tracking (pending/indexed/failed). Supports batch and incremental insert.
- **nano-graphrag:** `insert()` → chunk by tokens → context-dependent entity extraction via LLM → store. Simple, ~1100 LOC total.
- **fast-graphrag:** `insert()` → similar but with PageRank-aware entity merging and typed async.

**Recommendation (.85):** Async pipeline using `asyncio`, matching LightRAG's proven pattern:

```
IngestPipeline:
  async ingest(source: str | Path | URL) -> IngestResult:
    1. content = await intake(source)        # read file/URL/text
    2. chunks = chunk(content, metadata)      # split into chunks
    3. embeddings, entities_edges = await asyncio.gather(
         embed_chunks(chunks),               # batch embed
         extract_entities(chunks),            # LLM extract (parallel)
       )
    4. store(chunks, embeddings, entities_edges)  # write to DB
    5. deduplicate_entities()                 # merge near-duplicates
    return IngestResult(chunks=len(chunks), entities=..., edges=...)
```

Steps 3a and 3b (embed + extract) run in parallel — embedding is CPU/ONNX-bound while extraction is LLM I/O-bound. This is a significant optimization seen in all major implementations.

Error recovery: track document status (pending/processing/indexed/failed) in a `document_status` table. Failed documents can be retried without re-processing successful ones.

## 4. Recommendation (.80 confidence)

Build the ingestion pipeline as `src/owlbear/memory/knowledge/ingest.py` (orchestrator) plus supporting modules:

| Module | Purpose | Priority |
|--------|---------|----------|
| `ingest.py` | Pipeline orchestrator: intake → chunk → embed → extract → store | needed |
| `chunker.py` | Recursive separator-based text chunking (512 tokens, 50 overlap) | needed |
| `extractor.py` | LLM-based entity/relation extraction using PydanticAI structured output | needed |
| `intake.py` | Content readers: file (text/markdown), URL (via httpx), raw text | needed |
| `dedup.py` | Entity deduplication — string similarity merge for near-duplicate entities | important |

**Embed with bge-small-en-v1.5** (already implemented). **Extract entities via LLM** (PydanticAI structured output — return `list[Entity]` and `list[Edge]`). **Chunk with recursive separator** (512 tokens, 50 overlap). **Store in existing GraphStore + VectorStore**.

Schema changes: add `document_status` table and `chunk_id` / `source_document_id` columns to link chunks back to source documents and entities back to extraction sources.

### Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LLM entity extraction quality varies | Medium | Structured output prompt with examples; validate output schema |
| Token cost for large documents | Medium | Batch chunks, use cheaper models for extraction, cache results |
| Duplicate entities across chunks | High | Deduplication pass with fuzzy string matching after extraction |
| SQLite write contention during parallel ingest | Low | Serialize store step; WAL mode for concurrent reads |

## 5. Follow-up Tasks

1. **Chunker module** — Recursive separator-based text chunking
2. **Entity extractor** — LLM-based extraction with PydanticAI structured output
3. **Content intake** — File/URL/text readers with metadata
4. **Pipeline orchestrator** — Async pipeline coordinating chunk → embed → extract → store
5. **Schema migration** — Add document_status table, chunk tracking
6. **Entity deduplication** — Fuzzy string matching to merge near-duplicate entities
7. **Tests for ingestion pipeline** — Unit + integration tests per module

See §5 in follow-up task commands below.
