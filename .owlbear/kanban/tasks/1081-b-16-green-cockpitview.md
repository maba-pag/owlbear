---
id: 1081
title: 'B-16: GREEN — CockpitView'
status: todo
priority: needed
created: 2026-04-21T10:50:32.631056+00:00
updated: 2026-04-21T10:50:32.631056+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1078
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §5, §3.8
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement CockpitView facade — OCC-guarded mutations + admin operations. Two categories:

1. **OCC-guarded writes:** edit_task and move_task with mandatory `expected_updated` param, routed through `storage.write_task_if_unchanged` (Brief C CAS primitive). Mismatch → ConcurrencyError(ERR_STALE).

2. **Admin operations:** release_task (unconditional claim clear, idempotent), sweep (expire all stale claims via CAS), scan_corruption (read-only), repair_storage (two-phase: scan_and_fix + AR creation), compact_activity.

3. **Activity reads:** list_activity (filtered raw events), list_sessions (derived SessionRecord view per D31).

## Acceptance Criteria

- [ ] All RED tests from B-15 (#1078) pass
- [ ] edit_task/move_task route through storage CAS; ERR_STALE on mismatch
- [ ] release_task: idempotent on unclaimed (AC-NEW-21)
- [ ] sweep: returns released task IDs; idempotent (AC-NEW-22); per-task CAS, skip on ERR_STALE
- [ ] scan_corruption: read-only, returns list[CorruptionError]
- [ ] repair_storage: phase-1 (storage scan_and_fix) + phase-2 (AR creation via engine); never at startup
- [ ] compact_activity: delegates to storage.compact_activity_log
- [ ] list_activity: filter by task_id, action, source, time window
- [ ] list_sessions: derive SessionRecord from activity events; filter per D31
- [ ] ActivityEvent.source set automatically per §3.8 (agent/cockpit/engine)
- [ ] Method exposure: NO create_task, start_work, end_work, pick_tasks on CockpitView