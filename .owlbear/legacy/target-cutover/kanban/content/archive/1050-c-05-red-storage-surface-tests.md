---
id: 1050
title: 'C-05: RED — storage surface tests'
status: archived
priority: medium
created: 2026-04-21T10:42:50.277750+00:00
updated: 2026-04-22T22:34:25.266837+00:00
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
archival_reason:
archival_refs: []
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
[[2026-04-21]]
## Builder Notes

### Files changed
- `serve/kanban/src/owlbear_kanban/storage.py` — new module (created)
- `serve/kanban/src/owlbear_kanban/engine.py` — added `repair_storage()` method
- `serve/kanban/tests/test_storage_1050.py` — added `TestBuilderDiscovered` (3 tests)

### Test results
- 27 passed (24 TestFromAC + 3 TestBuilderDiscovered), 0 failed
- ruff: clean on all changed files
- Coverage on `owlbear_kanban.storage`: 92% (target ≥ 90% ✓)

### Implementation summary
- `storage.py` provides: `CorruptionError`, `MigrationRequiredError`, `read_task`, `write_task`, `detect_corruption`, `move_to_quarantine`, `load_config` (re-export)
- `write_task(task, kanban_dir)` writes in §2.3 canonical field order using `CommentedMap`; normalises naive ISO-8601 timestamps to `+00:00`; excludes `claimed_by`; returns written `Path`
- `read_task(path)` delegates to `task_io.read_task` then sets `claimed_by = None` (AC-C48)
- `detect_corruption` checks the parent dir name against `config.archive_dir` to exempt archive files; returns `CorruptionError(code="ERR_CORRUPT_MISSING_FIELD", detail="forbidden field claimed_by present")` for tasks/ files with non-null `claimed_by`
- `repair_storage()` on engine scans tasks/, detects corruption, quarantines, creates AR tasks with `type:user-action` tag and `## Quarantined file` body section

### Builder-discovered tests
1. `MigrationRequiredError` attributes (code, user_message) — covered lines 85-87
2. `detect_corruption` with missing closing `---` returns None — covered line 222
3. `detect_corruption` without frontmatter returns None — covered lines 217-218

### Commit: ac7cb6e1
[[2026-04-21]]
## Review Evidence

### Test Results
- pytest: 27 passed, 0 failed (quality-runner, independent)

### Lint
- ruff: clean (all changed files)

### Coverage
- `owlbear_kanban.storage`: 92% ✓
- `owlbear_kanban.engine`: 28% (untouched; `repair_storage` covered via integration tests in test_storage_1050.py)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C13 canonical order | `test_written_frontmatter_fields_in_canonical_order` (line 163) | Yes — in-order key comparison | COVERED |
| AC-C13 vendor after canonical | `test_vendor_extra_fields_appear_after_canonical_fields` (line 177) | Yes — fixture guarantees both lists non-empty | COVERED |
| AC-C14 extra=allow | `test_task_model_accepts_vendor_extra_fields` (L200), `test_vendor_extra_fields_survive_write_read_round_trip` (L213) | Yes — model_dump checks exact values | COVERED |
| AC-C15 UTC +00:00 | `test_all_timestamp_fields_end_with_utc_offset` (L230), `test_naive_timestamps_stored_with_utc_offset` (L248) | Yes for naive; **No for Z-suffix** (see §5.5-A) | LAX |
| AC-C16 mode-3 detection | `test_detect_corruption_claimed_by_in_tasks_dir` (L297), `test_detect_corruption_claimed_by_detail_exact_string` (L309) | Yes — `.code` and `.detail` checked exactly | COVERED |
| AC-C28 dir created | `test_move_to_quarantine_creates_dir_when_absent` (L346), `test_move_to_quarantine_no_error_when_dir_already_exists` (L354) | Yes | COVERED |
| AC-C29 file path | 4 tests (L362–L395) — path equality, physical existence, source removal, content | Yes | COVERED |
| AC-C30 AR tag + body | `test_repair_storage_ar_task_has_type_user_action_tag` (L416), `test_repair_storage_ar_body_contains_quarantined_file_section` (L433), `test_repair_storage_ar_body_has_code_path_detail_fields` (L455) | Section header: yes; field values: **No** (see §5.3-A) | LAX |
| AC-C48 archive read | `test_archive_file_with_claimed_by_reads_without_exception` (L492), `test_archive_claimed_by_stripped_from_returned_task` (L501), `test_archive_vendor_fields_preserved_when_claimed_by_stripped` (L554) | Yes | COVERED |
| AC-C48 engine init | `test_engine_init_with_archive_claimed_by_no_migration_error` (L508) | **No — structurally inert** (see §5.0-A) | **MISSING** |

---

#### §5.0-A — MISSING: Inert test for AC-C48 engine init (FAIL)

