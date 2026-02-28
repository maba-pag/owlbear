---
id: 107
title: Create owlbear.memory.knowledge.schema module
status: archived
priority: high
created: 2026-02-27T03:31:16.02141+01:00
updated: 2026-02-27T13:21:38.2099456+01:00
started: 2026-02-27T03:32:48.1775178+01:00
completed: 2026-02-27T13:21:38.2099456+01:00
tags:
    - memory
    - knowledge-graph
    - phase-2
depends_on:
    - 106
    - 108
    - 116
class: standard
---

DDL and database initialization for the knowledge graph. Adapted from tool.graphicator `db/schema.py`.

## Acceptance Criteria

- [ ] New file: `src/owlbear/memory/knowledge/schema.py`
- [ ] `init_db(conn: sqlite3.Connection) -> None` function that creates all tables
- [ ] Tables created:
  - `documents` — id TEXT PK, title TEXT, content TEXT, metadata TEXT (JSON), created_at TEXT
  - `entities` — id TEXT PK, name TEXT, entity_type TEXT, description TEXT, metadata TEXT (JSON), created_at TEXT
  - `edges` — id TEXT PK, source_id TEXT FK(entities), target_id TEXT FK(entities), relation TEXT, weight REAL, metadata TEXT (JSON), created_at TEXT
  - `entity_embeddings` — vec0 virtual table (384 dimensions, float32)
  - `document_embeddings` — vec0 virtual table (384 dimensions, float32)
  - `embedding_rowid_map` — rowid INTEGER PK, entity_or_doc_id TEXT, embedding_type TEXT ('entity'|'document')
  - `schema_version` — version INTEGER, applied_at TEXT
- [ ] `CREATE TABLE IF NOT EXISTS` for idempotency — calling `init_db` twice is safe
- [ ] Foreign key enforcement enabled (`PRAGMA foreign_keys = ON`)
- [ ] `sqlite_vec` extension loaded via `sqlite_vec.load(conn)`
- [ ] Embedding dimension (384) defined as module-level constant `EMBEDDING_DIM`
- [ ] Works with in-memory SQLite (`:memory:`) for testing
- [ ] `ruff check` clean

See docs/knowledge-graph-research.md section 3.4, 4
