---
id: 802
title: Add TaskSummary model + server integration
status: research
priority: needed
created: '2026-04-10T21:20:49.680606+00:00'
updated: '2026-04-10T21:20:49.680606+00:00'
tags:
- phase-1
- scope:mcp-kanban
- model
- rigor:thorough
parent: 798
depends_on:
- 801
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `TaskSummary` Pydantic model in `engine_models.py`
- Fields: id, title, status, priority, tags, blocked, block_reason, claimed (bool), parent, depends_on
- `list_tasks` engine method returns `list[TaskSummary]`
- `server.py` `_strip` dict eliminated, replaced by `TaskSummary`
- Adapter `outputSchema` patching updated to match TaskSummary schema
- #801 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, Chain 1 step 4. Depends on #801 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`