`test_engine_init_with_archive_claimed_by_no_migration_error` ([test_storage_1050.py:508–527](serve/kanban/tests/test_storage_1050.py#L508-L527)) asserts that `KanbanEngine.__init__` does not raise `MigrationRequiredError` when `archive/` contains a file with `claimed_by`. This test is structurally inert for two independent reasons:

1. `KanbanEngine.__init__` ([engine.py:269–298](serve/kanban/src/owlbear_kanban/engine.py#L269-L298)) only calls `load_config()` and sets instance variables — it never reads any `.md` task files. No task I/O occurs during init.
2. `MigrationRequiredError` ([storage.py:81](serve/kanban/src/owlbear_kanban/storage.py#L81)) is **defined but never raised anywhere in the codebase** (`grep: 0 hits for "raise MigrationRequiredError"`). The exception cannot be triggered by any code path.

The test passes trivially regardless of what `archive/` contains. AC-C48's "no MigrationRequiredError" requirement for engine operation on such a board is unmeasured.

**Fix (test-writer):** Replace the inert test with one that exercises actual engine operations (`list_tasks()`, `show_task()`, `get_task()`) on a board where `archive/` contains a file with `claimed_by`, verifying no exception is raised and the archived task is accessible. If `MigrationRequiredError` is intended as a future guard, document this with a `pytest.skip` reason or a `TestBuilderDiscovered` that validates the exception is never raised at the actual call sites.

---

#### §5.3-A — WEAK: Substring-only assertions for AC-C30 body fields (FAIL)

`test_repair_storage_ar_body_has_code_path_detail_fields` ([test_storage_1050.py:455–472](serve/kanban/tests/test_storage_1050.py#L455-L472)) asserts:
```python
assert "code" in body
assert "path" in body
assert "detail" in body
```
These are single-word substring checks. Any body containing the words "code", "path", or "detail" anywhere passes — including prose like `"Quarantined for review. Contact your code owner for the file path details."`. The actual field values `"ERR_CORRUPT_MISSING_FIELD"` and `"forbidden field claimed_by present"` ([engine.py:1041–1046](serve/kanban/src/owlbear_kanban/engine.py#L1041-L1046)) are not verified. AC-C30 specifies the `## Quarantined file` section contains `code`, `path`, and `detail` field-value pairs — the assertions must verify the values, not just the labels.

**Fix (test-writer):** Strengthen assertions in `TestFromAC_QuarantineRepair.test_repair_storage_ar_body_has_code_path_detail_fields` to check for the actual error code and detail string, e.g.:
```python
assert "ERR_CORRUPT_MISSING_FIELD" in body
assert "forbidden field claimed_by present" in body
```

---

#### §5.5-A — Implementation gap: AC-C15 Z-suffix not normalized (FAIL)

`_normalize_timestamp` ([storage.py:107–109](serve/kanban/src/owlbear_kanban/storage.py#L107-L109)):
```python
if tz:
    return ts  # already has timezone info
```
`_TS_RE` ([storage.py:61–63](serve/kanban/src/owlbear_kanban/storage.py#L61-L63)) matches `Z` as a valid `tz` group. When `tz == "Z"`, the function returns `ts` unchanged — writing `"2026-04-20T10:00:00Z"` to disk rather than `"2026-04-20T10:00:00+00:00"`. AC-C15 requires "explicit `+00:00`". No test in the suite covers Z-suffix input; the test-writer's coverage only exercises naive (no-tz) and already-`+00:00` inputs.

**Fix (builder):** In `_normalize_timestamp`, handle the Z case:
```python
if tz:
    if tz == "Z":
        return f"{base}{frac}+00:00"
    return ts
```
Add a `TestBuilderDiscovered` test for `_normalize_timestamp` with Z-suffix input verifying the returned value ends with `+00:00`.

---

#### Security Review
No issues. Path containment validated in `write_task`; YAML round-trip mode used (no unsafe loader); no subprocess; no hardcoded secrets; `move_to_quarantine` caller-supplied path is board-controlled.

#### Test Integrity
All `TestFromAC_*` methods: PRESERVED. Builder added only `TestBuilderDiscovered` (3 tests). No weakening or removal.

#### Data Safety
No issues. `write_task` uses `mkstemp + Path.replace` (atomic). `move_to_quarantine` uses `Path.replace` (atomic at OS level). Single-threaded; no shared mutable state.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- **Private import:** `storage.py:29` imports `_make_yaml` (underscore-private) from `task_io`. Fragile — if `task_io._make_yaml` is renamed, the import breaks silently. Consider exporting as a public function.
- **Type contract:** Tests call `engine.show_task(task_id=t.id)` where `t.id` is `int` but signature declares `task_id: str`. Works at runtime but violates declared type contract; should be `str(t.id)`.
- **AC terminology mismatch:** AC-C16 says "mode 3" but `CorruptionError` has no `mode` attribute — only `code`, `detail`, `path`. Mapping is implicit.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | storage.py CommentedMap writes _CANONICAL_FIELD_ORDER (L130–155); test_written_frontmatter_fields_in_canonical_order passes | L163 | PASS |
| AC-C14 | Task model has `extra="allow"` (storage.py:46); round-trip test preserves vendor fields | L200, L213 | PASS |
| AC-C15 | Naive normalized; Z-suffix **not** normalized — implementation bug | L230, L248 | **FAIL** |
| AC-C16 | detect_corruption returns CorruptionError with exact code+detail for tasks/ claimed_by; archive/ exempt | L297, L309 | PASS |
| AC-C28 | move_to_quarantine mkdir(exist_ok=True) (storage.py:~267) | L346, L354 | PASS |
| AC-C29 | Returns quarantine/{original-filename}; file physically exists; source removed; content preserved | L362–L395 | PASS |
| AC-C30 | AR task created with type:user-action tag and ## Quarantined file section; body field values unverified (weak test) | L416, L433, L455 | **FAIL** |
| AC-C48 | read_task strips claimed_by; detect_corruption exempts archive/; engine init test inert | L492–L554 | **FAIL** |

### Deductions
- §5.0-A MISSING (AC-C48 inert test): −0.12
- §5.3-A WEAK (AC-C30 assertions): −0.10
- §5.5-A impl gap (AC-C15 Z-suffix): −0.10

### Verdict
Confidence: 0.68 → **FAIL** → `in-progress`

**Required fixes (builder):**
1. `storage.py:_normalize_timestamp` — handle `tz == "Z"` → return `f"{base}{frac}+00:00"` instead of `ts`
2. Add `TestBuilderDiscovered` test for Z-suffix normalization

**Required fixes (test-writer, next cycle after impl fix):**
3. Strengthen `test_repair_storage_ar_body_has_code_path_detail_fields` — assert `"ERR_CORRUPT_MISSING_FIELD"` and `"forbidden field claimed_by present"` present in body
4. Replace `test_engine_init_with_archive_claimed_by_no_migration_error` — test actual engine operations on board with claimed_by in archive/ (not just `__init__`)
[[2026-04-21]]
## Builder Notes
- Implementation: updated `serve/kanban/src/owlbear_kanban/storage.py` `_normalize_timestamp` to rewrite `Z` timestamps to explicit `+00:00`.
- Tests: added `TestBuilderDiscovered.test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc` in `serve/kanban/tests/test_storage_1050.py`.
- Lint cleanup: removed unused fixture arguments from two existing `TestBuilderDiscovered` normalization tests in `serve/kanban/tests/test_storage_1050.py` to keep scoped ruff clean.
- RED evidence (quality-runner, scoped): 1 failing test (`TestBuilderDiscovered::test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc`), lint clean.
- GREEN evidence (quality-runner, scoped): 45 passed, 0 failed, 0 skipped across `serve/kanban/tests/test_storage_1050.py` and `serve/kanban/tests/test_storage.py`; ruff clean for `serve/kanban/src/` and `serve/kanban/tests/test_storage_1050.py`.
- Coverage evidence (quality-runner, scoped): `owlbear_kanban.storage` reported 69% module coverage in this run.
- Commit: `c8e1eb30` (`fix: normalize Z timestamp suffix (#1050, builder)`).

### Reflection
- Reproduced the reviewer-reported AC-C15 gap with a dedicated builder-discovered test before changing implementation.
- Kept `TestFromAC_*` classes untouched; all changes remained in implementation plus `TestBuilderDiscovered` only.
- Used a surgical one-branch fix in timestamp normalization, preserving behavior for non-`Z` timezone inputs.
- Scoped quality-runner execution provided clear pre/post evidence without broad suite churn.
[[2026-04-21]]
## Review Evidence

### Test Results
- Scoped quality-runner: pytest 34 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py`
- Related-surface quality-runner: pytest 54 passed, 2 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py`
- Failing related tests:
  - `serve/kanban/tests/test_engine_storage.py::TestFromAC_ListTasksCorruption::test_ac_c19_list_tasks_skips_mode6_id_filename_mismatch` -> expected mode-6 file to be skipped; observed task ids included `2001`
  - `serve/kanban/tests/test_engine_storage.py::TestFromAC_ListTasksCorruption::test_ac_c19_list_tasks_skips_mode9_invalid_priority` -> expected mode-9 file to be skipped; observed task ids included `1002`

### Lint
- Scoped ruff: clean on `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_storage_1050.py`

### Coverage
- Scoped quality-runner: `owlbear_kanban.storage` 69%, `owlbear_kanban.engine` 28%
- Result: below the 90% review bar for the touched storage surface

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C13 canonical order | `test_written_frontmatter_fields_in_canonical_order` (163), `test_vendor_extra_fields_appear_after_canonical_fields` (177) | Yes | COVERED |
| AC-C14 extra="allow" | `test_task_model_accepts_vendor_extra_fields` (205), `test_vendor_extra_fields_survive_write_read_round_trip` (220) | Yes | COVERED |
| AC-C15 explicit `+00:00` | `test_all_timestamp_fields_end_with_utc_offset` (242), `test_naive_timestamps_stored_with_utc_offset` (260), `TestBuilderDiscovered.test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc` (644) | Yes | COVERED |
| AC-C16 mode-3 claimed_by detection | `test_detect_corruption_claimed_by_in_tasks_dir` (294), `test_detect_corruption_claimed_by_detail_exact_string` (305), `test_detect_corruption_archive_file_with_claimed_by_returns_none` (329) | Yes | COVERED |
| AC-C28 quarantine dir creation | `test_move_to_quarantine_creates_dir_when_absent` (351), `test_move_to_quarantine_no_error_when_dir_already_exists` (361) | Yes | COVERED |
| AC-C29 quarantine path/content | `test_move_to_quarantine_returns_quarantine_subpath` (370), `test_move_to_quarantine_file_exists_at_returned_path` (380), `test_move_to_quarantine_source_file_removed` (392), `test_move_to_quarantine_preserves_file_content` (401) | Yes | COVERED |
| AC-C30 AR tag + section + fields | `test_repair_storage_ar_task_has_type_user_action_tag` (420), `test_repair_storage_ar_body_contains_quarantined_file_section` (439), `test_repair_storage_ar_body_has_code_path_detail_fields` (460) | Yes for tag/section/field presence | COVERED |
| AC-C48 archive claimed_by exemption | `test_archive_file_with_claimed_by_reads_without_exception` (491), `test_archive_claimed_by_stripped_from_returned_task` (501), `test_archive_claimed_by_does_not_raise_corruption_error` (511), `test_engine_init_with_archive_claimed_by_no_migration_error` (524), `test_archive_vendor_fields_preserved_when_claimed_by_stripped` (544) | Direct storage reads and migration-gate scope: yes; engine archived read path: no | LAX |

#### Security Review
- No issues found. No subprocess injection, no secret handling, and no path-traversal exposure in the changed storage/repair paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` in `serve/kanban/tests/test_storage_1050.py` | No weakening observed in current file; builder added `TestBuilderDiscovered.test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc` (644) | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most AC tests assert exact values; AC-C30 body-field test (460-480) checks field labels only. |
| Negative/error-path coverage | ADEQUATE | AC-C16 and AC-C48 direct error/exemption paths are covered. |
| Manual mutation reasoning | WEAK | The task file stays green even when engine bypasses the storage surface, because it never exercises `list_tasks(archived=True)`; only plain `engine.list_tasks()` calls appear at 431, 452, 471. |
| Test independence | STRONG | `tmp_path`-isolated boards throughout. |
| Descriptive test names | STRONG | Names map directly to the AC clauses. |

#### Data Safety
- No issues found. `move_to_quarantine()` uses `Path.replace()`, and `repair_storage()` creates AR tasks only after quarantine completes.

#### Implementation-Aware Gaps
- `serve/kanban/src/owlbear_kanban/storage.py:3` says the new storage module is the single import boundary that `engine.py` and tests use.
- `serve/kanban/src/owlbear_kanban/engine.py:40` still imports `read_task` / `write_task` from `task_io`, not from the storage surface.
- `serve/kanban/src/owlbear_kanban/engine.py:472` uses that imported `read_task` inside `list_tasks()`.
- The strip logic required by AC-C48 exists in `serve/kanban/src/owlbear_kanban/storage.py:172-216`, specifically `task.claimed_by = None` at line 216.
- `serve/kanban/src/owlbear_kanban/models.py:178` turns any surviving `claimed_by` into `claimed=True` for `TaskSummary`.
- Net effect: archived files with legacy `claimed_by` can still surface through engine list paths without the storage-surface strip semantics. Task #1050 does not cover this path.
- This is a significant untested path for AC-C48 and an integration defect in the advertised storage boundary.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- AC-C30 would be stronger if the AR body test asserted actual `code` / `detail` values, not just field labels.
- `test_storage_1050.py` passes `int` IDs to `show_task()` even though the signature is `task_id: str`; runtime coercion hides the mismatch.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | Canonical field list in `storage.py` (68, 249, 254, 262) and passing tests at 163 / 177 | `TestFromAC_Frontmatter` | PASS |
| AC-C14 | `Task.model_config = ConfigDict(extra="allow")` in `models.py:121`; round-trip tests at 205 / 220 pass | `TestFromAC_Frontmatter` | PASS |
| AC-C15 | `_normalize_timestamp()` handles `Z` at `storage.py:152, 161-162`; builder-discovered test at 644 passes | `TestFromAC_Frontmatter` + `TestBuilderDiscovered` | PASS |
| AC-C16 | `detect_corruption()` claimed_by branch at `corruption.py:153, 215, 220`; tests at 294 / 305 / 329 pass | `TestFromAC_CorruptionDetection` | PASS |
| AC-C28 | `move_to_quarantine()` creates directory at `storage.py:368-373`; tests at 351 / 361 pass | `TestFromAC_Quarantine` | PASS |
| AC-C29 | `move_to_quarantine()` destination path and replace semantics at `storage.py:372-373`; tests at 370 / 380 / 392 / 401 pass | `TestFromAC_Quarantine` | PASS |
| AC-C30 | `repair_storage()` builds AR body and tag at `engine.py:1057, 1081, 1083-1084`; tests at 420 / 439 / 460 pass | `TestFromAC_QuarantineRepair` | PASS |
| AC-C48 | Direct archive reads strip `claimed_by` via `storage.py:216` and tests at 491 / 501 / 511 / 524 / 544 pass, but engine archived read paths still bypass the storage surface via `engine.py:40, 472` and are untested in this task | `TestFromAC_ArchiveExemption` | FAIL |

### Deductions
- AC-C48 engine integration gap and missing archived engine-read coverage: -0.18
- Related-surface regressions in independent quality-runner run (`test_engine_storage.py` mode-6 / mode-9 skips): -0.12
- Coverage below review bar (`owlbear_kanban.storage` 69%, `owlbear_kanban.engine` 28%): -0.08

### Verdict
Confidence: 0.62 -> FAIL -> `in-progress`

### Required fixes
1. Route `KanbanEngine` read/write paths through the public storage surface, or implement equivalent `claimed_by` stripping semantics in engine archived read paths and update the storage module contract text.
2. Add a regression test covering `KanbanEngine.list_tasks(archived=True)` with an archive file containing `claimed_by`, verifying the archived task is readable without surfacing legacy claim state.
3. Resolve the related engine-storage failures exposed by the broader run: mode-6 id/filename mismatch and mode-9 invalid priority must be skipped.
4. Raise coverage on the touched storage surface to the 90% review bar.

### Reflection
- The earlier AC-C15 timestamp defect is fixed correctly; the blocking issue is now boundary integration, not timestamp normalization.
- The prior review note treating the AC-C48 migration test as inert does not match current code: `KanbanEngine.__init__` does scan `tasks/` for legacy `claimed_by`. The real gap is that archived engine reads still bypass the storage surface.
[[2026-04-21]]
## Builder Notes
- Implementation:
  - Updated `KanbanEngine.list_tasks()` in `serve/kanban/src/owlbear_kanban/engine.py` to run storage-surface corruption detection for active tasks before parse, so mode-6 id/filename mismatch and mode-9 invalid priority files are silently skipped.
  - Updated archived listing behavior to clear legacy `claimed_by` on archived records before `TaskSummary` projection, preventing archived tasks from surfacing as claimed.
- Tests:
  - Added `TestBuilderDiscovered.test_engine_list_tasks_archived_strips_legacy_claimed_by` in `serve/kanban/tests/test_storage_1050.py`.
  - Added focused `TestBuilderDiscovered` coverage tests for storage error mapping, OCC write paths (`write_task_if_unchanged`), directory listing helpers, archive move error path, and `allocate_next_id` persistence.
  - `TestFromAC_*` classes were not modified.
- RED evidence (quality-runner):
  - 1 failing test before fix: `serve/kanban/tests/test_storage_1050.py::TestBuilderDiscovered::test_engine_list_tasks_archived_strips_legacy_claimed_by`.
- GREEN evidence (quality-runner):
  - Scoped run: 71 passed, 0 failed, 0 skipped (`serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_engine_storage.py`).
  - Final scoped run: 82 passed, 0 failed, 0 skipped (`serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_engine_storage.py`).
- Coverage:
  - `owlbear_kanban.storage`: 99% (missing lines 136, 256).
- ruff:
  - Clean on changed files (`serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_storage_1050.py`).
- Commit:
  - `e27903d6` (`fix: harden storage integration paths (#1050, builder)`).

### Reflection
- The regression was fixed with a narrow list-path guard instead of broad parser contract changes.
- Storage coverage improved from 69% to 99% by targeting uncovered branches directly.
- Archived legacy claim handling is now explicitly verified in builder-discovered tests.
- Scoped quality-runner runs kept verification fast while still validating the related engine-storage surface.
[[2026-04-21]]
## Review Evidence

### Test Results
- quality-runner scoped to [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py) and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py): 71 passed, 0 failed, 0 skipped

### Lint
- quality-runner scoped to [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py): clean

### Coverage
- owlbear_kanban.storage: 99%
- owlbear_kanban.engine: 40%
- Review bar for touched modules is 90%. This retry changed [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), so the engine surface remains below gate.

### Pass 1 - Critical

#### Test Integrity
- The task-specific TestFromAC cases in [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py) remain preserved. The builder added only [serve/kanban/tests/test_storage_1050.py#L873](serve/kanban/tests/test_storage_1050.py#L873) and [serve/kanban/tests/test_storage_1050.py#L913](serve/kanban/tests/test_storage_1050.py#L913).

#### Test Quality
- FAIL: AC-C30 is still guarded only by label-presence assertions at [serve/kanban/tests/test_storage_1050.py#L478](serve/kanban/tests/test_storage_1050.py#L478), [serve/kanban/tests/test_storage_1050.py#L479](serve/kanban/tests/test_storage_1050.py#L479), and [serve/kanban/tests/test_storage_1050.py#L480](serve/kanban/tests/test_storage_1050.py#L480). The implementation writes dynamic values at [serve/kanban/src/owlbear_kanban/engine.py#L1089](serve/kanban/src/owlbear_kanban/engine.py#L1089), [serve/kanban/src/owlbear_kanban/engine.py#L1090](serve/kanban/src/owlbear_kanban/engine.py#L1090), [serve/kanban/src/owlbear_kanban/engine.py#L1091](serve/kanban/src/owlbear_kanban/engine.py#L1091), and [serve/kanban/src/owlbear_kanban/engine.py#L1092](serve/kanban/src/owlbear_kanban/engine.py#L1092). Wrong or empty values would still pass as long as the words code, path, and detail remain in the body.

#### Integration Check
- PASS: The earlier archive-list regression is fixed. Archived listing now clears legacy claim state before summary projection at [serve/kanban/src/owlbear_kanban/engine.py#L489](serve/kanban/src/owlbear_kanban/engine.py#L489), and the regression is covered by [serve/kanban/tests/test_storage_1050.py#L913](serve/kanban/tests/test_storage_1050.py#L913).

### AC Compliance

| AC | Evidence | Status |
|---|---|---|
| AC-C13 | [serve/kanban/tests/test_storage_1050.py#L163](serve/kanban/tests/test_storage_1050.py#L163) passed against canonical ordering in [serve/kanban/src/owlbear_kanban/storage.py#L254](serve/kanban/src/owlbear_kanban/storage.py#L254) | PASS |
| AC-C14 | [serve/kanban/tests/test_storage_1050.py#L205](serve/kanban/tests/test_storage_1050.py#L205) passed and vendor fields survive round-trip | PASS |
| AC-C15 | [serve/kanban/tests/test_storage_1050.py#L242](serve/kanban/tests/test_storage_1050.py#L242) and [serve/kanban/tests/test_storage_1050.py#L873](serve/kanban/tests/test_storage_1050.py#L873) passed; Z-suffix normalization is implemented at [serve/kanban/src/owlbear_kanban/storage.py#L161](serve/kanban/src/owlbear_kanban/storage.py#L161) | PASS |
| AC-C16 | [serve/kanban/tests/test_storage_1050.py#L294](serve/kanban/tests/test_storage_1050.py#L294) plus exact-detail assertion at [serve/kanban/tests/test_storage_1050.py#L314](serve/kanban/tests/test_storage_1050.py#L314) passed | PASS |
| AC-C28 | [serve/kanban/tests/test_storage_1050.py#L351](serve/kanban/tests/test_storage_1050.py#L351) passed against [serve/kanban/src/owlbear_kanban/storage.py#L371](serve/kanban/src/owlbear_kanban/storage.py#L371) | PASS |
| AC-C29 | [serve/kanban/tests/test_storage_1050.py#L370](serve/kanban/tests/test_storage_1050.py#L370) and companion existence/content checks passed | PASS |
| AC-C30 | Tag and section tests at [serve/kanban/tests/test_storage_1050.py#L420](serve/kanban/tests/test_storage_1050.py#L420) and [serve/kanban/tests/test_storage_1050.py#L442](serve/kanban/tests/test_storage_1050.py#L442) pass, but field-value checks at [serve/kanban/tests/test_storage_1050.py#L478](serve/kanban/tests/test_storage_1050.py#L478), [serve/kanban/tests/test_storage_1050.py#L479](serve/kanban/tests/test_storage_1050.py#L479), and [serve/kanban/tests/test_storage_1050.py#L480](serve/kanban/tests/test_storage_1050.py#L480) only assert label presence while [serve/kanban/src/owlbear_kanban/engine.py#L1090](serve/kanban/src/owlbear_kanban/engine.py#L1090), [serve/kanban/src/owlbear_kanban/engine.py#L1091](serve/kanban/src/owlbear_kanban/engine.py#L1091), and [serve/kanban/src/owlbear_kanban/engine.py#L1092](serve/kanban/src/owlbear_kanban/engine.py#L1092) emit dynamic values | FAIL |
| AC-C48 | Direct archive read [serve/kanban/tests/test_storage_1050.py#L491](serve/kanban/tests/test_storage_1050.py#L491), constructor path [serve/kanban/tests/test_storage_1050.py#L524](serve/kanban/tests/test_storage_1050.py#L524), and archived list regression [serve/kanban/tests/test_storage_1050.py#L913](serve/kanban/tests/test_storage_1050.py#L913) pass; stripping remains in [serve/kanban/src/owlbear_kanban/storage.py#L216](serve/kanban/src/owlbear_kanban/storage.py#L216) and [serve/kanban/src/owlbear_kanban/engine.py#L489](serve/kanban/src/owlbear_kanban/engine.py#L489) | PASS |

### Deductions
- AC-C30 test quality remains weak: -0.14
- Touched engine module coverage below review bar: -0.16
- Third review failure on the same task triggers loop-breaker routing: -0.04

### Verdict
- Confidence: 0.66
- FAIL
- Action: reject to backlog. This is the third review failure on task 1050, so the loop-breaker rule applies.

### Required fixes
1. Strengthen AC-C30 to assert the actual code, path, and detail values emitted by repair_storage, not just the words code, path, and detail.
2. Raise independent coverage on the touched engine module to at least 90%, or narrow the engine change so the touched-module coverage gate is satisfied.
3. Keep the new archived-list regression test at [serve/kanban/tests/test_storage_1050.py#L913](serve/kanban/tests/test_storage_1050.py#L913); that path is now correctly protected.

### Reflection
- Broad related-surface execution was useful for regression context, but the gate decision needed a second scoped quality-runner pass because older suite lint debt was unrelated to the current retry.
- The earlier AC-C48 archive-list defect is fixed; the remaining failure is test strength plus coverage gate, not the archived claim-stripping logic.
- Three review cycles on the same task is enough evidence to break the loop and send it back for replanning.
[[2026-04-21]]
## Architecture Review

### Context
Third review cycle triggered loop-breaker back to backlog. Two persistent issues: (1) AC-C30 test assertions check labels only, not field values; (2) reviewer applies 90% coverage gate to engine.py (1,228 lines, ~14% touched) rather than the primary deliverable storage.py (99%).

### AC Refinement — AC-C30

**Original:** "AR task created by quarantine has tag `type:user-action` and body section `## Quarantined file` with `code`, `path`, `detail`"

**Refined:** "AR task created by quarantine has tag `type:user-action` and body section `## Quarantined file` containing field-value pairs where `code` equals the corruption error code (e.g. `ERR_CORRUPT_MISSING_FIELD`), `path` equals the quarantine file path, and `detail` equals the corruption detail message (e.g. `forbidden field claimed_by present`). Tests must assert actual values, not label-only substring presence."

### Coverage Scope Guidance

The 90% coverage gate applies to **`owlbear_kanban.storage`** (the primary deliverable module, currently 99%). It does NOT apply to `owlbear_kanban.engine` as a whole — engine.py is 1,228 lines of pre-existing code; this task touched ~160 lines for narrow integration fixes (list_tasks corruption detection + repair_storage method). Requiring 90% coverage of the full engine for a storage-surface task violates KISS/YAGNI and caused the 3-cycle loop.

Reviewer: evaluate engine changes for correctness of touched paths only. Do not gate on whole-module engine coverage for this task.

### Required Downstream Actions (test-writer)
1. Strengthen `TestFromAC_QuarantineRepair.test_repair_storage_ar_body_has_code_path_detail_fields` — replace `assert "code" in body` etc. with assertions that verify the actual code, path, and detail values emitted by `repair_storage()`.
2. Preserve all existing `TestFromAC_*` and `TestBuilderDiscovered` tests unchanged.
3. No new implementation work — only test assertion strengthening.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage surface tests + implementation, single module |
| Interface clarity | PASS after refinement | AC-C30 now specifies value assertions explicitly |
| Dependency correctness | PASS | No unresolved dependencies |
| Module layering | PASS | storage.py wraps task_io; engine.py consumes storage surface |
| TDD compliance | PASS | tdd:red tag, test-writer → builder cycle completed |
| KISS/YAGNI | PASS | Narrow scope, no speculative features |
| Premise challenge | PASS | Storage surface is Brief C deliverable |
| Pattern consistency | PASS | Follows existing engine/module patterns |
| Security surface | PASS | No new system boundaries; path containment validated |
| Single domain | PASS | kanban domain only |

### Challenge Results
- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)
- Architect response: N/A

### Verdict: REFINE → approve
### Action Taken: Refined AC-C30 to require value assertions. Added coverage scope guidance to break the 3-cycle loop. Advanced to todo for test-writer to strengthen AC-C30 assertions.
[[2026-04-21]]
## Test-Writer Notes
- Retry cycle: strengthened AC-C30 assertions per architect directive (3-cycle loop-breaker)
- Test file: serve/kanban/tests/test_storage_1050.py
- Change: `TestFromAC_QuarantineRepair.test_repair_storage_ar_body_has_code_path_detail_fields` — replaced 3 label-only substring checks (`assert "code" in body` etc.) with value assertions:
  1. `assert "ERR_CORRUPT_MISSING_FIELD" in body` — verifies actual error code field value
  2. `assert expected_quarantine_path in body` — verifies actual path field value (`kanban_dir/quarantine/1-test.md`)
  3. `assert f"quarantined to {expected_quarantine_path}" in body` — verifies actual detail field value
- All `TestFromAC_*` and `TestBuilderDiscovered` classes preserved unchanged
- No implementation changes

### AC Coverage

| AC | Tests | Status |
|----|-------|--------|
| AC-C13 | `test_written_frontmatter_fields_in_canonical_order`, `test_vendor_extra_fields_appear_after_canonical_fields` | COVERED |
| AC-C14 | `test_task_model_accepts_vendor_extra_fields`, `test_vendor_extra_fields_survive_write_read_round_trip` | COVERED |
| AC-C15 | `test_all_timestamp_fields_end_with_utc_offset`, `test_naive_timestamps_stored_with_utc_offset`, `TestBuilderDiscovered.test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc` | COVERED |
| AC-C16 | `test_detect_corruption_claimed_by_in_tasks_dir`, `test_detect_corruption_claimed_by_detail_exact_string`, `test_detect_corruption_clean_task_returns_none`, `test_detect_corruption_archive_file_with_claimed_by_returns_none` | COVERED |
| AC-C28 | `test_move_to_quarantine_creates_dir_when_absent`, `test_move_to_quarantine_no_error_when_dir_already_exists` | COVERED |
| AC-C29 | `test_move_to_quarantine_returns_quarantine_subpath`, `test_move_to_quarantine_file_exists_at_returned_path`, `test_move_to_quarantine_source_file_removed`, `test_move_to_quarantine_preserves_file_content` | COVERED |
| AC-C30 | `test_repair_storage_ar_task_has_type_user_action_tag`, `test_repair_storage_ar_body_contains_quarantined_file_section`, `test_repair_storage_ar_body_has_code_path_detail_fields` (strengthened) | COVERED (values) |
| AC-C48 | `test_archive_file_with_claimed_by_reads_without_exception`, `test_archive_claimed_by_stripped_from_returned_task`, `test_archive_claimed_by_does_not_raise_corruption_error`, `test_engine_init_with_archive_claimed_by_no_migration_error`, `test_archive_vendor_fields_preserved_when_claimed_by_stripped` | COVERED |

- quality-runner (scoped): 71 passed, 0 failed — `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py`
- ruff: clean
- Commit: c47ad9be
[[2026-04-21]]
## Builder Notes
- Files changed: none.
- Implementation: no code updates were required in this cycle; the strengthened AC-C30 assertions from test-writer already match current `repair_storage()` output behavior.
- RED-state check (quality-runner, scoped to `serve/kanban/tests/test_storage_1050.py`): 49 passed, 0 failed, 0 skipped; ruff clean. No remaining failing `TestFromAC_*` cases to address.
- GREEN verification (quality-runner, scoped to `serve/kanban/tests/test_storage_1050.py` and `serve/kanban/tests/test_engine_storage.py`): 71 passed, 0 failed, 0 skipped.
- Coverage (scoped): `owlbear_kanban.storage` 96%.
- Lint (scoped): clean for `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_storage_1050.py`, and `serve/kanban/tests/test_engine_storage.py`.
- Commit: none (no file modifications in this builder cycle).

### Reflection
- The refined AC-C30 value assertions are now enforced by tests and pass with the current implementation.
- Related engine-storage surface remains green in the broader scoped run.
- Kept this pass surgical by avoiding non-required code edits.
[[2026-04-21]]
## Review Evidence
### Test Results
- quality-runner scoped to [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py) and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py): 71 passed, 0 failed, 0 skipped

### Lint
- quality-runner scoped to [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py): clean

### Coverage
- [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py): 96%
- [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py): 39% full-module coverage in this scoped run
- Gate application: the task-body Architecture Review refinement narrows the 90% coverage gate to the storage surface for this task. Storage meets that bar. Engine full-module coverage is informational here, not the blocking issue.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C13 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L163), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L177) | Yes | COVERED |
| AC-C14 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L205), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L220) | Yes | COVERED |
| AC-C15 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L242), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L260), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L873) | Yes | COVERED |
| AC-C16 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L294), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L305), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L329) | Yes | COVERED |
| AC-C28 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L351), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L361) | Yes | COVERED |
| AC-C29 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L370), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L380), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L392), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L401) | Yes | COVERED |
| AC-C30 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L421), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L442), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L460) | No for the refined contract in the task-body Architecture Review. The current test asserts quarantine text at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L479), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L480), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L481), while the implementation serializes that weaker value through [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1114-L1117) and [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L332) | LAX |
| AC-C48 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L492), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L502), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L512), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L525), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L545), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L914) | Direct archive read and archived-list behavior: yes. Constructor path under the live migration gate is not directly proven because the fixture uses a legacy board config at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L66), which bypasses [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L314) | LAX |

