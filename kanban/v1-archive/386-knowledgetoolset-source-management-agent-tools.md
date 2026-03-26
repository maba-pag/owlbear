---
id: 386
title: 'KnowledgeToolset: source management agent tools'
status: archived
priority: important
created: 2026-03-01T20:15:29.0176817+01:00
updated: 2026-03-02T09:14:52.489027+01:00
started: 2026-03-01T20:23:05.7941898+01:00
completed: 2026-03-02T09:14:52.489027+01:00
tags:
    - phase-9
    - knowledge-graph
    - agent
depends_on:
    - 432
class: standard
---

From #254 source-registry.md. FunctionToolset exposing source management to agents.

## Location
- src/owlbear/tools/knowledge_source.py (new file, follows KnowledgeToolset pattern)
- Or extend existing src/owlbear/tools/knowledge.py -- builder decides based on complexity

## Acceptance Criteria
- KnowledgeSourceToolset subclasses FunctionToolset
- Constructor: (store: KnowledgeSourceStore, orchestrator: RefreshOrchestrator, workspace_root: Path | None = None)
- _register_tools() registers 3 tools via self.add_function()
- Tool 'add_source': (name: str, source_type: str, config_json: str, scope: str = 'global') -> str
  - Parses config_json (JSON string) to dict, validates source_type against SourceType enum
  - Creates KnowledgeSource via store.create(), returns confirmation: 'Source {name} ({source_type}) created.'
  - On validation error: returns error message (not exception)
- Tool 'list_sources': (scope: str | None = None) -> str
  - Calls store.list_all(scope), returns formatted list: '- {name} [{type}] (scope: {scope}, enabled: {yes/no}, last refresh: {time or never})'
  - Returns 'No sources registered.' when empty
- Tool 'refresh_source': (name: str) -> str
  - Loads source via store.get_by_name(name), triggers orchestrator.refresh(source)
  - Returns summary: 'Refreshed {name}: {n} ingested, {s} skipped, {f} failed'
  - On source not found: returns 'Source {name} not found.'
- All tool functions have descriptive docstrings for agent discoverability
- Follows KnowledgeToolset._register_tools / _safe_path patterns

Depends on test task #432, #382, #384.
