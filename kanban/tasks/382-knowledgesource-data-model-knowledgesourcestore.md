---
id: 382
title: KnowledgeSource data model + KnowledgeSourceStore (SQLite CRUD)
status: archived
priority: needed
created: 2026-03-01T20:14:55.0073904+01:00
updated: 2026-03-02T09:14:45.2243181+01:00
started: 2026-03-01T20:22:57.6332414+01:00
completed: 2026-03-02T09:14:45.2243181+01:00
tags:
    - phase-9
    - knowledge-graph
    - model
depends_on:
    - 428
class: standard
---

From #254 source-registry-research.md. Data model and SQLite CRUD store for knowledge sources.

## Location
- SourceType enum + KnowledgeSource model: src/owlbear/memory/knowledge/models.py (alongside Entity, Edge, Document)
- KnowledgeSourceStore: src/owlbear/memory/knowledge/source_store.py (new file, follows GraphStore pattern)

## Acceptance Criteria
- SourceType(StrEnum) with exactly 3 members: url_list, crawl, file_glob
- KnowledgeSource(BaseModel, frozen=True) with fields: id (str, default uuid4 hex), name (str), source_type (SourceType), config (dict[str, Any]), scope (str, default 'global'), enabled (bool, default True), priority (int, default 0), last_refreshed_at (str | None, default None), last_error (str | None, default None), created_at (str), updated_at (str)
- KnowledgeSourceStore(conn: sqlite3.Connection) constructor, same pattern as GraphStore
- store.create(source: KnowledgeSource) -> None: INSERT, raises sqlite3.IntegrityError on duplicate name+scope
- store.get(source_id: str) -> KnowledgeSource | None
- store.get_by_name(name: str, scope: str = 'global') -> KnowledgeSource | None
- store.list_all(scope: str | None = None) -> list[KnowledgeSource]: all sources, optionally filtered by scope
- store.list_enabled(scope: str | None = None) -> list[KnowledgeSource]: enabled=True only, ordered by priority DESC
- store.update(source: KnowledgeSource) -> None: UPDATE by id, raises ValueError if not found
- store.delete(source_id: str) -> bool: DELETE, returns True if existed
- config dict is JSON-serialized on write, deserialized on read (reuse GraphStore._dump_meta/_load_meta pattern)
- enabled stored as INTEGER (0/1) in SQLite, mapped to bool in Python

Depends on test task #428.
