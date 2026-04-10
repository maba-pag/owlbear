---
id: 817
title: Tests — Engine package boundary + public API
status: research
priority: critical
created: '2026-04-10T21:22:21.043519+00:00'
updated: '2026-04-10T21:22:21.043519+00:00'
tags:
- phase-2
- type:test
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 802
- 804
- 806
- 808
- 810
- 812
- 814
- 816
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `from owlbear_kanban import KanbanEngine, Task, TaskSummary` works
- Tests verify engine package does NOT import `mcp` or any transport package (boundary test)
- Tests verify engine public API surface: KanbanEngine methods, Task, TaskSummary, BoardConfig exports
- Tests verify MCP adapter is allowed to import `owlbear_kanban`
- Tests fail RED before extraction

## Context

Phase 2, step 1. Depends on all Phase 1 implementation tasks completing.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`