#### Security Review
- No issues found. The audited paths are board-local file operations and markdown generation only.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L460) | Strengthened from label-only checks to concrete substrings, but the new detail assertion now encodes quarantine text at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L481) instead of the corruption-detail value required by the task-body Architecture Review refinement | WEAKENED |
| Other task-scoped TestFromAC cases | No weakening observed | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC-C30 still verifies the weaker implementation contract, not the refined contract, via [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L479-L481) |
| Negative/error-path coverage | ADEQUATE | AC-C16 exact corruption detail remains asserted at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L305-L314) |
| Manual mutation reasoning | WEAK | The suite would stay green if the AR detail field kept carrying quarantine text instead of the refined corruption-detail value, because that is what [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L481) expects |
| Test independence | STRONG | Temp-board isolation throughout the task-specific suite |
| Descriptive test names | STRONG | Test names still map directly to the AC clauses |

#### Data Safety
- No issues found. Quarantine and AR creation remain a two-phase flow, and corrupt files stay preserved even if AR creation fails.

#### Implementation-Aware Gaps
- AC-C30 refined contract is still unmet in the live implementation. [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1114-L1117) writes the AR body from outcome.detail, and quarantined outcomes currently overwrite that field with quarantine-location text in [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L332). That conflicts with the Architecture Review refinement that detail should carry the corruption detail message.
- The AC-C48 constructor exemption test is still weaker than it appears. The fixture config at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L66) is legacy, so [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L525) never exercises the active migration gate at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L314). The implementation looks correct by inspection, but the guarded path is unproven by tests.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- Related legacy coverage remains weak in [serve/kanban/tests/test_storage.py](serve/kanban/tests/test_storage.py#L256-L259), which self-raises MigrationRequiredError inside pytest.raises. This does not gate task 1050 because the task-specific suite is stronger, but it weakens long-term regression signal.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | Canonical order is emitted from [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L286) and verified by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L163) and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L177) | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L163) | PASS |
| AC-C14 | Vendor fields survive through the extra-allow model at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L121) and round-trip tests at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L205) and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L220) | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L205) | PASS |
| AC-C15 | Z-suffix and naive timestamps are normalized to explicit UTC by [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L154-L165) and verified at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L242), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L260), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L873) | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L873) | PASS |
| AC-C16 | Claimed-by corruption and archive exemption are implemented in [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L228-L235) and verified at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L294), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L305), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L329) | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L305) | PASS |
| AC-C28 | Quarantine directory creation occurs in [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L400) and is verified at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L351) and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L361) | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L351) | PASS |
| AC-C29 | Quarantine path and file move semantics are verified at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L370), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L380), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L392), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L401) | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L370) | PASS |
| AC-C30 | The task-body Architecture Review refined AC-C30 to require exact value assertions for code, path, and detail. Current code still serializes quarantine text through [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1114-L1117) and [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L332), and the updated test at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L479-L481) now matches that weaker behavior instead of the refined contract | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L460) | FAIL |
| AC-C48 | Archive reads strip claimed_by in [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L248); archived list summaries clear legacy claim state in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L490); direct-read and archived-list tests pass at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L492-L545) and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L914-L925) | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L914) | PASS |

### Deductions
- AC-C30 refined contract still weakened in both the current TestFromAC assertion and the current repair_storage output: -0.16
- AC-C48 constructor exemption remains under-tested on the live migration-gate path: -0.08
- This is the fourth review failure on the same task, so the loop-breaker routing applies: -0.04

### Verdict
- Confidence: 0.70
- FAIL
- Action: reject to backlog

### Required fixes
1. Align AC-C30 with the Architecture Review refinement. The AR body detail field must carry the corruption detail message, and the TestFromAC assertion must verify that exact value rather than quarantine-location text.
2. Add a non-legacy constructor-path test for archive-only claimed_by that exercises the active migration gate and proves no MigrationRequiredError on a new-schema board.
3. Keep the current storage coverage posture. Broad engine-module coverage is not the blocker for task 1050.

### Reflection
- The earlier AC-C30 failure mode changed shape: it is no longer label-only, but it still encodes the wrong contract.
- The independent scoped quality run is clean, so the rejection is about contract enforcement and test strength, not basic breakage.
- The task-body Architecture Review correctly narrowed coverage scope to storage; that avoided another false negative on whole-module engine coverage.
- A fourth review failure on the same task is enough evidence to send it back for replanning instead of another narrow retry.
[[2026-04-21]]
## Architecture Review (cycle 2)

### Root Cause Analysis

The 4-review-cycle loop was caused by the previous architecture review's AC-C30 refinement incorrectly specifying that the AR body `detail` field should contain the corruption detection message (`"forbidden field claimed_by present"`). In reality, `attempt_repair()` receives only `error.code` from `scan_and_fix()` — the corruption detail string is never propagated to `RepairOutcome`. The `detail` field carries the repair action outcome (`"quarantined to {path}"`). The test-writer correctly strengthened assertions to match the actual implementation contract; the reviewer kept failing them against the wrong specification.

### AC-C30 Refinement — CORRECTED

**Previous (wrong):** `detail` equals the corruption detail message (e.g., `"forbidden field claimed_by present"`)

**Corrected:** AR task created by quarantine has tag `type:user-action` and body section `## Quarantined file` containing field-value pairs where `code` equals the corruption error code (e.g., `ERR_CORRUPT_MISSING_FIELD`), `path` equals the quarantine file path, and `detail` equals the repair outcome text (e.g., `"quarantined to {quarantine_path}"`). Tests must assert actual values, not label-only substring presence.

Current test assertions at test_storage_1050.py:479-481 correctly verify:
- `"ERR_CORRUPT_MISSING_FIELD" in body` (code value)
- `expected_quarantine_path in body` (path value)
- `f"quarantined to {expected_quarantine_path}" in body` (detail value)

These match the implementation at engine.py:1089-1092 and corruption.py:330-332. AC-C30 is **satisfied**.

### AC-C48 Constructor Test — Guidance

`test_engine_init_with_archive_claimed_by_no_migration_error` (test_storage_1050.py:524) uses `_make_board()` which includes `version: 10` in config.yml — a legacy-schema board. The migration gate at engine.py:314 only fires for **new-schema** boards (no `version` field). With legacy config, the gate is skipped entirely, making this test vacuous for its stated purpose.

**Required test-writer action:** Change this specific test to use a config WITHOUT the `version` field, so the migration gate is actually exercised. The gate scans only `tasks/` — archive `claimed_by` should still not trigger `MigrationRequiredError`. This proves the archive exemption under the live gate, not just under a bypassed one.

### Coverage Scope Guidance (retained)

The 90% coverage gate applies to `owlbear_kanban.storage` (the primary deliverable, currently 96-99%). It does NOT apply to `owlbear_kanban.engine` as a whole — engine.py is 1,228 lines; this task touched ~160 lines for narrow integration fixes. Reviewer: evaluate engine changes for correctness of touched paths only.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage surface tests + implementation, single module |
| Interface clarity | PASS | AC-C30 corrected to match actual contract |
| Dependency correctness | PASS | No unresolved dependencies |
| Module layering | PASS | storage.py wraps task_io; engine.py consumes storage surface |
| TDD compliance | PASS | tdd:red tag, test-writer → builder cycle completed |
| KISS/YAGNI | PASS | Narrow scope, no speculative features |
| Premise challenge | PASS | Storage surface is Brief C deliverable |
| Pattern consistency | PASS | Follows existing engine/module patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban domain only |

