---
id: 1122
title: 'GREEN: fix archived-task edit persistence'
status: research
priority: important
created: 2026-04-24T23:20:30.734062+00:00
updated: 2026-04-24T23:20:30.734062+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent:
depends_on:
- 1121
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — extends #1120 research.
Module: `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`

Fix the archived-task edit persistence path so edits to tasks in `archive/` are read from and written back to the archive directory.

## Acceptance Criteria

- [ ] Core `edit_task` finds archived task files via `_find_task_path` archive fallback
- [ ] `write_task` accepts optional `target_dir` param (defaults to `tasks/` for backwards compat)
- [ ] Edited archived task file is written to `archive/` dir, not `tasks/`
- [ ] No duplicate file created in `tasks/`
- [ ] All tests from RED task pass (GREEN phase)
- [ ] Existing 26 tests in `test_engine_create_edit_1070.py` still pass (regression)
- [ ] ruff clean on changed files
