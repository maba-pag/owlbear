---
id: 1368
title: 'P1-05: Test kanban corruption scanner encoding hardening'
status: archived
priority: medium
created: 2026-05-06T00:58:38.511616+00:00
updated: 2026-05-06T06:32:37.887704+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:kanban
- type:test
- backend
- corruption-scan
- encoding
parent: 1363
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write focused Python tests for non-UTF8 kanban task/archive files in the corruption scanner.

## Problem Evidence
- POST /api/tasks/scan returns 500 on real repo data because detect_corruption() reads UTF-8 and does not handle UnicodeDecodeError for archived files.
- Storage parsing handles encoding fallback more gracefully, so scanner behavior is inconsistent.
- Archived tasks with non-UTF8 bytes were observed under .owlbear/kanban/archive.

## Acceptance Criteria
- Tests write a binary fixture (non-UTF8 bytes) to a task-file path under a tmp board's `tasks/` and `archive/` dirs, then call `detect_corruption(path, config)` and prove it does not raise `UnicodeDecodeError`. (td:2)
- Tests assert `detect_corruption` returns a `CorruptionError` (not `None`, not raises) whose `.code` references encoding (e.g. `ERR_CORRUPT_ENCODING`), `.file_path` is set to the bad file, and `.detail` is a non-empty string describing the encoding failure. (td:2)
- A regression test calls `detect_corruption` on a valid UTF-8 task fixture and asserts it returns `None` (no corruption). (td:1)
- Test module imports `detect_corruption` from `owlbear_kanban.corruption` directly — not tested via Cockpit HTTP routes. (td:0)
- Running the test against the current unpatched code produces a failure (the `UnicodeDecodeError` propagates or assertion on return type fails), confirming RED phase validity for #1369. (td:1)

## Scope
- In scope: kanban corruption scanner tests and fixture coverage for encoding handling.
- Out of scope: Cockpit UI error rendering, route-level catch-all masking, and the cp1252 fallback approach (scanner reports encoding errors as findings, unlike storage which falls back).

## Architecture Notes
- Target module: `serve/kanban/src/owlbear_kanban/corruption.py`, function `detect_corruption()` at line ~222.
- Bug location: `path.read_text(encoding="utf-8")` catches `OSError` but not `UnicodeDecodeError`.
- Design choice: scanner reports encoding as a CorruptionError (its purpose is to find problems), rather than silently falling back like `storage.py` does with cp1252.
- New error code: #1369 will add `ERR_CORRUPT_ENCODING` via `_make_corruption_code_type()`. Tests should reference this code name.
- Test file location: `tests/test_corruption_1368.py` (task-scoped, follows existing `test_corruption_1057.py` pattern).
- Fixture pattern: use `path.write_bytes(b'\x80\x81...')` to create non-UTF8 content wrapped in valid-looking `---` delimiters so the encoding error triggers during `read_text`, not during delimiter parsing.

## Counterpart
Implementation task: #1369.

