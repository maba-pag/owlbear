# Qdrant Filesystem Persistence + Source Identity Tests

> **Owning task:** #1319 — P0-03: Tests — Qdrant filesystem persistence + source identity
> **Date:** 2026-05-04 **Status:** Complete

## 1. Context and Question

Task #1319 (TDD RED) must produce tests for two Foundation (Layer 0) concerns: (a) Qdrant and SQLite persist data to disk across restarts, and (b) source identity resolution links ingested documents to registered source records with `fetch_method` and `enrich` fields. The implementation task #1320 depends on these tests.

**Core question:** Which ACs test existing behavior (GREEN immediately) vs. require new code (RED until #1320)?

## 2. Sources Studied

| Source | Location | Relevance | What |
|--------|----------|-----------|------|
| QdrantVectorStore | `serve/knowledge/src/owlbear_knowledge/qdrant.py` | 1.0 | `path=` constructor already supports filesystem |
| KnowledgeSource model | `serve/knowledge/src/owlbear_knowledge/models.py` | 1.0 | Has id/name/source_type — **no enrich, no fetch_method** |
| KnowledgeSourceStore | `serve/knowledge/src/owlbear_knowledge/source_store.py` | 1.0 | CRUD by id — **no lookup by URL/path** |
| Schema v9 | `serve/knowledge/src/owlbear_knowledge/schema.py` | 1.0 | knowledge_sources table — no enrich/fetch_method columns |
| IngestPipeline | `serve/knowledge/src/owlbear_knowledge/ingest.py` | 1.0 | `ingest_text()` doesn't pass source_id |
| Qdrant tests | `serve/knowledge/tests/test_qdrant_vector_store.py` | .95 | In-memory only — no filesystem persistence coverage |
| Qdrant local docs | qdrant.tech/documentation | .90 | `QdrantClient(path=...)` persists to disk (no server) |
| Brief §4.3 | `.owlbear/briefs/draft-knowledge-activation/brief.md` | 1.0 | Source identity design, enrich flag, fetch_method |

## 3. Analysis

### 3.1 AC Classification — GREEN vs RED

| AC | Description | Status | Rationale |
|----|-------------|--------|-----------|
| AC1 | Qdrant persists to filesystem (restart) | **GREEN** | `QdrantVectorStore(location=path)` works; untested but functional |
| AC2 | SQLite persists to disk | **GREEN** | `init_db(sqlite3.connect(path))` works; untested at this layer |
| AC3 | ingest_document registers/resolves source | **RED** | `ingest_text()` has no source_id param or source registration |
| AC4 | Source record stores fetch_method + enrich | **RED** | Fields absent from model, schema, and store |
| AC5 | Source identity resolution by URL/path | **RED** | No `resolve_by_url()` or `resolve_by_path()` method exists |
| AC6 | Enrich flag controls eligibility | **RED** | Field doesn't exist; no downstream gating logic |

### 3.2 Test Architecture

**Test file:** `tests/test_qdrant_source_identity_1319.py`

**Persistence tests (AC1 + AC2) — GREEN immediately:**

- **Qdrant restart:** Create `QdrantVectorStore(location=str(tmp_path/"qdrant"))`, store embedding, delete instance, re-create with same path, verify `get_embedding` returns stored vector. Uses `pytest.fixture` with `tmp_path`.
- **SQLite restart:** `init_db(sqlite3.connect(str(tmp_path/"test.db")))`, insert via `KnowledgeSourceStore.create()`, close connection, reopen, verify `get()` returns the record.

**Source identity tests (AC3–AC6) — RED until #1320:**

- **AC3 (source registration):** Call `ingest_document` → verify a `KnowledgeSource` record is created/resolved and `documents.source_id` FK is set. Currently fails because `ingest_text()` doesn't touch sources.
- **AC4 (field storage):** Create `KnowledgeSource` with `fetch_method="http"`, `enrich=True` → persist → retrieve → assert fields round-trip. Currently fails because fields don't exist on model.
- **AC5 (resolution):** Insert source with `config.url="https://example.com"` → call `resolve_by_url("https://example.com")` → verify returns same source. Currently fails because no resolution method exists.
- **AC6 (enrich flag gating):** Create source with `enrich=False` → ingest document → verify chunks are marked as not eligible for enrichment batch. Scoped to the **flag value on the source record**, not enrichment worker machinery (Phase 1).

### 3.3 Dual Identity Mechanism Risk

Two identity systems coexist:

| Mechanism | Table | Key | Purpose |
|-----------|-------|-----|---------|
| Content dedup | `document_status` | `source` string (URL/path) | Delta detection (skip unchanged content) |
| Source identity | `knowledge_sources` | `id` UUID | Source lifecycle, enrichment control |

Tests must assert the **knowledge_sources** path (UUID-based FK linkage), not the document_status string-based path. A shallow test that only checks "document was created" could false-GREEN through the wrong mechanism.

### 3.4 Dependency and Scope

- AC1/AC2 tests: no dependency — can pass immediately
- AC3–AC6 tests: depend on #1320 implementation (model fields, schema migration, resolution logic)
- AC6 scope boundary: test the `enrich` flag **value** on the source record + a simple eligibility check. The enrichment worker queue/state machinery is Phase 1 (task #1323)

Challenge note: `Challenge: reconsider — confidence in original: 0.39`. Revised approach separates GREEN/RED ACs and addresses identity mechanism confusion.

## 4. Recommendation

**Confidence: 0.85** — Write tests in a single file with two clear test classes:

1. `TestFromAC_Persistence` — AC1/AC2, expected GREEN
2. `TestFromAC_SourceIdentity` — AC3–AC6, expected RED

The GREEN persistence tests validate library capabilities that are already implemented but untested with filesystem paths. The RED source identity tests define the contract that #1320 must implement.

**Key constraint:** AC6 tests should assert the `enrich` flag on `KnowledgeSource` and a simple "is this source eligible for enrichment?" check — NOT the enrichment_state column or worker claim table (those belong to #1323).

## 5. Follow-up Tasks

1. **#1319 itself** → advance to backlog for test-writer to implement the test file
2. **#1320** already exists as the implementation dependency (P0-04)
