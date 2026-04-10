---
id: 799
title: Tests — Rename TaskRecord → Task
status: research
priority: critical
created: '2026-04-10T21:20:28.162627+00:00'
updated: '2026-04-10T21:20:28.162627+00:00'
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

- Test file verifies `Task` importable from `engine_models`
- Verifies `TaskRecord` alias resolves to `Task` (same object identity)
- Verifies engine CRUD works with renamed model (create, edit, move, show, list)
- Tests fail RED before implementation

## Context

Phase 1, Chain 1 step 1. First task in the model cleanup chain.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`