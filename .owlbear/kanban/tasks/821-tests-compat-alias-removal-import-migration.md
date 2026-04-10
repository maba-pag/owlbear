---
id: 821
title: Tests — Compat alias removal + import migration
status: research
priority: needed
created: '2026-04-10T21:22:46.872069+00:00'
updated: '2026-04-10T21:22:46.872069+00:00'
tags:
- phase-2
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 820
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify no `TaskRecord` references remain in workspace (grep verification)
- Tests verify all engine imports use `owlbear_kanban` namespace
- Tests verify existing test files import from correct package
- Tests fail RED before migration

## Context

Phase 2, step 5. Depends on #820 (adapter slimmed).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`