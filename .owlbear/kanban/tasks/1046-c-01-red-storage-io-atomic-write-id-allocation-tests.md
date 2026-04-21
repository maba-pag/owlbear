---
id: 1046
title: 'C-01: RED — storage_io atomic-write & ID-allocation tests'
status: todo
priority: needed
created: 2026-04-21T10:42:50.236472+00:00
updated: 2026-04-21T13:03:26.381022+00:00
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
claimed_at: 2026-04-21T13:03:26.381022+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.1, §8.11
Module: `serve/kanban/tests/test_storage_io.py`

## Acceptance Criteria

- [ ] AC-C1: `atomic_write(target, content)` writes to `.tmp-*` sibling, fsyncs, replaces, fsyncs parent dir on POSIX
- [ ] AC-C2: `atomic_write` cleans up `.tmp-*` on exception; target unaffected. Simulated `os.replace` failure
- [ ] AC-C3: `list_task_files` filters out `.tmp-*` files
- [ ] AC-C4: `allocate_next_id` holds `.next_id.lock` during read+increment+save. Concurrent test: 50 threads × 1 ID → 50 distinct IDs
- [ ] AC-C4a: `write_task_if_unchanged` CAS test: 20 threads racing → exactly 1 success, 19 `ERR_STALE`; survivor write intact
- [ ] AC-C4b: Lock files at `tasks/.<id>.lock`, gitignored, never returned by `list_task_files`/`list_archive_files`, never quarantined
- [ ] AC-C51: ID burn on crash: simulate crash between `save_config` and `write_task` → next `create_task` allocates `original_next_id + 2`
- [ ] All tests fail (RED phase — no implementation exists yet)