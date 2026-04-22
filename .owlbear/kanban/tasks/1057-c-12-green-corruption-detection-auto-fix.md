---
id: 1057
title: 'C-12: GREEN — corruption detection & auto-fix'
status: review
priority: needed
created: 2026-04-21T10:43:21.218408+00:00
updated: 2026-04-22T06:33:49.188898+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1048
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief C (#1043) — paper-c.md §4, §8.4
Module: `serve/kanban/src/owlbear_kanban/corruption.py`

## Acceptance Criteria

- [ ] AC-C17: 9 ERR_CORRUPT_* modes implemented with positive detection for each
- [ ] AC-C18: `detect_corruption(file_path, location)` returns `CorruptionError` for each mode
- [ ] AC-C21: Each code is a `CorruptionError` subclass per C8.8 shape (`code`, `user_message`, `file_path`)
- [ ] AC-C22: Auto-fix matrix (§4.2) implemented — per (mode, field, default) triple
- [ ] 9 modes: missing-frontmatter, duplicate-id, forbidden-field, id-mismatch, missing-required-field, invalid-field-type, status-out-of-range, duplicate-location, orphan-archive-ref
- [ ] All RED tests from C-03 (#1048) pass
[[2026-04-22]]
## Test-Writer Notes
- Test file: tests/test_corruption_1057.py
- Classes: TestFromAC_ForbiddenFieldCode, TestFromAC_NineC12ModesExported
- Tests per category: happy 0, edge 0, error 4, boundary 2
- Total: 6 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests | Status |
|----|-------|--------|
| AC-C17 (9 modes, positive detection) | test_ac_c17_err_corrupt_forbidden_field_exported, test_ac_c17_forbidden_field_code_is_corruption_error_subclass, test_ac_c17_detect_corruption_returns_forbidden_field_for_claimed_by, test_ac_c17_all_nine_c12_mode_codes_exported | FAIL |
| AC-C21 (subclass shape) | test_ac_c21_c12_new_codes_are_corruption_error_subclasses | FAIL |
| AC-C22 (auto-fix matrix) | test_ac_c22_attempt_repair_forbidden_field_quarantines | FAIL |

### Implementation Note

The C-12 AC names 9 modes including "forbidden-field" (distinct from "missing-required-field") and "orphan-archive-ref" (9th mode). The current corruption.py uses ERR_CORRUPT_MISSING_FIELD for both the forbidden-field and missing-required-field cases, and has no ERR_CORRUPT_ORPHAN_ARCHIVE_REF code at all.

The builder must implement:
1. `ERR_CORRUPT_FORBIDDEN_FIELD` — new CorruptionError subclass code for the claimed_by detection case
2. `ERR_CORRUPT_ORPHAN_ARCHIVE_REF` — new CorruptionError subclass code for the 9th mode
3. `detect_corruption` must return ERR_CORRUPT_FORBIDDEN_FIELD (not ERR_CORRUPT_MISSING_FIELD) when claimed_by is present in a tasks/ file
4. `attempt_repair` must handle ERR_CORRUPT_FORBIDDEN_FIELD explicitly (quarantine, migration path)

Note: The C-03 test suite (serve/kanban/tests/test_corruption.py, 61 tests) currently asserts ERR_CORRUPT_MISSING_FIELD for the claimed_by case and passes. The builder should verify the AC intent — whether "forbidden-field" truly needs a separate code from "missing-required-field", or if C-12 AC is using informal aliases for the same C-03 codes. If the architect confirms the C-03 codes are authoritative, the C-12 test file should be revised to remove the FORBIDDEN_FIELD assertions.
[[2026-04-22]]
## Builder Notes
- Implementation files changed: serve/kanban/src/owlbear_kanban/corruption.py, serve/kanban/src/owlbear_kanban/storage.py.
- Implemented new code classes ERR_CORRUPT_FORBIDDEN_FIELD and ERR_CORRUPT_ORPHAN_ARCHIVE_REF as CorruptionError subclasses.
- detect_corruption now returns ERR_CORRUPT_FORBIDDEN_FIELD for non-null claimed_by in tasks files.
- attempt_repair now explicitly handles ERR_CORRUPT_FORBIDDEN_FIELD with quarantine migration path.
- Added a narrow compatibility mapping in read_task so targeted reads preserve legacy ERR_CORRUPT_MISSING_FIELD behavior for claimed_by corruption while direct corruption detection uses ERR_CORRUPT_FORBIDDEN_FIELD.

Verification evidence:
- quality-runner scoped RED before implementation on tests/test_corruption_1057.py: 6 failed, ruff clean.
- quality-runner scoped GREEN after implementation on tests/test_corruption_1057.py and serve/kanban/tests/test_corruption.py: 67 passed, 0 failed.
- lint status: clean on changed files.
- coverage on owlbear_kanban.corruption in scoped run: 85 percent.

Post-task reflection:
- Main risk was contract drift between new C-12 mode naming and existing read_task mode-3 expectations.
- Workaround was to keep the new detect_corruption contract and adapt read_task at the boundary for backward compatibility.
- Useful pattern: introducing new corruption codes can require boundary-layer compatibility shims where legacy call sites assert historical code names.
- Time sink was reconciling transient task-scoped AC tests with durable module-level regression expectations.
- Quality gap: durable coverage for corruption module remains below 90 percent in scoped verification, despite passing regressions.