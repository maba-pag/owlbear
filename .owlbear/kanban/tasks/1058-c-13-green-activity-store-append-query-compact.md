---
id: 1058
title: 'C-13: GREEN — activity_store append/query/compact'
status: todo
priority: needed
created: 2026-04-21T10:43:21.228592+00:00
updated: 2026-04-21T10:43:21.228592+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1049
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §7, §8.9
Module: `serve/kanban/src/owlbear_kanban/activity_store.py`

## Acceptance Criteria

- [ ] AC-C42: `append_activity_event(kanban_dir, event)` writes `ActivityEvent` as JSONL to board-level `activity.jsonl` (gitignored)
- [ ] AC-C42: `list_activity_events(kanban_dir, ...)` applies filters (task_id, action, since, limit) without scanning task frontmatter
- [ ] AC-C44: No separate session table — all derived from `activity.jsonl`
- [ ] AC-C44a: `compact_activity_log(kanban_dir, before_dt=None)`: auto-resolve cutoff to most recently closed session; retain open-session entries; retain last 500 entries minimum; atomic rewrite; idempotent
- [ ] `ActivityEvent` and `ActivityCompactionResult` models from §1.2
- [ ] Fresh canonical stream — no legacy migration of old activity formats
- [ ] All RED tests from C-04 (#1049) pass