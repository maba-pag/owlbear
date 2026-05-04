---
id: 1341
title: Wire OCC (expected_updated) through engine edit_task, move_task, and 
  sweep
status: todo
priority: important
created: 2026-05-04T15:00:05.889996+00:00
updated: 2026-05-04T15:01:06.378253+00:00
tags:
- soft-blocker
- kanban
- cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

CockpitView passes `expected_updated` but engine methods don't accept it. Storage's `write_task_if_unchanged()` exists and works. Engine needs plumbing to route there. 4 real regression tests + 1 stale mock to fix.

## Acceptance Criteria

1. `engine.edit_task()` accepts optional `expected_updated: str | None = None`; when provided, calls `storage.write_task_if_unchanged()` instead of `write_task()`
2. `engine.move_task()` same pattern
3. `engine.sweep()` uses `write_task_if_unchanged()` for claim releases; catches `ConcurrencyError("ERR_STALE")` and silently skips stale tasks
4. `test_compact_activity_delegates_to_storage_compact_activity_log` fixed (correct mock target)
5. All 5 previously-failing OCC tests in test_engine_cockpit_view.py pass
6. Existing callers that don't pass expected_updated continue to work (non-OCC path preserved)

## Key Files

- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/kanban/src/owlbear_kanban/storage.py`
- `serve/cockpit/src/owlbear_cockpit/view.py`
- `tests/test_engine_cockpit_view.py`

## Source

Finding 7 in `.owlbear/research/kanban-mcp-deployment-audit.md`