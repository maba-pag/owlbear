---
id: 428
title: Test KnowledgeSource model + KnowledgeSourceStore
status: archived
priority: needed
created: 2026-03-02T01:50:35.9735051+01:00
updated: 2026-03-02T09:15:27.2561086+01:00
started: 2026-03-02T01:50:41.6474191+01:00
completed: 2026-03-02T09:15:27.2561086+01:00
tags:
    - phase-9
    - knowledge-graph
    - test
class: standard
---

TDD red-phase for #382. Tests for KnowledgeSource Pydantic model and KnowledgeSourceStore SQLite CRUD.

## Acceptance Criteria
- SourceType enum has exactly 3 members: url_list, crawl, file_glob (StrEnum)
- KnowledgeSource model validates all required fields (id, name, source_type, config, scope, enabled, priority, last_refreshed_at, last_error, created_at, updated_at)
- KnowledgeSource.config is dict[str, Any] (JSON-serializable)
- KnowledgeSource is frozen (immutable)
- KnowledgeSourceStore.create() inserts and returns a KnowledgeSource
- KnowledgeSourceStore.get() retrieves by id, returns None for missing
- KnowledgeSourceStore.get_by_name() retrieves by name+scope, returns None for missing
- KnowledgeSourceStore.list_all() returns all sources, optionally filtered by scope
- KnowledgeSourceStore.list_enabled() returns only enabled sources
- KnowledgeSourceStore.update() overwrites an existing record (raises on missing)
- KnowledgeSourceStore.delete() removes by id, returns bool
- Unique constraint on name+scope: create() raises on duplicate name within same scope
- Different scopes can have same name (no conflict)
- JSON round-trip: config dict survives store/retrieve cycle
