---
id: 1075
title: 'B-10: GREEN — move_task + start_work'
status: todo
priority: needed
created: 2026-04-21T10:49:32.320431+00:00
updated: 2026-04-21T10:49:32.320431+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1073
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.6, §1.7, §3.1, §3.2
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement AgentView.move_task and AgentView.start_work. Fork point: B-11 (end_work) and B-15 (CockpitView) both depend on this task.

move_task: status transitions, archival validation (D37 matrix), write-time predicate on destination (D15+D41 atomicity), skip-transition guidance (D54), archive clears claim atomically (D17).

start_work: claim semantics (no identity per D11), lazy-release on expired claims (D18+D36 via CAS), blocked/archived not claimable.

## Acceptance Criteria

- [ ] All RED tests from B-09 (#1073) pass
- [ ] move_task validates archival_reason/archival_refs per D37 full matrix
- [ ] Write-time predicate fires on destination; failure → atomic rollback (D41)
- [ ] Archive operation clears claim atomically (D17)
- [ ] start_work sets `claimed_at = now()`, no `claimed_by` (D11)
- [ ] Expired-claim lazy-release via `storage.write_task_if_unchanged` CAS (D18+D36)
- [ ] `updated` advanced on success (D14)
- [ ] AgentView.move_task has NO `expected_updated` param (D46)