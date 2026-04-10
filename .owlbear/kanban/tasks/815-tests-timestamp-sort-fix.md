---
id: 815
title: Tests — timestamp sort fix
status: research
priority: needed
created: '2026-04-10T21:22:06.986868+00:00'
updated: '2026-04-10T21:22:06.986868+00:00'
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

- Tests verify sort by `created` produces correct order with mixed timezone offsets (`+02:00` vs `+00:00`)
- Tests verify sort by `updated` produces correct order with mixed timezone offsets
- Tests verify sort handles both Go 7-digit nanosecond format and Python microsecond format
- Tests verify stored timestamp format is unchanged (string round-trip fidelity preserved)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`