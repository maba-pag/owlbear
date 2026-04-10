---
id: 805
title: Tests — board_config
status: research
priority: needed
created: '2026-04-10T21:21:09.498916+00:00'
updated: '2026-04-10T21:21:09.498916+00:00'
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

- Tests verify `board_config()` returns config with valid statuses and display order
- Tests verify `board_config()` returns config with valid priorities and display order
- Tests verify returned object is a copy (mutation doesn't affect engine internal state)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`