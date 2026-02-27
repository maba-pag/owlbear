---
id: 118
title: Test knowledge vector search operations
status: todo
priority: high
created: 2026-02-27T03:42:46.59104+01:00
updated: 2026-02-27T03:45:17.727812+01:00
tags:
    - memory
    - knowledge-graph
    - test
    - phase-2
depends_on:
    - 107
class: standard
---

TDD test suite for `owlbear.memory.knowledge.vectors`. Write tests BEFORE implementation (#110).

## Acceptance Criteria

- [ ] New file: `tests/test_knowledge_vectors.py`
- [ ] Shared fixture: `db_conn` — in-memory SQLite connection with `init_db` + `sqlite_vec` loaded
- [ ] Shared fixture: `vector_store` — `VectorStore(db_conn)`
- [ ] Test `store_embedding` inserts vector + rowid_map entry for embedding_type 'entity'
- [ ] Test `store_embedding` inserts vector + rowid_map entry for embedding_type 'document'
- [ ] Test `store_embedding` raises `ValueError` when embedding length != 384
- [ ] Test `store_embedding` upserts — calling twice with same id updates the vector
- [ ] Test `get_embedding` returns stored vector (verify first/last elements match)
- [ ] Test `get_embedding` returns `None` for nonexistent id
- [ ] Test `search_similar` returns results ordered by ascending distance
- [ ] Test `search_similar` respects `top_k` parameter
- [ ] Test `search_similar` with `embedding_type` filter narrows results
- [ ] Test `delete_embedding` returns `True` and removes both vec0 row and rowid_map entry
- [ ] Test `delete_embedding` returns `False` for nonexistent id
- [ ] All tests initially fail (import error) until #110 implements the module
- [ ] `ruff check` clean on test file
