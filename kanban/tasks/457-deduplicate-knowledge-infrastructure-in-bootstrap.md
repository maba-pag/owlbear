---
id: 457
title: Deduplicate knowledge infrastructure in bootstrap
status: archived
priority: critical
created: 2026-03-04T07:37:37.7196664+01:00
updated: 2026-03-06T19:28:05.7266428+01:00
started: 2026-03-06T00:01:03.394596+01:00
completed: 2026-03-06T19:28:05.7266428+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

## Research Findings (2026-03-05)

### Status: ALREADY IMPLEMENTED

The deduplication described in the AC was implemented in commit `f7ba7f9` (2026-03-04) via the `_KnowledgeInfra` dataclass pattern. The audit docs that generated this task were committed 30s later in the same batch.

### AC Verification

| AC Item | Status | Evidence |
|---------|--------|----------|
| Single SQLite conn | DONE | `_build_knowledge_infra()` creates one `sqlite3.connect()`, stored in `_KnowledgeInfra.conn`, passed to both toolsets |
| Single BgeM3 instance | DONE | One `BgeM3EmbeddingProvider()` in `_build_knowledge_infra()`, shared via `infra.embedding_provider` |
| Single QdrantVectorStore | DONE | One `QdrantVectorStore()` in `_build_knowledge_infra()`, shared via `infra.vector_store` |

### Implementation Details

- `_KnowledgeInfra` dataclass (bootstrap.py:252) holds: conn, graph_store, vector_store, embedding_provider, entity_extractor, text_chunker
- `_build_knowledge_infra()` factory (bootstrap.py:268) creates all shared objects once
- `build_toolsets()` (bootstrap.py:591) calls factory once, passes result to both `_build_knowledge_toolset()` and `_build_bookmark_toolset()`
- Two separate `IngestPipeline` instances exist (one with inter_doc_builder, one without) but share all heavy infra  this is by design

### Test Coverage

Tests in `test_bootstrap.py` (line 1580+) verify:
- Dataclass exists with correct fields
- QdrantClient created exactly once in build_toolsets
- BgeM3EmbeddingProvider created exactly once
- Both toolsets present in output
- Object identity preserved
- No bookmark warning logged

### Minor Finding (separate task)

The SQLite connection in `_KnowledgeInfra` is NOT registered in `BootstrapResult.cleanup`. The conn is never explicitly closed  it relies on GC/process exit. Low priority since this is a daemon, but worth tracking separately.

### Recommendation (.95 confidence)

This task is already complete. Fast-track through pipeline to done. Create one minor follow-up task for the missing conn cleanup.
