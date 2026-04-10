---
id: 813
title: Tests — status/priority validation
status: research
priority: needed
created: '2026-04-10T21:21:54.982332+00:00'
updated: '2026-04-10T21:21:54.982332+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `create_task` raises `ValueError` for invalid status
- Tests verify `create_task` raises `ValueError` for invalid priority
- Tests verify `edit_task` raises `ValueError` for invalid status
- Tests verify `edit_task` raises `ValueError` for invalid priority
- Tests verify valid status/priority values accepted (from config)
- Tests verify MCP adapter maps `ValueError` to `ToolError` for create_task and edit_task
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`