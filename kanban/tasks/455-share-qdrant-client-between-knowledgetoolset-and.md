---
id: 455
title: Share Qdrant client between KnowledgeToolset and BookmarkToolset
status: archived
priority: needed
created: 2026-03-03T20:33:18.1158658+01:00
updated: 2026-03-04T07:58:29.3474759+01:00
started: 2026-03-03T20:33:25.2541629+01:00
completed: 2026-03-04T07:58:29.3474759+01:00
tags:
    - phase-refactor
    - knowledge-graph
    - daemon
class: standard
---

## Problem

`_build_knowledge_toolset()` and `_build_bookmark_toolset()` each independently create QdrantVectorStore, sqlite3 connection, GraphStore, BgeM3EmbeddingProvider, EntityExtractor, and TextChunker â€” all pointing at the same `.owlbear/` directory.  Qdrant local mode locks the storage folder, so the second QdrantVectorStore fails with RuntimeError.  BgeM3EmbeddingProvider loads the ~1 GB model twice.  BookmarkToolset silently fails.

## AC

### Shared infrastructure

- [ ] New helper `_build_knowledge_infra(workspace, chat_model)` returns a dataclass (e.g. `_KnowledgeInfra`) containing: `conn` (sqlite3.Connection), `graph_store` (GraphStore), `vector_store` (QdrantVectorStore), `embedding_provider` (BgeM3EmbeddingProvider), `entity_extractor` (EntityExtractor), `text_chunker` (TextChunker).  Follow `BootstrapResult` dataclass pattern (module-private, `@dataclass`).
- [ ] `_build_knowledge_infra` calls `init_db(conn)` exactly once.
- [ ] `_build_knowledge_infra` returns `None` on import/init failure; logs one WARNING.

### Builder signatures

- [ ] `_build_knowledge_toolset(infra, ...)` receives `_KnowledgeInfra` as first arg.  Removes all infra construction from its body.  Still creates its own `IngestPipeline` (with optional `inter_doc_builder`), `GraphAugmentedRetriever`, `KnowledgeQueryService`, `KnowledgeToolset`.
- [ ] `_build_bookmark_toolset(infra, ...)` receives `_KnowledgeInfra` as first arg.  Removes all infra construction from its body.  Still creates its own `IngestPipeline` (without `inter_doc_builder`), `BookmarkStore`, `SourceEvaluator`, `BookmarkPipeline`, `BookmarkToolset`.
- [ ] Each builder keeps its own try/except for toolset-specific failures (returns `None`, logs WARNING).

### Orchestration

- [ ] `build_toolsets()` calls `_build_knowledge_infra()` once; if it returns `None`, both knowledge and bookmark toolsets are skipped.
- [ ] `build_toolsets()` passes the result to both `_build_knowledge_toolset()` and `_build_bookmark_toolset()`.

### Verification

- [ ] Test: mock `QdrantVectorStore` constructor â€” assert called exactly once per `build_toolsets()` invocation.
- [ ] Test: mock `BgeM3EmbeddingProvider` constructor â€” assert called exactly once.
- [ ] Test: when `_build_knowledge_infra` succeeds, no `'Failed to create BookmarkToolset'` WARNING in logs.
- [ ] Test: when infra fails, both toolsets absent and exactly one WARNING logged.
- [ ] Existing tests pass (`uv run pytest -q --tb=short`).
- [ ] Ruff clean (`uv run ruff check src/owlbear/bootstrap.py`).

## Architecture notes

- `_KnowledgeInfra` is module-private (underscore prefix) â€” not part of the public API.
- Each builder still creates its own `IngestPipeline` to preserve existing behavior: knowledge pipeline gets optional `inter_doc_builder`; bookmark pipeline does not.  `IngestPipeline` is lightweight (just holds references).
- `EntityExtractor` and `TextChunker` are cheap but shared to avoid duplication and keep both builders' `IngestPipeline`s consistent.
- Existing `_build_knowledge_toolset` params (`project_id`, `max_tokens`, `knowledge_graph_expansion`, `inter_doc_graph_building`) stay on that builder â€” they are not infra concerns.
