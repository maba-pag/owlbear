# Extract Knowledge Engine from v1

> **Owning task:** #15 — Extract knowledge engine from v1
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #15 extracts the foundation layer of the knowledge engine from `v1/src/owlbear/memory/knowledge/` into `packages/knowledge/src/owlbear_knowledge/`. Six modules are targeted: `models.py`, `schema.py`, `graph.py`, `document_store.py`, `source_store.py`, `protocol.py`. Vector, entity-extraction, and search layers are deferred to #32/#33/#34.

**Key question:** Can all six modules be extracted as-is, or do dependency entanglements require splitting?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Microsoft GraphRAG v3 | <https://github.com/microsoft/graphrag> | `.90` — Multi-package monorepo (`packages/`), uv workspace, foundation-vs-layer separation |
| PrivateGPT (Zylon) | <https://github.com/zylon-ai/private-gpt> | `.70` — Component-based DI, abstraction-first storage |
| v1 knowledge codebase | Local (`v1/src/owlbear/memory/knowledge/`) | `1.0` — The actual code being extracted |
| Pydantic v2 docs | <https://docs.pydantic.dev/latest/concepts/models/> | `.80` — Frozen models, ConfigDict patterns used in v1 models |

## 3. Analysis

### 3.1 Module Dependency Map

| Module | External deps | Internal deps | Extractable as-is? |
|--------|--------------|---------------|---------------------|
| `models.py` (117 LOC) | pydantic | — | Yes |
| `schema.py` (377 LOC) | — (stdlib) | — | Yes |
| `graph.py` (442 LOC) | — (stdlib) | models | Yes |
| `protocol.py` (83 LOC) | pydantic | — | Yes |
| `source_store.py` (186 LOC) | — (stdlib) | models | Yes |
| `document_store.py` (353 LOC) | pydantic | protocol, chunker*, embeddings*, extractor*, graph, intake* | **No** — see §3.2 |

\* = excluded from #15 (handled by #32/#33/#34)

### 3.2 document_store.py Split

`DocumentStore.__init__` requires `VectorStoreProtocol` and `EmbeddingProvider` — both from excluded modules. The class has two distinct concerns:

| Concern | Methods | Deps on excluded modules? |
|---------|---------|---------------------------|
| **Status tracking** | `find_status_by_source`, `check_content_changed`, `set_status`, `update_content_hash`, `DocumentStatus`, `compute_content_hash` | No — pure SQLite |
| **Ingest storage** | `insert_document`, `store_chunks`, `store_embeddings`, `store_extractions`, `store_entity_embeddings`, `delete_document_data` | Yes — needs Chunk, EmbeddingProvider, ExtractionResult, IntakeResult, VectorStoreProtocol |

**Recommendation (.85 confidence):** Split into `status_store.py` (foundation, #15) and keep full `DocumentStore` for #33 (ingest pipeline). This follows KISS — the foundation layer only contains what works standalone with zero external deps beyond pydantic.

### 3.3 PydanticAI / Daemon Import Audit

Grep of all 6 target modules found **zero** PydanticAI, daemon, hook, or cancellation imports. The AC items "Remove PydanticAI imports" and "Remove daemon/hook/cancellation imports" are no-ops for these modules. They're already clean.

### 3.4 Import Path Migration

All internal references change: `owlbear.memory.knowledge.X` → `owlbear_knowledge.X`. Three modules have internal cross-references:
- `graph.py` imports from `models`
- `source_store.py` imports from `models`
- `status_store.py` (split from document_store) imports nothing internal

### 3.5 Package Dependencies

| Dependency | Version | Why |
|------------|---------|-----|
| `pydantic` | `>=2.10.0` | Frozen models in models.py, protocol.py |

Everything else is Python stdlib (sqlite3, json, hashlib, datetime, uuid, enum, contextlib, collections).

### 3.6 Architecture Fit (GraphRAG Comparison)

GraphRAG v3 separates packages by concern: `graphrag-common` (DI/config), `graphrag-storage` (persistence), `graphrag-vectors`, `graphrag-chunking`. OwlBear's #15 maps to GraphRAG's storage layer — models + SQLite persistence without vector/LLM deps. The 4-task split (#15/#32/#33/#34) mirrors GraphRAG's package boundaries.

## 4. Recommendation (.85 confidence)

Extract 5 modules as-is with import path changes. Split `document_store.py` into a foundation `status_store.py` (for #15) containing `DocumentStatus`, `compute_content_hash`, and a `StatusStore` class. Leave the full `DocumentStore` for #33.

**Risks:**
- `schema.py` has 8 migration steps (377 LOC). Consider whether v2 needs all migrations or can start fresh at v8. **Recommendation:** Keep all migrations — they're tested, idempotent, and the cost of carrying them is near zero vs. the risk of breaking existing databases.
- `document_store.py` split creates a new class name (`StatusStore`) not in v1. Downstream tasks (#33) must compose `StatusStore` + ingest methods into the full `DocumentStore`.

**Testing strategy:** All tests use `:memory:` SQLite. Zero external deps.
- `GraphStore`: entity/edge/document CRUD, merge, BFS traversal
- `StatusStore`: status tracking, content hash delta detection
- `KnowledgeSourceStore`: full CRUD + scope filtering
- `init_db`: idempotency, migration chain

## 5. Follow-up Tasks

AC refinement for #15 — the task body's AC already covers all extraction items. The only modification needed is clarifying the document_store.py split. No new tasks are needed beyond what #15/#32/#33/#34 already cover.

The existing AC item "Extract document_store.py (document CRUD)" should be interpreted as: extract the status-tracking foundation (`StatusStore` + `DocumentStatus` + `compute_content_hash`) into `status_store.py`. The full `DocumentStore` class reassembly belongs to #33.