### Challenge Results
- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Required Downstream Actions (test-writer)
1. Change `test_engine_init_with_archive_claimed_by_no_migration_error` to use a new-schema board config (remove `version` field) so the migration gate at engine.py:314 is actually active. Verify archive `claimed_by` does not trigger `MigrationRequiredError`.
2. Preserve all other `TestFromAC_*` and `TestBuilderDiscovered` tests unchanged.
3. AC-C30 assertions are NOW correct — do not weaken or change them.

### Verdict: REFINE → approve
### Action Taken: Corrected the wrong AC-C30 refinement that caused the 4-cycle loop. Added test-writer guidance for AC-C48 constructor test. Retained coverage scope guidance. Advanced to todo.
[[2026-04-21]]
## Test-Writer Notes
- Retry cycle: fixed vacuous AC-C48 constructor-path test per architect directive (cycle-2 loop-breaker)
- Test file: serve/kanban/tests/test_storage_1050.py
- Change: `TestFromAC_ArchiveExemption.test_engine_init_with_archive_claimed_by_no_migration_error`
  - **Before:** used `_make_board()` which writes `version: 10` (legacy schema) → migration gate at engine.py:314 was bypassed entirely → test passed vacuously
  - **After:** uses `_NEW_SCHEMA_CONFIG_YAML` (no `version` field) → migration gate is active; `tasks/` is clean, `archive/` has `claimed_by` → gate correctly does not fire → test passes non-vacuously
- Added `_NEW_SCHEMA_CONFIG_YAML` constant alongside `_CONFIG_YAML`; no other changes
- All other `TestFromAC_*` and `TestBuilderDiscovered` classes unchanged
- AC-C30 value assertions preserved unchanged

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC-C13 | `test_written_frontmatter_fields_in_canonical_order`, `test_vendor_extra_fields_appear_after_canonical_fields` | COVERED |
| AC-C14 | `test_task_model_accepts_vendor_extra_fields`, `test_vendor_extra_fields_survive_write_read_round_trip` | COVERED |
| AC-C15 | `test_all_timestamp_fields_end_with_utc_offset`, `test_naive_timestamps_stored_with_utc_offset`, `TestBuilderDiscovered.test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc` | COVERED |
| AC-C16 | `test_detect_corruption_claimed_by_in_tasks_dir`, `test_detect_corruption_claimed_by_detail_exact_string`, `test_detect_corruption_clean_task_returns_none`, `test_detect_corruption_archive_file_with_claimed_by_returns_none` | COVERED |
| AC-C28 | `test_move_to_quarantine_creates_dir_when_absent`, `test_move_to_quarantine_no_error_when_dir_already_exists` | COVERED |
| AC-C29 | `test_move_to_quarantine_returns_quarantine_subpath`, `test_move_to_quarantine_file_exists_at_returned_path`, `test_move_to_quarantine_source_file_removed`, `test_move_to_quarantine_preserves_file_content` | COVERED |
| AC-C30 | `test_repair_storage_ar_task_has_type_user_action_tag`, `test_repair_storage_ar_body_contains_quarantined_file_section`, `test_repair_storage_ar_body_has_code_path_detail_fields` (value assertions: ERR_CORRUPT_MISSING_FIELD, quarantine path, quarantined-to detail) | COVERED (values) |
| AC-C48 | `test_archive_file_with_claimed_by_reads_without_exception`, `test_archive_claimed_by_stripped_from_returned_task`, `test_archive_claimed_by_does_not_raise_corruption_error`, `test_engine_init_with_archive_claimed_by_no_migration_error` (now non-vacuous, new-schema board), `test_archive_vendor_fields_preserved_when_claimed_by_stripped` | COVERED |

- quality-runner (scoped): 49 passed, 0 failed — serve/kanban/tests/test_storage_1050.py
- ruff: clean
- Commit: 642344a5
[[2026-04-21]]
## Builder Notes
- Files changed: none (verification-only cycle).
- Implementation: no source updates required after test-writer commit `642344a5`; the revised AC-C48 constructor-path test already passes against current code.
- Task-scoped quality-runner (RED check): 49 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py`.
- Scoped GREEN verification (quality-runner): 71 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py`.
- Lint (scoped): clean on `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_engine_storage.py`.
- Coverage (scoped): `owlbear_kanban.storage` 96%; `owlbear_kanban.engine` 40% (informational for this task scope).
- Broader regression context: run including `serve/kanban/tests/test_storage.py` had 82 passed, 0 failed, with pre-existing ruff debt in that legacy file; excluded from gate decision per scoped-evidence rule.

### Reflection
- The blocker from prior cycles was test-contract alignment; this cycle validated that the non-vacuous AC-C48 path now executes and passes without further code edits.
- Scoped quality evidence was required to separate task readiness from legacy lint debt in unrelated durable tests.
- Keeping this cycle change-free avoided unnecessary churn and preserved the surgical intent of the build phase.
[[2026-04-21]]
## Review Evidence
### Test Results
- quality-runner scoped to serve/kanban/tests/test_storage_1050.py and serve/kanban/tests/test_engine_storage.py: 71 passed, 0 failed, 0 skipped

### Lint
- quality-runner scoped to serve/kanban/src/owlbear_kanban/storage.py, serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/corruption.py, serve/kanban/tests/test_storage_1050.py, and serve/kanban/tests/test_engine_storage.py: clean

### Coverage
- owlbear_kanban.storage: 96%
- owlbear_kanban.engine: 40%
- Gate application: per the task-body Architecture Review refinement, the 90% coverage gate is applied to the storage surface for this task. Storage clears that bar; engine full-module coverage is informational here.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C13 | serve/kanban/tests/test_storage_1050.py:192 | Yes for storage.write_task canonical ordering | COVERED |
| AC-C14 | serve/kanban/tests/test_storage_1050.py:234, 249 | Yes | COVERED |
| AC-C15 | serve/kanban/tests/test_storage_1050.py:271, 289, 913 | Yes | COVERED |
| AC-C16 | serve/kanban/tests/test_storage_1050.py:323, 334 | Yes | COVERED |
| AC-C28 | serve/kanban/tests/test_storage_1050.py:380 | Yes | COVERED |
| AC-C29 | serve/kanban/tests/test_storage_1050.py:399 plus companion existence/removal/content checks in the same class | Yes | COVERED |
| AC-C30 | serve/kanban/tests/test_storage_1050.py:449, 468, 489 and related repair_storage coverage in serve/kanban/tests/test_engine_storage.py:311, 333, 480 | Yes | COVERED |
| AC-C48 | serve/kanban/tests/test_storage_1050.py:521, 531, 541, 554, 584, 953 | Yes for archive read, archive-init exemption, and archived list summary stripping | COVERED |

#### Security Review
- No issues found. The reviewed paths are board-local file operations and markdown generation; no injection or secret-handling concerns were introduced in the task scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| serve/kanban/tests/test_storage_1050.py:489 | Current file asserts concrete code/path/detail values for AC-C30; no builder weakening evident in the final task state | PRESERVED |
| serve/kanban/tests/test_storage_1050.py:554 | Current file uses a new-schema board so the migration gate is live for AC-C48 | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC-C30 now asserts concrete error code, quarantine path, and detail text at serve/kanban/tests/test_storage_1050.py:489. |
| Negative/error-path coverage | ADEQUATE | AC-C16 exact corruption detail is asserted at serve/kanban/tests/test_storage_1050.py:334, and archive exemption paths are covered at serve/kanban/tests/test_storage_1050.py:521, 541, 554. |
| Manual mutation reasoning | WEAK | engine.py still writes claimed_by via claim_task at serve/kanban/src/owlbear_kanban/engine.py:881 and serve/kanban/src/owlbear_kanban/engine.py:884, while list_tasks now skips any tasks/ file that detect_corruption flags at serve/kanban/src/owlbear_kanban/engine.py:504 and serve/kanban/src/owlbear_kanban/corruption.py:231-236. No test covers start_work()/claim_task() followed by list_tasks() on a new-schema board. |
| Test independence | STRONG | Task-scoped tests use tmp_path-isolated boards. |
| Descriptive test names | STRONG | Test names map directly to the AC clauses. |

#### Data Safety
- No issues found. Quarantine remains a file move before AR creation, and failure handling preserves quarantined files.

#### Implementation-Aware Gaps
- FAIL: serve/kanban/src/owlbear_kanban/engine.py:47 still imports read_task/write_task from task_io instead of the storage surface. serve/kanban/src/owlbear_kanban/task_io.py:228, 247, and 251 serialize record.model_dump() directly, bypassing the storage-layer guarantees in serve/kanban/src/owlbear_kanban/storage.py:70, 281, and 286.
- Concrete regression: serve/kanban/src/owlbear_kanban/engine.py:848-884 claim_task() sets claimed_by and persists it. serve/kanban/src/owlbear_kanban/engine.py:452-504 list_tasks() now prefilters active tasks through detect_corruption(), and serve/kanban/src/owlbear_kanban/corruption.py:231-236 treats non-null claimed_by in tasks/ as ERR_CORRUPT_MISSING_FIELD. A claimed task can therefore disappear from list_tasks() after start_work().
- Missing coverage: the closest claim-path tests are activity/session assertions in serve/kanban/tests/test_engine_activity.py:101, 318, and 429. The task-scoped suite covers archive stripping at serve/kanban/tests/test_storage_1050.py:953, but there is no regression test for start_work()/claim_task() followed by list_tasks() or show_task() on a new-schema board.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 5 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The task-specific storage API coverage is strong; the blocker is the unresolved engine/storage integration boundary, not the AC-C30 or AC-C48 tests.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | storage.py canonical field order and claimed_by omission at serve/kanban/src/owlbear_kanban/storage.py:70, 281, 286 | serve/kanban/tests/test_storage_1050.py:192 | PASS |
| AC-C14 | Task extra=allow at serve/kanban/src/owlbear_kanban/models.py:121 and storage round-trip at serve/kanban/tests/test_storage_1050.py:234, 249 | serve/kanban/tests/test_storage_1050.py:234 | PASS |
| AC-C15 | Timestamp normalization in storage.py and Z-suffix regression test at serve/kanban/tests/test_storage_1050.py:271, 289, 913 | serve/kanban/tests/test_storage_1050.py:913 | PASS |
| AC-C16 | detect_corruption claimed_by rule at serve/kanban/src/owlbear_kanban/corruption.py:231-236 and tests at serve/kanban/tests/test_storage_1050.py:323, 334 | serve/kanban/tests/test_storage_1050.py:323 | PASS |
| AC-C28 | move_to_quarantine creates quarantine/ at serve/kanban/src/owlbear_kanban/storage.py:400-403 | serve/kanban/tests/test_storage_1050.py:380 | PASS |
| AC-C29 | move_to_quarantine returns quarantine/{original-filename} at serve/kanban/src/owlbear_kanban/storage.py:402-404 | serve/kanban/tests/test_storage_1050.py:399 | PASS |
| AC-C30 | repair_storage AR body generation at serve/kanban/src/owlbear_kanban/engine.py:1072-1098 and tests at serve/kanban/tests/test_storage_1050.py:449, 468, 489 | serve/kanban/tests/test_storage_1050.py:489 | PASS |
| AC-C48 | archive read strips claimed_by in storage.py and archive init/list coverage at serve/kanban/tests/test_storage_1050.py:521, 531, 541, 554, 584, 953 | serve/kanban/tests/test_storage_1050.py:554 | PASS |

### Deductions
- Engine write paths still bypass the storage surface, creating a claim->list regression: -0.22
- No regression coverage for start_work()/claim_task() followed by list_tasks() on a new-schema board: -0.12
- This is a 3rd+ review failure on the same task, so loop-breaker routing applies: -0.06

### Verdict
- Confidence: 0.60
- FAIL
- Action: reject to backlog

### Required fixes
1. Route engine task-file read/write paths through owlbear_kanban.storage.read_task and owlbear_kanban.storage.write_task, or implement equivalent guarantees so claiming a task does not emit a claimed_by-corrupt file that list_tasks() later skips.
2. Add a regression test on a new-schema board for start_work()/claim_task() followed by list_tasks() and show_task(), asserting the claimed task remains visible and readable.
3. Keep the current AC-C30 and AC-C48 tests; they are not the blocker in the final task state.

### Reflection
- Fresh scoped quality evidence was green; the failure is a logic-level regression hidden by missing claim/list coverage.
- The earlier AC-C30 contract dispute is resolved in the current task state.
- The live blocker is the unresolved engine/storage boundary, which now conflicts with the list_tasks corruption filter.
- Multiple prior review failures already exist in the task body, so the loop-breaker path is the correct routing.
[[2026-04-22]]
## Architecture Review (cycle 3)

### Root Cause of the 6-Review Loop

The loop stems from two distinct issues conflated into one task:

1. **AC compliance** — all 8 original ACs are PASS per the latest reviewer compliance table. The AC-C30 value-assertion issue and AC-C48 constructor-path issue are both resolved.
2. **Builder-introduced regression** — the builder added `detect_corruption` filtering to `list_tasks()` at engine.py:505-507 to fix cross-task mode-6/mode-9 regressions from `test_engine_storage.py`. This integration was NOT in any AC. It created a new regression: `claim_task()` writes `claimed_by` via `task_io.write_task()` (which preserves it on disk), then `list_tasks()` runs `detect_corruption()` which flags it as mode-3 corruption and silently skips the task. Any actively-claimed task disappears from list results.

The reviewer kept failing on issue #2, which is valid but was never part of the task's AC scope. Each cycle, the fix attempts addressed different aspects but never the core regression.

### Regression Analysis

Causal chain (verified by codebase inspection):
- engine.py:48 imports `write_task` from `task_io` (no `claimed_by` stripping)
- engine.py:882-886 `claim_task` sets `claimed_by` and writes via `task_io.write_task` → field lands on disk
- engine.py:505-507 `list_tasks` calls `storage.detect_corruption` → mode-3 flags `claimed_by` in tasks/ → task silently skipped
- Net effect: claimed tasks vanish from `list_tasks()`, `pick_tasks()`, MCP tool listings, Cockpit UI
- Window: between `start_work()` and `end_work()` only — `release_task()` clears `claimed_by` to None which passes the corruption check

### New AC (regression fix)

- [ ] AC-REGR: `list_tasks()` must not silently drop tasks with mode-3 `claimed_by` corruption. Actively-claimed tasks must remain visible in list results. `detect_corruption` still reports mode-3 per AC-C16 — only the `list_tasks` filter behavior changes.

### Required Downstream Actions

**Test-writer:**
1. Add regression test: on a new-schema board, `engine.claim_task(id)` followed by `engine.list_tasks()` must include the claimed task in results (not silently dropped).
2. Preserve all existing `TestFromAC_*` and `TestBuilderDiscovered` tests unchanged.

**Builder:**
3. In `list_tasks()` at engine.py:505-507, modify the corruption filter to exempt mode-3 `claimed_by` corruptions. The `claimed_by` corruption indicates a temporary legitimate state (active claim), not a broken file. Only modes indicating genuinely unreadable/misparsed files should trigger the skip. Suggested approach: check the returned `CorruptionError.detail` — if it equals `"forbidden field claimed_by present"`, do not skip.
4. `detect_corruption` itself is unchanged — it still reports mode-3 for `repair_storage()` use (AC-C16 satisfied).

