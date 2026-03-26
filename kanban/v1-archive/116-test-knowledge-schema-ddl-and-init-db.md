---
id: 116
title: Test knowledge schema DDL and init_db
status: archived
priority: high
created: 2026-02-27T03:42:34.8673295+01:00
updated: 2026-02-27T13:21:47.1087709+01:00
started: 2026-02-27T10:53:57.6136213+01:00
completed: 2026-02-27T13:21:47.1087709+01:00
tags:
    - memory
    - knowledge-graph
    - test
    - phase-2
depends_on:
    - 108
class: standard
---

TDD test suite for `owlbear.memory.knowledge.schema`. Write tests BEFORE implementation (#107).

## Acceptance Criteria

- [ ] New file: `tests/test_knowledge_schema.py`
- [ ] Test `init_db` creates `documents` table with expected columns (PRAGMA table_info)
- [ ] Test `init_db` creates `entities` table with expected columns
- [ ] Test `init_db` creates `edges` table with expected columns and foreign keys
- [ ] Test `init_db` creates `entity_embeddings` vec0 virtual table
- [ ] Test `init_db` creates `document_embeddings` vec0 virtual table
- [ ] Test `init_db` creates `embedding_rowid_map` table
- [ ] Test `init_db` creates `schema_version` table with version entry
- [ ] Test `init_db` is idempotent — calling twice does not raise
- [ ] Test `init_db` works with in-memory SQLite (`:memory:`)
- [ ] Test foreign keys are enforced (edge with nonexistent source raises)
- [ ] Test `EMBEDDING_DIM` constant equals 384
- [ ] All tests initially fail (import error) until #107 implements the module
- [ ] `ruff check` clean on test file
