---
id: 1071
title: 'B-06: GREEN — list_tasks + show_task'
status: todo
priority: needed
created: 2026-04-21T10:48:51.277671+00:00
updated: 2026-04-21T10:48:51.277671+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1069
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.1, §1.2, §3.3
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement AgentView.list_tasks and AgentView.show_task (+ identical signatures on CockpitView). Covers query construction, filter validation, ids-exclusive check, section extraction via parsed body, dep_status pure-function computation, archived-task reads, missing_ids population, guidance emission.

## Acceptance Criteria

- [ ] All RED tests from B-05 (#1069) pass
- [ ] `list_tasks` signature: 1:1 passthrough per §1.1 (status, priority, tag, archival_reason, ids, unclaimed, blocked, parent, search, sort, reverse, limit)
- [ ] `show_task` signature: (id, section) per §1.2
- [ ] `dep_status` computed per §3.3 every read — worst-wins precedence (blocked > redirect > ok)
- [ ] Section filter: case-insensitive heading match regardless of level per D56
- [ ] Default excludes archived unless `status="archived"` or `ids` used
- [ ] `guidance` field populated per D39 (envelope-only, never persisted)