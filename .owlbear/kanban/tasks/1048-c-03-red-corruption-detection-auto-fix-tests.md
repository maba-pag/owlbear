---
id: 1048
title: 'C-03: RED — corruption detection & auto-fix tests'
status: todo
priority: needed
created: 2026-04-21T10:42:50.258020+00:00
updated: 2026-04-21T13:03:26.394721+00:00
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
claimed_at: 2026-04-21T13:03:26.394721+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.4
Module: `serve/kanban/tests/test_corruption.py`

## Acceptance Criteria

- [ ] AC-C17: Each of the 9 ERR_CORRUPT_* modes (§4.1) has at least one positive-detection unit test
- [ ] AC-C18: `read_task` raises `CorruptionError(code=...)` for every detected mode (outside sweep context)
- [ ] AC-C21: Each ERR_CORRUPT_* code is a subclass of `CorruptionError` per C8.8 shape
- [ ] AC-C22: Auto-fix matrix (§4.2) exhaustively unit-tested per (mode, field, default) triple
- [ ] All tests fail (RED phase — no implementation exists yet)