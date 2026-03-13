# Docs Audit: Phase-9 Features (Tasks 278-287)

> **Owning task:** #289 — Docs audit: backfill documentation for phase-9 features
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

13 tasks were moved to `done` without a writer agent pass. This audit identifies which documentation files are stale or missing for the phase-9 knowledge pipeline features: schema v4, content hashing, delta re-ingest, BgeM3 idle-timeout, IntraDocGraphBuilder, Qdrant vector store, and graph enrichment pipeline hook.

## 2. Findings by Documentation File

### 2.1 `docs/architecture.md` — STALE (7 issues)

| Issue | Location | Current text | Should be |
|-------|----------|-------------|-----------|
| Package listing missing modules | Section 3, knowledge block | 11 files listed | 13 modules: add `graph_builder.py`, `protocol.py`; replace `vectors.py` with `qdrant.py` |
| File count | Section 3 | "11 files, ~2500 LOC" | "14 files" (13 modules + `__init__.py`) |
| `schema.py` description | Section 3 | "SQLite + sqlite-vec DDL, migrations" | "SQLite DDL, migrations (v1→v4)" — sqlite-vec no longer used |
| `embeddings.py` description | Section 3 | "EmbeddingProvider + FastEmbedProvider" | "EmbeddingProvider protocol + BgeM3EmbeddingProvider (idle-timeout)" |
| Memory system status | Section 4.6 | "Currently uses sqlite-vec + FastEmbed; planned migration to Qdrant + bge-m3 (#247-#261)" | Migration complete: Qdrant + BGE-M3 |
| Phase 9 status | Section 7 | "🔄 Active — Qdrant+bge-m3 migration in research" | "✅ Done" |
| Key Design Decisions | Section 8 | "Knowledge pipeline uses sqlite-vec (migrating to Qdrant)" | "Knowledge pipeline uses SQLite (schema) + Qdrant (vectors) + BGE-M3 (embeddings)" |

### 2.2 `.github/copilot-instructions.md` — STALE (1 issue)

| Issue | Location | Current text | Should be |
|-------|----------|-------------|-----------|
| Tech stack table | Row: Knowledge | "Knowledge (planned) \| Knowledge graph + vector DB \| Structured memory with embeddings; DB tech TBD" | "Knowledge \| SQLite (graph) + Qdrant (vectors) + BGE-M3 \| Knowledge graph with hybrid vector search; schema v4; idle-timeout model unloading" |

### 2.3 `README.md` — STALE (1 issue)

| Issue | Location | Current text | Should be |
|-------|----------|-------------|-----------|
| Architecture bullet | Architecture section | "Knowledge: Knowledge graph + vector DB (planned)" | "Knowledge: SQLite knowledge graph + Qdrant hybrid vector search (BGE-M3)" |

No new CLI commands were added by phase-9 tasks, so no CLI doc changes needed.

### 2.4 `knowledge/__init__.py` — STALE (missing exports)

The `__all__` list exports only the original graph/model/embedding types. The following phase-9 public APIs are **not exported**:

- `IngestPipeline`, `IngestResult`, `DocumentStatus` (from `ingest.py`)
- `compute_content_hash` (from `ingest.py`)
- `IntraDocGraphBuilder`, `GraphBuildResult` (from `graph_builder.py`)
- `BgeM3EmbeddingProvider` (from `embeddings.py`)
- `init_db` (from `schema.py`)
- `TextChunker`, `Chunk` (from `chunker.py`)

**Note:** Updating `__init__.py` is a code change, not a docs change. The writer agent should flag this but a builder should implement it.

### 2.5 Docstrings — COMPLETE ✅

All new public functions and classes have comprehensive docstrings:

| Module | Public API | Docstring? |
|--------|-----------|------------|
| `schema.py` | `init_db()`, `_migrate_v3_to_v4()` | ✅ Full (Parameters, idempotency notes, migration description) |
| `ingest.py` | `IngestPipeline`, `IngestResult`, `DocumentStatus` | ✅ Full (class + all public methods) |
| `ingest.py` | `compute_content_hash()` | ✅ Full (Parameters, Returns) |
| `ingest.py` | `find_status_by_source()` | ✅ Full (Parameters, Returns) |
| `ingest.py` | `check_content_changed()` | ✅ Full (Parameters, Returns with tuple semantics) |
| `ingest.py` | `delete_document_data()` | ✅ Full (cascade order documented) |
| `graph_builder.py` | `IntraDocGraphBuilder`, `GraphBuildResult` | ✅ Full (class + Usage example + all methods) |
| `graph.py` | `list_entities_for_document()` | ✅ Full |
| `embeddings.py` | `BgeM3EmbeddingProvider` | ✅ Full (class + all methods including `unload()`) |
| `embeddings.py` | `_reset_timer()`, `_ensure_model()` | ✅ Full (thread-safety noted) |
| `models.py` | `Entity.document_id` | ✅ Field present with `str | None = None` |
| `protocol.py` | `VectorStoreProtocol` | ✅ Full |
| `qdrant.py` | `QdrantVectorStore` | ✅ Full |

### 2.6 `docs/sources.md` — COMPLETE ✅

All external patterns adopted during phase-9 are already logged:

- Content hashing: LangChain indexing API, LlamaIndex IngestionPipeline, LightRAG (section "Content Hashing Research")
- Intra-document graph: Microsoft GraphRAG, LlamaIndex PropertyGraphIndex, nano-graphrag (section "Intra-Document Graph Builder Research")
- BGE-M3 integration: FlagEmbedding, bge-m3-qdrant-sample, FastEmbed issues (section "Embedding & Vector DB Research")
- Qdrant local: qdrant-client, Qdrant docs (section "Embedding & Vector DB Research")

### 2.7 `src/owlbear/config.py` — COMPLETE ✅

`embedding_idle_timeout: int = 600` is present and documented in config. No docs mentioning this setting exist in README or copilot-instructions, but it's an internal config — no user-facing docs needed beyond the config field itself.

## 3. Summary

| File | Status | Issue count | Effort |
|------|--------|-------------|--------|
| `docs/architecture.md` | 🔴 Stale | 7 | Medium — update package listing, descriptions, status markers |
| `.github/copilot-instructions.md` | 🟡 Stale | 1 | Low — update 1 row in tech stack table |
| `README.md` | 🟡 Stale | 1 | Low — update 1 bullet |
| `knowledge/__init__.py` | 🟡 Missing exports | 6+ symbols | Low — but requires builder, not writer |
| Docstrings (all modules) | ✅ Complete | 0 | None |
| `docs/sources.md` | ✅ Complete | 0 | None |

## 4. Recommendation (.95 confidence)

Split into 2 writer tasks (architecture.md is the bulk of work) + 1 builder task (for `__init__.py` exports):

1. **Writer task A** — Update `architecture.md` (7 issues): package structure, memory system status, phase table, design decisions table.
2. **Writer task B** — Update `copilot-instructions.md` (1 row) + `README.md` (1 bullet). Quick fix.
3. **Builder task** — Update `knowledge/__init__.py` `__all__` exports to include all phase-9 public APIs. Small diff.

## 5. Follow-up Tasks

See kanban create commands in researcher output below.