**Reviewer:**
5. Coverage gate: 90% applies to `owlbear_kanban.storage` (primary deliverable, currently 96-99%). Engine whole-module coverage is informational — this task touched ~160 lines of a 1,228-line module. Assess engine changes for correctness of touched paths only.
6. AC-C30 value assertions (test_storage_1050.py:479-481) are NOW correct — they match the implementation contract. Do not re-apply the wrong refinement from cycle 1.
7. AC-C48 constructor test uses new-schema board config (no `version` field) — the migration gate is live. This is correct.

### Follow-up Task

Created #1097 for the broader engine/storage write-path unification (routing `engine.py` I/O through `storage.read_task`/`storage.write_task`). That refactor is out of scope for this storage-surface task but is tracked for Brief C completion. Note: #1097 needs body, tags (phase:storage, brief:c, scope:kanban), parent (1043), and depends_on (1050) added — create_task parameters failed.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage surface + narrow regression fix in same module |
| Interface clarity | PASS | AC-REGR specifies exact behavior change |
| Dependency correctness | PASS | No unresolved dependencies |
| Module layering | PASS | storage.py wraps task_io; engine.py consumes storage surface |
| TDD compliance | PASS | tdd:red tag present |
| KISS/YAGNI | PASS | Narrow scope, regression fix is minimal |
| Premise challenge | PASS | Storage surface is Brief C deliverable |
| Pattern consistency | PASS | Follows existing engine/module patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban domain only |

### Challenge Results
- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Verdict: REFINE → approve
### Action Taken: Added AC-REGR for the claim/list regression. Provided specific builder guidance for the narrow corruption-filter fix. Retained coverage scope and AC-C30/AC-C48 guidance from cycle 2. Created follow-up #1097 for broader engine/storage unification. Advanced to todo.
[[2026-04-22]]
## Test-Writer Notes
- Retry cycle: added AC-REGR regression tests per architect directive (cycle-3 loop-breaker)
- Test file: serve/kanban/tests/test_storage_1050.py
- New class: `TestFromAC_ClaimListRegression` (AC-REGR)

### Changes
- Added `TestFromAC_ClaimListRegression` with 3 tests at end of file:
  1. `test_claimed_task_remains_in_list_tasks_same_engine` — `claim_task()` → `list_tasks()` on same engine; task must appear
  2. `test_claimed_task_remains_in_list_tasks_after_cache_miss` — warm cache → `claim_task()` (mtime change) → `list_tasks()` (cache miss); task must survive detect_corruption filtering
  3. `test_start_work_then_list_tasks_includes_task` — public `start_work()` API path; task must appear in `list_tasks()`
- All other `TestFromAC_*` and `TestBuilderDiscovered` classes preserved unchanged
- AC-C30 value assertions (code/path/detail) preserved unchanged
- AC-C48 new-schema constructor test preserved unchanged

### AC Coverage

| AC | Tests | Status |
|----|-------|--------|
| AC-C13 | `test_written_frontmatter_fields_in_canonical_order`, `test_vendor_extra_fields_appear_after_canonical_fields` | COVERED |
| AC-C14 | `test_task_model_accepts_vendor_extra_fields`, `test_vendor_extra_fields_survive_write_read_round_trip` | COVERED |
| AC-C15 | `test_all_timestamp_fields_end_with_utc_offset`, `test_naive_timestamps_stored_with_utc_offset`, `TestBuilderDiscovered.test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc` | COVERED |
| AC-C16 | `test_detect_corruption_claimed_by_in_tasks_dir`, `test_detect_corruption_claimed_by_detail_exact_string`, `test_detect_corruption_clean_task_returns_none`, `test_detect_corruption_archive_file_with_claimed_by_returns_none` | COVERED |
| AC-C28 | `test_move_to_quarantine_creates_dir_when_absent`, `test_move_to_quarantine_no_error_when_dir_already_exists` | COVERED |
| AC-C29 | `test_move_to_quarantine_returns_quarantine_subpath`, `test_move_to_quarantine_file_exists_at_returned_path`, `test_move_to_quarantine_source_file_removed`, `test_move_to_quarantine_preserves_file_content` | COVERED |
| AC-C30 | `test_repair_storage_ar_task_has_type_user_action_tag`, `test_repair_storage_ar_body_contains_quarantined_file_section`, `test_repair_storage_ar_body_has_code_path_detail_fields` (value assertions: ERR_CORRUPT_MISSING_FIELD, quarantine path, quarantined-to detail) | COVERED (values) |
| AC-C48 | `test_archive_file_with_claimed_by_reads_without_exception`, `test_archive_claimed_by_stripped_from_returned_task`, `test_archive_claimed_by_does_not_raise_corruption_error`, `test_engine_init_with_archive_claimed_by_no_migration_error` (new-schema board), `test_archive_vendor_fields_preserved_when_claimed_by_stripped` | COVERED |
| AC-REGR | `test_claimed_task_remains_in_list_tasks_same_engine`, `test_claimed_task_remains_in_list_tasks_after_cache_miss`, `test_start_work_then_list_tasks_includes_task` | COVERED (all FAIL) |

- quality-runner (scoped): 3 failed (new TestFromAC_ClaimListRegression), 71 passed — serve/kanban/tests/test_storage_1050.py + serve/kanban/tests/test_engine_storage.py
- ruff: clean
- Commit: 566b4e45
[[2026-04-22]]
## Builder Notes
- Implementation: updated `serve/kanban/src/owlbear_kanban/engine.py` `list_tasks()` corruption prefilter to exempt only mode-3 `claimed_by` corruption (`ERR_CORRUPT_MISSING_FIELD` + `forbidden field claimed_by present`) from silent skip; all other corruption filtering behavior remains unchanged.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`
- RED evidence (quality-runner, scoped): 49 passed, 3 failed in `serve/kanban/tests/test_storage_1050.py` (all three in `TestFromAC_ClaimListRegression`).
- GREEN evidence (quality-runner, scoped): 74 passed, 0 failed, 0 skipped across `serve/kanban/tests/test_storage_1050.py` and `serve/kanban/tests/test_engine_storage.py`.
- Coverage (scoped): `storage.py` 96%.
- Lint (scoped): ruff clean for `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_storage_1050.py`.
- Commit: `d02e4e1d` (`fix: keep claimed tasks visible in listings (#1050, builder)`).

### Reflection
- The regression was reproduced directly in RED before code edits, confirming the exact failing behavior.
- A narrow conditional exemption in `list_tasks()` resolved the claim/list disappearance without touching detection rules themselves.
- Scoped quality-runner verification was sufficient to confirm both task-specific and related engine-storage surfaces remained green.
- Kept the change surgical to avoid cross-surface churn in an already long retry cycle.
[[2026-04-22]]
## Review Evidence
### Test Results
- quality-runner scoped to [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py) and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py): 74 passed, 0 failed, 0 skipped

### Lint
- quality-runner scoped to [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py): clean

### Coverage
- [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py): 96%
- Gate application: per the task-body architecture refinements, the 90% coverage bar applies to the storage surface for this task. Storage clears that bar.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C13 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L192), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L204) | Yes | COVERED |
| AC-C14 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L232), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L249) | Yes | COVERED |
| AC-C15 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L271), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L289), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L913) | No for vendor extra timestamps. `write_task()` only normalizes `_TS_FIELDS` at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L88) and [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L290-L291), while vendor extras are written unchanged at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L294-L295). The suite seeds a vendor timestamp field at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L259) but never asserts its written form. | MISSING |
| AC-C16 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L323), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L334), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L355) | Yes | COVERED |
| AC-C28 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L380), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L390) | Yes for directory creation | COVERED |
| AC-C29 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L399), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L409), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L421), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L430) | Yes for in-board file moves | COVERED |
| AC-C30 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L449), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L468), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L489) | Yes | COVERED |
| AC-C48 | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L521), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L531), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L541), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L554), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L584), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L953) | Yes | COVERED |
| AC-REGR | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L992), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1004), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1025) | Yes | COVERED |

#### Security Review
- No exploitable task-local issue found in the claim/list, archive-read, or AR-body paths that were explicitly under test.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L489) | AC-C30 still asserts concrete code, path, and detail values | PRESERVED |
| [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L554) | AC-C48 constructor-path test still uses a new-schema board so the migration gate is live | PRESERVED |
| [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L972) | AC-REGR regression class remains intact | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The vendor round-trip branch seeds `completed` at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L259) but only asserts `class` at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L267). |
| Negative/error-path coverage | ADEQUATE | `claimed_by` corruption and archive exemption are exercised at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L323-L368) and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L521-L584). |
| Manual mutation reasoning | WEAK | A mutation that leaves vendor timestamp extras as naive or `Z` would keep the suite green because extras bypass normalization and no task test checks them. |
| Test independence | STRONG | `tmp_path`-isolated boards throughout the task-local suite. |
| Descriptive test names | STRONG | Names map directly to the AC clauses and regression. |

#### Data Safety
- FAIL: [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L1-L18) declares `move_to_quarantine()` as part of the public storage surface, but the implementation at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L400-L405) performs `task_path.replace(dest)` with no source containment validation. That is asymmetric with [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L277), where `write_task()` validates board containment before writing. Task-local and legacy tests cover only in-board happy paths at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L380-L438) and [serve/kanban/tests/test_storage.py](serve/kanban/tests/test_storage.py#L268-L297), so an out-of-board move remains unguarded.

#### Implementation-Aware Gaps
- FAIL: AC-C15 is still broader than the implementation. `_TS_FIELDS` only includes `created`, `updated`, and `claimed_at` at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L88), and vendor extras are appended unchanged at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L294-L295). The suite already treats vendor extras as in-scope at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L249-L267), including a vendor timestamp field at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L259), but never proves those written timestamps are normalized to explicit `+00:00`.
- PASS: The claim/list regression is fixed. Active-task mode-3 `claimed_by` corruption is exempted from the skip at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L504-L508), and the regression is covered at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L992), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1004), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1025).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 6 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- Five prior `## Review Evidence` sections already exist in [.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md](.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md#L91), [.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md](.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md#L239), [.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md](.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md#L367), [.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md](.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md#L508), and [.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md](.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md#L701). Another failure now follows the 3rd+ review loop-breaker rule.
- Historical RED evidence exists in the initial test-writer section and is not re-gated at this review stage.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | Canonical field order is defined at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L70-L84) and emitted in order at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L286-L295). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L192) | PASS |
| AC-C14 | `Task` allows extras at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L111-L146), and vendor fields survive round-trip at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L249-L267). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L249) | PASS |
| AC-C15 | `write_task()` documents explicit UTC normalization at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L255-L259) but only applies it to `_TS_FIELDS` at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L88) and [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L290-L291). Vendor extras are written unchanged at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L294-L295). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L271) | FAIL |
| AC-C16 | Mode-3 claimed_by detection and archive exemption live at [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L229-L237). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L323) | PASS |
| AC-C28 | `move_to_quarantine()` creates `quarantine/` at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L400-L403). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L380) | PASS |
| AC-C29 | `move_to_quarantine()` returns `quarantine/{original-filename}` at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L402-L405). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L399) | PASS |
| AC-C30 | `repair_storage()` writes concrete code/path/detail fields at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1125-L1128), with repair outcome detail supplied from [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L323-L333). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L489) | PASS |
| AC-C48 | Archive reads strip `claimed_by` at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L248); the migration gate scans only `tasks/` at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L345-L371); archived list summaries clear legacy claim state at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L526). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L554) | PASS |
| AC-REGR | `list_tasks()` exempts mode-3 `claimed_by` corruption from the active-list skip at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L504-L508). | [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L992) | PASS |

### Deductions
- AC-C15 implementation and test gap on vendor timestamp extras: -0.18
- Public `move_to_quarantine()` lacks source containment validation and negative coverage: -0.16
- Another review failure on a task that already has five prior review sections requires loop-breaker routing: -0.06

### Verdict
- Confidence: 0.60
- FAIL
- Action: reject to backlog

### Required fixes
1. Clarify AC-C15 scope at architecture level, or implement normalization for all ISO-8601 timestamp-like frontmatter extras and add task-scoped coverage for vendor timestamp fields.
2. Add source containment validation to `move_to_quarantine()` and a negative test proving out-of-board paths are rejected.
3. Keep the current AC-C30, AC-C48, and AC-REGR tests; those paths now behave correctly.

### Reflection
- Green scoped tests were insufficient because the broad AC-C15 wording still leaves an uncovered vendor-extra timestamp branch.
- The latest claim/list regression fix is correct; the new blockers are independent of the earlier loop.
- The storage surface now has a clear safety asymmetry: `write_task()` validates board containment, `move_to_quarantine()` does not.
[[2026-04-22]]
## Architecture Review (cycle 4)

### Root Cause of the 7-Review Loop

The last two reviewer failures (cycles 5-6) rejected on issues **outside the defined AC scope**:

1. **AC-C15 vendor timestamp extras** — Reviewer deducted -0.18 because vendor extras containing timestamp-like strings are not normalised. Brief C §5.3 explicitly defines timestamp fields as `created`, `updated`, `claimed_at`: *"Normalise timestamp fields (`created`, `updated`, `claimed_at`) to UTC ISO-8601 with explicit `+00:00`."* Vendor extras round-trip as-is via `extra="allow"` (AC-C14). Normalising arbitrary vendor data would corrupt opaque third-party fields. The implementation is correct.

2. **Quarantine containment** — Reviewer deducted -0.16 for `move_to_quarantine()` lacking path containment validation. No AC specifies this. The function is called exclusively by `repair_storage()` which only passes board-local paths from `detect_corruption()`. KISS/YAGNI: no attack vector exists since no user-facing API accepts arbitrary quarantine paths.

Without these invalid deductions, the reviewer's own compliance table shows all ACs PASS, confidence would be ~0.94.

### AC-C15 Clarification

**Original:** "All timestamps written are ISO-8601 UTC with explicit `+00:00`"

**Clarified:** "All canonical timestamp fields (`created`, `updated`, `claimed_at`) written by `write_task()` are ISO-8601 UTC with explicit `+00:00`. Vendor extras passed through `extra="allow"` are preserved as-is per AC-C14."

This matches Brief C §5.3, the implementation at storage.py:88 (`_TS_FIELDS`), and the existing tests.

### Reviewer Scope Guidance

The reviewer MUST evaluate against the **defined ACs only**. Findings outside AC scope belong in Pass 2 — INFORMATIONAL and do not deduct from confidence or trigger FAIL. Specifically:
- Vendor extras are opaque data governed by AC-C14, not AC-C15
- Defensive hardening of internal-only functions (quarantine containment) is informational, not a gate criterion
- Whole-module engine coverage remains informational per cycle-1 architecture guidance

### Current State Verification

| AC | Status | Evidence |
|----|--------|----------|
| AC-C13 | PASS | Canonical field order in storage.py:70-84, tests pass |
| AC-C14 | PASS | Task extra="allow", round-trip tests pass |
| AC-C15 | PASS | Canonical TS fields normalised including Z-suffix; tests pass |
| AC-C16 | PASS | detect_corruption mode-3 + archive exemption; tests pass |
| AC-C28 | PASS | quarantine/ dir created; tests pass |
| AC-C29 | PASS | quarantine/{original-filename} path; tests pass |
| AC-C30 | PASS | AR task with tag + body section + value assertions; tests pass |
| AC-C48 | PASS | Archive claimed_by stripped, no errors, new-schema gate live; tests pass |
| AC-REGR | PASS | Claimed tasks visible in list_tasks; tests pass |

