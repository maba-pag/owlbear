---
id: 808
title: Add valid_transitions(status)
status: research
priority: needed
created: '2026-04-10T21:21:23.793444+00:00'
updated: '2026-04-10T21:21:23.793444+00:00'
tags:
- phase-1
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 807
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `valid_transitions(status)` method on `KanbanEngine`
- Returns set of all configured statuses except the given one
- Raises `ValueError` for invalid status input
- `end_work()`'s linear behavior documented as agent-specific in docstring
- #807 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #807 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`