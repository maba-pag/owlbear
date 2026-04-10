---
id: 823
title: Tests — pick_dispatchable()
status: research
priority: needed
created: '2026-04-10T21:23:01.614181+00:00'
updated: '2026-04-10T21:23:01.614181+00:00'
tags:
- phase-3
- type:test
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 822
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `pick_dispatchable(engine, limit=25, tag="")` returns `list[Task]`
- Tests verify TDD gate: in-progress task without test-writer notes or non-impl tag is excluded
- Tests verify clarity gate: active-status task without bullet/numbered AC is excluded
- Tests verify priority ranking: critical > needed > important > nice-to-have > someday
- Tests verify status ranking: done > docs > review > in-progress > todo > backlog > research
- Tests verify result capping at `limit`
- Tests verify tag filtering
- Tests verify function is importable without MCP dependency
- Tests fail RED before implementation

## Context

Phase 3, step 1. Depends on #822 (Phase 2 complete).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`