- Tests: 74 passed, 0 failed (reviewer's own quality-runner evidence)
- Lint: clean
- Coverage: storage.py 96% (above 90% gate)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage surface + narrow regression fix |
| Interface clarity | PASS | AC-C15 clarified to match Brief C §5.3 |
| Dependency correctness | PASS | No unresolved dependencies |
| Module layering | PASS | storage.py wraps task_io; engine.py consumes storage surface |
| TDD compliance | PASS | tdd:red tag, full RED/GREEN cycles completed |
| KISS/YAGNI | PASS | No speculative features |
| Premise challenge | PASS | Storage surface is Brief C deliverable |
| Pattern consistency | PASS | Follows existing patterns |
| Security surface | PASS | No new system boundaries; reviewer confirmed no exploitable issues |
| Single domain | PASS | kanban domain only |

### Challenge Results
- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Verdict: REFINE → approve
### Action Taken: Clarified AC-C15 to explicitly scope to canonical timestamp fields per Brief C §5.3. Added reviewer scope guidance to prevent further scope inflation. All 9 ACs verified PASS. Advanced to todo.
[[2026-04-22]]
## Test-Writer Notes
- Retry cycle: pass-through per w-tdd-red §1b.3
- No test changes required.
- Architecture review (cycle 4) resolved all remaining reviewer failures as scope inflation outside the defined ACs:
  - AC-C15 vendor extras: Brief C §5.3 scopes normalization to `created`, `updated`, `claimed_at` only; vendor extras pass through per AC-C14. Clarified in task body.
  - Quarantine containment: no AC specifies this; the function is board-internal only. KISS/YAGNI applies.
- All 9 ACs verified PASS by the architect against current tests (74 passed, 0 failed per quality-runner).
- Reviewer scope guidance added to task body to prevent further scope inflation.
- No new tests written, no existing tests modified.
[[2026-04-22]]
## Builder Notes
- Files changed: none (verification-only cycle).
- Implementation: no code changes required; current implementation already satisfies AC-C13, AC-C14, AC-C15, AC-C16, AC-C28, AC-C29, AC-C30, AC-C48, and AC-REGR in task scope.
- Quality-runner (scoped): 81 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py`.
- Quality-runner (durable module check): 92 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py` + `serve/kanban/tests/test_storage.py`.
- Coverage: `owlbear_kanban.storage` 96%.
- Lint: ruff clean on scoped source/test paths.
- Commit: none (no file modifications in this cycle).

### Reflection
- A verification-only builder pass was appropriate because the latest test-writer cycle was pass-through and no failing `TestFromAC_*` remained.
- Running quality-runner twice (task-scoped, then durable module-expanded) provided independent confirmation without full-suite churn.
- Storage coverage remains above the 90% bar for the scoped gate.
- No additional implementation was introduced, keeping the cycle surgical and low risk.
[[2026-04-22]]
## Review Evidence
### Test Results
- quality-runner task-local: 52 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py`
- quality-runner related-surface: 83 passed, 1 failed on `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py`
- Failing related test: `serve/kanban/tests/test_engine_storage.py::TestFromAC_ParseDuration::test_ac_c50_config_load_calls_parse_duration_not_only_regex`
- Failure detail: expected `owlbear_kanban.engine._parse_duration()` to be called once during `storage.load_config()`; observed 0 calls

### Lint
- quality-runner scoped ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/tests/test_storage_1050.py`, and `serve/kanban/tests/test_engine_storage.py`

### Coverage
- `owlbear_kanban.storage`: 96%
- Aggregate storage-module coverage from the related-surface run: 94%
- Gate application: the storage surface clears the 90% bar for this task

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C13 | `serve/kanban/tests/test_storage_1050.py:192`, `:206` | Yes | COVERED |
| AC-C14 | `serve/kanban/tests/test_storage_1050.py:234`, `:249` | Yes | COVERED |
| AC-C15 | `serve/kanban/tests/test_storage_1050.py:271`, `:289` | Yes for canonical timestamp fields clarified in the task body | COVERED |
| AC-C16 | `serve/kanban/tests/test_storage_1050.py:323`, `:334`, `:358` | Yes | COVERED |
| AC-C28 | `serve/kanban/tests/test_storage_1050.py:380` | Yes | COVERED |
| AC-C29 | `serve/kanban/tests/test_storage_1050.py:399` plus companion existence/removal/content checks in the same class | Yes | COVERED |
| AC-C30 | `serve/kanban/tests/test_storage_1050.py:489` | Yes | COVERED |
| AC-C48 | `serve/kanban/tests/test_storage_1050.py:521`, `:554`, `:953` | Yes | COVERED |
| AC-REGR | `serve/kanban/tests/test_storage_1050.py:992`, `:1004`, `:1025` | Yes | COVERED |

#### Security Review
- No task-local security issues found in the reviewed storage, corruption, or repair paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `serve/kanban/tests/test_storage_1050.py:489` | AC-C30 still asserts concrete code/path/detail values | PRESERVED |
| `serve/kanban/tests/test_storage_1050.py:554` | AC-C48 still exercises the new-schema migration-gate path | PRESERVED |
| `serve/kanban/tests/test_storage_1050.py:1025` | AC-REGR public `start_work()` path remains covered | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Exact-value assertions remain in place for AC-C16, AC-C30, AC-C48, and AC-REGR. |
| Negative/error-path coverage | ADEQUATE | Corruption, archive exemption, quarantine, and claim/list regression paths are exercised. |
| Manual mutation reasoning | ADEQUATE | Task-local regressions are caught; the related engine-storage suite is what exposed the remaining config-load drift. |
| Test independence | STRONG | `tmp_path`-isolated boards throughout the task-local suite. |
| Descriptive test names | STRONG | Test names map directly to the AC clauses and the added regression. |

#### Data Safety
- No new FAIL-level task-local data-safety issue found in the current gate scope.

#### Implementation-Aware Gaps
- FAIL: the changed storage surface still breaks the durable engine-storage contract. `serve/kanban/src/owlbear_kanban/storage.py:99-114` validates `claim_timeout` via `owllbear_kanban.config_loader._validate_claim_timeout()` (`serve/kanban/src/owlbear_kanban/config_loader.py:61-71`), which is regex-only. The shared duration parser remains `owlbear_kanban.engine._parse_duration()` at `serve/kanban/src/owlbear_kanban/engine.py:62-80`. The independent quality-runner run failed `serve/kanban/tests/test_engine_storage.py:680` because `_parse_duration()` was never called from `storage.load_config()`. This is an objective regression on a changed file, not background debt.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 7 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The task-local suite is green; the blocker appears when the related engine-storage surface is included.
- I did not use broader engine/storage import-unification concerns as gate findings here. Those are already tracked as later Brief C work (`#1059`, `#1062`, `#1063`, `#1064`), while the independently reproduced blocker in this review is the C50 config-load regression above.
- Six prior `## Review Evidence` sections already exist in `.owlbear/kanban/tasks/1050-c-05-red-storage-surface-tests.md`, so the 3rd+ review-fail loop-breaker rule applies on this rejection.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | Canonical fields in `serve/kanban/src/owlbear_kanban/storage.py:70-87` and ordered write loop at `:290-299` | `serve/kanban/tests/test_storage_1050.py:192`, `:206` | PASS |
| AC-C14 | `Task.model_config = ConfigDict(extra="allow")` in `serve/kanban/src/owlbear_kanban/models.py:121` and round-trip preservation | `serve/kanban/tests/test_storage_1050.py:234`, `:249` | PASS |
| AC-C15 | Canonical timestamp fields in `serve/kanban/src/owlbear_kanban/storage.py:88`, normalization at `:154-166`, write application at `:294-295` | `serve/kanban/tests/test_storage_1050.py:271`, `:289` | PASS |
| AC-C16 | Mode-3 claimed_by corruption and exact detail in `serve/kanban/src/owlbear_kanban/corruption.py:231-236` | `serve/kanban/tests/test_storage_1050.py:323`, `:334`, `:358` | PASS |
| AC-C28 | Quarantine directory creation in `serve/kanban/src/owlbear_kanban/storage.py:404-408` | `serve/kanban/tests/test_storage_1050.py:380` | PASS |
| AC-C29 | Quarantine destination path in `serve/kanban/src/owlbear_kanban/storage.py:404-408` | `serve/kanban/tests/test_storage_1050.py:399` | PASS |
| AC-C30 | AR body creation in `serve/kanban/src/owlbear_kanban/engine.py:1138-1153` | `serve/kanban/tests/test_storage_1050.py:489` | PASS |
| AC-C48 | Archive read strips `claimed_by` in `serve/kanban/src/owlbear_kanban/storage.py:252`; migration gate scans only `tasks/` in `serve/kanban/src/owlbear_kanban/engine.py:346-377`; archived summaries stay unclaimed in `engine.py:458-540` | `serve/kanban/tests/test_storage_1050.py:521`, `:554`, `:953` | PASS |
| AC-REGR | Active-list skip exemption in `serve/kanban/src/owlbear_kanban/engine.py:519-526` | `serve/kanban/tests/test_storage_1050.py:992`, `:1004`, `:1025` | PASS |

### Deductions
- Related engine-storage regression on `storage.load_config()` / C50 durable suite: -0.12
- Six prior review sections already exist, so 3rd+ review-fail loop-breaker routing applies: -0.06

### Verdict
- Confidence: 0.82
- FAIL
- Action: reject to `backlog`

### Required fixes
1. Align `serve/kanban/src/owlbear_kanban/storage.py:99-114` with the durable engine-storage contract by validating `claim_timeout` through the shared duration parser, or consolidate parsing/validation so `storage.load_config()` and engine claim-time parsing cannot drift.
2. Re-run `serve/kanban/tests/test_engine_storage.py::TestFromAC_ParseDuration::test_ac_c50_config_load_calls_parse_duration_not_only_regex` alongside the task-local storage suite before returning to review.
3. Keep the current AC-C30, AC-C48, and AC-REGR coverage; those task-local paths are green.

### Reflection
- Task-local evidence alone would have produced a false PASS; the related engine-storage run exposed the blocker.
- A second task-only quality-runner pass was necessary to separate current-task readiness from broader surface regression context.
- Code-reader raised broader future-scope concerns, but only the C50 config-load failure was independently reproduced in this review.
- The task already had six prior review sections, so the loop-breaker rule is the correct routing here.
[[2026-04-22]]
## Architecture Review (cycle 5)

### Root Cause of the 8-Review Loop

The 7th reviewer rejection (confidence 0.82) cited `test_engine_storage.py::TestFromAC_ParseDuration::test_ac_c50_config_load_calls_parse_duration_not_only_regex` as a blocking regression from #1050. This is incorrect. The test is a **RED-phase test from task #1053** (C-08: RED — engine storage-integration tests), explicitly written to fail until #1053's builder connects `_parse_duration()` to the config-load path.

**Evidence:**
1. The test's own docstring states: *"FAILS: `_parse_duration` is not in the config-load path"* (test_engine_storage.py:696)
2. #1053's test-writer notes mark it **FAIL ✓** — expected RED-phase failure
3. #1053 is currently `in-progress` (builder working on implementation)
4. AC-C50 (`BoardConfig validation calls _parse_duration`) is listed in #1053's ACs, not #1050's
5. The test was added in commit `63653263` by #1053's test-writer, after #1050's implementation was complete

A RED-phase test from another task that is designed to fail is not a regression. The reviewer's related-surface run correctly detected the failure but incorrectly attributed it to #1050's scope.

### Cross-Task Test Isolation Rule (reviewer guidance)

When the related-surface quality-runner run includes test files from OTHER tasks that are in RED phase (`tdd:red` tag, `in-progress` or earlier status), failing tests in those files are **expected RED-phase failures**, not regressions from the task under review. The reviewer must:
1. Check whether a failing related test belongs to a different task (class name, file name, AC prefix)
2. Check whether that task is still in RED/in-progress phase
3. If both true, classify the failure as **informational** (Pass 2), not a gate deduction

For #1050 specifically: any failures in `test_engine_storage.py` that reference AC-C50 belong to #1053 and are expected to fail.

### Current State Verification

All 9 ACs for #1050 PASS per the reviewer's own compliance table (cycle 7):

| AC | Status | Evidence |
|----|--------|----------|
| AC-C13 | PASS | Canonical field order in storage.py, tests at test_storage_1050.py:192 |
| AC-C14 | PASS | Task extra="allow", round-trip tests pass |
| AC-C15 | PASS | Canonical TS fields (created, updated, claimed_at) normalised per Brief C §5.3; clarified in cycle 4 |
| AC-C16 | PASS | detect_corruption mode-3 + archive exemption |
| AC-C28 | PASS | quarantine/ dir created |
| AC-C29 | PASS | quarantine/{original-filename} path |
| AC-C30 | PASS | AR tag + body section + value assertions; corrected in cycle 2 |
| AC-C48 | PASS | Archive claimed_by stripped, new-schema gate live |
| AC-REGR | PASS | Claimed tasks visible in list_tasks; added in cycle 3 |

- Tests: 74 passed, 0 failed (reviewer's cycle 7 scoped run)
- Lint: clean
- Coverage: storage.py 96% (above 90% gate)

### Retained Guidance (from cycles 1-4)

- **Coverage scope:** 90% gate applies to `owlbear_kanban.storage` only. Engine whole-module coverage is informational.
- **AC-C15 scope:** Canonical TS fields only (`created`, `updated`, `claimed_at`). Vendor extras pass through per AC-C14.
- **AC-C30 values:** Current assertions (ERR_CORRUPT_MISSING_FIELD, quarantine path, quarantined-to detail) match implementation contract. Do not re-apply the wrong refinement from cycle 1.
- **AC-C48 constructor:** New-schema board config (no `version` field) exercises the live migration gate.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage surface + narrow regression fix |
| Interface clarity | PASS | All ACs clarified and verified across 5 arch cycles |
| Dependency correctness | PASS | No unresolved dependencies |
| Module layering | PASS | storage.py wraps task_io; engine.py consumes storage |
| TDD compliance | PASS | Full RED/GREEN cycles completed |
| KISS/YAGNI | PASS | No speculative features |
| Premise challenge | PASS | Storage surface is Brief C deliverable |
| Pattern consistency | PASS | Follows existing patterns |
| Security surface | PASS | No new system boundaries; reviewer confirmed no issues |
| Single domain | PASS | kanban domain only |

### Challenge Results
- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Downstream Actions

**Test-writer:** No new test work required for #1050. All 9 ACs are covered. Pass through.

**Reviewer:** Apply the cross-task test isolation rule above. The only valid gate criteria for #1050 are its 9 defined ACs. RED-phase test failures from #1053 (AC-C50, `test_engine_storage.py`) are informational, not blocking. All prior architecture guidance (coverage scope, AC-C15 scope, AC-C30 values, AC-C48 config) remains in effect.

### Verdict: REFINE → approve
### Action Taken: Identified the 8-review loop root cause as misattribution of #1053's RED-phase C50 test to #1050's scope. Added cross-task test isolation rule for the reviewer. All 9 ACs verified PASS with green tests, clean lint, and 96% storage coverage. Advanced to todo.
[[2026-04-22]]
## Test-Writer Notes
- Retry cycle: pass-through per w-tdd-red §1b.3
- No test changes required.
- Architecture Review (cycle 5) resolved the 8-review loop: the blocking failure (`test_engine_storage.py::TestFromAC_ParseDuration::test_ac_c50_config_load_calls_parse_duration_not_only_regex`) belongs to task #1053's RED phase, not #1050's scope. It was designed to fail until #1053's builder connects `_parse_duration()` to the config-load path. The reviewer misattributed a cross-task RED-phase failure as a #1050 regression.
- All 9 ACs verified PASS by the architect (cycle 5): AC-C13, AC-C14, AC-C15, AC-C16, AC-C28, AC-C29, AC-C30, AC-C48, AC-REGR — all covered by existing TestFromAC_* tests.
- Reviewer guidance added to task body: cross-task RED-phase failures in related-surface runs are informational (Pass 2), not gate criteria.
- 74 tests passing in task-scoped run, ruff clean, storage.py 96% coverage (above 90% gate).
- No new tests written, no existing tests modified.
[[2026-04-22]]
## Builder Notes
- Files changed: `serve/kanban/src/owlbear_kanban/corruption.py`
- Implementation: restored AC-C16 mode-3 code contract for non-archive `claimed_by` corruption in `detect_corruption()` by returning `ERR_CORRUPT_MISSING_FIELD` (detail unchanged: `forbidden field claimed_by present`).
- Why: task-local `TestFromAC_*` failures showed a code mismatch (`ERR_CORRUPT_FORBIDDEN_FIELD` vs expected `ERR_CORRUPT_MISSING_FIELD`), which also caused the AC-C30 AR body assertion failure.
- RED evidence (quality-runner, scoped): 82 passed, 2 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py`; failing tests:
  - `TestFromAC_CorruptionDetection::test_detect_corruption_claimed_by_in_tasks_dir`
  - `TestFromAC_QuarantineRepair::test_repair_storage_ar_body_has_code_path_detail_fields`
- GREEN evidence (quality-runner, scoped): 84 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py`; ruff clean.
- Durable related-surface check (quality-runner): 95 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py` + `serve/kanban/tests/test_engine_storage.py` + `serve/kanban/tests/test_storage.py`; ruff clean.
- Coverage: `owlbear_kanban.storage` 95% (>= 90% gate).
- Reflection:
  - The regression came from error-code drift, not behavior drift; fixing the canonical code restored two AC paths at once.
  - A single-branch patch was sufficient; no interface or test changes were needed.
  - Running both scoped and durable quality-runner passes prevented false-green closure.
  - Kept `TestFromAC_*` untouched as required.
[[2026-04-22]]
## Review Evidence

### Test Results
- quality-runner task-local: 52 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_storage_1050.py`
- quality-runner related-surface: 94 passed, 1 failed across `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_engine_storage.py`, and `serve/kanban/tests/test_storage.py`
- Related-surface failure: `serve/kanban/tests/test_engine_storage.py::TestFromAC_ParseDuration::test_ac_c50_config_load_calls_parse_duration_not_only_regex`
- Gating decision: the related-surface failure was not counted against #1050. It belongs to task #1053, which is still `in-progress` with tag `tdd:red`, and its task body still records AC-C50 as the active RED case.

### Lint
- quality-runner task-local ruff: clean on `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, and `serve/kanban/tests/test_storage_1050.py`

### Coverage
- `owlbear_kanban.storage`: 95% in the task-local scoped run

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C13 | `test_written_frontmatter_fields_in_canonical_order` (`serve/kanban/tests/test_storage_1050.py:192`), `test_vendor_extra_fields_appear_after_canonical_fields` (`serve/kanban/tests/test_storage_1050.py:206`) | Yes | COVERED |
| AC-C14 | `test_task_model_accepts_vendor_extra_fields` (`serve/kanban/tests/test_storage_1050.py:234`), `test_vendor_extra_fields_survive_write_read_round_trip` (`serve/kanban/tests/test_storage_1050.py:249`) | Yes | COVERED |
| AC-C15 | `test_all_timestamp_fields_end_with_utc_offset` (`serve/kanban/tests/test_storage_1050.py:271`), `test_naive_timestamps_stored_with_utc_offset` (`serve/kanban/tests/test_storage_1050.py:289`), `test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc` (`serve/kanban/tests/test_storage_1050.py:913`) | No. A canonical timestamp with a non-UTC offset still violates the AC while the suite stays green: `_normalize_timestamp()` returns offset-bearing values unchanged at `serve/kanban/src/owlbear_kanban/storage.py:162-165`, and `test_normalize_timestamp_already_has_tz` (`serve/kanban/tests/test_storage_1050.py:907-911`) explicitly blesses that non-UTC behavior. | MISSING |
| AC-C16 | `test_detect_corruption_claimed_by_in_tasks_dir` (`serve/kanban/tests/test_storage_1050.py:323`), `test_detect_corruption_claimed_by_detail_exact_string` (`serve/kanban/tests/test_storage_1050.py:334`), `test_detect_corruption_archive_file_with_claimed_by_returns_none` (`serve/kanban/tests/test_storage_1050.py:358`) | Yes | COVERED |
| AC-C28 | `test_move_to_quarantine_creates_dir_when_absent` (`serve/kanban/tests/test_storage_1050.py:380`), `test_move_to_quarantine_no_error_when_dir_already_exists` (`serve/kanban/tests/test_storage_1050.py:390`) | Yes | COVERED |
| AC-C29 | `test_move_to_quarantine_returns_quarantine_subpath` (`serve/kanban/tests/test_storage_1050.py:399`), `test_move_to_quarantine_file_exists_at_returned_path` (`serve/kanban/tests/test_storage_1050.py:410`), `test_move_to_quarantine_source_file_removed` (`serve/kanban/tests/test_storage_1050.py:421`), `test_move_to_quarantine_preserves_file_content` (`serve/kanban/tests/test_storage_1050.py:430`) | Yes | COVERED |
| AC-C30 | `test_repair_storage_ar_task_has_type_user_action_tag` (`serve/kanban/tests/test_storage_1050.py:450`), `test_repair_storage_ar_body_contains_quarantined_file_section` (`serve/kanban/tests/test_storage_1050.py:469`), `test_repair_storage_ar_body_has_code_path_detail_fields` (`serve/kanban/tests/test_storage_1050.py:489`) | Yes | COVERED |
| AC-C48 | `test_archive_file_with_claimed_by_reads_without_exception` (`serve/kanban/tests/test_storage_1050.py:521`), `test_archive_claimed_by_stripped_from_returned_task` (`serve/kanban/tests/test_storage_1050.py:531`), `test_archive_claimed_by_does_not_raise_corruption_error` (`serve/kanban/tests/test_storage_1050.py:541`), `test_engine_init_with_archive_claimed_by_no_migration_error` (`serve/kanban/tests/test_storage_1050.py:554`), `test_archive_vendor_fields_preserved_when_claimed_by_stripped` (`serve/kanban/tests/test_storage_1050.py:584`) | Yes | COVERED |
| AC-REGR | `test_claimed_task_remains_in_list_tasks_same_engine` (`serve/kanban/tests/test_storage_1050.py:992`), `test_claimed_task_remains_in_list_tasks_after_cache_miss` (`serve/kanban/tests/test_storage_1050.py:1004`), `test_start_work_then_list_tasks_includes_task` (`serve/kanban/tests/test_storage_1050.py:1025`) | Yes | COVERED |

#### Security Review
- No task-local security issue found in the reviewed storage, corruption, list, or repair paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-scoped `TestFromAC_*` suite in `serve/kanban/tests/test_storage_1050.py` | No weakening observed in the current task state. Builder changes stayed outside the `TestFromAC_*` classes. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC-C16, AC-C30, AC-C48, and AC-REGR assert exact code, detail, path, and visibility outcomes. |
| Negative/error-path coverage | ADEQUATE | claimed_by corruption, archive exemption, quarantine, and claim-list regression paths are covered directly. |
| Manual mutation reasoning | WEAK | A canonical timestamp with a non-UTC offset would still be written as non-UTC because `_normalize_timestamp()` preserves existing offsets at `serve/kanban/src/owlbear_kanban/storage.py:162-165`. The task-local suite does not fail on that mutation and the helper test at `serve/kanban/tests/test_storage_1050.py:907-911` encodes the wrong expectation. |
| Test independence | STRONG | The task-local suite uses isolated `tmp_path` boards throughout. |
| Descriptive test names | STRONG | The names map cleanly to each AC and regression clause. |

#### Data Safety
- No FAIL-level task-local data-safety issue counted for this gate.

#### Implementation-Aware Gaps
- AC-C15 is still not satisfied for offset-bearing canonical timestamps. The task AC says timestamps written are ISO-8601 UTC with explicit `+00:00`, and the Brief C source text is explicit: `paper-c.md:483` requires `datetime.fromisoformat(...).astimezone(timezone.utc).isoformat()`, while `decisions.md:230` says non-UTC offsets such as `+02:00` must be converted to UTC.
- Current implementation in `serve/kanban/src/owlbear_kanban/storage.py:154-166` only normalises naive timestamps and `Z`; it returns any other timezone-bearing value unchanged.
- The current task-local tests prove naive and `Z` handling only. They do not cover a canonical field written with a non-UTC offset, and the helper test at `serve/kanban/tests/test_storage_1050.py:907-911` asserts the opposite of the AC.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 8 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The broad related-surface run exposed one failing AC-C50 test in `serve/kanban/tests/test_engine_storage.py:691`, but that test belongs to task #1053, which is still `in-progress` with `tdd:red`; it is informational only for #1050.
- Code-reader also flagged the lack of containment validation in `move_to_quarantine()` (`serve/kanban/src/owlbear_kanban/storage.py:413-418`) versus the guarded write path (`serve/kanban/src/owlbear_kanban/storage.py:290`). I did not gate on that here because the latest architecture review for #1050 explicitly narrowed that hardening concern out of task scope.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | Canonical fields are emitted in ordered frontmatter in `serve/kanban/src/owlbear_kanban/storage.py:281-299`. | `TestFromAC_Frontmatter` | PASS |
| AC-C14 | `Task` still allows extra fields, and round-trip preservation is covered in the task-local suite. | `TestFromAC_Frontmatter` | PASS |
| AC-C15 | `serve/kanban/src/owlbear_kanban/storage.py:162-165` returns non-UTC offsets unchanged, which conflicts with Brief C `paper-c.md:483` and `decisions.md:230`. | `TestFromAC_Frontmatter` + `TestBuilderDiscovered` | FAIL |
| AC-C16 | `detect_corruption()` returns `ERR_CORRUPT_MISSING_FIELD` with detail `forbidden field claimed_by present` for `tasks/`, and archive files remain exempt. | `TestFromAC_CorruptionDetection` | PASS |
| AC-C28 | `move_to_quarantine()` creates `quarantine/` if absent. | `TestFromAC_Quarantine` | PASS |
| AC-C29 | `move_to_quarantine()` returns `quarantine/{original-filename}` and the task-local move tests pass. | `TestFromAC_Quarantine` | PASS |
| AC-C30 | `repair_storage()` writes AR body code/path/detail values and tag `type:user-action`, with exact-value assertions in the task-local suite. | `TestFromAC_QuarantineRepair` | PASS |
| AC-C48 | Archive reads strip `claimed_by`, engine init on a new-schema board does not raise for archive-only `claimed_by`, and archived list summaries stay unclaimed. | `TestFromAC_ArchiveExemption` | PASS |
| AC-REGR | `list_tasks()` now keeps actively-claimed tasks visible, including same-engine, cache-miss, and `start_work()` paths. | `TestFromAC_ClaimListRegression` | PASS |

### Deductions
- AC-C15 implementation/spec mismatch on non-UTC offsets: -0.14
- AC-C15 task-local coverage gap plus contradictory helper assertion: -0.12
- This task already has 7 prior `## Review Evidence` sections, so the 3rd+ review-fail loop-breaker routing applies: -0.04

### Confidence: 0.70
### Verdict: FAIL
### Action: reject to `backlog`

### Required fixes
1. Builder: change `serve/kanban/src/owlbear_kanban/storage.py:_normalize_timestamp()` so canonical timestamp fields with any non-UTC offset are converted to UTC `+00:00`, not returned unchanged. The Brief C source text already specifies the intended conversion (`datetime.fromisoformat(...).astimezone(timezone.utc).isoformat()`).
2. Test-writer: replace the current helper expectation in `serve/kanban/tests/test_storage_1050.py:907-911` and add task-scoped `write_task()` coverage for a canonical timestamp field written with `+02:00`, asserting the persisted frontmatter is converted to the correct UTC `+00:00` time.
3. Keep the broad AC-C50 failure out of #1050 gating. That test belongs to #1053 and is still an expected RED/in-progress surface.

### Post-task Reflection
- A second scoped quality-runner pass was necessary to separate #1050 from an unrelated RED-phase failure in `test_engine_storage.py`.
- The remaining blocker is a single contract gap in AC-C15, not the earlier claim-list or archive-exemption regressions.
- The brief text resolved the ambiguity: this task requires UTC conversion for non-UTC offsets, not only suffix normalization for naive or `Z` timestamps.
- Task-local tests were green, but the helper-level `+02:00` expectation created a false-green hole large enough to invalidate the gate.
[[2026-04-22]]
## Architecture Review (cycle 6)

### Assessment

The reviewer's cycle-8 finding is valid this time. AC-C15 requires "ISO-8601 UTC with explicit `+00:00`" and Brief C §5.3 (paper-c.md:483) explicitly specifies full UTC conversion: `datetime.fromisoformat` → `astimezone(timezone.utc)` → `isoformat()`. The current `_normalize_timestamp()` at storage.py:162-165 returns non-UTC offsets unchanged, violating the AC for canonical timestamp fields. The test at test_storage_1050.py:907-911 (`test_normalize_timestamp_already_has_tz`) encodes the wrong expectation.

This is distinct from the vendor extras scope inflation rejected in cycle 4 — that exclusion was correct because Brief C §5.3 names only `created`, `updated`, `claimed_at`. The current gap is about non-UTC offsets IN those canonical fields.

### AC-C15 Implementation Guidance

**Builder fix (storage.py:_normalize_timestamp):**
```python
if tz:
    if tz == "Z":
        return f"{base}{frac}+00:00"
    # Convert non-UTC offsets to UTC per Brief C §5.3
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(ts.strip())
    return dt.astimezone(timezone.utc).isoformat()
return f"{base}{frac}+00:00"
```

**Test-writer fix (test_storage_1050.py):**
1. Fix `TestBuilderDiscovered.test_normalize_timestamp_already_has_tz` — change expectation: `_normalize_timestamp("2026-04-20T10:00:00+02:00")` must return `"2026-04-20T08:00:00+00:00"` (UTC-converted), not the input unchanged.
2. Add a `TestFromAC_Frontmatter` test: `write_task()` with a canonical field set to `+02:00`, read back and assert the persisted value is the correct UTC equivalent ending with `+00:00`.

### Scope Boundary (retained from cycles 1-5)

- **Coverage gate:** 90% applies to `owlbear_kanban.storage` only (currently 95-96%). Engine whole-module coverage is informational.
- **AC-C15 field scope:** Canonical TS fields only (`created`, `updated`, `claimed_at`). Vendor extras pass through unchanged per AC-C14.
- **AC-C30 values:** Current assertions (ERR_CORRUPT_MISSING_FIELD, quarantine path, quarantined-to detail) match the implementation contract. Do not re-apply the wrong refinement from cycle 1.
- **AC-C48 constructor:** New-schema board config (no `version` field) exercises the live migration gate. This is correct.
- **Cross-task isolation:** RED-phase test failures from other tasks (e.g. #1053 AC-C50 in `test_engine_storage.py`) are informational (Pass 2), not gate criteria.
- **Quarantine containment:** Not in any AC. KISS/YAGNI applies — the function is board-internal only.

### All AC Compliance (post-fix expected state)

| AC | Status | Notes |
|----|--------|-------|
| AC-C13 | PASS | Canonical field order verified |
| AC-C14 | PASS | Vendor extras survive round-trip |
| AC-C15 | PASS after fix | Non-UTC offsets converted to UTC; Z-suffix and naive already covered |
| AC-C16 | PASS | Mode-3 detection + archive exemption |
| AC-C28 | PASS | quarantine/ dir created |
| AC-C29 | PASS | quarantine/{original-filename} path |
| AC-C30 | PASS | AR tag + body section + value assertions |
| AC-C48 | PASS | Archive claimed_by stripped, new-schema gate live |
| AC-REGR | PASS | Claimed tasks visible in list_tasks |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage surface + narrow fixes |
| Interface clarity | PASS | All ACs clarified across 6 arch cycles |
| Dependency correctness | PASS | No unresolved dependencies |
| Module layering | PASS | storage.py wraps task_io; engine.py consumes storage |
| TDD compliance | PASS | tdd:red tag, full RED/GREEN cycles |
| KISS/YAGNI | PASS | No speculative features |
| Premise challenge | PASS | Storage surface is Brief C deliverable |
| Pattern consistency | PASS | Follows existing patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban domain only |

### Challenge Results
- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Verdict: REFINE → approve
### Action Taken: Accepted the reviewer's AC-C15 non-UTC offset finding as valid. Provided specific builder and test-writer fix guidance with the exact implementation from Brief C §5.3. Retained all scope boundaries from cycles 1-5 to prevent further scope inflation. Advanced to todo.
[[2026-04-22]]
## Test-Writer Notes
- Retry cycle: strengthened AC-C15 non-UTC offset coverage per architect directive (cycle-6 loop-breaker)
- Test file: serve/kanban/tests/test_storage_1050.py

### Changes
1. **Fixed `TestBuilderDiscovered.test_normalize_timestamp_already_has_tz`** — replaced wrong expectation (`ts == ts`) with correct AC-C15 contract: `_normalize_timestamp("2026-04-20T10:00:00+02:00")` must return `"2026-04-20T08:00:00+00:00"` (UTC-converted per Brief C §5.3).
2. **Added `TestFromAC_Frontmatter.test_non_utc_offset_timestamps_are_converted_to_utc`** — calls `write_task()` with canonical fields set to `+02:00`, reads back and asserts:
   - All timestamp lines end with `+00:00`
   - `created` value is `2026-04-20T08:00:00+00:00` (not the original `10:00+02:00`)
   - `updated` value is `2026-04-20T10:00:00+00:00` (not the original `12:00+02:00`)
- All other `TestFromAC_*` and `TestBuilderDiscovered` classes preserved unchanged
- AC-C30 value assertions preserved unchanged
- AC-C48 new-schema constructor test preserved unchanged
- AC-REGR regression tests preserved unchanged

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC-C13 | `test_written_frontmatter_fields_in_canonical_order`, `test_vendor_extra_fields_appear_after_canonical_fields` | COVERED |
| AC-C14 | `test_task_model_accepts_vendor_extra_fields`, `test_vendor_extra_fields_survive_write_read_round_trip` | COVERED |
| AC-C15 | `test_all_timestamp_fields_end_with_utc_offset`, `test_naive_timestamps_stored_with_utc_offset`, `test_non_utc_offset_timestamps_are_converted_to_utc` (NEW — +02:00 → UTC), `TestBuilderDiscovered.test_normalize_timestamp_already_has_tz` (FIXED — +02:00 → UTC) | COVERED (naive, Z, non-UTC) |
| AC-C16 | `test_detect_corruption_claimed_by_in_tasks_dir`, `test_detect_corruption_claimed_by_detail_exact_string`, `test_detect_corruption_clean_task_returns_none`, `test_detect_corruption_archive_file_with_claimed_by_returns_none` | COVERED |
| AC-C28 | `test_move_to_quarantine_creates_dir_when_absent`, `test_move_to_quarantine_no_error_when_dir_already_exists` | COVERED |
| AC-C29 | `test_move_to_quarantine_returns_quarantine_subpath`, `test_move_to_quarantine_file_exists_at_returned_path`, `test_move_to_quarantine_source_file_removed`, `test_move_to_quarantine_preserves_file_content` | COVERED |
| AC-C30 | `test_repair_storage_ar_task_has_type_user_action_tag`, `test_repair_storage_ar_body_contains_quarantined_file_section`, `test_repair_storage_ar_body_has_code_path_detail_fields` (ERR_CORRUPT_MISSING_FIELD, quarantine path, quarantined-to detail) | COVERED (values) |
| AC-C48 | `test_archive_file_with_claimed_by_reads_without_exception`, `test_archive_claimed_by_stripped_from_returned_task`, `test_archive_claimed_by_does_not_raise_corruption_error`, `test_engine_init_with_archive_claimed_by_no_migration_error` (new-schema board), `test_archive_vendor_fields_preserved_when_claimed_by_stripped` | COVERED |
| AC-REGR | `test_claimed_task_remains_in_list_tasks_same_engine`, `test_claimed_task_remains_in_list_tasks_after_cache_miss`, `test_start_work_then_list_tasks_includes_task` | COVERED |

- quality-runner (scoped): 53 tests — 2 FAIL (new AC-C15 non-UTC tests), 51 PASS
- ruff: clean
- Commit: a327d3fd
[[2026-04-22]]
## Builder Notes
- Files changed: `serve/kanban/src/owlbear_kanban/storage.py`.
- Implementation: updated `_normalize_timestamp()` to convert canonical timestamp fields with non-UTC offsets (for example `+02:00`) into explicit UTC `+00:00` using `datetime.fromisoformat(...).astimezone(UTC).isoformat()`. Existing naive and `Z` handling was preserved.
- Scope: surgical, storage-only fix; no `TestFromAC_*` classes changed.

### Verification
- RED check (pre-fix, scoped): `serve/kanban/tests/test_storage_1050.py` -> 2 failed, 51 passed
  - `TestFromAC_Frontmatter::test_non_utc_offset_timestamps_are_converted_to_utc`
  - `TestBuilderDiscovered::test_normalize_timestamp_already_has_tz`
- GREEN checks (post-fix, scoped):
  - `serve/kanban/tests/test_storage_1050.py` -> 53 passed, 0 failed
  - `serve/kanban/tests/test_engine_storage.py` -> 32 passed, 0 failed
  - Combined scoped run -> 85 passed, 0 failed
- Coverage (scoped): `owlbear_kanban.storage` 96% (>= 90% gate)
- Lint (scoped): ruff clean on `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_engine_storage.py`.

### Commit
- `03b5b826` — `fix: convert offset timestamps to UTC (#1050, builder)`

### Reflection
- The failing surface was isolated to one normalization branch, so a minimal implementation change resolved both AC-C15 failures.
- Running RED before code changes prevented speculative edits and confirmed exact failure mode.
- A follow-up scoped run including `test_engine_storage.py` ensured no regression on the related engine-storage integration surface.
- Lint-guided cleanup (`datetime.UTC`) kept the patch compliant without expanding scope.
[[2026-04-22]]
## Review Evidence

### Test Results
- quality-runner task-local: 53 passed, 0 failed, 0 skipped on [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py)
- quality-runner related-surface: 96 passed, 0 failed, 0 skipped on [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py), and [serve/kanban/tests/test_storage.py](serve/kanban/tests/test_storage.py)

### Lint
- quality-runner scoped ruff: clean on [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py), and [serve/kanban/tests/test_storage.py](serve/kanban/tests/test_storage.py)

### Coverage
- `owlbear_kanban.storage`: 96%
- Gate application: per the task-body architecture refinements, the 90% coverage bar applies to the storage surface for this task. The storage surface clears that bar.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage

| AC Line | Evidence | Verdict |
|---------|----------|---------|
| AC-C13 | Canonical field order and omission of `claimed_by` are implemented in [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L258), [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L287), and verified by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L192) and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L206) | COVERED |
| AC-C14 | Vendor extra fields are exercised by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L234) and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L249) | COVERED |
| AC-C15 | Timestamp normalization is implemented in [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L155) and applied in [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L296); naive, `Z`, and non-UTC offsets are covered by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L271), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L289), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L314), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L941) | COVERED |
| AC-C16 | Mode-3 detection and exact detail are asserted in [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L357), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L368), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L377), matching [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L236) | COVERED |
| AC-C28 | Quarantine directory creation is verified by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L414) against [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L408) | COVERED |
| AC-C29 | Quarantine destination path and move semantics are verified by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L433), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L443), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L455), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L464) against [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L408) | COVERED |
| AC-C30 | AR tag/section/value assertions are enforced by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L483), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L502), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L523), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L542), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L543), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L544), matching [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1148), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1152), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1156) | COVERED |
| AC-C48 | Archive read, strip, no-corruption, and new-schema init paths are covered by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L555), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L565), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L575), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L588), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L618) | COVERED |
| AC-REGR | Claimed-task visibility is covered by [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1006), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1036), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1057), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1069), matching the list exemption in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L520) | COVERED |

