---
id: 1053
title: 'C-08: RED — engine storage-integration tests'
status: todo
priority: needed
created: 2026-04-21T10:42:50.306120+00:00
updated: 2026-04-21T13:03:37.801329+00:00
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
claimed_at: 2026-04-21T13:03:37.801329+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.4, §8.5, §8.11
Module: `serve/kanban/tests/test_engine_storage.py`

## Acceptance Criteria

- [ ] AC-C19: `list_tasks` SKIPS files failing modes 1, 3-9 silently
- [ ] AC-C20: `list_tasks` HARD-RAISES `CorruptionError(code="ERR_CORRUPT_DUPLICATE_ID")` for mode 2
- [ ] AC-C23: `sweep()` returns `list[int]` of released claim IDs only
- [ ] AC-C24: `repair_storage()` quarantines corrupt files via §4.4 sequence; file moved BEFORE AR creation attempt
- [ ] AC-C25: `repair_storage()` records `RepairOutcome(action="failed")` if AR creation fails; file remains quarantined
- [ ] AC-C26: `repair_storage()` resolves `ERR_CORRUPT_DUPLICATE_LOCATION` by archive-wins
- [ ] AC-C27: `sweep()` reconciles claim timeouts independently of corruption repair
- [ ] AC-C47: `KanbanEngine.__init__` raises `MigrationRequiredError(code="ERR_MIGRATION_REQUIRED")` if any `tasks/` file contains `claimed_by`
- [ ] AC-C49: `_parse_duration("30m")` returns `timedelta(minutes=30)`; malformed inputs raise `ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT")`
- [ ] AC-C50: `BoardConfig` validation calls `_parse_duration(claim_timeout)` at config load time (eager validation)
- [ ] AC-C52: `sweep()` releasing expired claim does NOT mutate task body; only `claimed_at` cleared and `updated` advanced
- [ ] AC-C54: AR creation by `repair_storage()` uses `body=str` (markdown), no `status` argument; verify against Brief B `create_task` signature
- [ ] All tests fail (RED phase — no implementation exists yet)