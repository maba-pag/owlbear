---
id: 1050
title: 'C-05: RED — storage surface tests'
status: in-progress
priority: critical
created: 2026-04-21T10:42:50.277750+00:00
updated: 2026-04-21T13:41:34.550987+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by: jade-fern
claimed_at: 2026-04-21T13:41:34.550987+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.3, §8.6, §8.11
Module: `serve/kanban/tests/test_storage.py`

## Acceptance Criteria

- [ ] AC-C13: Written frontmatter follows C8.6 canonical order
- [ ] AC-C14: Pydantic `Task` model has `extra="allow"` (vendor archive fields survive)
- [ ] AC-C15: All timestamps written are ISO-8601 UTC with explicit `+00:00`
- [ ] AC-C16: `detect_corruption` on `tasks/` file containing `claimed_by` reports mode 3 with `detail="forbidden field claimed_by present"`; archive files exempt per AC-C48
- [ ] AC-C28: `move_to_quarantine` creates `quarantine/` directory if absent
- [ ] AC-C29: Quarantined file path: `quarantine/{original-filename}`
- [ ] AC-C30: AR task created by quarantine has tag `type:user-action` and body section `## Quarantined file` with `code`, path, detail
- [ ] AC-C48: Archive files containing `claimed_by` read successfully (field silently stripped); no CorruptionError, no MigrationRequiredError
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_storage_1050.py
- Classes:
  - `TestFromAC_Frontmatter` (AC-C13, AC-C14, AC-C15)
  - `TestFromAC_CorruptionDetection` (AC-C16)
  - `TestFromAC_Quarantine` (AC-C28, AC-C29)
  - `TestFromAC_QuarantineRepair` (AC-C30)
  - `TestFromAC_ArchiveExemption` (AC-C48)
- Tests per category: happy 10, edge 6, error 5, boundary 3
- Total: 24 tests, all FAIL (ModuleNotFoundError: No module named 'owlbear_kanban.storage')
- ruff: clean

### AC Coverage

| AC | Tests | Notes |
|----|-------|-------|
| AC-C13 | `test_written_frontmatter_fields_in_canonical_order`, `test_vendor_extra_fields_appear_after_canonical_fields` | Canonical §2.3 key order, vendor fields after canonical |
| AC-C14 | `test_task_model_accepts_vendor_extra_fields`, `test_vendor_extra_fields_survive_write_read_round_trip` | extra="allow" model + write/read round-trip |
| AC-C15 | `test_all_timestamp_fields_end_with_utc_offset`, `test_naive_timestamps_stored_with_utc_offset` | UTC +00:00, naive input converted |
| AC-C16 | `test_detect_corruption_claimed_by_in_tasks_dir`, `test_detect_corruption_claimed_by_detail_exact_string`, `test_detect_corruption_clean_task_returns_none`, `test_detect_corruption_archive_file_with_claimed_by_returns_none` | Mode 3 detection, exact detail string, negative, archive exempt |
| AC-C28 | `test_move_to_quarantine_creates_dir_when_absent`, `test_move_to_quarantine_no_error_when_dir_already_exists` | Dir created, idempotent |
| AC-C29 | `test_move_to_quarantine_returns_quarantine_subpath`, `test_move_to_quarantine_file_exists_at_returned_path`, `test_move_to_quarantine_source_file_removed`, `test_move_to_quarantine_preserves_file_content` | Path, existence, removal, content |
| AC-C30 | `test_repair_storage_ar_task_has_type_user_action_tag`, `test_repair_storage_ar_body_contains_quarantined_file_section`, `test_repair_storage_ar_body_has_code_path_detail_fields` | type:user-action tag, ## Quarantined file section, code+path+detail |
| AC-C48 | `test_archive_file_with_claimed_by_reads_without_exception`, `test_archive_claimed_by_stripped_from_returned_task`, `test_archive_claimed_by_does_not_raise_corruption_error`, `test_engine_init_with_archive_claimed_by_no_migration_error`, `test_archive_vendor_fields_preserved_when_claimed_by_stripped` | No error, stripped, no CorruptionError, no MigrationRequiredError, vendor preserved |

- Commit: fecac0d2