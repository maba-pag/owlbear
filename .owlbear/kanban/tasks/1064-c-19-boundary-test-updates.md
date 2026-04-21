---
id: 1064
title: 'C-19: Boundary test updates'
status: todo
priority: important
created: 2026-04-21T10:44:21.882195+00:00
updated: 2026-04-21T10:44:21.882195+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1059
- 1062
- 1063
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §8.10
Modules: `tests/test_package_boundary.py`, `tests/test_deny_code_writes.py`

Last task — updates existing workspace-level boundary tests to reflect the new storage module structure after all Brief C implementation is complete.

## Acceptance Criteria

- [ ] AC-C45: `tests/test_package_boundary.py` enforces: no engine code imports from `task_io` (deleted); only `engine.py` may import from `storage`
- [ ] AC-C46: `tests/test_deny_code_writes.py` extension: storage tests prohibited from writing outside `tmp_path`
- [ ] Boundary tests pass with the new module layout (storage.py, storage_io.py, body_parser.py, activity_store.py, corruption.py, migrate.py, predicates.py)
- [ ] No import of removed `task_io` module anywhere in the codebase