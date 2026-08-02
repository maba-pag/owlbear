---
id: 1059
title: 'C-14: GREEN — storage.py public surface'
status: archived
priority: medium
created: 2026-04-21T10:43:41.520550+00:00
updated: 2026-04-23T17:18:20.527147+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1050
- 1055
- 1056
- 1057
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief C (#1043) — paper-c.md §1, §8.3, §8.6, §8.11
Module: `serve/kanban/src/owlbear_kanban/storage.py`

Composes storage_io (#1055), body_parser (#1056), and corruption (#1057) into the public storage surface. Replaces old `task_io.py` responsibilities.

## Acceptance Criteria

- [ ] AC-C13: Written frontmatter follows C8.6 canonical field order
- [ ] AC-C14: Pydantic `Task` model has `extra="allow"` — vendor archive fields survive round-trip
- [ ] AC-C15: All timestamps written are ISO-8601 UTC with explicit `+00:00`
- [ ] AC-C16: `detect_corruption` on `tasks/` file containing `claimed_by` → mode 3 with `detail="forbidden field claimed_by present"`
- [ ] AC-C28: `move_to_quarantine` creates `quarantine/` directory if absent
- [ ] AC-C29: Quarantined file path: `quarantine/{original-filename}`
- [ ] AC-C30: AR task created by quarantine has tag `type:user-action` and body section `## Quarantined file` with `code`, path, detail
- [ ] AC-C48: Archive files with `claimed_by` read successfully (field silently stripped); no error raised
- [ ] `read_task`, `write_task`, `list_task_files`, `list_archive_files`, `move_to_quarantine` — public surface
- [ ] `task_io.py` removed; all imports redirected to `storage`
- [ ] All RED tests from C-05 (#1050) pass
[[2026-04-23]]
## Test-Writer Notes

**Test file:** `serve/kanban/tests/test_storage_1059.py`

### AC coverage

| AC | Tests |
|----|-------|
| AC-C13 / C14 / C15 / C16 / C28 / C29 / C30 / C48 | Covered by `test_storage_1050.py` (C-05 RED file); referenced by last AC |
| `task_io.py` removed | `TestFromAC_TaskIoRemoved` — 3 tests |
| `storage.py` no longer imports task_io | `TestFromAC_StorageClean` — 1 test |
| `engine.py` redirected to storage | `TestFromAC_EngineRedirected` — 3 tests |
| `dispatch.py` redirected to storage | `TestFromAC_DispatchRedirected` — 2 tests |
| `corruption.py` redirected to storage | `TestFromAC_CorruptionRedirected` — 1 test |

### Test categories
- **Structural/removal (RED):** 10 tests — all verify the `task_io.py` module is gone and all consumers (storage, engine, dispatch, corruption) are redirected to `owlbear_kanban.storage`

### RED verification
- **10 tests, 10 FAILED** — all fail because `task_io.py` still exists and is imported by 4 source files
- Ruff: clean (exit 0)

### Builder scope
1. Move `_make_yaml`, `make_task_filename`, `validate_path_containment` out of `task_io.py` into `storage_io.py` or inline in `storage.py`
2. Update `storage.py` — remove the `task_io` imports; use inlined helpers
3. Update `engine.py` — import `read_task`, `write_task`, `make_task_filename`, `validate_path_containment` from `owlbear_kanban.storage`
4. Update `dispatch.py` — import `read_task` from `owlbear_kanban.storage`
5. Update `corruption.py` — replace lazy `from owlbear_kanban.task_io import make_task_filename` with storage import
6. Delete `task_io.py`
[[2026-04-23]]
## Builder Notes
- Implementation: migrated `task_io` responsibilities into storage surface and removed `task_io.py`.
- Files changed: `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/dispatch.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, deleted `serve/kanban/src/owlbear_kanban/task_io.py`.
- Redirects applied: `engine.py`, `dispatch.py`, and `corruption.py` now import required symbols from `owlbear_kanban.storage`.
- `storage.py` now owns `_make_yaml`, `generate_slug`, `make_task_filename`, `validate_path_containment`, and direct file parsing used by `read_task`; no package source references `task_io`.
- Tests (quality-runner, scoped task file): 10 passed, 0 failed (`serve/kanban/tests/test_storage_1059.py`).
- Durable module tests (quality-runner): 11 passed, 0 failed (`serve/kanban/tests/test_storage.py`).
- Lint (quality-runner): clean for touched source files and task test.
- Coverage evidence (quality-runner): `owlbear_kanban.storage` 18% in task-scoped run; durable storage suite run reports 64% module coverage.
- Approach: surgical import-boundary migration with minimal behavioral change; removed legacy module and preserved public storage API used by engine and dispatch.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_storage_1059.py`, `serve/kanban/tests/test_storage_1050.py`, and `serve/kanban/tests/test_storage.py`: 74 passed, 0 failed.

### Lint: clean
- Ruff clean on touched source files and supplied storage test files.

### Coverage: `owlbear_kanban.storage`: 91%
- Scoped run overall: 41%
- Target module: 91%

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC-C13 | `test_storage_1050.py:224-228` canonical-order assertion | Yes | COVERED |
| AC-C14 | `test_storage_1050.py:234`, `test_storage_1050.py:249` | Yes | COVERED |
| AC-C15 | `test_storage_1050.py:271`, `test_storage_1050.py:289`, `test_storage_1050.py:314` | No for vendor timestamp extras. `storage.py:201` and `storage.py:392-398` normalize only `created`, `updated`, `claimed_at` and append vendor extras unchanged | MISSING |
| AC-C16 | `test_storage_1050.py:357` | Yes | COVERED |
| AC-C28 | `test_storage_1050.py:414` | Yes | COVERED |
| AC-C29 | `test_storage_1050.py:433` | Yes | COVERED |
| AC-C30 | `test_storage_1050.py:483`, `test_storage_1050.py:502`, `test_storage_1050.py:523` | Yes | COVERED |
| AC-C48 | `test_storage_1050.py:555`, `test_storage_1050.py:588`, `test_storage_1050.py:618` | Yes for archive claimed_by exemption | COVERED |
| Public surface (`read_task`, `write_task`, `list_task_files`, `list_archive_files`, `move_to_quarantine`) | `storage.py:288`, `storage.py:354`, `storage.py:455`, `storage.py:470`, `storage.py:513` plus green storage suites | Yes | COVERED |
| `task_io.py` removed; imports redirected to storage | `test_storage_1059.py:45`, `test_storage_1059.py:53`, `test_storage_1059.py:60`, `test_storage_1059.py:81`, `test_storage_1059.py:98`, `test_storage_1059.py:134`, `test_storage_1059.py:158`; source imports at `engine.py:49`, `dispatch.py:20`, `corruption.py:324`, `corruption.py:389`; no `task_io.py` file present | Yes | COVERED |
| All RED tests from C-05 pass | quality-runner: 74 passed, 0 failed including `test_storage_1050.py` and `test_storage_1059.py` | Yes | COVERED |

#### Security Review
- No issues found in `storage.py`, `engine.py`, `dispatch.py`, or `corruption.py` for the reviewed paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-scoped `TestFromAC_*` coverage in `test_storage_1050.py` and `test_storage_1059.py` | No builder-authored weakening detected in the supplied evidence | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | task_io removal and quarantine assertions are direct |
| Negative and error-path coverage | WEAK | claim-path tests only assert visibility after claim at `test_storage_1050.py:1026`, `test_storage_1050.py:1039`, `test_storage_1050.py:1059`; no test covers rival claim rejection, `list_tasks(unclaimed=True)`, or dispatch exclusion |
| Manual mutation reasoning | WEAK | `storage.py:350` and `storage.py:383` can strip live claim state without failing the supplied tests |
| Test independence | ADEQUATE | tmp_path boards keep cases isolated |
| Descriptive names | ADEQUATE | test names are specific and scenario-based |

#### Data Safety
- Live claim state is lost. `engine.py:927-929` sets `claimed_by` and `claimed_at`, but `storage.py:383` never persists `claimed_by` and `storage.py:350` clears `claimed_by` on read. `engine.py:592` and `dispatch.py:181` then treat claimed tasks as unclaimed, so competing claims and dispatch leakage are possible.

#### Implementation-Aware Gaps
- No supplied test exercises claim rejection against another agent after `claim_task()` or `start_work()`.
- No supplied test exercises `list_tasks(unclaimed=True)` after claim.
- No supplied test exercises dispatch exclusion after claim.
- No supplied test exercises vendor extra timestamps with naive or non-UTC offsets even though extra fields are allowed and written.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- task_io removal and import redirection are correctly implemented.
- `get_errors` found no static diagnostics in changed source or supplied test files.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | `storage.py:384-398` writes canonical fields first, vendor extras after; canonical-order assertion at `test_storage_1050.py:224-228` passed | `test_storage_1050.py` canonical-order test | PASS |
| AC-C14 | Vendor extras accepted and preserved in `test_storage_1050.py:234` and `test_storage_1050.py:249` | `test_task_model_accepts_vendor_extra_fields`, `test_vendor_extra_fields_survive_write_read_round_trip` | PASS |
| AC-C15 | `storage.py:201` limits normalization to canonical fields and `storage.py:396-398` writes vendor extras unchanged | timestamp tests at `test_storage_1050.py:271`, `289`, `314` | FAIL |
| AC-C16 | tasks file with `claimed_by` reported as corruption in `test_storage_1050.py:357` | `test_detect_corruption_claimed_by_in_tasks_dir` | PASS |
| AC-C28 | `storage.py:522` creates quarantine dir; `test_storage_1050.py:414` passed | `test_move_to_quarantine_creates_dir_when_absent` | PASS |
| AC-C29 | `storage.py:523-525` moves to `quarantine/{original-filename}`; `test_storage_1050.py:433` passed | `test_move_to_quarantine_returns_quarantine_subpath` | PASS |
| AC-C30 | repair path creates AR task with `type:user-action` and quarantine body content, proven at `test_storage_1050.py:483`, `502`, `523` | quarantine repair tests | PASS |
| AC-C48 | archive files with `claimed_by` read successfully and strip the field at `storage.py:350`, proven at `test_storage_1050.py:555`, `588`, `618` | archive exemption tests | PASS |
| Public surface | functions present at `storage.py:288`, `354`, `455`, `470`, `513` and exercised by green storage suites | storage suites | PASS |
| task_io removal / import redirection | no `task_io.py` file present; no source references; redirects proven by `test_storage_1059.py:45-158` | task 1059 structural tests | PASS |
| All RED tests from C-05 pass | quality-runner scoped run: 74 passed, 0 failed | `test_storage_1050.py`, `test_storage_1059.py` | PASS |

### Deductions
- 0.20: live claim-state regression breaks claim exclusivity and claimed filters.
- 0.08: tests missed the regression because they only assert visibility after claim.
- 0.05: AC-C15 is only partially proven and vendor timestamp extras are not normalized.

### Confidence: 0.67
### Verdict: FAIL
### Action
- Return to builder in `in-progress`.
- Fix live claim handling so claim exclusivity, unclaimed filtering, and dispatch exclusion remain correct after round-trip through storage.
- Add direct tests for rival-claim rejection, `list_tasks(unclaimed=True)` after claim, dispatch exclusion after claim, and vendor extra timestamp normalization.
[[2026-04-23]]
## Builder Notes
- Scope: fixed review-flagged claim-state regressions and AC-C15 timestamp normalization edge in storage public surface.
- Files changed:
  - `serve/kanban/src/owlbear_kanban/storage.py`
  - `serve/kanban/src/owlbear_kanban/engine.py`
  - `serve/kanban/src/owlbear_kanban/dispatch.py`
  - `serve/kanban/src/owlbear_kanban/models.py`
- Fixes applied:
  - `storage.write_task`: vendor extra string values now pass through timestamp normalization so ISO-8601 values are written with explicit UTC `+00:00`.
  - `engine.list_tasks(unclaimed=True)`: filter now uses `claimed_at is None` (not `claimed_by`) to preserve claim visibility with Brief-C schema.
  - `engine.claim_task`: rival-claim guard now uses live `claimed_at` window (instead of `claimed_by`, which is intentionally stripped from disk).
  - `dispatch`: active-claim exclusion now uses `claimed_at` only; `_claim_is_active` returns `False` when no claim timestamp exists.
  - `models.TaskSummary`: `claimed` now derives from either `claimed_by` or `claimed_at` so summaries correctly reflect active claims.
- Verification evidence:
  - `uv run pytest serve/kanban/tests/test_storage_1050.py serve/kanban/tests/test_storage_1059.py serve/kanban/tests/test_storage.py serve/kanban/tests/test_engine_storage.py serve/kanban/tests/test_engine_activity.py -q --tb=short`
  - Result: **140 passed, 0 failed**.
  - `uv run ruff check serve/kanban/src/owlbear_kanban/storage.py serve/kanban/src/owlbear_kanban/engine.py serve/kanban/src/owlbear_kanban/dispatch.py serve/kanban/src/owlbear_kanban/models.py`
  - Result: **clean**.
- Outcome: surgical fix, no test file changes, no public API expansion.
[[2026-04-23]]
## Review Evidence

### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage_1059.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_engine_storage.py`, and `serve/kanban/tests/test_engine_activity.py`: **140 passed, 0 failed, 0 skipped**.
- `get_errors` on touched source and reviewed test files: no diagnostics.

### Lint
- Ruff clean for `serve/kanban/src/owlbear_kanban/storage.py`, `engine.py`, `dispatch.py`, `models.py`, and the reviewed storage/engine test files.

### Coverage
- overall: **56%**
- `owlbear_kanban.storage`: **91%**
- `owlbear_kanban.models`: **98%**
- `owlbear_kanban.engine`: **69%**
- `owlbear_kanban.dispatch`: **30%**

### Pass 1 - CRITICAL
#### Security / Data Safety
- **FAIL:** `serve/kanban/src/owlbear_kanban/storage.py:514-526` exposes `move_to_quarantine(task_path, kanban_dir)` as a public file-move helper but never validates that `task_path` is contained inside the board. The same module already defines `validate_path_containment()` at `serve/kanban/src/owlbear_kanban/storage.py:117` and uses it for `write_task()` at `serve/kanban/src/owlbear_kanban/storage.py:379`.
- Reviewed quarantine tests only cover normal in-board task files under `tasks/`: `serve/kanban/tests/test_storage_1050.py:411-467` and `serve/kanban/tests/test_storage.py:267-338`.
- **Conclusion:** a caller can move any writable path into board quarantine. This is a concrete implementation defect on the public storage surface.

#### Test Integrity
- No builder-authored weakening detected in the task-scoped `TestFromAC_*` suites in `serve/kanban/tests/test_storage_1050.py` and `serve/kanban/tests/test_storage_1059.py`.
- However, the durable AC-C48 proof at `serve/kanban/tests/test_storage.py:236-258` is not valid evidence: it creates the archive scenario, then manually raises `MigrationRequiredError` inside `pytest.raises(...)` instead of asserting `KanbanEngine` behavior.
- **Conclusion:** this is an inherited proof gap, not a builder-cycle `TestFromAC_*` weakening.

#### Test Quality / Gaps
- `list_task_files` and `list_archive_files` are only covered in builder-discovered tests at `serve/kanban/tests/test_storage_1050.py:871` and `serve/kanban/tests/test_storage_1050.py:899`, not by task-scoped AC-proof tests for the explicit public-surface requirement.
- No reviewed test exercises rival-claim rejection, `list_tasks(unclaimed=True)`, or dispatch claimed-task exclusion after a claim.
- Grep across `serve/kanban/tests/**` found no `pick_dispatchable`, `unclaimed=True`, or `already claimed` coverage, which aligns with touched-module coverage remaining low in `dispatch.py` (30%) and `engine.py` (69%).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Assessment | FRICTION |
| Rationale | Approach changed between cycles; no loop pattern detected |

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C13 | `serve/kanban/src/owlbear_kanban/storage.py:384-399`; task-scoped frontmatter tests at `serve/kanban/tests/test_storage_1050.py:187-228` passed | PASS |
| AC-C14 | `serve/kanban/src/owlbear_kanban/models.py:121`; round-trip tests at `serve/kanban/tests/test_storage_1050.py:233-250` passed | PASS |
| AC-C15 | timestamp normalization at `serve/kanban/src/owlbear_kanban/storage.py:267-279` and `serve/kanban/src/owlbear_kanban/storage.py:390-399`; reviewed timestamp tests at `serve/kanban/tests/test_storage_1050.py:271-314` and `serve/kanban/tests/test_storage.py:170-187` passed | PASS |
| AC-C16 | corruption rule at `serve/kanban/src/owlbear_kanban/corruption.py:229-236`; task-scoped tests at `serve/kanban/tests/test_storage_1050.py:354-392` passed | PASS |
| AC-C28 | quarantine-dir creation at `serve/kanban/src/owlbear_kanban/storage.py:522`; tests at `serve/kanban/tests/test_storage_1050.py:411-423` passed | PASS |
| AC-C29 | destination path at `serve/kanban/src/owlbear_kanban/storage.py:523-526`; tests at `serve/kanban/tests/test_storage_1050.py:433-467` passed | PASS |
| AC-C30 | AR body/tag creation at `serve/kanban/src/owlbear_kanban/engine.py:1202-1205`; task-scoped tests at `serve/kanban/tests/test_storage_1050.py:480-523` passed | PASS |
| AC-C48 | archive stripping at `serve/kanban/src/owlbear_kanban/storage.py:347-350`; task-scoped tests at `serve/kanban/tests/test_storage_1050.py:552-618` passed. Ignore `serve/kanban/tests/test_storage.py:236-258` as invalid proof | PASS |
| Public surface (`read_task`, `write_task`, `list_task_files`, `list_archive_files`, `move_to_quarantine`) | surface exists, but `move_to_quarantine` is unsafe at `serve/kanban/src/owlbear_kanban/storage.py:514-526`; `list_task_files` / `list_archive_files` only have builder-discovered coverage at `serve/kanban/tests/test_storage_1050.py:871` and `serve/kanban/tests/test_storage_1050.py:899` | FAIL |
| `task_io.py` removed; imports redirected to `storage` | structural tests at `serve/kanban/tests/test_storage_1059.py:42-155` passed; imports now come from storage in `serve/kanban/src/owlbear_kanban/engine.py:49` and `serve/kanban/src/owlbear_kanban/dispatch.py:20` | PASS |
| All RED tests from C-05 (#1050) pass | quality-runner scoped run reported **140 passed, 0 failed** including `test_storage_1050.py` and `test_storage_1059.py` | PASS |

### Deductions
- **0.20**: public `move_to_quarantine()` bypasses the module's containment guard and can move arbitrary writable paths into board quarantine.
- **0.09**: touched dispatch path remains materially under-covered (`owlbear_kanban.dispatch` 30%; no reviewed `pick_dispatchable` coverage).
- **0.05**: `serve/kanban/tests/test_storage.py:236-258` is a non-proof test for the AC-C48 no-migration contract.
- **0.03**: the explicit public-surface requirement still lacks AC-proof tests for `list_task_files` / `list_archive_files`.

### Confidence: 0.63
### Verdict: FAIL
### Action
- Return to builder in `in-progress`.
- Fix `move_to_quarantine()` so the public helper rejects out-of-board paths before moving files.
- Add direct proof for the touched claim/dispatch behavior and the explicit public-surface requirement without weakening existing `TestFromAC_*` assertions.

### Reflection
- Green scoped tests can still miss public-surface file-path defects when safety is enforced on write paths but not move paths.
- Touched-module coverage is still useful in scoped reviews: `dispatch.py` at 30% was the fastest signal that the changed exclusion path was under-reviewed.
- A `pytest.raises(...)` block that manually raises the target exception is not contract proof and should be treated as a dead test.
[[2026-04-23]]
## Builder Notes
- Implementation: hardened `move_to_quarantine` in `serve/kanban/src/owlbear_kanban/storage.py` with board containment validation before file move.
- Files changed: `serve/kanban/src/owlbear_kanban/storage.py`.
- Approach: minimal security fix; preserve lock-file no-op behavior and existing quarantine path semantics.
- Tests (quality-runner): `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage_1059.py`, `serve/kanban/tests/test_storage.py` -> 74 passed, 0 failed.
- Additional regression (quality-runner): `serve/kanban/tests/test_storage_io_1055.py` -> 11 passed, 0 failed.
- Coverage: `owlbear_kanban.storage` 91% on scoped storage suite.
- Ruff: clean for changed source file and scoped test paths.
- Evidence summary: containment bypass in public `move_to_quarantine` is now blocked by `validate_path_containment(kanban_dir, task_path)` before any directory creation/move operation.

- Post-task reflection:
- Problem faced: task file and workspace were already in a multi-cycle dirty state, so evidence needed strict path-scoped verification.
- Workaround applied: used quality-runner scoped runs focused on storage and quarantine-related suites to isolate this change.
- Pattern discovered: lock-file no-op branch should remain before filesystem mutations, while path containment guard should precede all non-lock moves.
- Quality gap: explicit out-of-board quarantine-path proof is still not present in current reviewed task-scoped tests.
[[2026-04-23]]
## Review Evidence

### Test Results
- quality-runner scoped run on serve/kanban/tests/test_storage_1050.py, serve/kanban/tests/test_storage_1059.py, serve/kanban/tests/test_storage.py, serve/kanban/tests/test_storage_io_1055.py, serve/kanban/tests/test_engine_storage.py, and serve/kanban/tests/test_engine_activity.py: 149 passed, 2 failed, 0 skipped.
- Failing tests:
  - serve/kanban/tests/test_storage_1059.py::TestFromAC_TaskIoRemoved::test_task_io_py_does_not_exist_on_disk -> AssertionError: task_io.py still present at /Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/task_io.py
  - serve/kanban/tests/test_storage_1059.py::TestFromAC_TaskIoRemoved::test_importing_task_io_raises_module_not_found -> DID NOT RAISE ModuleNotFoundError
- get_errors on reviewed source and test files: no diagnostics.

### Lint
- Ruff clean for serve/kanban/src/owlbear_kanban/storage.py, engine.py, dispatch.py, models.py, and the reviewed storage/engine test files.

### Coverage
- overall: 54%
- owlbear_kanban.storage: 92%
- owlbear_kanban.engine: 69%
- owlbear_kanban.dispatch: 30%
- owlbear_kanban.models: 98%

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C13 | serve/kanban/src/owlbear_kanban/storage.py:383-399 writes canonical fields first; serve/kanban/tests/test_storage_1050.py frontmatter tests stayed green in the quality-runner run | PASS |
| AC-C14 | serve/kanban/src/owlbear_kanban/models.py:99-121 keeps Task extra=allow; vendor round-trip tests in serve/kanban/tests/test_storage_1050.py stayed green | PASS |
| AC-C15 | serve/kanban/src/owlbear_kanban/storage.py:267-279 and 390-399 normalize timestamp-like strings to UTC +00:00; timestamp tests in serve/kanban/tests/test_storage_1050.py stayed green | PASS |
| AC-C16 | claimed_by corruption detection remains covered by serve/kanban/tests/test_storage_1050.py and served by corruption.py logic; no failing evidence in scoped run | PASS |
| AC-C28 | serve/kanban/src/owlbear_kanban/storage.py:522 creates quarantine dir; quarantine happy-path tests stayed green | PASS |
| AC-C29 | serve/kanban/src/owlbear_kanban/storage.py:523-526 moves to quarantine/{original-filename}; quarantine placement tests stayed green | PASS |
| AC-C30 | repair_storage AR creation remains covered by serve/kanban/tests/test_storage_1050.py and serve/kanban/tests/test_engine_storage.py; no failing evidence in scoped run | PASS |
| AC-C48 | archive claimed_by stripping at serve/kanban/src/owlbear_kanban/storage.py:347-350 remains green in task-scoped storage tests | PASS |
| Public surface: read_task, write_task, list_task_files, list_archive_files, move_to_quarantine | serve/kanban/src/owlbear_kanban/storage.py:557-585 exports the required names; implementation present | PASS |
| task_io.py removed; all imports redirected to storage | FAIL: serve/kanban/src/owlbear_kanban/task_io.py still exists on disk and imports cleanly, which is exactly what serve/kanban/tests/test_storage_1059.py:45-57 is supposed to reject. Import redirection itself looks correct at serve/kanban/src/owlbear_kanban/engine.py:49, serve/kanban/src/owlbear_kanban/dispatch.py:20, and serve/kanban/src/owlbear_kanban/corruption.py:324 and 389, but the deletion clause is still violated. | FAIL |
| All RED tests from C-05 (#1050) pass | quality-runner failures were confined to serve/kanban/tests/test_storage_1059.py; no C-05 test failures were reported | PASS |

#### Security Review
- No security defect found in the current containment implementation. serve/kanban/src/owlbear_kanban/storage.py:117-133 validates path containment, and serve/kanban/src/owlbear_kanban/storage.py:514-529 only renames into quarantine using task_path.name.

#### Test Integrity
- No builder-authored weakening detected in the task-scoped TestFromAC suites in serve/kanban/tests/test_storage_1050.py and serve/kanban/tests/test_storage_1059.py.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | serve/kanban/tests/test_storage.py:236-258 enters pytest.raises(MigrationRequiredError) and then raises MigrationRequiredError itself instead of asserting KanbanEngine behavior, so it is not contract proof for AC-C48. |
| Negative and error-path coverage | WEAK | The new containment-rejection path in serve/kanban/src/owlbear_kanban/storage.py:514-529 has no direct negative-path proof. Reviewed tests cover only happy-path quarantine placement and lock-file no-op behavior in serve/kanban/tests/test_storage_1050.py:411-476, serve/kanban/tests/test_storage.py:267-337, and serve/kanban/tests/test_storage_io_1055.py:184-242. |
| Manual mutation reasoning | WEAK | A regression that kept imports redirected but left the legacy module on disk survives until the dedicated removal tests run; that is exactly the current failure in serve/kanban/tests/test_storage_1059.py. |
| Test independence | ADEQUATE | tmp_path board fixtures isolate cases. |
| Descriptive names | STRONG | AC-scoped test names remain clear and specific. |

#### Data Safety
- No current data-safety defect found in the containment fix itself.

#### Implementation-Aware Gaps
- No direct proof exists for the documented PermissionError / outside-board rejection path added to move_to_quarantine at serve/kanban/src/owlbear_kanban/storage.py:514-529.
- The durable AC-C48 test at serve/kanban/tests/test_storage.py:236-258 is still a self-raised exception test and therefore not valid evidence.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Assessment | FRICTION |
| Rationale | The approaches varied across cycles, but this task is now on its 3rd review-failure path. Reviewer protocol routes any 3rd+ FAIL to backlog as a loop-breaker. |

### Deductions
- 0.35: independent quality-runner run still fails two task-owned structural tests.
- 0.12: the stale serve/kanban/src/owlbear_kanban/task_io.py module violates an explicit acceptance criterion.
- 0.07: the new move_to_quarantine containment guard still lacks a direct negative-path proof test.
- 0.03: serve/kanban/tests/test_storage.py:236-258 remains a non-proof AC-C48 test.

### Confidence: 0.38
### Verdict: FAIL
### Action
- Reject to backlog per reviewer loop-breaker rule for a 3rd review failure.
- Delete the stale serve/kanban/src/owlbear_kanban/task_io.py module so the task-owned removal suite can pass.
- Add a direct negative-path proof for move_to_quarantine rejecting out-of-board input.
- Replace the self-raised MigrationRequiredError pseudo-test in serve/kanban/tests/test_storage.py with a real behavior assertion.
- Re-run the task-owned storage suites, especially serve/kanban/tests/test_storage_1059.py.

### Reflection
- Builder-scoped reruns can miss task-owned structural failures when the latest cycle focuses only on the newest fix.
- A migration AC can be half-green: imports redirected correctly while the deleted module still exists and keeps the contract red.
- For path-containment fixes, happy-path quarantine tests are not enough; the rejection branch needs a direct proof test.
[[2026-04-23]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: compose storage surface, remove legacy task_io module |
| Interface clarity | PASS | Public surface explicit in AC and `__all__`: read_task, write_task, list_task_files, list_archive_files, move_to_quarantine |
| Dependency correctness | PASS | All deps (#1050, #1055, #1056, #1057) archived/done |
| Module layering | PASS | storage.py composes storage_io, body_parser, corruption — no upward imports. engine/dispatch import from storage (correct direction) |
| TDD compliance | PASS | RED tests in test_storage_1050.py and test_storage_1059.py exist; task tagged tdd:green |
| KISS/YAGNI | PASS | Minimal surface: re-exports + write/read/move helpers. No speculative features |
| Premise challenge | PASS | task_io → storage consolidation is necessary for Brief C boundary enforcement |
| Pattern consistency | PASS | Follows atomic_write, validate_path_containment, YAML12SafeLoader patterns established in storage_io/corruption |
| Security surface | PASS | validate_path_containment guards both write_task and move_to_quarantine against path traversal |
| Single domain | PASS | kanban storage domain only |

### Challenge Results
- Challenger: block (confidence 0.24)
- Architect response: REBUTTED — challenger conflated "builder hasn't done the work" with "AC has an open gap". The AC is precise (11 verifiable items). Each of the 3 prior review failures had a different cause (claim regression, containment miss, file not deleted), not a structural AC defect. The broader storage-boundary adoption (engine using list_task_files) is out of scope for this task's AC and belongs to other Brief C tasks.

### Loop-breaker context
This task returns from 3rd review failure via loop-breaker protocol. Failure pattern was sequential builder execution gaps, not architecture issues:
- Cycle 1: claim-state regression (fixed)
- Cycle 2: move_to_quarantine containment guard missing (fixed)
- Cycle 3: task_io.py not deleted from disk despite being unreferenced

Primary remaining builder action: delete serve/kanban/src/owlbear_kanban/task_io.py. All source imports are already redirected — no source file references task_io. The 2 failing tests (test_task_io_py_does_not_exist_on_disk, test_importing_task_io_raises_module_not_found) will pass once the file is removed.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable. Architecture sound. Loop-breaker notes added for builder context.
[[2026-04-23]]
## Test-Writer Notes

**Retry cycle** — reviewer flagged two gaps after 3rd review failure:
1. No direct negative-path proof for `move_to_quarantine` rejecting out-of-board paths.
2. `test_storage.py:236-258` was a self-raised `MigrationRequiredError` pseudo-test — not contract proof for AC-C48.

### Changes made

**`serve/kanban/tests/test_storage_1059.py`** — added `TestFromAC_QuarantineContainment` (3 tests):
- `test_move_to_quarantine_rejects_path_outside_kanban_dir` — PermissionError when path outside kanban_dir
- `test_move_to_quarantine_rejects_sibling_directory_path` — PermissionError when path in sibling dir
- `test_move_to_quarantine_does_not_create_quarantine_dir_on_rejection` — quarantine/ not created on rejection

**`serve/kanban/tests/test_storage.py`** — replaced pseudo-test with real behavior assertion:
- `test_ac_c48_archive_with_claimed_by_no_migration_required_error` now instantiates `KanbanEngine(kanban_dir)` and asserts it succeeds — proves the migration gate does not fire when `claimed_by` is only in `archive/`.
- Removed unused `import pytest`.

### Test results
- `test_storage_1059.py`: 11 passed, 2 failed (pre-existing: `test_task_io_py_does_not_exist_on_disk`, `test_importing_task_io_raises_module_not_found` — both fail because `task_io.py` still on disk; builder must delete it)
- `test_storage.py`: 11 passed, 0 failed
- Ruff: clean on both files

### AC coverage (additions)
| Gap | Tests added | Proves |
|-----|-------------|--------|
| `move_to_quarantine` out-of-board rejection | 3 | Containment guard raises PermissionError before any FS mutation |
| AC-C48 KanbanEngine no MigrationRequiredError | 1 (replacement) | Engine init succeeds when claimed_by only in archive/ |
[[2026-04-23]]
## Builder Notes
- Implementation: deleted legacy module `serve/kanban/src/owlbear_kanban/task_io.py` to satisfy AC clause "task_io.py removed" and enforce `ModuleNotFoundError` on import.
- Files changed: `serve/kanban/src/owlbear_kanban/task_io.py` (deleted).
- Commit: `e9abb758` (`feat: remove legacy task_io module (#1059, builder)`).
- RED verification (quality-runner, pre-change): `serve/kanban/tests/test_storage_1059.py` -> 11 passed, 2 failed (`task_io.py` still present; import did not raise).
- GREEN verification (quality-runner, scoped):
  - Tests: `serve/kanban/tests/test_storage_1059.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_io_1055.py`
  - Result: **88 passed, 0 failed**.
- Coverage: `owlbear_kanban.storage` **93%** (scoped run).
- Ruff: clean on scoped lint paths (`storage.py`, `storage_io.py`, `migrate.py`, `test_storage_1059.py`).
- Evidence summary: structural removal tests now pass because the module no longer exists on disk and importing `owlbear_kanban.task_io` raises module-not-found as expected.

- Post-task reflection:
- Problem faced: `apply_patch` delete reported success twice while file remained present on disk.
- Workaround applied: validated actual filesystem/git state and used direct `rm` deletion, then re-verified with quality-runner.
- Pattern discovered: for structural deletion ACs, always confirm both `git status` and directory listing before GREEN run.
- Quality gap observed: none blocking in this cycle; prior containment/AC-C48 proof gaps were already covered by existing test-writer updates.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage_1059.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_io_1055.py`, `serve/kanban/tests/test_engine_storage.py`, and `serve/kanban/tests/test_engine_activity.py`: **154 passed, 0 failed, 0 skipped**.
- Additional broadened claim-flow check on `serve/kanban/tests/test_engine_atomicity_1104.py` and `serve/kanban/tests/test_list_sessions_952.py`: **30 passed, 2 failed**. Failures were `test_integration_end_work_success_classifies_as_completed_pass` and `test_integration_end_work_reject_classifies_as_completed_rejected`; these are adjacent engine debt, not the primary 1059 gate.
- `get_errors` on touched source and reviewed test files: no diagnostics.

### Lint
- Ruff clean for `serve/kanban/src/owlbear_kanban/storage.py`, `engine.py`, `dispatch.py`, `corruption.py`, `models.py`, and the reviewed storage/engine test files.

### Coverage
- overall: **56%**
- `owlbear_kanban.storage`: **93%**
- `owlbear_kanban.engine`: **69%**
- `owlbear_kanban.dispatch`: **30%**
- `owlbear_kanban.models`: **98%**

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC-C13 | `serve/kanban/tests/test_storage_1050.py:192-228` | Yes | COVERED |
| AC-C14 | `serve/kanban/tests/test_storage_1050.py:234-249` | Yes | COVERED |
| AC-C15 | `serve/kanban/tests/test_storage_1050.py:271-314`, `serve/kanban/tests/test_storage.py:168-184` | Yes | COVERED |
| AC-C16 | `serve/kanban/tests/test_storage_1050.py:357-392` | Yes | COVERED |
| AC-C28 | `serve/kanban/tests/test_storage_1050.py:414-431` | Yes | COVERED |
| AC-C29 | `serve/kanban/tests/test_storage_1050.py:433-472` | Yes | COVERED |
| AC-C30 | `serve/kanban/tests/test_storage_1050.py:483-544` | Yes | COVERED |
| AC-C48 | `serve/kanban/tests/test_storage_1050.py:555-618`, `serve/kanban/tests/test_storage.py:236-258` | Yes | COVERED |
| Public surface (`read_task`, `write_task`, `list_task_files`, `list_archive_files`, `move_to_quarantine`) | `serve/kanban/tests/test_storage_1050.py:871-924`, plus exported functions at `serve/kanban/src/owlbear_kanban/storage.py:288`, `:354`, `:456`, `:471`, `:514`, `:557-585` | Yes | COVERED |
| `task_io.py` removed; imports redirected to storage | `serve/kanban/tests/test_storage_1059.py:42-213`, `serve/kanban/src/owlbear_kanban/engine.py:49-52`, `serve/kanban/src/owlbear_kanban/dispatch.py:20`, `serve/kanban/src/owlbear_kanban/corruption.py:324`; file search found no `serve/kanban/src/owlbear_kanban/task_io.py` | Yes | COVERED |
| All RED tests from C-05 (#1050) pass | quality-runner scoped run reported **154 passed, 0 failed** including `test_storage_1050.py` and `test_storage_1059.py` | Yes | COVERED |

#### Security Review
- No live security defect found in the reviewed storage surface. `move_to_quarantine()` validates containment before mutation at `serve/kanban/src/owlbear_kanban/storage.py:526`, and YAML loading remains on safe loaders in `serve/kanban/src/owlbear_kanban/storage.py:160` and `serve/kanban/src/owlbear_kanban/corruption.py:213`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-scoped `TestFromAC_*` suites in `serve/kanban/tests/test_storage_1050.py` and `serve/kanban/tests/test_storage_1059.py` | No weakened or removed assertions detected in the live files | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Task-owned AC proofs still assert exact order/detail/path values in `serve/kanban/tests/test_storage_1050.py:192-314`, `:368-377`, `:523-544` and `serve/kanban/tests/test_storage_1059.py:45-213`. |
| Negative and error-path coverage | WEAK | No runtime test executes `pick_dispatchable()` claim exclusion after the task changed `serve/kanban/src/owlbear_kanban/dispatch.py:75-85` and `:175-183`; no test proves `claim_task()` raises on blocked or already-claimed tasks at `serve/kanban/src/owlbear_kanban/engine.py:913-924`. |
| Manual mutation reasoning | WEAK | Dispatch could stop excluding active claims, or `claim_task()` could stop rejecting rival claims, and all task-owned suites would still pass because current 1059 coverage is structural/positive-path only (`serve/kanban/tests/test_storage_1059.py:131-145`, `serve/kanban/tests/test_storage_1050.py:1027-1069`). |
| Test independence | STRONG | `tmp_path` board fixtures isolate filesystem state across the reviewed suites. |
| Descriptive names | STRONG | Task-owned test names remain AC- and regression-specific. |

#### Data Safety
- No current implementation defect found in the live storage surface.

#### Implementation-Aware Gaps
- Global search found **no runtime test reference to `pick_dispatchable(` anywhere under `serve/kanban/tests/`**. The only 1059 dispatch proof is structural redirect checking in `serve/kanban/tests/test_storage_1059.py:131-145`, while the touched runtime gate lives in `serve/kanban/src/owlbear_kanban/dispatch.py:75-85` and `:175-183`.
- Search across `serve/kanban/tests/` found positive claim visibility proofs at `serve/kanban/tests/test_storage_1050.py:1027-1069` and rollback proofs at `serve/kanban/tests/test_engine_atomicity_1104.py:213-224` and `:407-419`, but **no direct proof** for the blocked/already-claimed rejection branches in `serve/kanban/src/owlbear_kanban/engine.py:913-924`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- `task_io.py` is truly gone from the package, and the storage redirect contract is now satisfied.
- The broadened adjacent engine run found two non-1059 failures in `serve/kanban/tests/test_list_sessions_952.py` around `completed-pass` / `completed-rejected` classification. These are not the primary gate for this task, but they reduce confidence in nearby engine behavior.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | canonical write order at `serve/kanban/src/owlbear_kanban/storage.py:384-399`; exact order asserted at `serve/kanban/tests/test_storage_1050.py:192-228` | `TestFromAC_Frontmatter` | PASS |
| AC-C14 | `Task` keeps `extra="allow"` at `serve/kanban/src/owlbear_kanban/models.py:121`; round-trip proved at `serve/kanban/tests/test_storage_1050.py:234-249` | vendor-extra tests | PASS |
| AC-C15 | timestamp normalization at `serve/kanban/src/owlbear_kanban/storage.py:267-279` and `:390-399`; timestamp tests stayed green at `serve/kanban/tests/test_storage_1050.py:271-314` and `serve/kanban/tests/test_storage.py:168-184` | timestamp tests | PASS |
| AC-C16 | corruption rule at `serve/kanban/src/owlbear_kanban/corruption.py:229-236`; exact detail asserted at `serve/kanban/tests/test_storage_1050.py:357-377` | corruption tests | PASS |
| AC-C28 | quarantine dir creation at `serve/kanban/src/owlbear_kanban/storage.py:528`; tests at `serve/kanban/tests/test_storage_1050.py:414-431` stayed green | quarantine dir tests | PASS |
| AC-C29 | quarantine path semantics at `serve/kanban/src/owlbear_kanban/storage.py:529-531`; tests at `serve/kanban/tests/test_storage_1050.py:433-472` stayed green | quarantine path tests | PASS |
| AC-C30 | repair/quarantine AR behavior proved by `serve/kanban/tests/test_storage_1050.py:483-544`; repair path in `serve/kanban/src/owlbear_kanban/corruption.py:324-334` | quarantine repair tests | PASS |
| AC-C48 | archive claimed_by stripping at `serve/kanban/src/owlbear_kanban/storage.py:347-350`; engine-init no-migration proof at `serve/kanban/tests/test_storage_1050.py:555-618` and `serve/kanban/tests/test_storage.py:236-258` | archive exemption tests | PASS |
| Public surface | public entry points exist at `serve/kanban/src/owlbear_kanban/storage.py:288`, `:354`, `:456`, `:471`, `:514`, `:557-585`; file-list behavior proved at `serve/kanban/tests/test_storage_1050.py:871-924` | storage surface tests | PASS |
| `task_io.py` removed; imports redirected to `storage` | `serve/kanban/tests/test_storage_1059.py:42-213` stayed green; imports now point at storage in `serve/kanban/src/owlbear_kanban/engine.py:49-52`, `dispatch.py:20`, `corruption.py:324` | structural redirect tests | PASS |
| All RED tests from C-05 pass | quality-runner scoped run reported **154 passed, 0 failed** including the full `serve/kanban/tests/test_storage_1050.py` suite | task-owned RED suite | PASS |

### Deductions
- **0.12**: touched `dispatch.py` runtime path has no behavioral tests anywhere in the kanban test suite.
- **0.10**: touched `engine.claim_task()` rejection branches remain unproved.
- **0.03**: broadened adjacent engine run surfaced non-1059 failures, reducing confidence in nearby engine behavior.

### Confidence: 0.75
### Verdict: FAIL
### Action
- Reject to `backlog` per the reviewer 3rd+-failure loop-breaker rule.
- Add direct runtime tests for `pick_dispatchable()` claimed-task exclusion and for `claim_task()` blocked/already-claimed rejection branches before re-reviewing #1059.

### Reflection
- Scoped storage suites can pass while a touched adjacent module (`dispatch.py`) has zero runtime proof.
- Structural redirect tests are not substitutes for behavioral tests when the redirected consumer also changed runtime logic.
- A broadened second pass is useful for separating background engine debt from task-owned evidence.
[[2026-04-23]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: compose storage surface, remove legacy task_io module |
| Interface clarity | PASS | Public surface explicit in AC and `__all__`: read_task, write_task, list_task_files, list_archive_files, move_to_quarantine |
| Dependency correctness | PASS | All deps (#1050, #1055, #1056, #1057) archived/done |
| Module layering | PASS | storage.py composes storage_io, body_parser, corruption — no upward imports. engine/dispatch import from storage (correct direction) |
| TDD compliance | PASS | RED tests in test_storage_1050.py and test_storage_1059.py exist; task tagged tdd:green |
| KISS/YAGNI | PASS | Minimal surface: re-exports + write/read/move helpers. No speculative features |
| Premise challenge | PASS | task_io → storage consolidation is necessary for Brief C boundary enforcement |
| Pattern consistency | PASS | Follows atomic_write, validate_path_containment, YAML12SafeLoader patterns from storage_io/corruption |
| Security surface | PASS | validate_path_containment guards both write_task and move_to_quarantine against path traversal |
| Single domain | PASS | kanban storage domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.61)
- Concerns: (1) dispatch/engine behavioral changes are non-mechanical per research #1097; (2) no runtime tests for pick_dispatchable claim exclusion or claim_task rejection; (3) follow-up ownership gap
- Architect response: REBUTTED with evidence —

**Rebuttal:**
1. **Claim model transition ownership is explicit.** #1062 (C-17) depends on #1059 and owns AC-C23, AC-C27, AC-C47, AC-C52 — all claim-related behavioral criteria. Research doc #1097 itself concludes "the full scope is distributed across C-14 → C-17 → C-18 → C-19" (§3.2). The claim behavioral adaptations in #1059 are bridge code to prevent regression; the formal behavioral testing lives in #1062.
2. **Dispatch behavioral testing is covered by Brief B.** #1074 (B-13) and #1076 (B-14) explicitly cover dispatch filter/sort/claim-exclusion via new pick_tasks API. The existing pick_dispatchable had zero tests before #1059.
3. **All 11 AC items PASS per the 4th reviewer's own compliance table.** The confidence deductions (0.12 + 0.10 + 0.03) are entirely about adjacent module test coverage for touched-but-not-AC-specified code, not AC violations.
4. **Blocking #1059 blocks the chain.** #1062 (C-17) and #1065 (B-01) both depend on #1059. Holding it hostage to pre-existing dispatch test debt stalls two dependency chains.
5. **The research doc's "non-mechanical" warning is about risk, not prohibition.** Research #1097 §3.3 establishes the ordering C-14 → C-17 → C-18 that manages that risk. #1059 is correctly positioned as the first step.

### Loop-breaker context
4th return from review. Failure pattern was sequential builder execution gaps across 4 cycles, not architecture defects:
- Cycle 1: claim-state regression (fixed)
- Cycle 2: move_to_quarantine containment guard missing (fixed)
- Cycle 3: task_io.py not deleted from disk (fixed)
- Cycle 4: reviewer requested dispatch/claim behavioral tests not in AC scope

Primary remaining builder action from test-writer retry: 2 failing structural tests (task_io existence) now pass per builder cycle 4 evidence; 3 new quarantine containment tests added by test-writer. The file is confirmed deleted via file_search.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable — all 11 items pass. Architecture sound. Challenger rebutted with dependency-chain ownership evidence. Claim model behavioral testing explicitly owned by downstream #1062 (C-17).
[[2026-04-23]]
## Test-Writer Notes

**Retry cycle** — architect's most recent review (4th cycle, loop-breaker) explicitly resolved the scope dispute:
- All 11 AC items PASS per architecture review AC compliance table.
- Reviewer's dispatch/claim behavioral concerns (deductions 0.12 + 0.10) ruled **out of scope** for #1059 — owned by #1062 (C-17) and Brief B tasks #1074/#1076.
- Quarantine containment tests (`TestFromAC_QuarantineContainment`, 3 tests) and AC-C48 proof fix added in previous test-writer retry remain intact.

**Current state (verified):**
- `serve/kanban/tests/test_storage_1059.py`: **13 passed, 0 failed**
- Ruff: **clean**

No new tests added — no AC gap exists. Passing through per Step 1b rule 3 (reviewer cited implementation-adjacent coverage, not AC violations; architect approved).
[[2026-04-23]]
## Builder Notes
- Implementation: no code edits required in this cycle; task implementation was already present in workspace state (`task_io.py` absent and imports redirected to `storage`).
- Files changed: none.
- Tests (quality-runner, scoped): `serve/kanban/tests/test_storage_1059.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_io_1055.py` -> **88 passed, 0 failed, 0 skipped**.
- Coverage: `owlbear_kanban.storage` **93%** (scoped run overall 41%).
- Ruff: clean on touched storage source paths and scoped test paths.
- Evidence summary: AC-owned storage/public-surface and structural-removal suites are green; no residual `task_io` imports detected in package sources.

- Post-task reflection:
- Problem faced: task had long multi-cycle history with prior conflicting reviewer signals.
- Workaround applied: re-ran a strict scoped quality-runner pass against AC-owned suites only to establish current-cycle evidence.
- Pattern discovered: for structural deletion ACs, filesystem checks (`task_io` absent) plus scoped TestFromAC reruns prevent stale-state ambiguity.
- Time sink: reconciling historical review notes versus current AC scope required additional pre-flight validation.
- Quality gap: none blocking for this task’s AC in the current cycle.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage_1059.py`, `serve/kanban/tests/test_storage.py`, and `serve/kanban/tests/test_storage_io_1055.py`: 88 passed, 0 failed, 0 skipped.
- `get_errors` on `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/dispatch.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/models.py`, and the reviewed storage test files: no diagnostics.

### Lint
- Ruff clean on the reviewed storage source files and scoped test files.

### Coverage
- overall: 41%
- `owlbear_kanban.storage`: 93%
- `owlbear_kanban.models`: 96%

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC-C13 | `test_storage_1050.py:192-228`, `test_storage.py:89-113` | Yes | COVERED |
| AC-C14 | `test_storage_1050.py:234-249`, `test_storage.py:116-151` | Yes | COVERED |
| AC-C15 | canonical-field tests at `test_storage_1050.py:271-345` and `test_storage.py:153-184`; helper tests at `test_storage_1050.py:941-956` | No for the vendor-extra write path in `serve/kanban/src/owlbear_kanban/storage.py:397-399`; no test writes a vendor extra timestamp through `write_task()` and asserts on-disk normalization | LAX |
| AC-C16 | `test_storage_1050.py:357-392`, `test_storage.py:197-228` | Yes | COVERED |
| AC-C28 | `test_storage_1050.py:414-431`, `test_storage.py:262-276`, `test_storage_1059.py:175-213` | Yes | COVERED |
| AC-C29 | `test_storage_1050.py:433-472`, `test_storage.py:279-293` | Yes | COVERED |
| AC-C30 | `test_storage_1050.py:483-544`, `test_storage.py:295-330` | Yes | COVERED |
| AC-C48 | `test_storage_1050.py:555-618`, `test_storage.py:214-251` | Yes | COVERED |
| Public surface | direct imports/calls in `test_storage_1050.py:871-924`, `test_storage_io_1055.py:87-175`, exports in `serve/kanban/src/owlbear_kanban/storage.py:557-585` | Yes for callable availability | COVERED |
| `task_io.py` removed; imports redirected | `test_storage_1059.py:45-162`; no `serve/kanban/src/owlbear_kanban/task_io.py` file on disk; imports come from storage in `engine.py:49-52`, `dispatch.py:20`, `corruption.py:324` | Yes | COVERED |
| All RED tests from C-05 pass | quality-runner scoped run: 88 passed, 0 failed including `serve/kanban/tests/test_storage_1050.py` | Yes | COVERED |

#### Security Review
- No issues found. `move_to_quarantine()` validates containment before mutation at `serve/kanban/src/owlbear_kanban/storage.py:526-531`, and rejection is directly tested in `serve/kanban/tests/test_storage_1059.py:175-213`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-scoped `TestFromAC_*` suites in `serve/kanban/tests/test_storage_1050.py` and `serve/kanban/tests/test_storage_1059.py` | No weakened or removed assertions found in current files | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | exact order/detail/path assertions remain in `test_storage_1050.py:192-345`, `test_storage_1050.py:523-544`, `test_storage_1059.py:45-213` |
| Negative and error-path coverage | STRONG | corruption, archive exemption, and out-of-board quarantine rejection are exercised in `test_storage_1050.py:357-392`, `test_storage_1050.py:555-618`, `test_storage_1059.py:175-213` |
| Manual mutation reasoning | WEAK | removing the vendor-extra normalization call in `serve/kanban/src/owlbear_kanban/storage.py:397-399` would leave the current suites green because only canonical fields and the helper function are asserted |
| Test independence | STRONG | `tmp_path` boards isolate the reviewed suites |
| Descriptive names | STRONG | AC-scoped names remain specific |

#### Data Safety
- No implementation defect found in the live storage surface.

#### Implementation-Aware Gaps
- FAIL: `serve/kanban/src/owlbear_kanban/storage.py:397-399` normalizes vendor extra string values during `write_task()`, but no test proves that branch through the public API.
- `serve/kanban/tests/test_storage_1050.py:243-249` round-trips vendor extras without asserting timestamp normalization, and `serve/kanban/tests/test_storage.py:119-151` only reads vendor extras from disk.
- Helper coverage at `serve/kanban/tests/test_storage_1050.py:941-956` proves `_normalize_timestamp()` in isolation, not that `write_task()` applies it to vendor extras.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 5 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- `task_io.py` is gone from the package and the import-redirect contract now holds.
- The explicit public-surface bullet is adequately proven for callable availability, although the boundary proof still relies partly on direct imports and builder-discovered tests rather than a dedicated API-boundary assertion.
- This rejection is not the earlier dispatch/claim-scope objection; it is a remaining AC-C15 proof gap inside the storage write path itself.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C13 | canonical write order at `serve/kanban/src/owlbear_kanban/storage.py:384-399` | `test_storage_1050.py:192-228`, `test_storage.py:89-113` | PASS |
| AC-C14 | `Task` extra allow at `serve/kanban/src/owlbear_kanban/models.py:121` | `test_storage_1050.py:234-249`, `test_storage.py:116-151` | PASS |
| AC-C15 | vendor extra normalization path exists at `serve/kanban/src/owlbear_kanban/storage.py:397-399` but is not directly asserted through `write_task()` | canonical timestamp tests plus helper-only normalization tests | FAIL |
| AC-C16 | claimed_by corruption rule at `serve/kanban/src/owlbear_kanban/corruption.py:231-236` | `test_storage_1050.py:357-392`, `test_storage.py:197-228` | PASS |
| AC-C28 | quarantine directory creation at `serve/kanban/src/owlbear_kanban/storage.py:529` | `test_storage_1050.py:414-431`, `test_storage.py:262-276` | PASS |
| AC-C29 | quarantine path semantics at `serve/kanban/src/owlbear_kanban/storage.py:530-531` | `test_storage_1050.py:433-472`, `test_storage.py:279-293` | PASS |
| AC-C30 | AR task payload at `serve/kanban/src/owlbear_kanban/engine.py:1202-1213` | `test_storage_1050.py:483-544`, `test_storage.py:295-330` | PASS |
| AC-C48 | archive strip/read path at `serve/kanban/src/owlbear_kanban/storage.py:334-350` | `test_storage_1050.py:555-618`, `test_storage.py:214-251` | PASS |
| Public surface | exports at `serve/kanban/src/owlbear_kanban/storage.py:557-585`; file-list behavior in `test_storage_1050.py:871-924` and `test_storage_io_1055.py:87-175` | storage public-surface tests | PASS |
| `task_io.py` removed; imports redirected | no `task_io.py` file on disk; redirects at `serve/kanban/src/owlbear_kanban/engine.py:49-52`, `serve/kanban/src/owlbear_kanban/dispatch.py:20`, `serve/kanban/src/owlbear_kanban/corruption.py:324` | `test_storage_1059.py:45-162` | PASS |
| All RED tests from C-05 pass | quality-runner scoped run reported 88 passed, 0 failed | `serve/kanban/tests/test_storage_1050.py` | PASS |

### Deductions
- 0.12: AC-C15 still lacks end-to-end proof for the vendor-extra timestamp normalization branch in `write_task()`.

### Confidence: 0.88
### Verdict: FAIL
### Action
- Reject to `backlog` per the reviewer 3rd-plus-failure loop-breaker rule.
- Add a direct write-side test that passes a vendor extra timestamp through `write_task()` and asserts UTC `+00:00` normalization on disk. A helper-only `_normalize_timestamp()` assertion is not sufficient for this AC.

### Reflection
- Latest architecture refinements matter: the prior dispatch/claim-scope objection was stale, but the AC-C15 write-path gap remains current.
- Helper-function tests can hide a missing public-surface proof when the integration branch is a one-line call site.
- Scoped quality runs were clean; the blocker is proof quality on an AC-owned path, not a live implementation failure.
[[2026-04-23]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: compose storage surface, remove legacy task_io module |
| Interface clarity | PASS | Public surface explicit in AC and `__all__`: read_task, write_task, list_task_files, list_archive_files, move_to_quarantine |
| Dependency correctness | PASS | All deps (#1050, #1055, #1056, #1057) archived |
| Module layering | PASS | storage.py composes storage_io, body_parser, corruption — no upward imports. engine/dispatch import from storage (correct direction) |
| TDD compliance | PASS | RED tests in test_storage_1050.py and test_storage_1059.py exist; task tagged tdd:green |
| KISS/YAGNI | PASS | Minimal surface: re-exports + write/read/move helpers. No speculative features |
| Premise challenge | PASS | task_io → storage consolidation is necessary for Brief C boundary enforcement |
| Pattern consistency | PASS | Follows atomic_write, validate_path_containment, YAML12SafeLoader patterns from storage_io/corruption |
| Security surface | PASS | validate_path_containment guards both write_task (storage.py:379) and move_to_quarantine (storage.py:526) |
| Single domain | PASS | kanban storage domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Concerns: (1) latest reviewer FAIL at 0.88 not addressed; (2) AC-C15 vendor-extra test proof gap; (3) prior rebuttal addressed different concern
- Architect response: REBUTTED —
  1. AC-C15 says "All timestamps written" — universal quantifier already covers vendor extras. No AC ambiguity exists.
  2. The reviewer's deduction (0.12) is about missing test proof, not AC imprecision. The reviewer's explicit test instruction is now in the task body for the test-writer.
  3. The architect evaluates AC precision and architecture soundness, not test coverage verification. The AC is sufficient for the test-writer to derive the missing vendor-extra timestamp write-path test.
  4. Refining "All" to "All, including vendor extras" adds cycle cost without adding clarity.

### Loop-breaker context
6th cycle (3rd architecture review). Failure pattern was sequential execution gaps across 5 cycles, not architectural defects:
- Cycle 1: claim-state regression (fixed)
- Cycle 2: move_to_quarantine containment guard missing (fixed)
- Cycle 3: task_io.py not deleted from disk (fixed)
- Cycle 4: dispatch/claim behavioral tests (ruled out of scope — owned by #1062 C-17)
- Cycle 5: vendor-extra timestamp AC-C15 test proof gap (reviewer feedback now in body)

### Test-writer guidance
The reviewer's latest feedback explicitly requires: "Add a direct write-side test that passes a vendor extra timestamp through write_task() and asserts UTC +00:00 normalization on disk." AC-C15 "All timestamps written" already mandates this — the test-writer must derive coverage for the vendor-extra path in storage.py:397-399.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise (11 verifiable items, all universally quantified where needed). Architecture sound. Challenger rebutted — test proof gap is downstream test-writer scope with explicit reviewer guidance in body.
[[2026-04-23]]
## Test-Writer Notes

**Retry cycle** — architect's 6th-cycle review explicitly required a direct write-side proof for AC-C15 vendor-extra timestamp normalization through `write_task()`.

### Changes made

**`serve/kanban/tests/test_storage_1059.py`** — added board helper (`_CONFIG_YAML`, `_make_board`) and new class `TestFromAC_VendorExtraTimestamps` (3 tests):

- `test_vendor_extra_naive_timestamp_written_with_utc_offset` — naive timestamp vendor extra field → `+00:00` on disk via `write_task()` (exercises `storage.py:397-399`)
- `test_vendor_extra_z_suffix_timestamp_converted_to_plus_zero` — Z-suffix vendor extra → `+00:00` (Z replaced), not passed through raw
- `test_vendor_extra_non_timestamp_string_written_unchanged` — non-timestamp vendor extra value survives `write_task()` unmodified (boundary: confirms normalization is selective)

### AC coverage (addition)

| AC | Gap plugged | Tests |
|----|-------------|-------|
| AC-C15 vendor-extra write path | Direct end-to-end proof through `write_task()` public API | 3 |

### Test results

- **16 passed, 0 failed** (13 existing + 3 new)
- Ruff: **clean**

### Note on RED/GREEN state

All 3 new tests PASS. This task is tagged `tdd:green`; the implementation at `storage.py:397-399` was already correct from prior builder cycles. These are GREEN proof tests that close the AC-C15 evidence gap identified by the reviewer. The builder has no remaining work on this test file.
[[2026-04-23]]
## Builder Notes
- Implementation: no additional code edits were required in this cycle; existing storage-surface implementation remains valid.
- Files changed: none.
- Tests: 91 passed, 0 failed, 0 skipped (quality-runner scoped verification for task-owned storage suites).
- Coverage: overall 41%; `owlbear_kanban.storage` 93%, `owlbear_kanban.storage_io` 82%.
- Ruff: clean (0 violations).
- Evidence summary: task-owned AC suites and structural-removal checks are green, lint is clean, and storage module coverage remains above the 90% target for touched module.
- Post-task reflection:
  - Problem faced: task has long multi-cycle history with prior conflicting review signals.
  - Workaround applied: used a fresh quality-runner scoped verification in this cycle to confirm present-state evidence.
  - Pattern discovered: for structural deletion/public-surface tasks, strict task-owned suite reruns are the fastest way to resolve stale-state uncertainty.
[[2026-04-23]]
## Review Evidence

### Scope
- Reviewed the current live state after the latest Architecture Review refinement and latest Test-Writer cycle.
- Focused on the storage public surface, the task-owned storage suites, and the previously open AC-C15 vendor-extra timestamp proof gap.

### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_storage_1059.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/tests/test_storage.py`, and `serve/kanban/tests/test_storage_io_1055.py`: **91 passed, 0 failed, 0 skipped**.
- `get_errors` on reviewed source and test files: no diagnostics.

### Lint
- Ruff clean on `serve/kanban/src/owlbear_kanban/storage.py`, `models.py`, `engine.py`, `dispatch.py`, `corruption.py`, and the reviewed storage test files.

### Coverage
- overall: **41%**
- `owlbear_kanban.storage`: **93%**
- `owlbear_kanban.models`: **96%**

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C13 | canonical write order at `serve/kanban/src/owlbear_kanban/storage.py:384-399`; exact order asserted in `serve/kanban/tests/test_storage_1050.py:192-228` | PASS |
| AC-C14 | `Task` keeps `extra="allow"` in `serve/kanban/src/owlbear_kanban/models.py:121`; round-trip/vendor-extra assertions in `serve/kanban/tests/test_storage_1050.py:234-249` and `serve/kanban/tests/test_storage.py:116-151` | PASS |
| AC-C15 | canonical timestamp normalization in `serve/kanban/src/owlbear_kanban/storage.py:392-399`; canonical-field proofs in `serve/kanban/tests/test_storage_1050.py:271-345`; vendor-extra write-path proofs in `serve/kanban/tests/test_storage_1059.py:268-385` | PASS |
| AC-C16 | claimed_by corruption rule in `serve/kanban/src/owlbear_kanban/corruption.py:231-236`; exact detail asserted in `serve/kanban/tests/test_storage_1050.py:357-392` and `serve/kanban/tests/test_storage.py:197-228` | PASS |
| AC-C28 | quarantine directory creation in `serve/kanban/src/owlbear_kanban/storage.py:528-529`; creation/rejection proofs in `serve/kanban/tests/test_storage_1050.py:414-431`, `serve/kanban/tests/test_storage.py:262-276`, and `serve/kanban/tests/test_storage_1059.py:175-213` | PASS |
| AC-C29 | quarantine path semantics in `serve/kanban/src/owlbear_kanban/storage.py:529-531`; exact path assertions in `serve/kanban/tests/test_storage_1050.py:433-472` and `serve/kanban/tests/test_storage.py:279-293` | PASS |
| AC-C30 | quarantine AR behavior exercised through repair flow in `serve/kanban/tests/test_storage_1050.py:483-544` and `serve/kanban/tests/test_storage.py:295-330` | PASS |
| AC-C48 | archive claimed_by strip/read path in `serve/kanban/src/owlbear_kanban/storage.py:334-350`; direct read and engine-init proofs in `serve/kanban/tests/test_storage_1050.py:555-618` and `serve/kanban/tests/test_storage.py:214-251` | PASS |
| Public surface (`read_task`, `write_task`, `list_task_files`, `list_archive_files`, `move_to_quarantine`) | public entry points exported from `serve/kanban/src/owlbear_kanban/storage.py:557-585`; direct callable behavior covered in `serve/kanban/tests/test_storage_1050.py:871-924` and `serve/kanban/tests/test_storage_io_1055.py:87-242` | PASS |
| `task_io.py` removed; imports redirected to storage | no `serve/kanban/src/owlbear_kanban/task_io.py` file on disk; structural proofs in `serve/kanban/tests/test_storage_1059.py:45-162`; imports come from storage in `serve/kanban/src/owlbear_kanban/engine.py:49-53`, `serve/kanban/src/owlbear_kanban/dispatch.py:20`, and `serve/kanban/src/owlbear_kanban/corruption.py:324,389,589` | PASS |
| All RED tests from C-05 pass | quality-runner scoped run reported **91 passed, 0 failed** including `serve/kanban/tests/test_storage_1050.py` | PASS |

#### Security Review
- No live security defect found in the reviewed storage surface.
- `move_to_quarantine()` validates containment before mutation at `serve/kanban/src/owlbear_kanban/storage.py:526-531`, and the out-of-board rejection path is directly tested in `serve/kanban/tests/test_storage_1059.py:175-213`.
- No secret handling, shell execution, unsafe deserialization, or injection sink found in the scoped files.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-scoped `TestFromAC_*` suites in `serve/kanban/tests/test_storage_1050.py` and `serve/kanban/tests/test_storage_1059.py` | No weakened or removed assertions found in the live files; latest additions are additive AC proofs for containment rejection and vendor-extra timestamps | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | exact field order, exact corruption detail, exact quarantine path, exact on-disk timestamp values |
| Negative and error-path coverage | STRONG | import failure, corruption detection, archive exemption, and out-of-board quarantine rejection are directly asserted |
| Manual mutation reasoning | ADEQUATE | removing vendor-extra normalization from the `write_task()` extra-field branch, removing task_io deletion, or skipping containment validation would now fail the live task-owned suites |
| Test independence | STRONG | `tmp_path` boards isolate reviewed suites |
| Descriptive names | STRONG | AC-scoped and scenario-specific names throughout the reviewed suites |

#### Data Safety
- No implementation defect found in the live storage surface.
- Writes remain atomic and move operations remain single-step filesystem replacements in the reviewed code paths.

#### Implementation-Aware Gaps
- No significant in-scope gap found.
- The prior AC-C15 proof gap is closed: vendor extra strings now have direct end-to-end `write_task()` coverage in `serve/kanban/tests/test_storage_1059.py:268-385`, not just helper-only coverage.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 6 |
| Approach variation | Yes |
| Assessment | FRICTION |
| Rationale | Multi-cycle task history, but no live loop defect remains and the current state is green |

### Pass 2 - INFORMATIONAL
- `task_io.py` is absent from the package and the redirect contract now holds across storage, engine, dispatch, and corruption.
- The latest vendor-extra timestamp tests prove the public entry point itself by reading the serialized frontmatter on disk after `write_task()`.
- No current evidence justifies reopening earlier out-of-scope dispatch/claim objections for this task.

### Deductions
- **0.00**: no blocking deductions remain in the current live state.

### Confidence: 0.97
### Verdict: PASS
### Action
- Advance to `docs`.

### Reflection
- On looped tasks, the current review must anchor to the latest architecture refinement plus fresh live-file evidence, not stale failure notes.
- The last real gap here was proof quality, not implementation correctness; direct entry-point assertions closed it cleanly.
- Scoped quality-runner evidence was sufficient once the task-owned AC suites and latest proof additions were both included.
[[2026-04-23]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/kanban/README.md` checked — no `task_io` reference, `KanbanEngine` API surface and `pick_dispatchable` import accurate; no update needed |
| 2 | Module docstrings | Yes | Verified | `storage.py`, `engine.py`, `dispatch.py`, `corruption.py`, `models.py` all have accurate module-level docstrings; none reference deleted `task_io`; `task_io.py` deleted |
| 3 | External attribution | No | N/A | Internal import-boundary migration; no external patterns used |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` and `share/diagrams/mcp-topology.excalidraw` both have `describes: serve/kanban/src/**`; footers updated from `e2d8fb9e` → `9ca2b1b2` (2026-04-23) |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | Yes | N/A | `task_io.py` deleted; all IN-scope docs checked — no current-system references found in `serve/kanban/README.md`, root `README.md`, or other IN-scope docs; research doc references are historical artifacts (pre-deletion context), not current-system descriptions |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/storage.py` | IN (docstrings) | Verified accurate |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Verified accurate |
| `serve/kanban/src/owlbear_kanban/dispatch.py` | IN (docstrings) | Verified accurate |
| `serve/kanban/src/owlbear_kanban/corruption.py` | IN (docstrings) | Verified accurate |
| `serve/kanban/src/owlbear_kanban/models.py` | IN (docstrings) | Verified accurate |
| `serve/kanban/src/owlbear_kanban/task_io.py` | IN (deleted) | No orphaned IN-scope prose docs found |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated → `2026-04-23 (9ca2b1b2)` |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated → `2026-04-23 (9ca2b1b2)` |
| Test files | OUT | No action |

### Files Updated
- `share/diagrams/kanban.excalidraw`
- `share/diagrams/mcp-topology.excalidraw`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None
[[2026-04-23]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C13: canonical field order | storage.py:384-399 writes canonical first; test_storage_1050.py:192-228 asserts exact order | PASS |
| AC-C14: Task extra="allow" | models.py:121 ConfigDict(extra="allow"); test_storage_1050.py:234-249 round-trip proof | PASS |
| AC-C15: ISO-8601 UTC +00:00 | storage.py:267-279, :390-399 normalize; test_storage_1050.py:271-345 canonical + test_storage_1059.py:268-385 vendor extras | PASS |
| AC-C16: claimed_by → mode 3 corruption | corruption.py:229-236; test_storage_1050.py:357-392 exact detail assertion | PASS |
| AC-C28: quarantine/ created if absent | storage.py:528-529; test_storage_1050.py:414-431 | PASS |
| AC-C29: quarantine/{original-filename} | storage.py:529-531; test_storage_1050.py:433-472 exact path | PASS |
| AC-C30: AR tag + body | engine.py:1202-1213; test_storage_1050.py:483-544 | PASS |
| AC-C48: archive claimed_by stripped | storage.py:334-350; test_storage_1050.py:555-618, test_storage.py:214-251 | PASS |
| Public surface (5 functions) | storage.py:288,:354,:456,:471,:514 exports at :557-585; test_storage_1050.py:871-924 | PASS |
| task_io.py removed; imports redirected | file absent; engine.py:49-52, dispatch.py:20, corruption.py:324 import from storage; test_storage_1059.py:45-162 | PASS |
| All RED tests from C-05 pass | quality-runner full: 1409 passed including all test_storage_1050.py and test_storage_1059.py; 0 task-scope failures | PASS |

### Test Results
- pytest (full suite): 1409 passed, 119 failed, 4 skipped. All 119 failures outside task scope (mcp-models 51, yaml12-loader 24, sessions 18, cockpit 11, knowledge 5, other 10). Zero failures in task-owned storage suites.
- ruff: 5 W292 violations — all in unrelated test files (test_deny_non_doc_writes.py, test_ideation_overhaul_static.py, test_setup_init_hook_conflicts.py, test_setup_init_settings.py, test_write_guard_hooks.py). No violations in task-changed files.

### Architect Quality: 4/5
11 specific, verifiable AC items. Minor gap: AC-C15 universal quantifier "All timestamps" didn't explicitly mention vendor extras, causing multiple review cycles. Builder/reviewer filled the gap. No structural architect deficiency.

### Deduction Breakdown
- AC lines without evidence: 0 (all 11 PASS)
- Lint violations in scope: 0
- AC quality ≤ 3: N/A (score 4)
- Missing reviewer section: 0 (present, thorough, 0.97 PASS)
- Task-scope test failures: 0

### Confidence: 1.00
### Action: archive