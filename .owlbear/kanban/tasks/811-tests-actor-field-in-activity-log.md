---
id: 811
title: Tests — actor field in activity log
status: research
priority: needed
created: '2026-04-10T21:21:41.924380+00:00'
updated: '2026-04-10T21:21:41.924380+00:00'
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

- Tests verify new JSONL entries include `"actor"` field
- Tests verify old entries without `actor` load without error (backward compat)
- Tests verify default actor is `"engine"` when not specified
- Tests verify actor field appears in all action types (create, edit, move, claim, release)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`