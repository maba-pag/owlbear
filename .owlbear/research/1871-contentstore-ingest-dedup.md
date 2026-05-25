# ContentStore — Ingest & Dedup Implementation Research

> **Owning task:** #1871 — Knowledge: ContentStore — ingest & dedup
> **Date:** 2026-05-25  **Status:** Complete

## 1. Context and Question

Implement the ContentStore concrete class satisfying the `ContentStore` protocol. Core concerns: (1) document identity for dedup, (2) atomicity semantics across SQLite + Qdrant, (3) per-chunk vs document-level hashing, (4) Qdrant abstraction reuse.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Qdrant Points API | qdrant.tech/documentation/manage-data/points/ | .90 |
| Existing `QdrantVectorStore` | serve/knowledge/src/owlbear_knowledge/qdrant.py | .95 |
| Existing `compute_content_hash` | serve/knowledge/src/owlbear_knowledge/status_store.py | .90 |
| Prior research #253 — Content Hashing | .owlbear/research/content-hashing.md | .85 |
| IngestCoordinator protocol | serve/knowledge/src/owlbear_knowledge/protocols/ingest.py | .95 |
| Registry (table/collection ownership) | serve/knowledge/src/owlbear_knowledge/protocols/registry.py | .90 |
| LangChain Indexing API | github.com/langchain-ai/langchain (indexing/api.py) | .80 |
| LightRAG | github.com/HKUDS/LightRAG | .75 |

## 3. Analysis

### 3.1 Document Identity

| Approach | Multi-doc safe? | Stable across renames? | Complexity |
|----------|----------------|----------------------|------------|
| (source_id, scope) unique | **No** — breaks multi-doc | Yes | Low |
| (source_id, title, scope) | Yes | **No** — title changes | Low |
| (source_id, external_id\|uri\|title, scope) → deterministic UUID5 | Yes | Yes if external_id/uri stable | Medium |
| Caller-provided document_id | Yes | Yes | Pushes complexity upstream |

**Decision (.85):** Deterministic document_id via `uuid5(NAMESPACE, f"{source_id}:{external_id or uri or title}:{scope}")`. This handles multi-document sources (one source → many documents), provides stable identity across re-ingests, and aligns with LightRAG's `compute_mdhash_id` pattern. No unique constraint on (source_id, scope) — index on source_id for purge queries.

### 3.2 Atomicity Semantics

The IngestCoordinator protocol explicitly states: "Atomicity across modules is implementation-defined (saga vs transaction). Partial failure returns status=PARTIAL." Within ContentStore itself:

| Phase | Store | Atomic? | Recovery |
|-------|-------|---------|----------|
| SQLite: doc + chunks | SQLite transaction | Yes | Rollback |
| Qdrant: vector upsert | Qdrant batch upsert | Idempotent | Retry on same IDs |

**Decision (.80):** Interpret AC "one transaction" as: SQLite transaction for metadata (truly atomic), followed by Qdrant batch upsert (idempotent). If Qdrant fails after SQLite commit, the store is in a consistent state (chunks exist without vectors). Repair: next ingest of same content detects UNCHANGED but can verify/repair vector presence. This matches the existing ingest.py compensating pattern.

### 3.3 Hash Semantics (Document vs Chunk level)

| Concern | Level | Field | Purpose |
|---------|-------|-------|---------|
| Dedup/change detection | Document | `ContentDocument.content_hash` | SHA-256 of normalized full text |
| Chunk provenance | Chunk | `ContentChunk.content_hash` | SHA-256 of normalized chunk text |

**Decision (.90):** Document-level dedup (per research #253). Per-chunk `content_hash` is stored for provenance/audit but NOT used for dedup decisions. Reuse `compute_content_hash` (SHA-256 with whitespace collapse normalization).

### 3.4 Qdrant Abstraction

| Option | Pros | Cons |
|--------|------|------|
| Reuse `QdrantVectorStore(collection_name="content_chunks")` | Zero new code, tested pattern | Slightly overloaded API surface |
| New thin wrapper | Tailored API | Violates DRY, duplicates init logic |

**Decision (.90):** Reuse existing `QdrantVectorStore` instantiated with `collection_name="content_chunks"`. Already parameterized, already has store/delete/search/ensure_collection. No missing capabilities identified.

### 3.5 Implementation Structure

```
serve/knowledge/src/owlbear_knowledge/stores/
├── __init__.py
└── content.py       # SqliteContentStore class
```

**Constructor dependencies:** `sqlite3.Connection` + `QdrantVectorStore` + `EmbeddingProvider` + `TextChunker`

**Table DDL** (`ensure_tables` idempotent):
- `content_documents`: document_id PK, source_id, title, uri, scope, content_hash, chunk_count, trusted, metadata (JSON), ingested_at
- `content_chunks`: id PK, document_id FK, source_id, chunk_index, text, content_hash, scope, uri, section_path (JSON), trusted, metadata (JSON), created_at, updated_at
- Indexes: source_id on both tables; (document_id, chunk_index) on chunks

**Ingest flow:**
1. Validate (non-empty text, non-empty source_id) → ValueError
2. Compute document content_hash via `compute_content_hash(text)`
3. Derive document_id: `uuid5(NAMESPACE, f"{source_id}:{external_id or uri or title}:{scope}")`
4. Lookup existing document by document_id in SQLite
5. If exists with same content_hash → return UNCHANGED (chunk_ids from existing)
6. If exists with different hash → capture replaced_chunk_ids, delete old chunks + vectors
7. Chunk text via TextChunker → list[Chunk]
8. Generate chunk_ids (UUID4), compute per-chunk content_hash
9. Embed chunks via EmbeddingProvider (async batch)
10. SQLite transaction: INSERT/REPLACE document + INSERT chunks
11. Qdrant batch upsert: vectors with deterministic point_ids (UUID5 from chunk_id)
12. Return ContentIngestResult with state + chunk_ids + replaced_chunk_ids

## 4. Recommendation

**Proceed with implementation** using the refined identity model (deterministic UUID5 document_id) and saga-style atomicity (SQLite transaction + idempotent Qdrant upsert).

Challenge: **proceed** — confidence in original after challenger revision: **.78**

Challenger correctly identified that (source_id, scope) is NOT a valid unique key for documents. Refined to deterministic UUID5 from distinguishing attributes. Atomicity concern resolved by aligning with existing ingest.py saga pattern and reinterpreting "one transaction" as logical atomicity (SQLite truly atomic + Qdrant idempotent).

## 5. Follow-up Tasks

- Task #1871 implementation (already exists — move to backlog)
- Task #1872 (search & purge) depends on this — no action needed
