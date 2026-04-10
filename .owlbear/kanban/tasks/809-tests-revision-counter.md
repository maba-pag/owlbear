---
id: 809
title: Tests — revision counter
status: research
priority: needed
created: '2026-04-10T21:21:30.609548+00:00'
updated: '2026-04-10T21:21:30.609548+00:00'
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

- Tests verify `engine.revision` property starts at 0
- Tests verify revision increments on every write (`create_task`, `edit_task`, `move_task`, `claim_task`, `release_task`, `start_work`, `end_work`)
- Tests verify revision is read-only (no setter)
- Tests verify revision is per-instance (two engine instances have independent counters)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`