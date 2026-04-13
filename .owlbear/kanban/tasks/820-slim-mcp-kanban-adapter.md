---
id: 820
title: Slim mcp-kanban adapter
status: research
priority: needed
created: '2026-04-10T21:22:41.393257+00:00'
updated: '2026-04-12T03:33:19.015014+00:00'
tags:
- phase-2
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 819
blocked: false
block_reason: null
claimed_by: crisp-loch
claimed_at: '2026-04-12T03:33:19.015014+00:00'
---
## Acceptance Criteria

- mcp-kanban `pyproject.toml` adds `owlbear-kanban` as dependency
- `server.py` imports from `owlbear_kanban` instead of local engine modules
- Engine modules removed from mcp-kanban source tree
- `models.py` retains `KanbanTask` (MCP boundary model)
- `__main__.py` retained
- #819 tests pass GREEN
- All 8 MCP tool tests pass (O4)

## Context

Phase 2, step 4. Depends on #819 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`