---
id: 67
title: 'Test: Scaffold mcp-project MCP server package'
status: archived
priority: medium
created: 2026-03-26 20:03:36.607063+01:00
updated: 2026-03-27 22:15:50.535769+01:00
started: 2026-03-27 22:15:50.535769+01:00
completed: 2026-03-27 22:15:50.535769+01:00
tags:
- phase-1
- scope:mcp
- scope:build
- test
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
TDD RED phase: write failing tests for mcp-project scaffold before builder implements.

## Test Scenarios
- [ ] set_active_project tool returns 'Not yet implemented' string
- [ ] list_projects tool returns 'Not yet implemented' string
- [ ] project://definition resource returns file contents when owlbear-project.json exists (tmp_path fixture)
- [ ] project://definition resource returns JSON error object when owlbear-project.json missing
- [ ] app_lifespan yields AppContext with project_store=None
- [ ] __main__ module is importable and has expected entry point

## Context
See docs/research/scaffold-mcp-project-server.md for tool/resource signatures.
Parent impl task: #41.
Pattern: follow packages/mcp-kanban/tests/test_server.py structure from #65.
