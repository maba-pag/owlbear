---
id: 1061
title: 'C-16: GREEN — kanban-migrate entry point'
status: todo
priority: important
created: 2026-04-21T10:44:12.239610+00:00
updated: 2026-04-21T10:44:12.239610+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1052
- 1059
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §5, §8.7, §8.11
Module: `serve/kanban/src/owlbear_kanban/migrate.py`
Entry point: `kanban-migrate` registered in `serve/kanban/pyproject.toml`

Depends on storage surface (#1059) for atomic_write, read_task, write_task, frontmatter canonicalisation.

## Acceptance Criteria

- [ ] AC-C31: `uv run kanban-migrate` registered as console script in `serve/kanban/pyproject.toml`
- [ ] AC-C32: `--lane tasks|archive|config|all` runs only selected lane; `--lane all` runs all three
- [ ] AC-C33: Per-lane algorithms match §5.3 (tasks, archive) and §5.4 (config) exactly
- [ ] AC-C34: Idempotency — re-running on fully migrated board reports `Migrated: 0`
- [ ] AC-C35: Idempotency checks follow lane-specific rules (contract-critical archive fields, canonical active-task fields)
- [ ] AC-C36: `--dry-run` writes nothing; only prints actions
- [ ] AC-C37: Crash mid-migration leaves no partial files (uses atomic_write); resume converges
- [ ] AC-C38: Exit code 1 if any file failed; 0 otherwise
- [ ] AC-C38a: When `config`/`archive` lanes leave unresolved manual work, emit manual-action summary for `type:user-action` tasks
- [ ] All RED tests from C-07 (#1052) pass