---
id: 822
title: Remove compat alias + migrate all workspace imports
status: research
priority: needed
created: '2026-04-10T21:22:52.811363+00:00'
updated: '2026-04-10T21:22:52.811363+00:00'
tags:
- phase-2
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 821
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `TaskRecord = Task` compat alias removed from engine
- All workspace imports updated (full `grep -r TaskRecord` verification — zero hits)
- All workspace imports use `owlbear_kanban` for engine symbols
- All existing tests pass
- #821 tests pass GREEN

## Context

Phase 2, step 6. Depends on #821 (RED tests). Final Phase 2 task.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`