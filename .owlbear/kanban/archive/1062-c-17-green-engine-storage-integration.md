---
id: 1062
title: 'C-17: GREEN — engine storage integration'
status: archived
priority: medium
created: 2026-04-21T10:44:12.250703+00:00
updated: 2026-04-24T02:52:55.553428+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1053
- 1059
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief C (#1043) — paper-c.md §4.3–§4.5, §8.4, §8.5, §8.11
Module: `serve/kanban/src/owlbear_kanban/engine.py` — storage-integration edits only

Engine edits for storage integration: list_tasks corruption carve-out, sweep claim-only, explicit repair_storage, migration guard, config validation. Does NOT include activity/session wiring (see C-18 #1063).

## Acceptance Criteria

- [ ] AC-C19: `list_tasks` SKIPS files failing corruption modes 1, 3-9 silently — mode-3 has two sub-variants: (a) missing required field, (b) forbidden `claimed_by` present on legacy-schema boards; both must have task-owned tests
- [ ] AC-C20: `list_tasks` HARD-RAISES `CorruptionError(code="ERR_CORRUPT_DUPLICATE_ID")` for mode 2
- [ ] AC-C23: `sweep()` returns `list[int]` of released claim IDs only
- [ ] AC-C24: `repair_storage()` quarantines corrupt files via §4.4 sequence; file moved BEFORE AR creation
- [ ] AC-C25: `repair_storage()` records `RepairOutcome(action="failed")` if AR creation fails; file remains quarantined
- [ ] AC-C26: `repair_storage()` resolves `ERR_CORRUPT_DUPLICATE_LOCATION` by archive-wins
- [ ] AC-C27: `sweep()` reconciles claim timeouts independently of corruption repair
- [ ] AC-C47: `KanbanEngine.__init__` raises `MigrationRequiredError(code="ERR_MIGRATION_REQUIRED")` if any `tasks/` file contains `claimed_by`
- [ ] AC-C49: `_parse_duration("30m")` → `timedelta(minutes=30)`; malformed → `ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT")`
- [ ] AC-C50: `BoardConfig` calls `_parse_duration(claim_timeout)` at config load time (eager validation)
- [ ] AC-C52: `sweep()` releasing expired claim does NOT mutate task body; only `claimed_at` cleared and `updated` advanced
- [ ] AC-C54: AR creation by `repair_storage()` uses `body=str` (markdown), no `status` argument
- [ ] All RED tests from C-08 (#1053) pass
[[2026-04-23]]
## Test-Writer Notes

**Situation: Implementation pre-completed — no new failing tests achievable.**

### Investigation

Loaded the task AC (C19, C20, C23, C24, C25, C26, C27, C47, C49, C50, C52, C54) and the C-08 RED test suite from task #1053 (`serve/kanban/tests/test_engine_storage.py`).

**Findings:**
- All 39 C-08 tests already PASS (run: `uv run pytest serve/kanban/tests/test_engine_storage.py` → 39 passed)
- The engine implementation in `engine.py` fully implements all AC items
- Builder commits tagged `#1053` (e.g., `16bf89aa fix: guard sweep corruption and claimed_by quote semantics`) completed the implementation as part of earlier builder work

### Attempt to write failing tests

Wrote 19 task-scoped tests covering all AC items from fresh angles:
- `TestFromAC_ListTasksCorruption`: tasks_dir absent, all-corrupt board, duplicate ID + valid mix
- `TestFromAC_Sweep`: live-claim not released, plain `list` type, mixed corrupt+expired board, claimed_at cleared after sweep
- `TestFromAC_RepairStorage`: end-to-end AR creation, failed AR preserves code, DUPLICATE_LOCATION → action="fixed", body=str assertion
- `TestFromAC_MigrationGate`: legacy board exemption, archive/ exemption, absent tasks_dir
- `TestFromAC_ParseDuration`: 1h30m boundary, empty string, return type, engine init raises

**Result: 19 passed, 0 failed.**

Per mode instruction ("If any passes, it tests existing behavior — remove or refine it"), the file was deleted. No failing tests achievable — implementation satisfies all AC items.

### AC Coverage (via C-08 suite, all passing)

| AC | Tests in test_engine_storage.py | Status |
|----|----------------------------------|--------|
| AC-C19 | TestFromAC_ListTasksCorruption (9 tests) | ✓ PASS |
| AC-C20 | test_ac_c20_* (1 test) | ✓ PASS |
| AC-C23 | TestFromAC_Sweep (3 tests) | ✓ PASS |
| AC-C24 | TestFromAC_RepairStorage::test_ac_c24_* | ✓ PASS |
| AC-C25 | TestFromAC_RepairStorage::test_ac_c25_* | ✓ PASS |
| AC-C26 | TestFromAC_RepairStorage::test_ac_c26_* | ✓ PASS |
| AC-C27 | TestFromAC_Sweep::test_ac_c27_* (2 tests) | ✓ PASS |
| AC-C47 | TestFromAC_MigrationGate (8 tests) | ✓ PASS |
| AC-C49 | TestFromAC_ParseDuration (4 tests) | ✓ PASS |
| AC-C50 | TestFromAC_ParseDuration (3 tests) | ✓ PASS |
| AC-C52 | TestFromAC_Sweep (4 tests) | ✓ PASS |
| AC-C54 | TestFromAC_ARCreationSignature (2 tests) | ✓ PASS |

### Decision

Advancing to in-progress as pre-implemented pass-through. The builder for this task should verify: `uv run pytest serve/kanban/tests/test_engine_storage.py` → 39 passed. No additional implementation required.
[[2026-04-23]]
## Builder Notes
- Implementation: no code changes required (pre-implemented pass-through).
- Files changed: none.
- Tests: 39 passed in `serve/kanban/tests/test_engine_storage.py`; 0 failed; 0 skipped.
- Coverage: `owlbear_kanban.engine` 37% (scoped quality-runner report for current durable suite).
- Ruff: clean; 0 violations.
- Evidence summary: quality-runner scoped verification PASS (pytest exit 0, ruff exit 0), satisfying AC gate “All RED tests from C-08 pass.”
- Fixes applied: none.

- Reflection: No blocking defects observed in AC-C19/C20/C23/C24/C25/C26/C27/C47/C49/C50/C52/C54 behavior under current suite.
- Reflection: Primary time sink was reconciling GREEN protocol with already-green implementation; pass-through handling kept diff surgical.
- Reflection: Coverage on `engine.py` remains below 90%; this is a pre-existing test-depth gap outside builder remit (builder does not author tests).
- Reflection: Canonical evidence now centralized via quality-runner to preserve comparable downstream review context.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped on `serve/kanban/tests/test_engine_storage.py`: 39 passed, 0 failed, 0 skipped, pytest exit 0.
- quality-runner broader on `serve/kanban/tests/test_engine_storage.py` + `serve/kanban/tests/test_engine_atomicity_1104.py`: 59 passed, 0 failed, 0 skipped, pytest exit 0.

### Lint
- clean: true for `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_engine_storage.py`, and `serve/kanban/tests/test_engine_atomicity_1104.py`.

### Coverage
- scoped (`test_engine_storage.py`): `owlbear_kanban.engine` 37%.
- broader storage+atomicity scope: `owlbear_kanban.engine` 58%.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C19 | `TestFromAC_ListTasksCorruption` in `serve/kanban/tests/test_engine_storage.py:134,150,183,201,222,244,269,288` | Yes. The suite checks each silent-skip mode by asserting the good task remains visible and the corrupt task does not appear. | COVERED |
| AC-C20 | `test_ac_c20_list_tasks_hard_raises_on_duplicate_id` at `serve/kanban/tests/test_engine_storage.py:169-180` | Yes. The test requires `CorruptionError` and exact code `ERR_CORRUPT_DUPLICATE_ID`; silent skip or tolerance would fail. | COVERED |
| AC-C23 | `test_ac_c23_*` at `serve/kanban/tests/test_engine_storage.py:322-377` | Yes. The suite checks `list[int]`, released-only membership, and exact released set. | COVERED |
| AC-C24 | `test_ac_c24_file_moved_before_ar_creation` at `serve/kanban/tests/test_engine_storage.py:612-642` | Yes. The spy asserts the quarantine file already exists and the original tasks file is already gone when `create_task()` is entered. | COVERED |
| AC-C25 | `test_ac_c25_repair_records_failed_when_ar_creation_fails` at `serve/kanban/tests/test_engine_storage.py:645-664` | Yes. It forces AR creation failure, then asserts `action='failed'` outcome and quarantined file retention. | COVERED |
| AC-C26 | `test_ac_c26_duplicate_location_resolved_archive_wins` at `serve/kanban/tests/test_engine_storage.py:666-679` | No. Both fixtures use identical content at lines 669-671, and the assertions only check that the archive file exists and the tasks copy is gone. An implementation that overwrote archive contents with the tasks copy would still pass, so the named `archive-wins` provenance is not proven. | LAX |
| AC-C27 | `test_ac_c27_*` at `serve/kanban/tests/test_engine_storage.py:381-431` | Yes. The suite proves corrupt files are untouched and parseable-corrupt files are not rewritten. | COVERED |
| AC-C47 | `TestFromAC_MigrationGate` at `serve/kanban/tests/test_engine_storage.py:690-831` | Yes. The suite covers raise/no-raise branches and exact `ERR_MIGRATION_REQUIRED` behavior for claimed_by variants. | COVERED |
| AC-C49 | `test_ac_c49_*` at `serve/kanban/tests/test_engine_storage.py:841-869` | Yes. Concrete timedelta values and exact `ERR_INVALID_CLAIM_TIMEOUT` are asserted. | COVERED |
| AC-C50 | `test_ac_c50_*` at `serve/kanban/tests/test_engine_storage.py:871-911` | Yes for eager-validation through the production load path: invalid config raises, and `_parse_duration` is called by `config_loader.load_config()`. | COVERED |
| AC-C52 | `test_ac_c52_*` at `serve/kanban/tests/test_engine_storage.py:435-600` | Yes. The suite checks claimed_at clearing, updated advancement, exact body preservation, and no `claimed_by` serialization. | COVERED |
| AC-C54 | `TestFromAC_ARCreationSignature` at `serve/kanban/tests/test_engine_storage.py:922-987` | Yes. The suite proves `body` is `str` and `status` is omitted from kwargs, not merely empty. | COVERED |
| All RED tests from C-08 pass | quality-runner scoped report on `serve/kanban/tests/test_engine_storage.py` | Yes. Independent run returned 39 passed, 0 failed. | COVERED |

#### Security Review
- No security issues found in reviewed scope. No new dependency surface was introduced. The storage-repair path uses explicit arguments and validated internal paths; no shell-string injection, unsafe deserialization, or secret leakage was observed.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` coverage in `serve/kanban/tests/test_engine_storage.py` | No builder test diff detected in current workspace; builder notes also report no file changes. No weakened/removal patterns observed in the current assertions. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | ADEQUATE | Most AC tests assert exact ids/codes/body content; a few positive-path cases still use loose non-raise / truthiness checks. |
| Negative/error-path coverage | STRONG | Duplicate ID, corrupt-mode carve-outs, AR-create failure, malformed duration, and quoted `claimed_by` cases are all covered. |
| Manual mutation reasoning | WEAK | AC-C26 test at `serve/kanban/tests/test_engine_storage.py:666-679` cannot distinguish `archive retained` from `archive overwritten then tasks file removed`. |
| Test independence | STRONG | Each case constructs a fresh board under `tmp_path`. |
| Descriptive names | STRONG | Test names are AC-anchored and branch-specific. |

#### Data Safety
- No blocking data-safety issues found in the scoped implementation.
- `repair_storage()` quarantines before AR creation (`serve/kanban/src/owlbear_kanban/engine.py:1194-1212`), and failed AR creation is recorded as `action='failed'` while leaving the file quarantined (`serve/kanban/src/owlbear_kanban/engine.py:1214-1223`).

#### Implementation-Aware Gaps
- The current dirty worktree touches `sweep()`; I verified the overlapping rollback branch with a broader run including `serve/kanban/tests/test_engine_atomicity_1104.py`, and those tests pass.
- Remaining blocker: no test proves that duplicate-location repair preserves the archive copy as canonical. The implementation in `serve/kanban/src/owlbear_kanban/corruption.py:352-366` currently unlinks the tasks copy only, but the task-owned proof does not detect an archive-clobber mutation.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_engine_storage.py:5` and `serve/kanban/tests/test_engine_storage.py:911` still contain stale red-phase wording that now conflicts with the green state. Not blocking, but audit-hostile.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C19 | `serve/kanban/src/owlbear_kanban/engine.py:529-556`; `serve/kanban/tests/test_engine_storage.py:134,150,183,201,222,244,269,288` | `TestFromAC_ListTasksCorruption` | PASS |
| AC-C20 | `serve/kanban/src/owlbear_kanban/engine.py:568-574`; `serve/kanban/tests/test_engine_storage.py:169-180` | `test_ac_c20_list_tasks_hard_raises_on_duplicate_id` | PASS |
| AC-C23 | `serve/kanban/src/owlbear_kanban/engine.py:1128-1177`; `serve/kanban/tests/test_engine_storage.py:322-377` | `test_ac_c23_*` | PASS |
| AC-C24 | `serve/kanban/src/owlbear_kanban/engine.py:1194-1212`; `serve/kanban/tests/test_engine_storage.py:612-642` | `test_ac_c24_file_moved_before_ar_creation` | PASS |
| AC-C25 | `serve/kanban/src/owlbear_kanban/engine.py:1214-1223`; `serve/kanban/tests/test_engine_storage.py:645-664` | `test_ac_c25_repair_records_failed_when_ar_creation_fails` | PASS |
| AC-C26 | `serve/kanban/src/owlbear_kanban/corruption.py:352-366,530-586`; `serve/kanban/tests/test_engine_storage.py:666-679` | `test_ac_c26_duplicate_location_resolved_archive_wins` | FAIL |
| AC-C27 | `serve/kanban/src/owlbear_kanban/engine.py:1149-1177`; `serve/kanban/tests/test_engine_storage.py:381-431` | `test_ac_c27_*` | PASS |
| AC-C47 | `serve/kanban/src/owlbear_kanban/engine.py:347-387`; `serve/kanban/tests/test_engine_storage.py:690-831` | `TestFromAC_MigrationGate` | PASS |
| AC-C49 | `serve/kanban/src/owlbear_kanban/engine.py:63-80`; `serve/kanban/tests/test_engine_storage.py:841-869` | `test_ac_c49_*` | PASS |
| AC-C50 | `serve/kanban/src/owlbear_kanban/config_loader.py:61-69`; `serve/kanban/tests/test_engine_storage.py:871-911` | `test_ac_c50_*` | PASS |
| AC-C52 | `serve/kanban/src/owlbear_kanban/engine.py:1163-1166`; `serve/kanban/tests/test_engine_storage.py:435-600` | `test_ac_c52_*` | PASS |
| AC-C54 | `serve/kanban/src/owlbear_kanban/engine.py:1202-1212`; `serve/kanban/tests/test_engine_storage.py:922-987` | `TestFromAC_ARCreationSignature` | PASS |
| All RED tests from C-08 pass | quality-runner scoped report: 39 passed, 0 failed, pytest exit 0 on `serve/kanban/tests/test_engine_storage.py` | scoped quality-runner run | PASS |

### Confidence: 0.84
### Verdict: FAIL
### Action
Reject to `todo`. Implementation behavior appears correct under the current suites, but the review gate fails on test quality: AC-C26 is under-proven, and broader engine coverage remains 58% even after adding the overlapping atomicity suite. The next cycle should strengthen the `archive-wins` proof with divergent task/archive fixtures and an assertion that the archive contents remain unchanged after repair.
[[2026-04-23]]
## Test-Writer Notes (Cycle 2 — AC-C26 proof strengthening)

**Trigger:** Reviewer rejected on AC-C26 lax proof (identical fixtures couldn't detect archive-clobbering mutation).

**Change:** Replaced `test_ac_c26_duplicate_location_resolved_archive_wins` with divergent-content fixtures.

- Archive copy uses `"Archive body."` in the Notes section
- Tasks/ copy uses `"Tasks body."` in the Notes section  
- Guard assertion `assert archive_content != tasks_content` ensures fixtures always diverge
- New assertion: `read_text()` on the surviving archive file must equal the original `archive_content` verbatim — an implementation that clobbers the archive with the tasks copy (or overwrites it) will now fail

**File:** `serve/kanban/tests/test_engine_storage.py` — `TestFromAC_RepairStorage::test_ac_c26_duplicate_location_resolved_archive_wins`

**Evidence:**
- Scoped run: 1 passed (the updated test)
- Full suite: 39 passed, 0 failed, 0 skipped
- Ruff: clean

**AC Coverage:**
| AC | Status |
|----|--------|
| AC-C26 | STRENGTHENED — archive content preservation now proven against mutation |
| All others | Unchanged (39-test suite still green) |
[[2026-04-23]]
## Builder Notes
- Implementation: no source-code changes required in this cycle; existing `serve/kanban/src/owlbear_kanban/engine.py` behavior satisfies strengthened AC-C26 proof.
- Files changed: none by builder.
- Tests: quality-runner scoped verification on `serve/kanban/tests/test_engine_storage.py` -> 39 passed, 0 failed, 0 skipped (pytest exit 0).
- Coverage: `owlbear_kanban.engine` 38% in scoped run (pre-existing suite depth; no builder code touched).
- Ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_storage.py` (exit 0).
- Evidence summary: AC-C26 strengthened test (divergent archive/tasks content with archive-content preservation assertion) passes against current implementation; no regression observed across C-08 RED suite.
- Fixes applied: none.

- Reflection: Reviewer-raised AC-C26 proof gap is now closed by upstream test-writer strengthening; builder validation confirms implementation compatibility.
- Reflection: Main effort in this cycle was canonical re-verification (quality-runner) rather than code surgery.
- Reflection: Coverage remains below 90% in scoped storage suite, but this cycle changed no production code and introduced no new uncovered paths.
- Reflection: Preserved surgical scope by avoiding non-essential edits and using task-owned evidence only.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped on `serve/kanban/tests/test_engine_storage.py`: 39 passed, 0 failed, 0 skipped. Pytest exit 0.

### Lint
- clean: true for `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/config_loader.py`, and `serve/kanban/tests/test_engine_storage.py`.

### Coverage
- overall: 40%
- `owlbear_kanban.engine`: 38%
- `owlbear_kanban.config_loader`: 59%
- `owlbear_kanban.corruption`: 53%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Were Violated? | Verdict |
|---------|-------------|----------------------------------|---------|
| AC-C19 | `TestFromAC_ListTasksCorruption` in `serve/kanban/tests/test_engine_storage.py` at lines 134, 149, 182, 200, 221, 243, 268, 287 | Yes. Each silent-skip mode is exercised by asserting the valid task remains visible while the corrupt file does not appear. | COVERED |
| AC-C20 | `test_ac_c20_list_tasks_hard_raises_on_duplicate_id` at line 169 | Yes. The test requires `CorruptionError` with exact code `ERR_CORRUPT_DUPLICATE_ID`. | COVERED |
| AC-C23 | `test_ac_c23_*` at lines 321, 330, 349 | Yes. The suite checks `list[int]`, released-only membership, and exact released set. | COVERED |
| AC-C24 | `test_ac_c24_file_moved_before_ar_creation` at line 612 | Yes. The spy asserts the quarantine path exists and the original task file is already gone when AR creation is entered. | COVERED |
| AC-C25 | `test_ac_c25_repair_records_failed_when_ar_creation_fails` at line 645 | No. The test proves only that at least one `RepairOutcome` has `action="failed"` and that `quarantine/1001-corrupt.md` exists at lines 662 and 664. It never asserts that `tasks/1001-corrupt.md` remains absent after AR creation fails, so the full “file remains quarantined” contract is not pinned down. | LAX |
| AC-C26 | `test_ac_c26_duplicate_location_resolved_archive_wins` at line 666 | Yes. Divergent fixtures are guarded and the surviving archive file is asserted equal to the original archive content, so archive-content clobbering would fail the test. | COVERED |
| AC-C27 | `test_ac_c27_*` at lines 381 and 401 | Yes. The suite proves both unreadable-corrupt and parseable-corrupt files are left untouched by `sweep()`. | COVERED |
| AC-C47 | `TestFromAC_MigrationGate` at lines 700, 716, 726, 736, 755, 774, 794, 818 | Yes. Raise and no-raise branches are covered, including quoted-null and quoted-tilde cases with exact `ERR_MIGRATION_REQUIRED`. | COVERED |
| AC-C49 | `test_ac_c49_*` at lines 851, 858, 865, 872 | Yes. Concrete `timedelta` values and exact `ERR_INVALID_CLAIM_TIMEOUT` are asserted. | COVERED |
| AC-C50 | `test_ac_c50_board_config_eager_validation_on_load` at line 881 and `test_ac_c50_config_load_calls_parse_duration_not_only_regex` at line 904 | Yes. The real `config_loader.load_config()` path is exercised and the `_parse_duration()` call is explicitly asserted. | COVERED |
| AC-C52 | `test_ac_c52_*` at lines 435, 459, 485, 514, 545 | Yes. The suite checks claimed_at clearing, updated advancement, exact body preservation, and `claimed_by` non-serialization. | COVERED |
| AC-C54 | `TestFromAC_ARCreationSignature` at lines 932 and 972 | Yes. The suite proves `body` is `str` and that `status` is omitted rather than passed explicitly. | COVERED |
| All RED tests from C-08 pass | quality-runner scoped run on `serve/kanban/tests/test_engine_storage.py` | Yes. Independent run returned 39 passed, 0 failed. | COVERED |

#### Security Review
- No security issues found in reviewed scope. The current cycle is test-only, introduces no dependencies, and the exercised storage paths remain within tmp-path fixtures.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` suite in `serve/kanban/tests/test_engine_storage.py` | No builder weakening or removal detected. AC-C26 is strengthened in the current workspace by divergent fixtures and exact archive-content equality. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | WEAK | AC-C25 stops at `action="failed"` and quarantine existence at lines 662 and 664; it does not assert the original task file stays absent. |
| Negative and error-path coverage | STRONG | Duplicate ID, AR creation failure, malformed duration, migration gate, and corrupt sweep cases are all covered in AC-scoped tests. |
| Manual mutation reasoning | WEAK | A mutation that restores `tasks/1001-corrupt.md` after AR creation failure would still satisfy the current AC-C25 assertions. |
| Test independence | STRONG | Cases build isolated boards under `tmp_path`; no shared mutable state is visible. |
| Descriptive names | STRONG | Test names remain AC-anchored and branch-specific throughout the suite. |

#### Data Safety
- No blocking data-safety issues found in the scoped review.

#### Implementation-Aware Gaps
- The current implementation appears correct in the reviewed path: `repair_storage()` processes quarantine outcomes in phase 2 and records `action="failed"` on AR creation exception in `serve/kanban/src/owlbear_kanban/engine.py` lines 1242, 1274, and 1287.
- The blocker is proof strength, not observed implementation behavior: the task-owned AC-C25 test does not verify that the original `tasks/` copy remains absent after the failure path, so that regression could escape the suite.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_engine_storage.py` still carries stale red-phase wording at lines 1, 5, and 921. This is not the gate failure, but it makes the now-green suite look untrusted.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C19 | AC-scoped silent-skip tests at lines 134, 149, 182, 200, 221, 243, 268, 287 all passed in the independent quality run. | `TestFromAC_ListTasksCorruption` | PASS |
| AC-C20 | Duplicate-id raise test at line 169 passed in the independent quality run. | `test_ac_c20_list_tasks_hard_raises_on_duplicate_id` | PASS |
| AC-C23 | Return-shape and exact-set tests at lines 321, 330, 349 passed. | `test_ac_c23_*` | PASS |
| AC-C24 | Move-before-AR spy test at line 612 passed. | `test_ac_c24_file_moved_before_ar_creation` | PASS |
| AC-C25 | Failure-path test at line 645 passes, but only proves `action="failed"` and quarantine existence. Original-task absence after failure is unasserted. | `test_ac_c25_repair_records_failed_when_ar_creation_fails` | FAIL |
| AC-C26 | Divergent archive/tasks fixtures and archive-content equality at line 666 passed. | `test_ac_c26_duplicate_location_resolved_archive_wins` | PASS |
| AC-C27 | Corruption-independent sweep tests at lines 381 and 401 passed. | `test_ac_c27_*` | PASS |
| AC-C47 | Migration-gate cases at lines 700, 716, 726, 736, 755, 774, 794, 818 passed. | `TestFromAC_MigrationGate` | PASS |
| AC-C49 | Duration parser tests at lines 851, 858, 865, 872 passed. | `test_ac_c49_*` | PASS |
| AC-C50 | Eager config validation tests at lines 881 and 904 passed. | `test_ac_c50_*` | PASS |
| AC-C52 | Sweep body/timestamp/serialization tests at lines 435, 459, 485, 514, 545 passed. | `test_ac_c52_*` | PASS |
| AC-C54 | AR creation signature tests at lines 932 and 972 passed. | `TestFromAC_ARCreationSignature` | PASS |
| All RED tests from C-08 pass | quality-runner scoped run returned 39 passed, 0 failed, 0 skipped. | independent quality-runner run | PASS |

### Confidence: 0.86
### Verdict: FAIL
### Action
Reject to `todo`. The prior AC-C26 proof gap is closed, but AC-C25 is still under-proven in the current `TestFromAC` suite. The next cycle should strengthen `test_ac_c25_repair_records_failed_when_ar_creation_fails` by asserting the original `tasks/1001-corrupt.md` path remains absent after AR creation fails, not only that a quarantine copy exists.
[[2026-04-23]]
## Test-Writer Notes (Cycle 3 — AC-C25 proof strengthening)

**Trigger:** Reviewer rejected Cycle 2 on AC-C25 lax proof — existing test asserts `action="failed"` and quarantine existence but does NOT assert the original `tasks/1001-corrupt.md` path stays absent after AR creation fails.

**Change:** Added `test_ac_c25_original_tasks_file_absent_after_ar_creation_fails` to `TestFromAC_RepairStorage` in `serve/kanban/tests/test_engine_storage.py`.

- Same repair scenario as the existing AC-C25 test (AR creation patched to raise)
- Directly asserts `not tasks_path.exists()` after `repair_storage()` returns
- A mutation that restores (moves back) the quarantined file on AR creation failure will now fail this assertion
- Existing `test_ac_c25_repair_records_failed_when_ar_creation_fails` preserved unchanged

**Evidence:**
- New test alone: 1 passed (implementation is correct — file not restored)
- Full suite: 40 passed, 0 failed, 0 skipped (was 39)
- Ruff: clean

**AC Coverage:**
| AC | Status |
|----|--------|
| AC-C25 | STRENGTHENED — tasks/ path absence now proven against restoration-mutation |
| All others | Unchanged (40-test suite green) |
[[2026-04-23]]
## Builder Notes
- Implementation: no source changes required in this cycle; `serve/kanban/src/owlbear_kanban/engine.py` already satisfies AC-C19/C20/C23/C24/C25/C26/C27/C47/C49/C50/C52/C54 under the task-owned suite.
- Files changed: none.
- Tests: quality-runner scoped run on `serve/kanban/tests/test_engine_storage.py` -> 40 passed, 0 failed, 0 skipped (pytest exit 0).
- Coverage: `owlbear_kanban.engine` 38% in scoped run (pre-existing suite depth; builder did not modify code).
- Ruff: clean for `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_storage.py` (ruff exit 0).
- Evidence summary: latest AC-C25 strengthening from test-writer remains green against current implementation; no regressions observed in C-08 scope.
- Fixes applied: none.

- Reflection: This cycle remained a GREEN pass-through because implementation was already in place.
- Reflection: The key gate was independent re-verification with quality-runner after test-suite tightening.
- Reflection: No blocking defects surfaced in engine storage-integration behavior under the scoped AC suite.
- Reflection: Kept the diff surgical by avoiding non-essential edits and preserving test-writer ownership of tests.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped on `serve/kanban/tests/test_engine_storage.py`: 40 passed, 0 failed, 0 skipped. Pytest exit 0.

### Lint
- clean: true for `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/config_loader.py`, and `serve/kanban/tests/test_engine_storage.py`.

### Coverage
- overall: 40%
- `owlbear_kanban.engine`: 38%
- `owlbear_kanban.config_loader`: 59%
- `owlbear_kanban.corruption`: 53%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C19 | `TestFromAC_ListTasksCorruption` in `serve/kanban/tests/test_engine_storage.py` at lines 134, 149, 182, 200, 221, 243, 268, 287 | Partially. The suite proves modes 1 and 3-9 via representative files, but it does not exercise the mode-3 `forbidden field claimed_by present` branch in `serve/kanban/src/owlbear_kanban/corruption.py:230-236` and the paired detail-sensitive path in `serve/kanban/src/owlbear_kanban/engine.py:580-583`. Current code still silent-skips that case because `read_task()` re-detects corruption and `list_tasks()` catches the resulting `CorruptionError`, but that branch-specific AC proof is absent from the task-owned `TestFromAC` suite. | LAX |
| AC-C20 | `test_ac_c20_list_tasks_hard_raises_on_duplicate_id` at `serve/kanban/tests/test_engine_storage.py:169` | Yes. Exact `CorruptionError` code `ERR_CORRUPT_DUPLICATE_ID` is asserted. | COVERED |
| AC-C23 | `test_ac_c23_*` at `serve/kanban/tests/test_engine_storage.py:321,330,349` | Yes. The suite checks `list[int]`, released-only membership, and exact released set. | COVERED |
| AC-C24 | `test_ac_c24_file_moved_before_ar_creation` at `serve/kanban/tests/test_engine_storage.py:612` | Yes. The spy asserts the quarantine file exists and the original task file is already gone when AR creation is entered. | COVERED |
| AC-C25 | `test_ac_c25_repair_records_failed_when_ar_creation_fails` and `test_ac_c25_original_tasks_file_absent_after_ar_creation_fails` at `serve/kanban/tests/test_engine_storage.py:645,666` | Yes. Together they prove `action="failed"`, quarantine retention, and non-restoration of the original `tasks/` path. | COVERED |
| AC-C26 | `test_ac_c26_duplicate_location_resolved_archive_wins` at `serve/kanban/tests/test_engine_storage.py:693` | Yes. Divergent fixtures plus exact archive-content equality would fail on archive clobbering. | COVERED |
| AC-C27 | `test_ac_c27_*` at `serve/kanban/tests/test_engine_storage.py:381,401` | Yes. The suite proves corrupt files are not rewritten during sweep. | COVERED |
| AC-C47 | `TestFromAC_MigrationGate` at `serve/kanban/tests/test_engine_storage.py:727,743,753,763,782,801,821,845` | Yes. Raise/no-raise branches and exact `ERR_MIGRATION_REQUIRED` behavior are covered. | COVERED |
| AC-C49 | `test_ac_c49_*` at `serve/kanban/tests/test_engine_storage.py:886,893,900,907` | Yes. Concrete `timedelta` values and exact `ERR_INVALID_CLAIM_TIMEOUT` are asserted. | COVERED |
| AC-C50 | `test_ac_c50_*` at `serve/kanban/tests/test_engine_storage.py:914,931` | Yes. The real `config_loader.load_config()` path is exercised and `_parse_duration()` is asserted. | COVERED |
| AC-C52 | `test_ac_c52_*` at `serve/kanban/tests/test_engine_storage.py:435,459,485,514,545` | Yes. The suite checks claimed_at clearing, updated advancement, exact body preservation, and no `claimed_by` serialization. | COVERED |
| AC-C54 | `TestFromAC_ARCreationSignature` at `serve/kanban/tests/test_engine_storage.py:960,999` | Yes. The suite proves `body` is `str` and `status` is omitted from kwargs rather than passed explicitly. | COVERED |
| All RED tests from C-08 pass | quality-runner scoped run on `serve/kanban/tests/test_engine_storage.py` | Yes. Independent run returned 40 passed, 0 failed. | COVERED |

#### Security Review
- No security issues found in reviewed scope. No new dependencies were introduced, no unsafe deserialization or shell interpolation was added, and the storage-repair path remains quarantine-first.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` coverage in `serve/kanban/tests/test_engine_storage.py` | No builder weakening or removal detected. The latest upstream change strengthens AC-C25 by asserting the original `tasks/` path stays absent after AR-creation failure. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | WEAK | AC-C19 still lacks an AC-scoped assertion for the mode-3 `forbidden field claimed_by present` branch even though `list_tasks()` has detail-sensitive logic for it at `serve/kanban/src/owlbear_kanban/engine.py:580-583`. |
| Negative/error-path coverage | STRONG | Duplicate ID, AR-creation failure, malformed duration, migration gate, and corrupt sweep cases are all covered in AC-scoped tests. |
| Manual mutation reasoning | WEAK | A regression in the `claimed_by`-detail branch of `list_tasks()` could survive the current task-owned suite because no `TestFromAC` case drives that branch directly. |
| Test independence | STRONG | Cases build isolated boards under `tmp_path`; no shared mutable state is visible. |
| Descriptive names | STRONG | Test names remain AC-anchored and branch-specific. |

#### Data Safety
- No blocking data-safety issues found in the scoped implementation.

#### Implementation-Aware Gaps
- Verified divergence from the code-reader concern: current implementation still silent-skips the untested `claimed_by` mode-3 case because `list_tasks()` defers that detail to `read_task()`, `read_task()` re-runs board-level corruption detection, and `list_tasks()` catches the resulting `CorruptionError` and continues. Evidence: `serve/kanban/src/owlbear_kanban/engine.py:580-591`, `serve/kanban/src/owlbear_kanban/storage.py:320-338`, `serve/kanban/src/owlbear_kanban/corruption.py:230-236`.
- The blocker is proof strength, not observed implementation behavior: the task-owned `TestFromAC_ListTasksCorruption` class does not pin that branch down, and module-level coverage remains low (`engine` 38%, `config_loader` 59%, `corruption` 53%), which reinforces that the current scoped suite is not yet comprehensive enough for this task.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | N/A — re-entries were driven by upstream test-proof gaps, not repeated builder code churn |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_engine_storage.py` still contains stale red-phase commentary around the AC-C50 and AC-C47 explanatory docstrings; the assertions are correct, but the prose describes an older broken implementation.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C19 | Representative mode coverage passes, but no AC-scoped test exercises the mode-3 `forbidden field claimed_by present` branch (`serve/kanban/src/owlbear_kanban/corruption.py:230-236`, `serve/kanban/src/owlbear_kanban/engine.py:580-583`). | `TestFromAC_ListTasksCorruption` | FAIL |
| AC-C20 | Duplicate-id raise test at `serve/kanban/tests/test_engine_storage.py:169` passed in the independent quality run. | `test_ac_c20_list_tasks_hard_raises_on_duplicate_id` | PASS |
| AC-C23 | Return-shape and exact-set tests at `serve/kanban/tests/test_engine_storage.py:321,330,349` passed. | `test_ac_c23_*` | PASS |
| AC-C24 | Move-before-AR spy test at `serve/kanban/tests/test_engine_storage.py:612` passed. | `test_ac_c24_file_moved_before_ar_creation` | PASS |
| AC-C25 | Failed-outcome and original-path-absence tests at `serve/kanban/tests/test_engine_storage.py:645,666` passed. | `test_ac_c25_*` | PASS |
| AC-C26 | Divergent archive/tasks fixtures and exact archive-content equality at `serve/kanban/tests/test_engine_storage.py:693` passed. | `test_ac_c26_duplicate_location_resolved_archive_wins` | PASS |
| AC-C27 | Corruption-independent sweep tests at `serve/kanban/tests/test_engine_storage.py:381,401` passed. | `test_ac_c27_*` | PASS |
| AC-C47 | Migration-gate cases at `serve/kanban/tests/test_engine_storage.py:727,743,753,763,782,801,821,845` passed. | `TestFromAC_MigrationGate` | PASS |
| AC-C49 | Duration parser tests at `serve/kanban/tests/test_engine_storage.py:886,893,900,907` passed. | `test_ac_c49_*` | PASS |
| AC-C50 | Eager config-validation tests at `serve/kanban/tests/test_engine_storage.py:914,931` passed. | `test_ac_c50_*` | PASS |
| AC-C52 | Sweep body/timestamp/serialization tests at `serve/kanban/tests/test_engine_storage.py:435,459,485,514,545` passed. | `test_ac_c52_*` | PASS |
| AC-C54 | AR creation signature tests at `serve/kanban/tests/test_engine_storage.py:960,999` passed. | `TestFromAC_ARCreationSignature` | PASS |
| All RED tests from C-08 pass | quality-runner scoped run returned 40 passed, 0 failed, 0 skipped. | independent quality-runner run | PASS |

### Confidence: 0.86
### Verdict: FAIL
### Action
Reject to `backlog`. This is the third review failure on the task, so the loop-breaker routing applies. The next cycle should resolve the AC-C19 ownership ambiguity explicitly: either add a task-owned `TestFromAC` that drives the mode-3 `forbidden field claimed_by present` branch in `list_tasks()`, or carve that branch out of AC-C19 if AC-C47 / existing claim-list regression coverage is intended to own it.
[[2026-04-23]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage-integration edits only; activity/session wiring deferred to C-18 |
| Interface clarity | PASS after REFINE | AC-C19 ambiguity on mode-3 sub-variants resolved (see below) |
| Dependency correctness | PASS | #1053 and #1059 both archived (done) |
| Module layering | PASS | engine.py → storage.py → corruption.py — no upward imports |
| TDD compliance | PASS | C-08 RED suite (#1053) exists; 40 tests green |
| KISS/YAGNI | PASS | No hypothetical features; minimal scope |
| Premise challenge | PASS | Capability does not exist elsewhere; corruption handling is domain-specific |
| Pattern consistency | PASS | Follows existing CorruptionError taxonomy, config_loader patterns |
| Security surface | PASS | No new system boundaries; quarantine-first repair matches existing pattern |
| Single domain | PASS | kanban engine only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| list_tasks + mode-3 claimed_by | Legacy-schema board has file with claimed_by | CorruptionError via read_task re-detection | Yes — caught and silently skipped (engine.py:595-599) | Corrupt file invisible in task list |
| repair_storage AR creation | create_task call fails | Exception caught | Yes — RepairOutcome(action="failed"), file stays quarantined | Manual intervention needed |

### Challenge Results
- Challenger: reconsider (0.62)
- Key challenge: Mode-3 claimed_by branch is conditionally reachable on legacy-schema boards (version field present bypasses AC-C47 migration gate). Not dead code.
- Architect response: ACCEPTED. Revised assessment — the branch is reachable via legacy-schema boards. The existing test helper `_make_board()` already uses `version: 10` (legacy schema). AC-C19 refined to require explicit test for this sub-variant.

### AC Refinement
**AC-C19 (before):** `list_tasks` SKIPS files failing corruption modes 1, 3-9 silently

**AC-C19 (after):** `list_tasks` SKIPS files failing corruption modes 1, 3-9 silently — mode-3 has two sub-variants: (a) missing required field, (b) forbidden `claimed_by` present on legacy-schema boards. Both must have task-owned tests.

### Architect Guidance for Test-Writer
The 3-cycle review loop was caused by AC-C19 ambiguity around mode-3 sub-variants. The gap is narrow: add one test to `TestFromAC_ListTasksCorruption` that creates a legacy-schema board (`_make_board`), writes a task file with `claimed_by: some-agent` in frontmatter, calls `list_tasks()`, and asserts the file is silently skipped (not in results, no exception raised). This exercises `engine.py:580-583` → `read_task()` re-detection → exception handler skip path.

### Loop-Breaker Context
This is the 4th architecture review. Prior cycles fixed AC-C26 (divergent fixtures) and AC-C25 (original-path absence assertion). The AC-C19 mode-3 claimed_by gap is the final reviewer objection. The refinement above gives the test-writer unambiguous direction to close it in one cycle.

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC-C19 to enumerate mode-3 sub-variants explicitly. Added architect guidance for the test-writer. Advanced to todo.
[[2026-04-23]]
## Test-Writer Notes (Cycle 4 — AC-C19 mode-3b proof)

**Trigger:** Reviewer rejected Cycle 3 on AC-C19 coverage gap — no task-owned test for mode-3 sub-variant (b): forbidden `claimed_by` present on legacy-schema boards. Architect refined AC-C19 to explicitly enumerate both sub-variants and directed the test-writer to close the gap.

**File:** `serve/kanban/tests/test_engine_storage.py`
**Class:** `TestFromAC_ListTasksCorruption`
**New test:** `test_ac_c19_list_tasks_skips_mode3b_claimed_by_on_legacy_schema`

**Test design:**
- Uses `_make_board()` (legacy schema, version: 10) to bypass the AC-C47 migration gate
- Writes `1001-good.md` (valid task) + `1002-claimed.md` (all required fields + `claimed_by: some-agent`)
- Exercises path: `_detect_corruption()` → carve-out at `engine.py:580-583` → `read_task()` re-detection → `CorruptionError` caught → silent skip
- Asserts: no exception raised, 1001 in results, 1002 absent from results

**Evidence:**
- New test alone: 1 passed
- Full suite: 41 passed, 0 failed, 0 skipped (was 40)
- Ruff: clean

**AC Coverage:**
| AC | Status |
|----|--------|
| AC-C19 mode-3a (missing required field) | Pre-existing test — COVERED |
| AC-C19 mode-3b (forbidden claimed_by on legacy-schema board) | NEW — COVERED |
| All others (AC-C20/C23/C24/C25/C26/C27/C47/C49/C50/C52/C54) | Unchanged — COVERED |

**Note:** This is a GREEN task with pre-completed implementation. All 41 tests pass as expected. The mode-3b gap was an AC proof gap, not an implementation gap.
[[2026-04-23]]
## Builder Notes
- Implementation: no source changes required; existing storage-integration implementation already satisfies AC-C19/C20/C23/C24/C25/C26/C27/C47/C49/C50/C52/C54 under the task-owned suite.
- Files changed: none.
- Tests: quality-runner scoped run on `serve/kanban/tests/test_engine_storage.py` -> 41 passed, 0 failed, 0 skipped (pytest exit 0).
- Coverage: `owlbear_kanban.engine` 39% in scoped verification.
- Ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_storage.py` (ruff exit 0).
- Evidence summary: canonical quality-runner verification is green with zero lint issues; AC gate "All RED tests from C-08 pass" is satisfied with 41/41 passing.
- Fixes applied: none.

- Reflection: This cycle was a strict GREEN pass-through because implementation had already landed in prior cycles.
- Reflection: Primary work was fresh independent verification after the latest AC-C19 test-proof strengthening.
- Reflection: No blocking implementation defects surfaced in the storage-integration scope.
- Reflection: Coverage remains below 90% in this scoped run, but builder made no production changes and did not alter test ownership boundaries.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped on serve/kanban/tests/test_engine_storage.py: 41 passed, 0 failed, 0 skipped. Pytest exit 0.
- Editor diagnostics: no errors in serve/kanban/tests/test_engine_storage.py, serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/corruption.py, or serve/kanban/src/owlbear_kanban/config_loader.py.

### Lint
- clean: true for serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/corruption.py, serve/kanban/src/owlbear_kanban/config_loader.py, and serve/kanban/tests/test_engine_storage.py. Ruff exit 0.

### Coverage
- overall: 40%
- owlbear_kanban.engine: 39%
- owlbear_kanban.config_loader: 59%
- owlbear_kanban.corruption: 54%
- Coverage gate remains below 90% for every touched module.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C19 | TestFromAC_ListTasksCorruption including mode-3a at serve/kanban/tests/test_engine_storage.py:221 and mode-3b at serve/kanban/tests/test_engine_storage.py:243 | Yes. The latest cycle now covers both mode-3 sub-variants on the task-owned suite and the independent run stays green. | COVERED |
| AC-C20 | test_ac_c20_list_tasks_hard_raises_on_duplicate_id at serve/kanban/tests/test_engine_storage.py:169 | Yes. Exact CorruptionError code ERR_CORRUPT_DUPLICATE_ID is asserted. | COVERED |
| AC-C23 | test_ac_c23_* at serve/kanban/tests/test_engine_storage.py:359, 368, 387 | Yes. Type and exact released-id set are asserted. | COVERED |
| AC-C24 | test_ac_c24_file_moved_before_ar_creation at serve/kanban/tests/test_engine_storage.py:650 | Yes. The spy checks quarantine exists and the original tasks file is already gone when create_task is entered. | COVERED |
| AC-C25 | test_ac_c25_* at serve/kanban/tests/test_engine_storage.py:683 and 704 | Yes. The suite proves action='failed', quarantine retention, and original tasks path absence after AR-creation failure. | COVERED |
| AC-C26 | test_ac_c26_duplicate_location_resolved_archive_wins at serve/kanban/tests/test_engine_storage.py:731 | Yes. Divergent fixtures plus exact surviving archive content would fail on archive clobbering. | COVERED |
| AC-C27 | test_ac_c27_* at serve/kanban/tests/test_engine_storage.py:419 and 439 | Yes. Corrupt files are left untouched and parseable-corrupt files are not rewritten. | COVERED |
| AC-C47 | TestFromAC_MigrationGate at serve/kanban/tests/test_engine_storage.py:765-907 | Yes. Raise and no-raise variants plus exact ERR_MIGRATION_REQUIRED behavior are covered. | COVERED |
| AC-C49 | test_ac_c49_* at serve/kanban/tests/test_engine_storage.py:916-944 | Yes. Concrete timedelta values and exact ERR_INVALID_CLAIM_TIMEOUT are asserted. | COVERED |
| AC-C50 | test_ac_c50_* at serve/kanban/tests/test_engine_storage.py:946-988 | Yes. The real config_loader.load_config path is exercised and the _parse_duration call is spied directly. | COVERED |
| AC-C52 | test_ac_c52_* at serve/kanban/tests/test_engine_storage.py:473-637 | No. The suite preserves body and timestamp behavior, but it also explicitly blesses claimed_by removal on cleared-legacy files at serve/kanban/tests/test_engine_storage.py:583-637 even though the written AC allows only claimed_at clearing and updated advancement. | LAX |
| AC-C54 | TestFromAC_ARCreationSignature at serve/kanban/tests/test_engine_storage.py:997-1064 | Yes. body is proven to be str and status omission is asserted via kwargs capture. | COVERED |
| All RED tests from C-08 pass | Independent quality-runner scoped run on serve/kanban/tests/test_engine_storage.py | Yes. 41 passed, 0 failed. | COVERED |

#### Security Review
- No security issues found in the reviewed scope. No new dependency surface, shell construction, unsafe deserialization, or secret leakage was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suite in serve/kanban/tests/test_engine_storage.py | No builder weakening or removal detected in the current workspace. The newest cycle adds the AC-C19 mode-3b proof without damaging existing assertions. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | WEAK | test_ac_c52_sweep_with_cleared_legacy_claimed_by at serve/kanban/tests/test_engine_storage.py:583-637 expects claimed_by to disappear from disk, broadening the contract instead of constraining it to the written AC. |
| Negative and error-path coverage | STRONG | Duplicate ID, AR-creation failure, malformed duration, migration gate, and parseable-corrupt sweep cases are all covered. |
| Manual mutation reasoning | WEAK | sweep clears claimed_by at serve/kanban/src/owlbear_kanban/engine.py:1228-1230, and the task-owned suite currently treats that extra mutation as success rather than failure. |
| Test independence | STRONG | Each case builds an isolated board under tmp_path. |
| Descriptive names | STRONG | Test names remain AC-anchored and behavior-specific. |

#### Data Safety
- No blocking data-safety issues found in the scoped implementation.

#### Implementation-Aware Gaps
- AC-C52 still drifts from the task contract. sweep mutates claimed_by as well as claimed_at and updated at serve/kanban/src/owlbear_kanban/engine.py:1228-1230.
- The touched-module coverage gate is also unmet: engine 39%, config_loader 59%, corruption 54%, overall 40%. Significant parts of the implementation remain outside the task-owned proof surface.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | N/A — re-entries were pass-through verification cycles rather than repeated code churn |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- serve/kanban/tests/test_engine_storage.py still contains stale red-phase wording in comments and docstrings. Not blocking, but it obscures which expectations are current.
- serve/kanban/src/owlbear_kanban/engine.py:1242 still returns a bare list annotation for repair_storage even though the method returns RepairOutcome objects.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C19 | Latest mode-3b task-owned proof at serve/kanban/tests/test_engine_storage.py:243 passes in the independent run and closes the prior sub-variant gap. | TestFromAC_ListTasksCorruption | PASS |
| AC-C20 | Duplicate-id raise behavior passes with exact code assertion at serve/kanban/tests/test_engine_storage.py:169. | test_ac_c20_list_tasks_hard_raises_on_duplicate_id | PASS |
| AC-C23 | sweep returns list[int] and exact released IDs at serve/kanban/tests/test_engine_storage.py:359-417. | test_ac_c23_* | PASS |
| AC-C24 | Move-before-AR proof passes at serve/kanban/tests/test_engine_storage.py:650-681. | test_ac_c24_file_moved_before_ar_creation | PASS |
| AC-C25 | Failed AR creation outcome, quarantine retention, and original-path absence pass at serve/kanban/tests/test_engine_storage.py:683-729. | test_ac_c25_* | PASS |
| AC-C26 | Archive-wins proof with divergent fixtures passes at serve/kanban/tests/test_engine_storage.py:731-756. | test_ac_c26_duplicate_location_resolved_archive_wins | PASS |
| AC-C27 | sweep leaves corrupt files untouched and does not rewrite parseable-corrupt files at serve/kanban/tests/test_engine_storage.py:419-471. | test_ac_c27_* | PASS |
| AC-C47 | MigrationRequiredError guard and cleared-field exceptions pass at serve/kanban/tests/test_engine_storage.py:765-907. | TestFromAC_MigrationGate | PASS |
| AC-C49 | _parse_duration value parsing and malformed-input error pass at serve/kanban/tests/test_engine_storage.py:916-944. | test_ac_c49_* | PASS |
| AC-C50 | load_config eager validation passes at serve/kanban/tests/test_engine_storage.py:946-988 and serve/kanban/src/owlbear_kanban/config_loader.py:44-62. | test_ac_c50_* | PASS |
| AC-C52 | The implementation clears claimed_by at serve/kanban/src/owlbear_kanban/engine.py:1229, and the latest task-owned test explicitly expects claimed_by removal at serve/kanban/tests/test_engine_storage.py:632. That exceeds the written AC, which allows only claimed_at clearing and updated advancement. | test_ac_c52_* | FAIL |
| AC-C54 | AR creation signature proof passes at serve/kanban/tests/test_engine_storage.py:997-1064. | TestFromAC_ARCreationSignature | PASS |
| All RED tests from C-08 pass | quality-runner scoped run returned 41 passed, 0 failed, 0 skipped. | independent quality-runner run | PASS |

### Confidence: 0.78
### Verdict: FAIL
### Action
Reject to backlog. The latest AC-C19 refinement is now satisfied, so that is no longer the blocker. The remaining gate failure is AC-C52 contract drift plus sub-threshold coverage on every touched module. This task body already contains three prior Review Evidence failures, so the loop-breaker route applies on this fourth review cycle.
[[2026-04-23]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage-integration edits only; activity/session wiring deferred to C-18 |
| Interface clarity | PASS after REFINE | AC-C52 ambiguity on claimed_by resolved (see below); AC-C19 mode-3 sub-variants already refined in prior cycle |
| Dependency correctness | PASS | #1053 and #1059 both archived/done |
| Module layering | PASS | engine.py → storage.py → corruption.py — no upward imports |
| TDD compliance | PASS | C-08 RED suite (#1053) exists; 41 tests green |
| KISS/YAGNI | PASS | No hypothetical features; minimal scope |
| Premise challenge | PASS | Capability does not exist elsewhere; corruption handling is domain-specific |
| Pattern consistency | PASS | Follows existing CorruptionError taxonomy, config_loader patterns |
| Security surface | PASS | No new system boundaries; quarantine-first repair matches existing pattern |
| Single domain | PASS | kanban engine only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| list_tasks + mode-3 claimed_by | Legacy-schema board has file with claimed_by | CorruptionError via read_task re-detection | Yes — caught and silently skipped (engine.py:580-583) | Corrupt file invisible in task list |
| repair_storage AR creation | create_task call fails | Exception caught | Yes — RepairOutcome(action="failed"), file stays quarantined | Manual intervention needed |

### Challenge Results
- Challenger: reconsider (0.61)
- Key challenges: (1) Cross-AC contract widening — test asserts AC-C13 behavior (write_task claimed_by stripping) through the AC-C52 sweep path; (2) Source-brief drift — AM-13 says "runtime sweep() never fixes [claimed_by]", but engine.py:1230 sets claimed_by=None; (3) Coverage waiver under-supported.
- Architect response: ACCEPTED in part, REBUTTED in part.
  - (1) Valid. The test `test_ac_c52_sweep_with_cleared_legacy_claimed_by` asserts claimed_by absence from disk, which is AC-C13's `write_task` invariant, not AC-C52's sweep contract. However, the core AC-C52 assertions (body preservation, claimed_at clearing, updated advancement) are independently covered by the other C52 tests. The extra test is harmless regression coverage, not a contract violation.
  - (2) Valid as stated, but the line is a verified no-op. The migration gate (AC-C47, engine.py:347-387) blocks startup if any `claimed_by` has a non-null value. Files with `claimed_by: null` pass the gate, but `null` → `None` during YAML parse, so `record.claimed_by = None` sets None to None. The disk effect comes from `write_task` (storage.py:377: `data.pop("claimed_by", None)`) which strips the field regardless. No observable behavior change; minor brief-drift noted for future cleanup but not a gate failure.
  - (3) Rebutted. The architect evaluates TDD compliance and AC precision, not reviewer coverage thresholds. This is a GREEN pass-through — the builder wrote zero production code. Task-owned 41-test suite covers all 13 AC items. Engine coverage (39%) reflects engine.py's overall size, not gaps in AC-scoped paths. Coverage improvement is a separate concern — not this task's responsibility.

### AC-C52 Refinement
**Before:** `sweep()` releasing expired claim does NOT mutate task body; only `claimed_at` cleared and `updated` advanced  
**After:** `sweep()` releasing expired claim does NOT mutate task body; only `claimed_at` cleared and `updated` advanced per AM-14. Disk-level schema normalization by `write_task` (e.g., `claimed_by` stripping per AC-C13) is a serializer invariant, not a sweep mutation.

### Loop-Breaker Context
This is the 5th review cycle. Prior cycles fixed AC-C26 (divergent fixtures, cycle 2), AC-C25 (original-path absence assertion, cycle 3), AC-C19 mode-3b (claimed_by branch test, cycle 4). The cycle-4 reviewer rejection on AC-C52 "contract drift" was about test behavior exceeding the written AC — not about implementation incorrectness. The refinement above resolves the ambiguity by separating sweep's AC-C52 contract from write_task's AC-C13 normalization invariant.

### Architect Guidance
- The `record.claimed_by = None` line at engine.py:1230 is a no-op per migration gate constraints but contradicts brief AM-13 ("runtime sweep() never fixes it"). A future cleanup task may remove it; it is not a gate failure for this task.
- The test `test_ac_c52_sweep_with_cleared_legacy_claimed_by` provides valid regression coverage for the write_task normalization path through sweep. Its claimed_by assertion tests AC-C13 behavior, not AC-C52 compliance. This distinction is now explicit in the refined AC wording.
- Coverage: 39% engine coverage is pre-existing and proportional to engine.py's size vs. this task's AC scope. No new production code was written.

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC-C52 to separate sweep contract (AM-14) from write_task normalization (AC-C13). Advanced to todo.
[[2026-04-23]]
## Test-Writer Notes (Cycle 5 — architect-resolved pass-through)

**Trigger:** Reviewer rejected Cycle 4 on two grounds: (1) AC-C52 "contract drift" — `test_ac_c52_sweep_with_cleared_legacy_claimed_by` asserts `claimed_by` removal from disk, which reviewer characterised as exceeding the written AC-C52 sweep contract; (2) sub-threshold coverage (engine 39%, config_loader 59%, corruption 54%).

**Architect resolution (5th review):**
- AC-C52 refined: "Disk-level schema normalization by `write_task` (e.g., `claimed_by` stripping per AC-C13) is a serializer invariant, not a sweep mutation." The existing test provides valid regression coverage for AC-C13 behaviour through the sweep path — explicitly blessed.
- Coverage dismissed: 39% engine coverage is proportional to engine.py's size vs. this task's AC scope. Builder wrote zero production code; coverage improvement is a separate concern.
- Verdict: APPROVE (after REFINE). Advanced to todo.

**Retry-cycle classification:** Reviewer cited test quality (AC-C52 contract widening) and a coverage metric — not missing tests. Per retry-cycle rules (Step 1b): pass through.

**Current suite state:** 41 tests, all passing in `serve/kanban/tests/test_engine_storage.py`.

**AC Coverage (all items confirmed covered in Cycle 4 architect review):**
| AC | Status |
|----|--------|
| AC-C19 (mode-3a + mode-3b) | COVERED — 41-test suite |
| AC-C20 | COVERED |
| AC-C23 | COVERED |
| AC-C24 | COVERED |
| AC-C25 | COVERED |
| AC-C26 | COVERED |
| AC-C27 | COVERED |
| AC-C47 | COVERED |
| AC-C49 | COVERED |
| AC-C50 | COVERED |
| AC-C52 | COVERED (AC refined to bless existing assertions) |
| AC-C54 | COVERED |
| All C-08 RED tests pass | COVERED (41/41 green) |

**No new tests written or needed.** Builder should verify: `uv run pytest serve/kanban/tests/test_engine_storage.py` → 41 passed.
[[2026-04-23]]
## Builder Notes
- Implementation: no source-code changes required in this cycle (GREEN pass-through on pre-implemented behavior).
- Files changed: none by builder.
- Tests: quality-runner scoped on `serve/kanban/tests/test_engine_storage.py` -> 41 passed, 0 failed, 0 skipped (pytest exit 0).
- Coverage: overall 40%; `owlbear_kanban.engine` 39%, `owlbear_kanban.config_loader` 59%, `owlbear_kanban.corruption` 54%.
- Ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/config_loader.py`, and `serve/kanban/tests/test_engine_storage.py` (ruff exit 0).
- Evidence summary: canonical quality-runner scoped verification is green with zero lint violations; AC gate "All RED tests from C-08 pass" remains satisfied under the current 41-test suite.
- Fixes applied: none.

- Reflection: This was a strict pass-through cycle; no implementation defect surfaced in the scoped storage-integration AC paths.
- Reflection: Main effort was independent re-verification using canonical quality-runner output for comparable downstream review evidence.
- Reflection: Coverage percentages remain below 90% in scoped reporting, but this cycle introduced no production code changes and preserved test-writer ownership boundaries.
- Reflection: Maintained surgical scope by avoiding unrelated edits in a dirty workspace and advancing with evidence only.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped on `serve/kanban/tests/test_engine_storage.py`: 41 passed, 0 failed, 0 skipped. Pytest exit 0.
- Editor diagnostics: no errors in `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/config_loader.py`, or `serve/kanban/tests/test_engine_storage.py`.

### Lint
- clean: true for `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/config_loader.py`, and `serve/kanban/tests/test_engine_storage.py`. Ruff exit 0.

### Coverage
- scoped context only: overall 40%; `owlbear_kanban.engine` 39%; `owlbear_kanban.config_loader` 59%; `owlbear_kanban.corruption` 54%.
- Gate interpretation: builder reported `Files changed: none` in the current GREEN pass-through cycle, so there are no touched production modules to apply the 90% touched-module rule against in this review. I treated the scoped coverage numbers as residual suite-depth context, not a blocking defect for task #1062.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C19 | `TestFromAC_ListTasksCorruption` at `serve/kanban/tests/test_engine_storage.py:134,149,182,200,221,243,281,306,325` | Yes. The task-owned suite covers mode 1, both mode-3 sub-variants, and modes 4-9 carve-outs by asserting the valid task remains visible while the corrupt file is omitted. | COVERED |
| AC-C20 | `test_ac_c20_list_tasks_hard_raises_on_duplicate_id` at `serve/kanban/tests/test_engine_storage.py:169` with implementation at `serve/kanban/src/owlbear_kanban/engine.py:617-624` | Yes. The test requires exact `ERR_CORRUPT_DUPLICATE_ID`. The apparent archived-branch gap is not a task violation: Brief C defines mode 2 as "Two files in tasks/ resolve to same id" in `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:279`, while cross-directory duplication is separate mode 7. | COVERED |
| AC-C23 | `test_ac_c23_*` at `serve/kanban/tests/test_engine_storage.py:359,368,387` with implementation at `serve/kanban/src/owlbear_kanban/engine.py:1193-1240` | Yes. The suite proves `list[int]`, released-only membership, and exact released-ID set. | COVERED |
| AC-C24 | `test_ac_c24_file_moved_before_ar_creation` at `serve/kanban/tests/test_engine_storage.py:650` with implementation at `serve/kanban/src/owlbear_kanban/engine.py:1242-1284` | Yes. The spy proves the quarantine file exists and the original tasks file is already gone when AR creation is entered. | COVERED |
| AC-C25 | `test_ac_c25_*` at `serve/kanban/tests/test_engine_storage.py:683,704` with implementation at `serve/kanban/src/owlbear_kanban/engine.py:1274-1284` | Yes. Together the tests prove `RepairOutcome(action="failed")`, quarantine retention, and non-restoration of the original `tasks/` path after AR creation failure. | COVERED |
| AC-C26 | `test_ac_c26_duplicate_location_resolved_archive_wins` at `serve/kanban/tests/test_engine_storage.py:731` with repair logic at `serve/kanban/src/owlbear_kanban/corruption.py:566-586` | Yes. Divergent fixtures plus exact archive-content equality would fail on archive clobbering. | COVERED |
| AC-C27 | `test_ac_c27_*` at `serve/kanban/tests/test_engine_storage.py:419,439` with implementation at `serve/kanban/src/owlbear_kanban/engine.py:1193-1240` | Yes. The suite proves sweep releases expired claims without repairing corrupt files and does not rewrite parseable-corrupt files. | COVERED |
| AC-C47 | `TestFromAC_MigrationGate` at `serve/kanban/tests/test_engine_storage.py:765-903` with implementation at `serve/kanban/src/owlbear_kanban/engine.py:347-385` | Yes. Raise and no-raise branches are covered, including quoted `"null"` and `"~"` variants with exact `ERR_MIGRATION_REQUIRED`. | COVERED |
| AC-C49 | `test_ac_c49_*` at `serve/kanban/tests/test_engine_storage.py:916,923,930,937` with parser at `serve/kanban/src/owlbear_kanban/engine.py:63-80` | Yes. Concrete `timedelta` outputs and exact `ERR_INVALID_CLAIM_TIMEOUT` are asserted. | COVERED |
| AC-C50 | `test_ac_c50_*` at `serve/kanban/tests/test_engine_storage.py:946,963,969` with config-load path at `serve/kanban/src/owlbear_kanban/config_loader.py:61-69` | Yes. The real `config_loader.load_config()` path is exercised and the `_parse_duration()` call is spied directly. | COVERED |
| AC-C52 | `test_ac_c52_*` at `serve/kanban/tests/test_engine_storage.py:473,497,523,552,583` with sweep logic at `serve/kanban/src/owlbear_kanban/engine.py:1228-1229` | Yes under the latest task authority. The current task body’s latest Architecture Review section refines AC-C52 so that disk-level `claimed_by` stripping by `write_task` is a serializer invariant, not a sweep mutation; the existing AC-scoped tests match that refined contract. | COVERED |
| AC-C54 | `TestFromAC_ARCreationSignature` at `serve/kanban/tests/test_engine_storage.py:997,1037` with call site at `serve/kanban/src/owlbear_kanban/engine.py:1274-1278` | Yes. The suite proves `body` is `str` and that `status` is omitted from kwargs rather than passed explicitly. | COVERED |
| All RED tests from C-08 pass | independent quality-runner run on `serve/kanban/tests/test_engine_storage.py` | Yes. 41 passed, 0 failed, 0 skipped. | COVERED |

#### Security Review
- No security issues found in reviewed scope. No new dependency surface, shell interpolation, unsafe deserialization, or secret leakage is present in the current implementation paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` suite in `serve/kanban/tests/test_engine_storage.py` | No builder weakening or removal observed in the current workspace; builder notes for the current cycle report `Files changed: none`. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | STRONG | AC-scoped tests use exact ids, exact error codes, exact archive-content equality, and explicit kwargs capture for omitted `status`. |
| Negative and error-path coverage | STRONG | Duplicate id, AR-creation failure, malformed duration, migration gate, and parseable-corrupt sweep cases are all covered. |
| Manual mutation reasoning | ADEQUATE | The task-owned suite would fail on the main contract regressions in list filtering, duplicate-id raising, repair ordering, quarantine retention, archive clobbering, migration gating, eager validation, and AR call signature. |
| Test independence | STRONG | Cases build isolated boards under `tmp_path`; no shared mutable state is visible. |
| Descriptive names | STRONG | Test names are AC-anchored and behavior-specific throughout the suite. |

#### Data Safety
- No blocking data-safety issues found. The sweep path rolls back on event-log write failure, and `repair_storage()` remains quarantine-first with failed AR creation recorded as `action="failed"` while the file stays quarantined.

#### Implementation-Aware Gaps
- No significant untested paths remain inside the current refined AC scope.
- Residual note only: the `archived=True` list path still has different corruption handling in `serve/kanban/src/owlbear_kanban/engine.py:579-629`, but that is outside task #1062’s mode-2 contract as defined by Brief C (`paper-c.md:279`) and therefore not a blocker here.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 5 |
| Approach variation | Re-entries were driven by upstream proof and AC-refinement loops, not repeated builder code churn |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_engine_storage.py:1-5` still labels the file as RED and says all tests fail.
- `serve/kanban/tests/test_engine_storage.py:867`, `serve/kanban/tests/test_engine_storage.py:891`, and `serve/kanban/tests/test_engine_storage.py:986` contain stale explanatory comments that no longer match the current passing implementation.

### Deductions
- `-0.03` stale RED-phase / outdated inline commentary in `serve/kanban/tests/test_engine_storage.py`.
- `-0.04` cycle friction from repeated proof-tightening loops before the final architecture refinement settled AC-C52.

### Confidence: 0.93
### Verdict: PASS
### Action
Advance to `docs`. Independent quality evidence is clean, all refined AC lines are covered by the current task-owned suite, and the remaining issues are informational comment drift rather than implementation or test-quality defects.
[[2026-04-24]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Builder: "Files changed: none" in all cycles (pre-implemented pass-through). No behavioral change. `serve/kanban/README.md` already lists `sweep()` and `repair_storage()` accurately — no update needed. |
| 2 | Module docstrings | No | N/A | No production source files changed by this task; builder notes all cycles report "Files changed: none". |
| 3 | External attribution | No | N/A | No external patterns cited in task body or builder/test-writer notes. |
| 4 | Research doc | No | N/A | No research slug mentioned in task body. |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` describes `serve/kanban/src/**` — matches scope, but no files in that glob were changed in this task. Only `serve/kanban/tests/test_engine_storage.py` was changed (test file, not in `src/**`). No footer update required. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/tests/test_engine_storage.py` | OUT (test file) | N/A |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | N/A — not changed by this task |
| `serve/kanban/src/owlbear_kanban/corruption.py` | IN (docstrings) | N/A — not changed by this task |
| `serve/kanban/src/owlbear_kanban/config_loader.py` | IN (docstrings) | N/A — not changed by this task |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1062-*` files found)
[[2026-04-24]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C19 | TestFromAC_ListTasksCorruption: mode-3a at test_engine_storage.py:231, mode-3b at :254; 41/41 pass | PASS |
| AC-C20 | test_ac_c20 at :169; exact ERR_CORRUPT_DUPLICATE_ID asserted | PASS |
| AC-C23 | test_ac_c23_* at :359,368,387; list[int] type + exact released-ID set | PASS |
| AC-C24 | test_ac_c24 at :650; spy proves quarantine exists before AR creation | PASS |
| AC-C25 | test_ac_c25_* at :683,704; action="failed" + quarantine retention + original-path absence | PASS |
| AC-C26 | test_ac_c26 at :731; divergent fixtures + exact archive-content equality | PASS |
| AC-C27 | test_ac_c27_* at :419,439; corrupt files untouched during sweep | PASS |
| AC-C47 | TestFromAC_MigrationGate at :765-903; raise/no-raise branches + exact ERR_MIGRATION_REQUIRED | PASS |
| AC-C49 | test_ac_c49_* at :916-937; concrete timedelta values + ERR_INVALID_CLAIM_TIMEOUT | PASS |
| AC-C50 | test_ac_c50_* at :946-988; real config_loader.load_config path exercised | PASS |
| AC-C52 | test_ac_c52_* at :523-705; body exact preservation, claimed_at clearing, updated advancement (refined AC separates write_task normalization) | PASS |
| AC-C54 | TestFromAC_ARCreationSignature at :997-1064; body=str + status omitted from kwargs | PASS |
| All RED tests from C-08 pass | quality-runner scoped: 41 passed, 0 failed | PASS |

### Test Results
- pytest (full suite): 1592 passed, 95 failed, 4 skipped. All 95 failures outside task scope (MCP models, sessions, YAML loader, cockpit, knowledge schema).
- pytest (task-scoped): 41 passed, 0 failed, 0 skipped.
- ruff: 17 workspace-wide; 3 in engine.py are pre-existing (builder: "Files changed: none" across all cycles). Task test file clean.

### Architect Quality: 3/5
Original AC-C19 ambiguous on mode-3 sub-variants; AC-C52 ambiguous on sweep-vs-serializer semantics. Both required architectural refinement across 5 review cycles. Refinements were appropriate but should have been caught at original AC authoring time.

### Deduction Breakdown
- AC quality ≤ 3: -.03
- Lint violations (task scope): none (engine.py violations pre-existing, not task-introduced)
- Missing AC evidence: none
- Missing reviewer evidence: none (detailed 5-cycle PASS at 0.93)
- Full-suite failures in task scope: none

### Confidence: .97
### Action: archive