---
id: 1338
title: 'Fix migration/storage suites: prove old-to-new schema round-trip before sync'
status: in-progress
priority: needed
created: 2026-05-04T15:00:05.755705+00:00
updated: 2026-05-04T15:47:16.361069+00:00
tags:
- sync-blocker
- kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Storage now emits grouped schema (storage.py L171–174) but migration and compatibility tests are red. Must prove old-format boards can be read/migrated without data loss before syncing to main.

## Acceptance Criteria

1. test_migrate.py passes (all migration tests green)
2. test_storage_1050.py passes (storage compat tests green)
3. test_storage.py passes (core storage tests green)
4. test_engine_atomicity_1104.py passes (atomicity with new schema green)
5. Round-trip test: old-format board → engine loads → saves → old-format reader can still parse (or explicit migration converts cleanly)

## Key Files

- `serve/kanban/src/owlbear_kanban/storage.py`
- `serve/kanban/src/owlbear_kanban/migrate.py`
- `serve/kanban/tests/test_storage_1050.py`
- `serve/kanban/tests/test_storage.py`
- `serve/kanban/tests/test_migrate.py`

## Source

Finding 3 in `.owlbear/research/kanban-mcp-deployment-audit.md`
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_schema_roundtrip_1338.py
- Classes: TestFromAC_SchemaRoundTrip, TestFromAC_ArchiveClaimedByStripping, TestFromAC_TimestampRoundTrip
- Tests per category: happy 0, edge 2, error 2, boundary 3 (all contract-level round-trip proofs)
- Total: 7 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC 5 (round-trip) | test_full_round_trip_timestamps_unquoted_in_written_file, test_full_round_trip_task_data_preserved_after_migrate_and_write |
| AC 5 / AC-C48 (archive claimed_by stripping) | test_archive_read_task_claimed_by_stripped_to_none, test_archive_read_task_claimed_by_not_in_model_extra |
| AC 5 / AC-C15 (timestamp format) | test_write_task_timestamp_line_ends_with_utc_offset, test_write_task_naive_timestamp_stored_with_utc_offset_unquoted, test_write_task_non_utc_timestamp_converted_unquoted |

Root causes proven failing:
1. write_task wraps timestamps in single quotes so `line.rstrip().endswith('+00:00')` is False (line ends with `'`)
2. read_task on archive files does NOT strip claimed_by — it leaks through Task.extra='allow' returning 'some-agent' instead of None

ACs 1–4 already have failing tests in the existing suites (test_migrate.py, test_storage_1050.py, test_storage.py, test_engine_atomicity_1104.py). Those 13 failures are the builder's fix targets.