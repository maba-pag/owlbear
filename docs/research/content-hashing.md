# Content Hashing and Delta Re-Ingest Strategy

> **Owning task:** #253 — Research: Content hashing and delta re-ingest strategy
> **Date:** 2026-07-13
> **Status:** Complete

## 1. Context and Question

Re-ingesting the same URL or file currently creates duplicate content. Each
`ingest()` call generates a new `uuid4().hex` document ID with no dedup check.
The pipeline has no content hashing, no source-URI lookup, and no change
detection. This research answers five questions:

1. What hash algorithm and normalization strategy to use?
2. Where to store the hash?
3. What deletion/re-ingest flow fits our architecture?
4. Full re-ingest on change vs. chunk-level diffing vs. hybrid?
5. How to handle metadata-only changes and HTTP caching headers?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| LangChain indexing API | [langchain-core/indexing/api.py](https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/indexing/api.py) | .90 | Content+metadata dual hash, RecordManager, cleanup modes (incremental/full/scoped_full), SHA-1 default |
| LlamaIndex IngestionPipeline | [llamaindex.ai/module_guides/loading/ingestion_pipeline](https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/) | .85 | `doc_id → document_hash` map in docstore, skip-if-unchanged, re-process-if-hash-changed, IngestionCache for node+transform hashing |
| LightRAG | [HKUDS/LightRAG/lightrag.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/lightrag.py) | .80 | MD5 content-addressed doc IDs (`compute_mdhash_id`), DocStatusStorage, comprehensive `adelete_by_doc_id()` (chunks → entities → relationships → rebuild affected graph), duplicate detection via `full_docs.filter_keys()` |
| OwlBear web-crawling-research | [docs/research/web-crawling.md](../docs/research/web-crawling.md) | .75 | Already recommended "SHA-256 of extracted text body — before ingestion — skip re-processing identical content" and "Check documents table by source URL metadata — cross-session" |

## 3. Analysis

### 3.1 Hash Algorithm Comparison

| Criterion | SHA-256 (.85) | SHA-1 (.60) | MD5 (.50) | blake2b (.70) |
|-----------|--------------|-------------|-----------|---------------|
| Collision resistance | Strong (256-bit) | Weak (broken) | Broken | Strong (256-bit) |
| Speed (Python hashlib) | Fast | Fast | Fastest | Fastest |
| stdlib support | `hashlib.sha256` | `hashlib.sha1` | `hashlib.md5` | `hashlib.blake2b` |
| Industry adoption | De facto standard | Legacy | Legacy | Newer, less common |
| KISS score | High | Medium | Medium | Medium |

**Recommendation (.85):** SHA-256. Standard, collision-resistant, fast enough for
document-scale hashing. LangChain defaults to SHA-1 but supports SHA-256;
LightRAG uses MD5 for IDs (not security-critical). Since we hash for change
detection (not security), SHA-256 gives us future-proofness with negligible cost.

### 3.2 What To Hash

| Approach | LangChain | LlamaIndex | LightRAG | Recommendation |
|----------|-----------|------------|----------|----------------|
| Hash raw content | No | No | Yes (MD5 of raw text) | No |
| Hash normalized content | Yes (stripped) | Yes (via node hash) | No | **Yes (.90)** |
| Separate metadata hash | Yes (content_hash + metadata_hash) | No | No | Later (YAGNI for now) |
| Hash chunks individually | No (doc-level) | Yes (node+transform pairs) | No (doc-level) | No |

**Recommendation (.90):** Hash the **normalized** (whitespace-stripped) document
content at the **document level**. Chunk boundaries shift when chunker params
change, making chunk-level hashing fragile. Normalize with
`content.strip()` before hashing — this avoids false positives from trailing
whitespace in HTTP responses.

Separate metadata hashing is YAGNI for now. If metadata changes but content
doesn't, re-ingest is unnecessary (embeddings/entities derive from content).

### 3.3 Delta Strategy Comparison

