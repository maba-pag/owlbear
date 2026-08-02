---
id: 571
title: Register owlbear-memory server in .vscode/mcp.json
status: archived
priority: medium
created: 2026-04-03 11:04:53.322429+02:00
updated: 2026-04-03 12:12:26.624206+02:00
started: 2026-04-03 12:12:26.624206+02:00
completed: 2026-04-03 12:12:26.624206+02:00
tags:
- scope:config
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

Add owlbear-memory MCP server entry to .vscode/mcp.json. Currently only owlbear-kanban and owlbear_knowledge are registered. Without this, agent tool patterns added by #568 are inert. Also fix setup.py naming to use kebab-case matching workspace convention. AC: - All .vscode/mcp.json includes owlbear-memory server entry - setup.py MCP server keys use kebab-case - Existing agent tool patterns resolve correctly
