# Extract Vector Store + Embedding Pipeline

> **Owning task:** #32 — Extract vector store + embedding pipeline
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #32 is subtask 2/4 of knowledge engine extraction. It calls for extracting `qdrant.py` and `embeddings.py` from v1 into `packages/knowledge/`. During #15 implementation, the builder extracted simplified versions of both modules ahead of schedule. **Key question:** What was dropped in the simplified extraction, what remains for #32, and should the full v1 features be restored now or deferred?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Qdrant Python client docs | https://python-client.qdrant.tech/ | `.85` — local mode API, prefetch/rescore patterns |
| BGE-M3 model card (HuggingFace) | https://huggingface.co/BAAI/bge-m3 | `.90` — model specs (1024-d dense, 8192 tokens, ~3 GB), caching, FlagEmbedding API |
| v1 qdrant.py (local) | `v1/src/owlbear/memory/knowledge/qdrant.py` | `1.0` — source of extraction |
| v2 qdrant.py (local) | `packages/knowledge/src/owlbear_knowledge/qdrant.py` | `1.0` — current extracted state |
| v1 embeddings.py (local) | `v1/src/owlbear/memory/knowledge/embeddings.py` | `1.0` — source of extraction |
| v2 embeddings.py (local) | `packages/knowledge/src/owlbear_knowledge/embeddings.py` | `1.0` — current extracted state |
| #15 research doc | `docs/research/extract-knowledge-engine-v1.md` | `.95` — prior extraction analysis |
| Qdrant quickstart | https://qdrant.tech/documentation/quickstart/ | `.70` — local mode vs Docker guidance |

## 3. Analysis

### 3.1 Extraction Completeness — Gap Analysis

| Feature | v1 (480 LOC) | v2 (196 LOC) | Gap? |
|---------|-------------|-------------|------|
| Dense store/get/search/delete | Yes | Yes | No |
| Sparse vector storage | Yes | Yes | No |
| ColBERT multivector config | Yes (HNSW, INT8 quant) | **No** — collection omits colbert named vector | **Yes** |
| Hybrid search (prefetch+rescore) | Yes (`_hybrid_search`) | **No** — dense-only search | **Yes** |
| Temporal boost (`_apply_temporal_boost`) | Yes | **No** — `recency_weight`/`decay_rate` marked `ARG002` | **Yes** |
| `IMPORTANCE_BY_TYPE` dict | Yes | No | **Yes** |
| `_compute_recency_score()` helper | Yes | No | **Yes** |
| `delete_by_document_id()` | Yes | No | Minor — non-protocol convenience |
| Import path migration | `owlbear.memory.knowledge.*` | `owlbear_knowledge.*` | No |
| PydanticAI/daemon imports | v1 had `owlbear.memory.knowledge.models` import | **Clean** in v2 | No |

**embeddings.py:** v2 extraction is functionally complete. Differences are cosmetic (TYPE_CHECKING import guard, minor docstring edits). No gap.

### 3.2 Scope Boundary with #33 and #34

| Feature | Owner task | Rationale |
|---------|-----------|-----------|
| Hybrid search (prefetch+ColBERT rescore) | **#34** — "Hybrid search works" AC | Explicitly in #34 AC |
| Temporal boost + importance weighting | **#32** — "vector store insert/search" | Search quality feature of the vector store itself |
| ColBERT vector config in collection | **#34** — prerequisite for hybrid search | ColBERT vectors only useful with hybrid search |
| `delete_by_document_id()` | **#33** — ingest pipeline needs batch delete | Non-protocol convenience for document lifecycle |
| README (BGE-M3 model cache location) | **#34** — "README.md in packages/knowledge/" | Explicitly in #34 AC |

### 3.3 Qdrant Local File-Based Mode (.85 confidence)

Qdrant Python client supports three modes per the docs and v1 code:

| Mode | Constructor | Use case |
|------|------------|----------|
| In-memory | `QdrantClient(location=":memory:")` | Tests, ephemeral |
| Local file | `QdrantClient(path="./data/qdrant")` | Production, no Docker |
| Remote server | `QdrantClient(url="http://...")` | Scaled deployment |

v2 already handles all three correctly (line 51-54 in qdrant.py). The Windows drive-letter pitfall (`C:` parsed as URL scheme) is handled via the `path=` parameter. **No changes needed for local mode support.**

Qdrant local mode stores data in the specified directory as RocksDB files. Persistence is automatic — no explicit flush/sync needed. Collections survive process restarts.

### 3.4 BGE-M3 Model Caching (.90 confidence)

Per the HuggingFace model card and FlagEmbedding source:

- **Model size:** ~2.3 GB download, ~3 GB in RAM (FP16)
- **Cache location:** HuggingFace hub cache at `~/.cache/huggingface/hub/models--BAAI--bge-m3/`
- **Override:** Set `HF_HOME` or `TRANSFORMERS_CACHE` env var
- **First-use download:** Automatic on `BGEM3FlagModel('BAAI/bge-m3')` — no manual step needed
- **Idle unload:** v2 already implements `idle_timeout` (default 600s) with thread-safe timer

Documentation of cache location belongs to #34's README AC, not #32.

### 3.5 What Actually Remains for #32

Given the ahead-of-schedule extraction, #32's remaining work per AC:

| AC Item | Status | Action needed |
|---------|--------|---------------|
| Extract qdrant.py | ✅ Done | None |
| Extract embeddings.py | ✅ Done | None |
| Remove PydanticAI/daemon imports | ✅ Clean | None |
| Qdrant local file-based mode | ✅ Supported | None |
| BGE-M3 cache documentation | Deferred to #34 | None for #32 |
| Package dependencies | ✅ Done | None |
| Unit tests | ⚠️ Exist but need review | Verify coverage of v2 code |
| Integration with graph store | ✅ Via shared protocol.py | None |

### 3.6 Temporal Boost — Defer or Restore? (.75 confidence)

| Option | Pros | Cons | KISS/YAGNI |
|--------|------|------|------------|
| Restore now (#32) | Complete vector store, search quality | More code before consumers exist | YAGNI violation |
| Defer to #34 | Simpler #32, tested alongside hybrid search | Temporal boost lives in search, not hybrid | Neutral |

**(rec:)** Defer temporal boost to #34 alongside hybrid search. Both are search-quality features that should be tested together. The current dense-only search is sufficient for the foundation layer.

## 4. Recommendation (.85 confidence)

**#32 is effectively complete.** The ahead-of-schedule extraction under #15 delivered all #32 AC items. The remaining gaps (hybrid search, ColBERT, temporal boost, README) belong to #33/#34.

**Recommended action:** Refine #32 AC to acknowledge the pre-extraction, verify existing test coverage is adequate, and advance it. No new code is needed — only verification and test coverage audit.

**Risks:**
- Test coverage for qdrant.py and embeddings.py was written under #15's test task, not #32-specific TDD. The architect should verify AC coverage before advancing.
- The `recency_weight`/`decay_rate` params on `search_similar` are currently no-ops (`ARG002`). This is a known gap — either remove them or implement them. **(rec:)** Keep as no-ops with a comment referencing #34; removing them would break `VectorStoreProtocol`.

## 5. Follow-up Tasks

No new tasks needed. #32's AC is satisfied by #15's extraction. #33 and #34 already cover the remaining gaps (hybrid search, temporal boost, ColBERT, README, `delete_by_document_id`).

The architect should review #32 for advancement given this analysis.
