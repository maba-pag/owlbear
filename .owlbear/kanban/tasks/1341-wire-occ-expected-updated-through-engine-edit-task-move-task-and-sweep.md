---
id: 1341
title: Wire OCC (expected_updated) through engine edit_task, move_task, and 
  sweep
status: in-progress
priority: important
created: 2026-05-04T15:00:05.889996+00:00
updated: 2026-05-04T15:32:57.107900+00:00
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
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_engine_occ_1341.py
- Classes: TestFromAC_EngineEditTaskOCC, TestFromAC_EngineMoveTaskOCC, TestFromAC_EngineSweepOCC, TestFromAC_EngineNonOCCPathPreserved
- Tests per category: happy 7, edge 2, error 7, boundary 5
- Total: 21 tests — all PASS (see note below)
- ruff: clean

⚠️ Implementation pre-completed: All AC#1–3 and AC#6 are already implemented in the engine. engine.edit_task, engine.move_task, and engine.sweep all have expected_updated routed to storage.write_task_if_unchanged with ERR_STALE handling. All 5 previously-failing OCC tests in test_engine_cockpit_view.py now pass (verified: 45/45 green).

The 21 new engine-level tests exercise the contract directly (without CockpitView) and all pass against current code. Builder's remaining scope: verify AC#4 (test_compact_activity_delegates_to_storage_compact_activity_log mock target) — currently the test passes with `owlbear_kanban.engine.compact_activity_log` as the target, which is the correct location given the import in engine.py.