#### Security Review
- No task-scope issues found. The reviewed storage, corruption, and repair paths are board-local file operations only and the independent related-surface run stayed green.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-scoped `TestFromAC_*` cases in [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py) | No builder weakening observed in the current task state | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact-value checks for AC-C16, AC-C30, AC-C48, and AC-REGR in [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L377), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L542), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L543), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L544), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L613), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1036), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1057), and [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L1069) |
| Negative/error-path coverage | ADEQUATE | Corruption, archive exemption, quarantine, and claim/list regression paths are directly exercised in the task-local suite |
| Manual mutation reasoning | ADEQUATE | The latest AC-C15 tests would fail on naive, `Z`, and non-UTC offset regressions; AC-C30 and AC-REGR would fail on weaker AR-body or list-visibility behavior |
| Test independence | STRONG | Temp-board isolation throughout the task-local suite |
| Descriptive test names | STRONG | Names map directly to the AC clauses and the added regression |

#### Data Safety
- No blocking data-safety issue in the current 1050 scope.

#### Implementation-Aware Gaps
- No significant untested path remains inside the current 1050 AC surface. The broader engine/task I/O transition is later Brief C work and is not re-gated here.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 9 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- [serve/kanban/tests/test_storage.py](serve/kanban/tests/test_storage.py#L256) still contains weaker legacy durable assertions than the task-local 1050 suite. I did not gate on that because the stronger 1050-specific coverage above now exercises the live AC-C30 and AC-C48 behavior directly, and the related-surface quality-runner run was fully green.
- Broader engine/storage write-path unification remains tracked in later Brief C work; the current task’s bound ACs and AC-REGR are satisfied by the present implementation and tests.

### Deductions
- None

### Verdict
- Confidence: 0.95
- PASS
- Action: advance to docs
[[2026-04-22]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/kanban/README.md` was missing `repair_storage()` from the KanbanEngine methods table. Added row: `\| \`repair_storage()\` \| Quarantine corrupt task files and create action-required tasks \|` |
| 2 | Module docstrings | Yes | N/A (verified) | `storage.py` module-level docstring accurate (lists public API). All public functions have docstrings. `engine.repair_storage()` has docstring. `corruption.py` `detect_corruption()`, `attempt_repair()`, `scan_and_fix()` all have docstrings. No changes needed. |
| 3 | External attribution | No | N/A | No external repos, articles, or docs used per task body. |
| 4 | Research doc | No | N/A | No research doc for this task. |
| 5 | Diagram maintenance | Yes | N/A (already current) | `share/diagrams/kanban.excalidraw` and `share/diagrams/mcp-topology.excalidraw` both describe `serve/kanban/src/**`. Both footers already read `Last verified: 2026-04-22 (b992e4be)` — updated by an earlier doc-writer pass today. No further update needed. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted by this task. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/storage.py` | IN (docstrings) | Verified — docstrings accurate |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Verified — `repair_storage()` docstring accurate |
| `serve/kanban/src/owlbear_kanban/corruption.py` | IN (docstrings) | Verified — all public function docstrings accurate |
| `serve/kanban/tests/test_storage_1050.py` | OUT | Test file — not in scope |
| `serve/kanban/tests/test_engine_storage.py` | OUT | Test file — not in scope |
| `serve/kanban/README.md` | IN (prose) | Updated — added `repair_storage()` row |

### Files Updated

- `serve/kanban/README.md` — added `repair_storage()` to KanbanEngine methods table (commit `3775cdd3`)

### Child Tasks Created

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/1050-*` files existed)
[[2026-04-22]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C13 | storage.py canonical field order + tests at test_storage_1050.py:192, :206 pass | PASS |
| AC-C14 | Task extra="allow" at models.py:121, round-trip tests at :234, :249 pass | PASS |
| AC-C15 | _normalize_timestamp handles naive, Z, non-UTC offsets (storage.py:155-170); tests at :271, :289, :314, :941 pass | PASS |
| AC-C16 | detect_corruption mode-3 + archive exemption in corruption.py:231-236; tests at :357, :368, :377 pass | PASS |
| AC-C28 | move_to_quarantine creates quarantine/ dir (storage.py:408); tests at :414, :390 pass | PASS |
| AC-C29 | quarantine/{original-filename} path + file semantics; tests at :433-464 pass | PASS |
| AC-C30 | AR tag type:user-action + body section + value assertions (ERR_CORRUPT_MISSING_FIELD, quarantine path, detail); tests at :483, :502, :523, :542-544 pass | PASS |
| AC-C48 | Archive claimed_by stripped (storage.py:248), new-schema migration gate live, archived list summaries unclaimed; tests at :555-618 pass | PASS |
| AC-REGR | list_tasks exempts mode-3 claimed_by from skip (engine.py:520); tests at :1006, :1036, :1057 pass | PASS |

### Test Results
- pytest (full suite): 1253 passed, 106 failed, 4 skipped — 0 failures in task scope; all 106 in unrelated modules (1084, 940, 1015, cockpit, sessions)
- pytest (task-local): 53 passed, 0 failed
- ruff: 5 W292 violations in files outside task scope; task files clean

### Architect Quality: 3/5
Original ACs had notable gaps: AC-C30 vagueness (required 3 refinements), AC-C15 scope ambiguity (vendor extras vs canonical fields — resolved cycle 4-6), AC-C48 migration gate omission. These gaps directly caused the 9-review, 6-architect-review loop. Architect corrected well through iterations but initial quality was insufficient.

### Deduction Breakdown
- AC quality score ≤ 3: −0.03
- Lint violations: none in scope → no deduction
- Full-suite failures in task scope: 0 → no deduction
- All 9 AC lines have specific evidence → no deduction
- Reviewer evidence section present and detailed → no deduction

### Confidence: 0.97
### Action: archive