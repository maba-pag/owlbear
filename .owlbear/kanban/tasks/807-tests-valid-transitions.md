---
id: 807
title: Tests — valid_transitions
status: research
priority: needed
created: '2026-04-10T21:21:18.809894+00:00'
updated: '2026-04-10T21:21:18.809894+00:00'
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

- Tests verify `valid_transitions(status)` returns set of all configured statuses except the given one
- Tests verify invalid status input raises `ValueError`
- Tests verify transitions match config-defined statuses
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`