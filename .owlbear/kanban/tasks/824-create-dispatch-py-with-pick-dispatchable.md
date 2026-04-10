---
id: 824
title: Create dispatch.py with pick_dispatchable()
status: research
priority: needed
created: '2026-04-10T21:23:09.122392+00:00'
updated: '2026-04-10T21:23:09.122392+00:00'
tags:
- phase-3
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 823
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `dispatch.py` in `owlbear_kanban` package
- `pick_dispatchable(engine, *, limit=25, tag="") → list[Task]`
- Owns gate predicates: TDD gate (in-progress needs test-writer notes or non-impl tag), clarity gate (active statuses need bullet/numbered AC)
- Owns priority/status rank maps (hardcoded, intentionally separate from config display order)
- Result capping at `limit`
- Tag filtering
- Rank maps documented: execution priority ≠ display order
- #823 tests pass GREEN

## Context

Phase 3, step 2. Depends on #823 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`