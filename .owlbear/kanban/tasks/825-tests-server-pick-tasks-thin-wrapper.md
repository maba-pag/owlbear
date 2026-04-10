---
id: 825
title: Tests — Server pick_tasks thin wrapper
status: research
priority: needed
created: '2026-04-10T21:23:15.034176+00:00'
updated: '2026-04-10T21:23:15.034176+00:00'
tags:
- phase-3
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 824
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify server `pick_tasks` MCP tool calls `pick_dispatchable()` from engine
- Tests verify no inline gating logic remains in `server.py`
- Tests verify `pick_tasks` response format unchanged (dispatch wrapper with task details)
- Tests verify existing `pick_tasks` MCP contract preserved
- Tests fail RED before slimming

## Context

Phase 3, step 3. Depends on #824 (dispatch.py created).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`