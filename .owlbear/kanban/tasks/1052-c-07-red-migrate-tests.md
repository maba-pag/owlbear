---
id: 1052
title: 'C-07: RED — migrate tests'
status: todo
priority: important
created: 2026-04-21T10:42:50.297290+00:00
updated: 2026-04-21T13:03:33.776325+00:00
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
claimed_at: 2026-04-21T13:03:33.776325+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.7, §8.11
Module: `serve/kanban/tests/test_migrate.py`

## Acceptance Criteria

- [ ] AC-C31: `uv run kanban-migrate` registered in `serve/kanban/pyproject.toml`
- [ ] AC-C32: `kanban-migrate --lane tasks|archive|config|all` runs only the selected lane; `--lane all` runs all three
- [ ] AC-C33: Per-lane algorithms for `tasks`, `archive`, `config` match §5.3 and §5.4 exactly
- [ ] AC-C34: Idempotency: re-running on fully migrated board reports `Migrated: 0`
- [ ] AC-C35: Idempotency checks follow lane-specific rules including contract-critical archive fields and canonical active-task fields
- [ ] AC-C36: `--dry-run` writes nothing; only prints
- [ ] AC-C37: Crash mid-migration leaves no partial files; resume converges (atomic_write primitive)
- [ ] AC-C38: Exit code 1 if any file failed; 0 otherwise
- [ ] AC-C38a: When `config`/`archive` lanes leave unresolved manual work, emits manual-action summary for `type:user-action` tasks
- [ ] All tests fail (RED phase — no implementation exists yet)