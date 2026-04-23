---
id: 1055
title: 'C-10: GREEN — storage_io atomic-write & ID-allocation'
status: todo
priority: needed
created: 2026-04-21T10:43:21.197242+00:00
updated: 2026-04-21T10:43:21.197242+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1046
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §3, §8.1, §8.11
Module: `serve/kanban/src/owlbear_kanban/storage_io.py`

## Acceptance Criteria

- [ ] AC-C1: `atomic_write(target, content)` — mkstemp `.tmp-*` sibling, fsync file, os.replace, fsync parent dir (POSIX)
- [ ] AC-C2: Exception-path cleanup — `.tmp-*` removed, target unaffected
- [ ] AC-C3: `list_task_files` / `list_archive_files` filter `.tmp-*` and `.<id>.lock` files
- [ ] AC-C4: `allocate_next_id` — flock-based `.next_id.lock` read+increment+save sequence
- [ ] AC-C4a: `write_task_if_unchanged` — CAS with per-task `.<id>.lock`, raises `ConcurrencyError(code="ERR_STALE")` on mismatch
- [ ] AC-C4b: Lock file hygiene — `tasks/.<id>.lock` and `archive/.<id>.lock`, gitignored, excluded from list/quarantine
- [ ] AC-C51: ID burn safety — allocate reserves before write; crash wastes 1 ID, no duplicate
- [ ] All RED tests from C-01 (#1046) pass