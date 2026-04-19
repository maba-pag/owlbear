---
id: 990
title: Cockpit `block:user` tag lifecycle in mutation routes
status: backlog
priority: needed
created: 2026-04-18T21:23:00.867289+00:00
updated: 2026-04-18T21:48:47.850970+00:00
tags:
- type:feature
- scope:cockpit
- scope:kanban
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D3.

## Problem
Cockpit-initiated blocks are indistinguishable from agent-initiated blocks. Agents should not create DRs for user-driven blocks.

## Acceptance Criteria
- Cockpit `edit_task` route: when `block_reason` is set (blocking), append `block:user` to engine kwargs `add_tags`.
- Cockpit `edit_task` route: when `block_reason` is cleared (unblocking), append `block:user` to engine kwargs `remove_tags`.
- Tag injection happens in the route handler, AFTER `_build_edit_kwargs()` returns (avoids tag-diff contract conflict).
- Integration test: block via cockpit → task has `block:user` tag.
- Integration test: unblock via cockpit → `block:user` tag removed.
- Integration test: block with explicit tags list → `block:user` is added without breaking user's tag set.

## Files
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
- `tests/test_cockpit_mutation_api.py` (extend existing)

## Dependencies
- None (independent of MCP guidance work)
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/cockpit-block-user-tag-lifecycle-990.md
- Sources: 5 studied, 4 high-relevance (mutation.py, engine.py, architect stance, D3 decision)
- Recommendation: Proceed with architect's exact implementation — 8 LOC production, 3 integration tests (confidence: 0.92)
- Key finding: tag-diff conflict when user sends `tags` + `block_reason` simultaneously is handled correctly by architect's post-injection code (strip conflicting tag from opposite list before inserting)
- Follow-up tasks created: none needed — #990 AC already covers all identified scenarios
- Decision requests: none (T1 — implementation follows approved D3 decision)