# Trim knowledge `__init__.py` to 15 or fewer exports

> **Owning task:** #550 — Trim knowledge `__init__.py` to 15 or fewer exports
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

`src/owlbear/memory/knowledge/__init__.py` exports **35 symbols** via `__all__`, including implementation details like `compute_content_hash`, `TextChunker`, and `IntraDocGraphBuilder`. The integration audit (INT-11) flagged this as an over-exported API surface. Target: 15 or fewer public re-exports.

Question: Which symbols belong in the public API, and which should be imported from submodules?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PEP 8 — Public and Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | 1.0 |
| Google Python Style Guide — §2.2 Imports | <https://google.github.io/styleguide/pyguide.html#22-imports> | 0.9 |
| Internal: `core/__init__.py` (6 exports) | N/A — codebase convention | 0.9 |
| Internal: `channels/__init__.py` (3 exports) | N/A — codebase convention | 0.9 |

**Key guidance from PEP 8:** "Modules should explicitly declare the names in their public API using `__all__`. Imported names should always be considered an implementation detail."

**Google Style:** "Use `from x import y` where `x` is the package prefix and `y` is the module name." Favors importing from specific modules, not package-level re-exports.

**Codebase convention:** Other packages export only facade-level types — `core/` exports 6, `channels/` exports 3. `knowledge/` at 35 is a 6x outlier.

## 3. Analysis — Current usage via `__init__.py`

Of 35 exports, only **6 are actually imported from `__init__.py`** by external code:

| Symbol | Importer | Lines |
|--------|----------|-------|
| `GraphStore` | bootstrap.py | 291 |
| `TextChunker` | bootstrap.py | 291 |
| `init_db` | bootstrap.py | 291 |
| `IngestPipeline` | bootstrap.py | 360, 445, 493 |
| `BookmarkStore` | bootstrap.py | 445 |
| `IngestResult` | test_knowledge_toolset.py | 218, 244, 284 |

The remaining **29 symbols** are never imported via `__init__.py` — all external consumers import from submodules directly (e.g., `from owlbear.memory.knowledge.embeddings import BgeM3EmbeddingProvider`).

## 4. Recommendation — 14 exports (.85 confidence)

| # | Symbol | Category | Rationale |
|---|--------|----------|-----------|
| 1 | `Document` | Model | Core data model |
| 2 | `Edge` | Model | Core graph relationship |
| 3 | `Entity` | Model | Core graph node |
| 4 | `EntityType` | Enum | Needed to create entities |
| 5 | `RelationType` | Enum | Needed to create edges |
| 6 | `DocumentStatus` | Enum | Needed to interpret IngestResult |
| 7 | `GraphStore` | Service | Graph CRUD (used by bootstrap) |
| 8 | `IngestPipeline` | Service | Ingestion entry point (used by bootstrap) |
| 9 | `IngestResult` | Model | Ingestion result type (used by tests) |
| 10 | `KnowledgeQueryService` | Service | Query interface (used by bootstrap) |
| 11 | `BookmarkStore` | Service | Bookmark CRUD (used by bootstrap) |
| 12 | `EmbeddingProvider` | Protocol | Extension point for custom embeddings |
| 13 | `VectorStoreProtocol` | Protocol | Extension point for custom vector stores |
| 14 | `init_db` | Function | Schema initialization (used by bootstrap, CLI) |

**Remove 21 symbols** — all implementation details importable from their submodules:

`BgeM3EmbeddingProvider`, `Bookmark`, `BookmarkPipeline`, `BookmarkResult`, `BookmarkToolset`, `Chunk`, `Embedding`, `EntityExtractor`, `EvaluationResult`, `ExtractionResult`, `GraphAugmentedRetriever`, `GraphBuildResult`, `HybridEmbedding`, `InterDocGraphBuilder`, `IntraDocGraphBuilder`, `QdrantVectorStore`, `RetrievalResult`, `SourceEvaluator`, `SparseVector`, `TextChunker`, `compute_content_hash`

**Import path changes required** — only **1 production line** breaks:

| File | Current import | New import |
|------|---------------|------------|
| bootstrap.py L291 | `from owlbear.memory.knowledge import TextChunker` | `from owlbear.memory.knowledge.chunker import TextChunker` |

All other external consumers already import from submodules.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Trim knowledge __init__.py to 14 public exports" --priority nice-to-have --tags "audit,architecture,knowledge" --status todo --description "Remove 21 implementation-detail symbols from __all__. Keep 14 public exports per docs/research/knowledge-init-trim.md. Update bootstrap.py L291 to import TextChunker from .chunker. Run full test suite to verify no breakage."

kanban\kanban-md.exe create "Add public-API assertion test for knowledge package" --priority nice-to-have --tags "test,knowledge" --status ideation --description "Add a test that asserts len(owlbear.memory.knowledge.__all__) <= 15 to prevent API surface drift. Pattern: test_knowledge_public_api.py."
```
