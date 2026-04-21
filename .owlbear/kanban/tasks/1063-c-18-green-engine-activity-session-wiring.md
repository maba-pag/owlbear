---
id: 1063
title: 'C-18: GREEN — engine activity/session wiring'
status: todo
priority: needed
created: 2026-04-21T10:44:12.261314+00:00
updated: 2026-04-21T10:44:12.261314+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1054
- 1058
- 1062
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §7, §8.9
Module: `serve/kanban/src/owlbear_kanban/engine.py` — activity/session edits only

Engine wiring for activity stream and session derivation. Depends on activity_store (#1058) for append/query primitives and engine storage integration (#1062) for the base engine shape.

## Acceptance Criteria

- [ ] AC-C42: Engine methods (claim, edit, move, end_work, sweep) emit `ActivityEvent` entries via `append_activity_event`
- [ ] AC-C43: `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl` with `active`/`all`/`blocked-or-rejected`/`released` filter semantics per §7.2
- [ ] Fresh canonical stream — no legacy migration of old activity history
- [ ] All RED tests from C-09 (#1054) pass