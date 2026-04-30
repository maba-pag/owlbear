---
id: 1180
title: 'P1-01: Test decisions.py create_dr + resolve_pending_drs'
status: research
priority: needed
created: 2026-04-30T00:51:30.965405+00:00
updated: 2026-04-30T00:54:51.052626+00:00
tags:
- phase-1
- scope:kanban
- type:test
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by: dim-stream
claimed_at: 2026-04-30T00:54:51.052626+00:00
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test `create_dr` writes pending file with 5-field YAML frontmatter (task_id, agent, request_type, created, response=pending) + markdown body
- Test `create_dr` uses O_EXCL (atomic creation) — collision raises or appends counter suffix
- Test `create_dr` blocks the task (calls engine.block_task with generic reason)
- Test `create_dr` rolls back file if blocking fails (file deleted on engine error)
- Test `resolve_pending_drs` skips files where response=pending
- Test `resolve_pending_drs` processes approved/rejected: appends DR summary to task body, unblocks task, moves file to resolved/
- Test `resolve_pending_drs` processes needs-info: appends summary, keeps task blocked, moves file to resolved/
- Test `resolve_pending_drs` logs warning and skips unknown response values
- Test `resolve_pending_drs` catches per-file exceptions without stalling (fail-safe)
- Test reader ignores unknown frontmatter keys (forward-compatible with old files)

## Scope

- IN: unit tests for `serve/kanban/src/owlbear_kanban/decisions.py` functions
- OUT: MCP layer, pick_tasks integration, Cockpit

Brief: see parent #1179
