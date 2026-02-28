---
id: 251
title: Remove sqlite-vec and FastEmbed
status: archived
priority: needed
created: 2026-02-28T12:39:40.8178635+01:00
updated: 2026-02-28T23:54:27.5379381+01:00
started: 2026-02-28T16:34:32.1713778+01:00
completed: 2026-02-28T23:54:27.5379381+01:00
tags:
    - phase-9
    - knowledge-graph
    - embedding
depends_on:
    - 250
class: standard
---

## Context

Clean removal of sqlite-vec and fastembed from the codebase. Drop vec0 virtual tables, bridge table, old VectorStore class, FastEmbedProvider class. SQLite stays for relational data.

## Research Needed

- Which tests import sqlite_vec directly? All need updating.
- schema.py: remove sqlite_vec.load(), vec0 CREATE TABLE, EMBEDDING_DIM=384
- vectors.py (478 lines): entire file replaced by QdrantVectorStore
- What references VectorStore or FastEmbedProvider outside the knowledge module?

## Acceptance Criteria

- [ ] No `import sqlite_vec` anywhere in `src/` (currently: `schema.py` line 14)
- [ ] No `from fastembed import` anywhere in `src/` (currently: `embeddings.py` line 61)
- [ ] No reference to `sqlite-vec` or `fastembed` in `pyproject.toml` (already updated in #250)
- [ ] `schema.py`: remove `sqlite_vec.load(conn)` call, drop `entity_embeddings` and `document_embeddings` vec0 virtual table creation
- [ ] `schema.py`: remove `embedding_rowid_map` bridge table creation
- [ ] `schema.py`: remove `EMBEDDING_DIM = 384` constant (or update to 1024 if still referenced)
- [ ] Delete `src/owlbear/memory/knowledge/vectors.py` entirely (478 lines, replaced by `qdrant.py`)
- [ ] Delete `FastEmbedProvider` class from `embeddings.py` — keep `EmbeddingProvider` protocol and `DEFAULT_MODEL`/`DEFAULT_DIMENSION` if still referenced, else clean up
- [ ] Update `src/owlbear/memory/knowledge/__init__.py`: remove `VectorStore` from imports and `__all__`, add `QdrantVectorStore` from `qdrant`
- [ ] Update all test files that import `VectorStore`, `FastEmbedProvider`, `EMBEDDING_DIM`, or call `init_db()` with sqlite-vec expectations
- [ ] `init_db()` in `schema.py` must work without sqlite-vec — relational tables stay, vector tables gone
- [ ] All tests pass, ruff clean
- [ ] Verify: `grep -r "sqlite.vec\|fastembed\|vec0\|EMBEDDING_DIM" src/` returns nothing

## TDD — update existing tests

- [ ] `tests/test_knowledge_embeddings.py`: remove/update `FastEmbedProvider` tests, keep `EmbeddingProvider` protocol tests
- [ ] `tests/test_vector_protocol.py`: update `VectorStore` conformance test → `QdrantVectorStore` conformance
- [ ] Any test using `init_db()`: verify it works without sqlite-vec loaded
- [ ] `tests/test_knowledge_schema.py` (if exists): update for removed vec0 tables
- [ ] Run full test suite — no test should import sqlite_vec or fastembed

## Architecture Notes

- `EmbeddingProvider` protocol stays in `embeddings.py` — it's the interface, not tied to FastEmbed
- `_compute_recency_score()` and `IMPORTANCE_BY_TYPE` from `vectors.py` should already be in `qdrant.py` (from #249) before deletion
- `DEFAULT_MODEL` and `DEFAULT_DIMENSION` in `embeddings.py` may need updating or removal if nothing references the old bge-small model

[[2026-02-28]] Sat 12:55

## Merged from #260 (closed as redundant)

No existing data to migrate — user confirmed sqlite-vec was never used in production. The only cleanup needed is removing the empty vec0 tables and bridge table schema, which is already covered by the AC above. If data migration is ever needed in the future, create a new task then (YAGNI).