| Criterion | Full re-ingest (.85) | Chunk-level diff (.40) | Hybrid (.55) |
|-----------|---------------------|----------------------|--------------|
| Complexity | Low — delete old, ingest new | High — diff chunks, patch embeddings | Medium |
| Correctness | Always consistent | Fragile — chunk boundaries shift | Depends |
| Entity graph impact | Clean rebuild | Partial orphans likely | Partial |
| Embedding consistency | All re-embedded from scratch | Stale embeddings for unchanged chunks | Mixed |
| Cost (LLM calls) | Full entity re-extraction | Only changed chunks | Partial |
| KISS score | **High** | Low | Medium |
| Prior art support | LangChain, LightRAG | None found at doc level | LlamaIndex (node-level) |

**Recommendation (.85):** **Full re-ingest on change.** Delete old document data
entirely (SQLite + Qdrant), then re-ingest. This matches LangChain's approach
(delete stale → index new) and LightRAG's `adelete_by_doc_id()` pattern.
Chunk-level diffing is fragile because any content change shifts chunk
boundaries, invalidating index-based comparisons. The cost of re-embedding and
re-extracting one document is acceptable for a laptop daemon.

### 3.4 Architecture Fit — Deletion Flow

Our existing architecture supports the delete-then-re-ingest pattern well:

| Step | Current capability | Gap |
|------|--------------------|-----|
| Look up by source URI | None — no index on `document_status.source` | Need index + query method |
| Compare content hash | None — no `content_hash` column | Need schema v4 migration |
| Delete chunks (SQLite) | No cascade — must delete manually | Need `DELETE FROM chunks WHERE document_id = ?` |
| Delete chunks (Qdrant) | `QdrantVectorStore.delete_by_document_id()` exists | Ready |
| Delete document | `GraphStore.delete_document()` exists | Ready |
| Delete entities/edges | Entity dedup exists but no doc-scoped entity deletion | Entities are shared — skip (re-ingest adds to existing) |
| Re-ingest | `IngestPipeline.ingest()` / `ingest_text()` | Need to accept optional `document_id` override |

### 3.5 HTTP Caching Headers

| Header | Use | Implementation |
|--------|-----|----------------|
| `ETag` | Server-provided content fingerprint | Store in `document_status.metadata`; send `If-None-Match` on re-fetch |
| `Last-Modified` | Timestamp of last change | Store in `document_status.metadata`; send `If-Modified-Since` on re-fetch |

These are optimizations for URL sources — they allow skipping the download
entirely when content hasn't changed (HTTP 304). Store them in a JSON metadata
column rather than dedicated columns (YAGNI). Implementation is deferred to a
later task — content hashing alone is sufficient for correctness.

## 4. Recommendation (.85 confidence)

**Document-level SHA-256 content hashing with full re-ingest on change.**

The flow for `ingest(source)` becomes:

```
1. Read content from source
2. Compute content_hash = SHA-256(content.strip())
3. Look up existing document by source URI in document_status
4. If found and content_hash matches → skip (return existing result)
5. If found and content_hash differs → delete old (SQLite + Qdrant) → re-ingest
6. If not found → normal ingest (new document)
```

Implementation requires:

- **Schema v4 migration:** Add `content_hash TEXT` to `document_status` table
- **Source URI index:** `CREATE INDEX idx_document_status_source ON document_status(source)`
- **GraphStore additions:** `find_document_status_by_source()`, `delete_chunks_by_document_id()`
- **IngestPipeline changes:** Hash computation, lookup, conditional delete, re-ingest
- **IngestResult update:** Add `skipped: bool` field to signal no-op re-ingests

Risk: Entity/edge cleanup on document deletion is complex (entities may be
shared across documents). Mitigation: For v1, leave entities in place — they get
re-extracted on re-ingest and entity dedup handles merging. Full entity cleanup
(LightRAG-style graph pruning) is a separate, lower-priority task.

## 5. Follow-up Tasks

1. Schema v4 migration — add `content_hash` column + source index
2. Implement `find_status_by_source()` query in pipeline
3. Implement `has_changed()` content hash check
4. Implement `delete_document_data()` cascade (SQLite chunks + Qdrant points)
5. Wire delta check into `IngestPipeline.ingest()` and `ingest_text()`
6. Tests for all above (TDD)
7. _(Deferred)_ HTTP ETag/Last-Modified caching in `intake.py`
8. _(Deferred)_ Entity/edge cleanup on document deletion (graph pruning)
