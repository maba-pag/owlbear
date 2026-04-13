---
id: 867
title: Delete stale test_pick_tasks.py — 38 broken tests with zero unique coverage
status: backlog
priority: nice-to-have
created: '2026-04-13T20:51:15.145212+00:00'
updated: '2026-04-13T20:51:15.145212+00:00'
tags:
- phase-3
- type:test
- scope:mcp-kanban
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `tests/test_pick_tasks.py` is deleted
- No other test files are modified
- All remaining tests pass (`uv run pytest tests/ -m "not api" -q`)

## Context

Research in `.owlbear/research/stale-test-pick-tasks-cleanup.md` (#848) confirmed all 38 tests have zero unique coverage:
- 24 behaviors fully covered by test_pick_dispatchable_823/824, test_server_pick_tasks_thin_wrapper_825, test_kanban_mcp_migration
- 10 tests obsolete (tested `_run_kanban` CLI flags that no longer exist)
- 2 tests for atomicity gate intentionally removed from dispatch.py
- 2 tests for JSON null-body scenario obsoleted by Pydantic `body: str=""` model

Confidence: 0.95. This is a trivial file deletion.