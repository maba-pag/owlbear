---
id: 1054
title: 'C-09: RED — engine activity/session tests'
status: todo
priority: needed
created: 2026-04-21T10:42:50.316514+00:00
updated: 2026-04-21T13:03:37.794768+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by: strong-stag
claimed_at: 2026-04-21T13:03:37.794768+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.9
Module: `serve/kanban/tests/test_engine_activity.py`

## Acceptance Criteria

- [ ] AC-C42: Engine methods emit `ActivityEvent` entries via `append_activity_event` for claim/edit/move/end_work/sweep actions
- [ ] AC-C43: `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl` with `active`/`all`/`blocked-or-rejected`/`released` semantics matching §7.2
- [ ] Fresh canonical stream — no legacy migration of old activity history
- [ ] All tests fail (RED phase — no implementation exists yet)