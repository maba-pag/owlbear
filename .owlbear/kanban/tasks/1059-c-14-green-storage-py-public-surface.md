---
id: 1059
title: 'C-14: GREEN — storage.py public surface'
status: todo
priority: critical
created: 2026-04-21T10:43:41.520550+00:00
updated: 2026-04-21T10:43:41.520550+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1050
- 1055
- 1056
- 1057
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §1, §8.3, §8.6, §8.11
Module: `serve/kanban/src/owlbear_kanban/storage.py`

Composes storage_io (#1055), body_parser (#1056), and corruption (#1057) into the public storage surface. Replaces old `task_io.py` responsibilities.

## Acceptance Criteria

- [ ] AC-C13: Written frontmatter follows C8.6 canonical field order
- [ ] AC-C14: Pydantic `Task` model has `extra="allow"` — vendor archive fields survive round-trip
- [ ] AC-C15: All timestamps written are ISO-8601 UTC with explicit `+00:00`
- [ ] AC-C16: `detect_corruption` on `tasks/` file containing `claimed_by` → mode 3 with `detail="forbidden field claimed_by present"`
- [ ] AC-C28: `move_to_quarantine` creates `quarantine/` directory if absent
- [ ] AC-C29: Quarantined file path: `quarantine/{original-filename}`
- [ ] AC-C30: AR task created by quarantine has tag `type:user-action` and body section `## Quarantined file` with `code`, path, detail
- [ ] AC-C48: Archive files with `claimed_by` read successfully (field silently stripped); no error raised
- [ ] `read_task`, `write_task`, `list_task_files`, `list_archive_files`, `move_to_quarantine` — public surface
- [ ] `task_io.py` removed; all imports redirected to `storage`
- [ ] All RED tests from C-05 (#1050) pass