---
id: 819
title: Tests — MCP adapter slimming regression
status: research
priority: needed
created: '2026-04-10T21:22:34.474123+00:00'
updated: '2026-04-10T21:22:34.474123+00:00'
tags:
- phase-2
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 818
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify mcp-kanban imports from `owlbear_kanban` (not local engine files)
- Tests verify all 8 MCP tools return correct results after adapter slimming
- Tests verify `server.py` creates engine from `owlbear_kanban` package
- Tests fail RED before slimming

## Context

Phase 2, step 3. Depends on #818 (engine extracted).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`