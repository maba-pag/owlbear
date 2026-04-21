---
id: 1072
title: 'B-08: GREEN — create_task + edit_task'
status: todo
priority: needed
created: 2026-04-21T10:48:51.287524+00:00
updated: 2026-04-21T10:48:51.287524+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1070
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.4, §1.5, §3.2, §3.4, §3.5
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement AgentView.create_task and AgentView.edit_task. Fork point: B-09 (move/claim) and B-13 (pick_tasks) both depend on this task.

create_task: no `status` param (D50), tasks created at entry_status, predicate fires on entry, atomic ID allocation, body size validation, cross-ref validation.

edit_task: full parameter set per §1.5, body-exclusive gate, block_reason semantics (D53), no-op detection, archival field gates (D37 matrix), OCC bypass (AgentView — no expected_updated), timestamp prepend on append_body.

## Acceptance Criteria

- [ ] All RED tests from B-07 (#1070) pass
- [ ] `create_task` creates at `BoardConfig.entry_status` with no `status` param (D50)
- [ ] Body size: >500KB → ERR_BODY_TOO_LARGE; >100KB → guidance warning; applies to post-append total (D47)
- [ ] `edit_task` no-op → ERR_NO_OP (engine computes diff)
- [ ] block_reason non-empty → sets blocked=true + block_reason; empty/null → clears both (D53)
- [ ] Archival refs matrix fully enforced per §3.2
- [ ] Predicate on entry_status evaluated on create (D15+D50)
- [ ] `updated` advanced on any successful change (D14)
- [ ] AgentView.edit_task has NO `expected_updated` param (D46 — last-writer-wins)