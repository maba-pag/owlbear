---
id: 1078
title: 'B-15: RED — CockpitView tests'
status: todo
priority: needed
created: 2026-04-21T10:50:12.218304+00:00
updated: 2026-04-21T10:50:12.218304+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1071
- 1075
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §5, §3.8
Module: `serve/kanban/tests/test_engine_cockpit_view.py`

Test CockpitView facade — OCC-guarded mutations, admin operations, activity/session reads. CockpitView wraps engine methods with OCC (edit_task, move_task) and adds admin-only operations (release_task, sweep, scan_corruption, repair_storage, compact_activity, list_activity, list_sessions).

## Acceptance Criteria

- [ ] CockpitView.edit_task requires `expected_updated` param; mismatch → ConcurrencyError(ERR_STALE) per D22+D46
- [ ] CockpitView.move_task requires `expected_updated` param; mismatch → ConcurrencyError(ERR_STALE)
- [ ] AC-NEW-21: release_task on unclaimed → idempotent no-op (updated NOT advanced)
- [ ] AC-NEW-22: sweep returns list of released task IDs; idempotent (second call → [])
- [ ] release_task on missing id → NotFoundError(ERR_NOT_FOUND)
- [ ] list_activity supports filter by task_id, action, source, time window
- [ ] list_sessions returns SessionRecord list with correct state derivation per D31
- [ ] scan_corruption is read-only (no writes), returns list[CorruptionError]
- [ ] repair_storage: phase-1 scan_and_fix + phase-2 AR creation; never implicit at startup
- [ ] compact_activity calls storage.compact_activity_log
- [ ] CockpitView does NOT expose: create_task, start_work, end_work, pick_tasks
- [ ] ActivityEvent.source populated automatically: "agent" / "cockpit" / "engine" per §3.8
- [ ] All tests fail (RED phase)