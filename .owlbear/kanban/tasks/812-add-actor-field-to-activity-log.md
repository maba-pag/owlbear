---
id: 812
title: Add actor field to activity log
status: research
priority: needed
created: '2026-04-10T21:21:49.300844+00:00'
updated: '2026-04-10T21:21:49.300844+00:00'
tags:
- phase-1
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 811
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `log_activity()` gains `actor` parameter (default: `"engine"`)
- All engine call sites pass `actor` param
- New JSONL entries include `"actor"` field
- Old entries without `actor` remain readable (backward compatible — no migration)
- #811 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #811 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`