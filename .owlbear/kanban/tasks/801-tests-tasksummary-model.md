---
id: 801
title: Tests — TaskSummary model
status: research
priority: needed
created: '2026-04-10T21:20:41.798290+00:00'
updated: '2026-04-10T21:20:41.798290+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 800
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `TaskSummary` schema: id, title, status, priority, tags, blocked, block_reason, claimed (bool), parent, depends_on
- Tests verify `TaskSummary` excludes: body, created, updated, claimed_by, claimed_at, file
- Tests verify `list_tasks` returns `TaskSummary` projections instead of hand-built dicts
- Tests verify `TaskSummary` can be constructed from `Task` instance
- Tests fail RED before implementation

## Context

Phase 1, Chain 1 step 3. Depends on #800 (Task rename complete).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`