---
id: 1053
title: 'C-08: RED — engine storage-integration tests'
status: in-progress
priority: needed
created: 2026-04-21T10:42:50.306120+00:00
updated: 2026-04-21T17:14:24.324336+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
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
[[2026-04-21]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_storage.py
- Classes: TestFromAC_ListTasksCorruption, TestFromAC_Sweep, TestFromAC_RepairStorage, TestFromAC_MigrationGate, TestFromAC_ParseDuration, TestFromAC_ARCreationSignature
- Context: 20 previously committed tests were already GREEN (implementation was complete). Audited all AC coverage and found two genuine gaps in AC-C19: `list_tasks()` has no mode-6 (id-filename mismatch) or mode-9 (invalid priority) checks — both classes of corrupt files pass through silently instead of being skipped. Added 2 failing tests targeting these gaps.
- Tests per category: happy 6, edge 8, error 6, boundary 2
- Total: 22 tests — 20 PASS (existing GREEN), 2 FAIL (new RED)
- New failing tests:
  - test_ac_c19_list_tasks_skips_mode6_id_filename_mismatch — FAIL (mode 6 not filtered)
  - test_ac_c19_list_tasks_skips_mode9_invalid_priority — FAIL (mode 9 not filtered)
- ruff: clean
- AC coverage: C19 (now fully covered incl. modes 6+9), C20, C23, C24, C25, C26, C27, C47, C49, C50, C52, C54 — all covered