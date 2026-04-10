---
id: 810
title: Add revision counter
status: research
priority: needed
created: '2026-04-10T21:21:35.834128+00:00'
updated: '2026-04-10T21:21:35.834128+00:00'
tags:
- phase-1
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 809
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `self._revision: int` initialized to 0 in `__init__`
- `revision` read-only property on `KanbanEngine`
- Incremented on every write operation (create, edit, move, claim, release, start_work, end_work)
- Per-instance, no persistence (loss on restart acceptable)
- #809 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #809 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`