[[2026-05-06]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task, single focus: encoding handling in corruption scanner |
| Interface clarity | PASS | Refined AC specifies exact function, return type, error shape, and fixture strategy |
| Dependency correctness | PASS | No dependencies needed — test task with no prereqs |
| Module layering | PASS | Tests target engine layer directly (owlbear_kanban.corruption) |
| TDD compliance | PASS | This IS the test task; #1369 is the GREEN counterpart |
| KISS/YAGNI | PASS | Minimal scope — encoding error in one function |
| Premise challenge | PASS | Bug is real and observed (500 on production data) |
| Pattern consistency | PASS | Follows existing test_corruption.py fixture patterns (_make_board, _write) |
| Security surface | N/A | Test code only |
| Single domain | PASS | Kanban domain only |

### Design Decision
Scanner reports encoding issues as CorruptionError (new ERR_CORRUPT_ENCODING code) rather than silently falling back like storage.py. Rationale: scanner's purpose is to FIND problems; masking encoding errors defeats that purpose. Storage falls back because it needs to load data; scanner needs to report.

### Challenge Results
- Challenger: FALLBACK — agent returned no response
- Architect response: Proceeded with independent assessment; design is straightforward

### Test Depth
- Max depth: 2
- Test-writer: pass-through (type:test tag present)

### Verdict: APPROVE
### Action Taken: Refined AC from ambiguous dual-option behavior to specific error-reporting contract. Added Architecture Notes section with module location, bug line, fixture strategy, and new error code name. Advanced to todo.
[[2026-05-06]]
## Test-Writer Notes

**Test file:** `tests/test_corruption_1368.py`
**Class:** `TestFromAC_EncodingHardening`

### Test counts by category

| Category | Count |
|----------|-------|
| Happy path (valid UTF-8 → None) | 1 |
| Error path (non-UTF8 raises/returns) | 10 |
| **Total** | **11** |

All 11 tests FAIL (RED confirmed, ruff clean).

### Failure modes

| Tests | Failure type | Root cause |
|-------|-------------|-----------|
| 1–10 | `UnicodeDecodeError` | `detect_corruption()` catches `OSError` but not `UnicodeDecodeError` at line 222 of corruption.py |
| 11 | `ImportError` | `ERR_CORRUPT_ENCODING` not yet defined — added by #1369 |

### AC coverage

| AC line | td | Tests |
|---------|-----|-------|
| AC-1: non-UTF8 in tasks/ does not raise | td:2 | test_non_utf8_in_tasks_dir_does_not_raise_unicode_error, test_non_utf8_in_tasks_dir_returns_corruption_error |
| AC-2: tasks/ CorruptionError shape (.code, .file_path, .detail) | td:2 | test_non_utf8_in_tasks_dir_code_is_encoding, test_non_utf8_in_tasks_dir_file_path_is_set, test_non_utf8_in_tasks_dir_detail_is_non_empty |
| AC-1: non-UTF8 in archive/ does not raise | td:2 | test_non_utf8_in_archive_dir_does_not_raise_unicode_error, test_non_utf8_in_archive_dir_returns_corruption_error |
| AC-2: archive/ CorruptionError shape | td:2 | test_non_utf8_in_archive_dir_code_is_encoding, test_non_utf8_in_archive_dir_file_path_is_set, test_non_utf8_in_archive_dir_detail_is_non_empty |
| AC-3: valid UTF-8 returns None | td:1 | test_valid_utf8_task_returns_none (fails RED via ERR_CORRUPT_ENCODING ImportError) |
| AC-4: import from owlbear_kanban.corruption | td:0 | n/a (verified by module-level imports in test file) |
| AC-5: unpatched code produces failure | td:1 | confirmed — all 11 fail |

### Fixture strategy

Non-UTF8 bytes: `b"---\nid: 1001\ntitle: broken\n---\n\x80\x81\x82\x83 bad bytes"` — wrapped in valid-looking `---` delimiters; UnicodeDecodeError fires during `read_text()` before delimiter parsing. Tests cover both `tasks/` and `archive/` paths to exercise archive branch logic.

**Commit:** `test: corruption scanner encoding hardening RED (#1368, test-writer)`
[[2026-05-06]]
## Builder Notes
- Non-implementation task (`type:test`) with explicit counterpart implementation task `#1369`.
- No source-code edits applied by builder.
- Test-writer RED evidence is present and complete (11 failing `TestFromAC_EncodingHardening` tests) for downstream GREEN work in `#1369`.
- Routing: pass-through to review for process continuity on this test-only task.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped pytest on `tests/test_corruption_1368.py`: 11 failed, 0 passed.
- Failure alignment: 8 failures are propagated `UnicodeDecodeError` from `serve/kanban/src/owlbear_kanban/corruption.py:222`; 3 failures are `ImportError` for missing `ERR_CORRUPT_ENCODING` from `tests/test_corruption_1368.py:155`, `tests/test_corruption_1368.py:243`, and `tests/test_corruption_1368.py:296`.
- Snapshot verdict: STILL RED. This satisfies the RED-validity contract from task AC line 39 on the live snapshot.

### Lint Results
- quality-runner scoped ruff on `tests/test_corruption_1368.py`: clean.

### Coverage Data
- quality-runner reported 15% coverage for `owlbear_kanban.corruption`.
- Informational only for this RED-phase test task: the suite fails before the future encoding-handling branch is exercised, so this is not a blocking gate for task #1368.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC-1: non-UTF8 fixtures under `tasks/` and `archive/` prove no `UnicodeDecodeError` should escape (task line 35) | Tests exist at `tests/test_corruption_1368.py:111-126` and `tests/test_corruption_1368.py:202-215`; current scoped run fails with propagated `UnicodeDecodeError` at `serve/kanban/src/owlbear_kanban/corruption.py:222`, which is correct RED evidence against the live snapshot. | PASS |
| AC-2: returned `CorruptionError` must have encoding code, file_path, and `.detail` describing the encoding failure (task line 36) | Code and file_path assertions are discriminating at `tests/test_corruption_1368.py:164-165`, `tests/test_corruption_1368.py:181`, `tests/test_corruption_1368.py:252-253`, and `tests/test_corruption_1368.py:269`, but detail assertions only require `isinstance(result.detail, str)` and truthiness at `tests/test_corruption_1368.py:195-196` and `tests/test_corruption_1368.py:283-284`. A generic non-empty detail would still pass. | FAIL |
| AC-3: valid UTF-8 task returns `None` (task line 37) | `test_valid_utf8_task_returns_none` asserts exact `None` at `tests/test_corruption_1368.py:303-305`. | PASS |
| AC-4: direct import from `owlbear_kanban.corruption` (task line 38) | Module imports `detect_corruption` directly at `tests/test_corruption_1368.py:20`. | PASS |
| AC-5: live unpatched snapshot fails in RED phase (task line 39) | quality-runner confirmed 11 of 11 failures with the expected root causes: propagated `UnicodeDecodeError` and missing `ERR_CORRUPT_ENCODING`. | PASS |

### Deductions
- -0.10 AC-2 proof gap: detail-message assertions are lax and do not enforce an encoding-specific explanation.
- -0.04 dirty-tree contamination could not be checked from this tool surface; commit presence was confirmable, working-tree cleanliness was not.
- -0.02 TestFromAC immutability could not be proven from a direct diff in this session.

### Verdict
- FAIL
- Confidence: 0.84
- First review cycle confirmed: no prior `## Review Evidence` section exists in the live task file.
- Action: reject to `todo` for test-writer proof strengthening.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen the AC-2 detail assertions so they fail unless `CorruptionError.detail` explicitly references the encoding or decode failure, for both `tasks/` and `archive/` cases | `tests/test_corruption_1368.py` | Task AC line 36; current assertions at `tests/test_corruption_1368.py:195-196` and `tests/test_corruption_1368.py:283-284` accept any non-empty string |

[[2026-05-06]]
## Test-Writer Notes (revision)

**Test file:** `tests/test_corruption_1368.py`
**Class:** `TestFromAC_EncodingHardening`

### Fix applied (review rejection response)
Strengthened AC-2 detail assertions per reviewer feedback. The two lax `assert result.detail` checks (tests `test_non_utf8_in_tasks_dir_detail_is_non_empty` and `test_non_utf8_in_archive_dir_detail_is_non_empty`) now require at least one encoding-related keyword (`"encoding"`, `"decode"`, `"utf-8"`, `"utf8"`, `"unicode"`) to appear in `result.detail.lower()`. A generic non-empty string no longer passes.

### Test counts by category

| Category | Count |
|----------|-------|
| Happy path (valid UTF-8 → None) | 1 |
| Error path (non-UTF8 raises/returns) | 10 |
| **Total** | **11** |

All 11 tests FAIL (RED confirmed, ruff clean).

### Failure modes

| Tests | Failure type | Root cause |
|-------|-------------|------------|
| 1–8 | `UnicodeDecodeError` | `detect_corruption()` catches `OSError` but not `UnicodeDecodeError` at corruption.py:222 |
| 9–11 | `ImportError` | `ERR_CORRUPT_ENCODING` not yet defined — added by #1369 |

### AC coverage

| AC line | Tests |
|---------|-------|
| AC-1: non-UTF8 in tasks/ does not raise | test_non_utf8_in_tasks_dir_does_not_raise_unicode_error, test_non_utf8_in_tasks_dir_returns_corruption_error |
| AC-2: tasks/ CorruptionError shape (.code, .file_path, .detail with encoding keywords) | test_non_utf8_in_tasks_dir_code_is_encoding, test_non_utf8_in_tasks_dir_file_path_is_set, test_non_utf8_in_tasks_dir_detail_is_non_empty |
| AC-1: non-UTF8 in archive/ does not raise | test_non_utf8_in_archive_dir_does_not_raise_unicode_error, test_non_utf8_in_archive_dir_returns_corruption_error |
| AC-2: archive/ CorruptionError shape | test_non_utf8_in_archive_dir_code_is_encoding, test_non_utf8_in_archive_dir_file_path_is_set, test_non_utf8_in_archive_dir_detail_is_non_empty |
| AC-3: valid UTF-8 returns None | test_valid_utf8_task_returns_none |
| AC-4: direct import from owlbear_kanban.corruption | verified by module-level imports |
| AC-5: unpatched code fails | confirmed — all 11 fail |
[[2026-05-06]]
REJECT #1368 -> todo | task is RED-by-design test suite and not GREEN-buildable without implementation in counterpart #1369 — test-writer/architect: keep #1368 as RED contract, move implementation to builder task #1369.

## Builder Notes
- Files changed: none.
- quality-runner scoped pytest on `tests/test_corruption_1368.py`: 0 passed, 11 failed.
- Failure causes:
  - `UnicodeDecodeError` from `detect_corruption()` at `serve/kanban/src/owlbear_kanban/corruption.py:222` for non-UTF8 fixtures.
  - `ImportError` for missing `ERR_CORRUPT_ENCODING` symbol in `owlbear_kanban.corruption`.
- Ruff status: clean for `tests/test_corruption_1368.py`.
- Coverage (informational from scoped run): `owlbear_kanban.corruption` ~15% in this failing RED run.
- Evidence summary: #1368 is a test-only RED contract task. GREEN cannot be achieved within this task scope without implementing counterpart work in #1369.
[[2026-05-06]]
## Test-Writer Notes (re-verification after builder/reviewer bounce)

**Test file:** `tests/test_corruption_1368.py`
**Class:** `TestFromAC_EncodingHardening`

### Status
Test file was already complete from prior cycle (initial write + AC-2 detail strengthening per first review). Re-verification confirms all tests still fail correctly.

### Test counts by category

| Category | Count |
|----------|-------|
| Happy path (valid UTF-8 → None) | 1 |
| Error path (non-UTF8 raises/returns) | 10 |
| **Total** | **11** |

All 11 FAIL. Ruff: clean.

### Failure modes (re-verified 2026-05-06)

| Tests | Failure type | Root cause |
|-------|-------------|------------|
| 8 tests (non-code/file_path/detail variants) | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x80` | `corruption.py:222` catches `OSError` only |
| 3 tests (`*_code_is_encoding`, `test_valid_utf8_task_returns_none`) | `ImportError: cannot import name 'ERR_CORRUPT_ENCODING'` | Code added by #1369 |

### AC coverage

| AC line | Tests |
|---------|-------|
| AC-1: non-UTF8 in tasks/ does not raise | `test_non_utf8_in_tasks_dir_does_not_raise_unicode_error`, `test_non_utf8_in_tasks_dir_returns_corruption_error` |
| AC-2: tasks/ CorruptionError shape (.code, .file_path, .detail w/ encoding keywords) | `test_non_utf8_in_tasks_dir_code_is_encoding`, `test_non_utf8_in_tasks_dir_file_path_is_set`, `test_non_utf8_in_tasks_dir_detail_is_non_empty` |
| AC-1: non-UTF8 in archive/ does not raise | `test_non_utf8_in_archive_dir_does_not_raise_unicode_error`, `test_non_utf8_in_archive_dir_returns_corruption_error` |
| AC-2: archive/ CorruptionError shape | `test_non_utf8_in_archive_dir_code_is_encoding`, `test_non_utf8_in_archive_dir_file_path_is_set`, `test_non_utf8_in_archive_dir_detail_is_non_empty` |
| AC-3: valid UTF-8 returns None | `test_valid_utf8_task_returns_none` |
| AC-4: direct import from owlbear_kanban.corruption | verified by module-level import at line 20 |
| AC-5: unpatched code fails | confirmed — all 11 fail |

### Previous reviewer gap: resolved
AC-2 detail assertions now use keyword matching (`"encoding"`, `"decode"`, `"utf-8"`, `"utf8"`, `"unicode"`) — a generic non-empty string no longer passes. Assertions at lines 195–198 and 283–286.
[[2026-05-06]]
## Builder Notes
- Non-implementation task detected (`type:test`) with explicit implementation counterpart `#1369`.
- No code changes were made by builder.
- Applied GREEN pass-through rule from `w-tdd-green` Step 0a.
- Routing decision: advance to `review` for pipeline continuity on this test-only task.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped pytest on tests/test_corruption_1368.py: 11 failed, 0 passed.
- Failure alignment: the live snapshot remains RED as intended for this test-only contract task. `detect_corruption()` still reads UTF-8 text at serve/kanban/src/owlbear_kanban/corruption.py:222 and catches only `OSError` at line 223, so non-UTF8 fixtures still propagate `UnicodeDecodeError`. `ERR_CORRUPT_ENCODING` is still absent from serve/kanban/src/owlbear_kanban/corruption.py, so the explicit imports at tests/test_corruption_1368.py:155, tests/test_corruption_1368.py:248, and tests/test_corruption_1368.py:306 still fail on the unpatched snapshot.
- code-reader audit: no missing AC coverage, no visible TestFromAC weakening, no security or data-safety issues in the test module.

### Lint Results
- quality-runner scoped ruff on tests/test_corruption_1368.py: clean.

### Coverage Data
- quality-runner reported 15% coverage for owlbear_kanban.corruption.
- Informational only for this RED contract task. The review gate here is RED validity plus proof quality, not green-path module coverage.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC-1: non-UTF8 fixtures under tasks and archive prove no UnicodeDecodeError should escape | The suite creates task and archive fixture locations at tests/test_corruption_1368.py:87 and tests/test_corruption_1368.py:88, writes non-UTF8 bytes at tests/test_corruption_1368.py:121 and tests/test_corruption_1368.py:216, and calls `detect_corruption()` at tests/test_corruption_1368.py:125 and tests/test_corruption_1368.py:219. The live implementation still fails at serve/kanban/src/owlbear_kanban/corruption.py:222 on unpatched code, which is the intended RED proof. | PASS |
| AC-2: returned CorruptionError has encoding code, file_path, and encoding-specific detail | The suite asserts exact code equality at tests/test_corruption_1368.py:164 and tests/test_corruption_1368.py:257, exact file_path equality at tests/test_corruption_1368.py:181 and tests/test_corruption_1368.py:274, and encoding/decode keyword requirements in detail at tests/test_corruption_1368.py:197, tests/test_corruption_1368.py:198, tests/test_corruption_1368.py:290, and tests/test_corruption_1368.py:291. The prior proof-quality gap on generic non-empty detail is resolved. | PASS |
| AC-3: valid UTF-8 task returns None | The regression test writes a valid UTF-8 task at tests/test_corruption_1368.py:309, calls `detect_corruption()` at tests/test_corruption_1368.py:313, and asserts exact `None` at tests/test_corruption_1368.py:314. | PASS |
| AC-4: direct import from owlbear_kanban.corruption | Module-level direct import is present at tests/test_corruption_1368.py:20. | PASS |
| AC-5: current unpatched snapshot fails in RED phase for counterpart task 1369 | quality-runner confirmed the live snapshot still fails on the expected unpatched paths, and code-reader confirmed the suite is RED-by-design rather than false-green. | PASS |

### Deductions
- -0.03 The valid-UTF8 regression test includes an unused future-constant import at tests/test_corruption_1368.py:306, so its present-day RED failure is attributed to missing `ERR_CORRUPT_ENCODING` before the SUT call. This does not weaken the steady-state exact-`None` assertion at line 314, but it is a small evidence-quality deduction.
- -0.03 Dirty-tree contamination and exact TestFromAC immutability could not be proven from this tool surface because direct git diff/status inspection was unavailable in-session.

### Verdict
- PASS
- Confidence: 0.92
- Second review cycle: the earlier AC-2 detail-message proof gap is resolved.
- Action: advance to docs.

### Post-task Reflection
- Reviewing RED-only test tasks requires distinguishing expected test failure from actual proof weakness; the task now clears that bar.
- The previous blocker was assertion quality, not task scope. The revised keyword-gated detail assertions fixed the real problem.
- Tool-surface limits on git diff/status still warrant a small confidence deduction even when the live file reads cleanly.

[[2026-05-06]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Only changed file is tests/test_corruption_1368.py — no IN-scope prose docs reference test internals |
| 2 | Module docstrings | No | N/A | No source modules created or modified; this is a test-only task (type:test) |
| 3 | External attribution | No | N/A | No external patterns cited in task body |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram describes-match for test files |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_corruption_1368.py | OUT | N/A — test file, not an IN-scope doc |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1368-* scratch files found)
[[2026-05-06]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC-1: non-UTF8 in tasks/archive does not raise | Tests at test_corruption_1368.py:111-126, :205-221 call detect_corruption on binary fixtures; RED confirms UnicodeDecodeError propagates (correct RED signal) | PASS |\n| AC-2: CorruptionError shape (code, file_path, encoding detail) | Assertions at :164, :181, :195-198, :252, :269, :283-286; keyword-gated detail check resolved prior review gap | PASS |\n| AC-3: valid UTF-8 returns None | test_valid_utf8_task_returns_none at :302-314; exact None assertion | PASS |\n| AC-4: direct import from owlbear_kanban.corruption | Module-level import at :20 | PASS |\n| AC-5: unpatched code fails (RED validity) | 11/11 tests fail: 8 via UnicodeDecodeError, 3 via ImportError (ERR_CORRUPT_ENCODING absent) | PASS |\n\n### Test Results\n- pytest (full suite): 4675 passed, 241 failed (pre-existing background debt; zero regressions from this test-only task)\n- pytest (task-scoped): 11 failed, 0 passed (expected RED)\n- ruff (task file): clean\n\n### Architect Quality: 4/5\nAC was specific about return types, error codes, fixture strategy, and module targets. Minor initial ambiguity on detail-message requirements caught and resolved during review cycle. Good design rationale distinguishing scanner vs storage behavior.\n\n### Deduction Breakdown\n- -0.02: test_valid_utf8_task_returns_none fails via ImportError (confounding RED signal) rather than exercising the valid-path assertion; acceptable for RED contract but slightly reduces diagnostic clarity\n\n### Confidence: 0.98\n### Action: archive\n\n### Commits Verified\n- 69dba5eb test: corruption scanner encoding hardening RED (#1368, test-writer)\n- b198b923 test: enhance detail assertion for CorruptionError in encoding tests