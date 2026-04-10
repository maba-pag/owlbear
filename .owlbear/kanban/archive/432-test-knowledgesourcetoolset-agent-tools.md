---
id: 432
title: Test KnowledgeSourceToolset agent tools
status: archived
priority: important
created: 2026-03-02T01:51:49.5129413+01:00
updated: 2026-03-02T09:15:36.1008229+01:00
started: 2026-03-02T01:51:54.2057774+01:00
completed: 2026-03-02T09:15:36.1008229+01:00
tags:
    - phase-9
    - knowledge-graph
    - agent
    - test
class: standard
---

TDD red-phase for #386. Tests for KnowledgeSourceToolset (FunctionToolset exposing source management to agents).

## Acceptance Criteria
- KnowledgeSourceToolset subclasses FunctionToolset
- Constructor accepts KnowledgeSourceStore + RefreshOrchestrator + optional workspace_root
- Registers 3 tools: add_source, list_sources, refresh_source
- add_source(name, source_type, config_json, scope) creates source via store, returns confirmation string
- list_sources(scope) returns formatted list of sources (name, type, enabled, last_refreshed_at)
- list_sources returns 'No sources registered.' when empty
- refresh_source(name) triggers RefreshOrchestrator for the named source, returns summary string
- refresh_source with non-existent name returns error string (not exception)
- All tests use mocked KnowledgeSourceStore and RefreshOrchestrator
- Follows existing KnowledgeToolset pattern: FunctionToolset subclass with _register_tools method

Depends on #428 (test #382), #430 (test #384)
