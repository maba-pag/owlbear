---
id: 1049
title: 'C-04: RED — activity_store tests'
status: todo
priority: needed
created: 2026-04-21T10:42:50.268061+00:00
updated: 2026-04-21T13:03:33.762123+00:00
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
claimed_at: 2026-04-21T13:03:33.762123+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.9
Module: `serve/kanban/tests/test_activity_store.py`

## Acceptance Criteria

- [ ] AC-C42: `append_activity_event(...)` writes structured `ActivityEvent` JSONL entries to gitignored board-level `activity.jsonl`; `list_activity_events(...)` applies declared filters without scanning task frontmatter
- [ ] AC-C44: No separate session table on disk — `activity.jsonl` is the only persistent history substrate
- [ ] AC-C44a: `compact_activity_log` tests: (a) `before_dt=None` auto-resolves to most recently closed session `ended_at`; (b) entries in open sessions always retained; (c) last 500 entries always retained; (d) rewritten atomically via `atomic_write`; (e) idempotent on re-run
- [ ] All tests fail (RED phase — no implementation exists yet)