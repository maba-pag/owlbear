---
id: 800
title: Rename TaskRecord → Task with compat alias
status: research
priority: needed
created: '2026-04-10T21:20:34.453928+00:00'
updated: '2026-04-10T21:20:34.453928+00:00'
tags:
- phase-1
- scope:mcp-kanban
- model
- rigor:thorough
parent: 798
depends_on:
- 799
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `Task` is the canonical class name in `engine_models.py`
- `TaskRecord = Task` compat alias exported for transition
- All internal engine refs use `Task`
- #799 tests pass GREEN
- Existing MCP tests pass unchanged (O4)

## Context

Phase 1, Chain 1 step 2. Depends on #799 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`