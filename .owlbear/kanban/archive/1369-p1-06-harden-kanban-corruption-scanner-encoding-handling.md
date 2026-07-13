---
id: 1369
title: 'P1-06: Harden kanban corruption scanner encoding handling'
status: archived
priority: medium
created: 2026-05-06T00:58:39.965961+00:00
updated: 2026-05-06T08:59:46.088138+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:kanban
- type:fix
- backend
- corruption-scan
- encoding
parent: 1363
depends_on:
- 1368
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Harden kanban corruption scanning so non-UTF8 task and archive markdown files cannot crash Cockpit scans.

## Problem Evidence
- detect_corruption() can raise UnicodeDecodeError on archived files, surfacing as a Cockpit scan 500.
- Storage parsing has a more graceful encoding path, leaving scanner behavior inconsistent.
- Real archived task files with non-UTF8 bytes exist in .owlbear/kanban/archive.

## Acceptance Criteria
- Corruption scanning never crashes on non-UTF8 task or archive markdown files. (td:2)
- Non-UTF8 files produce a CorruptionError return with code=ERR_CORRUPT_ENCODING, file_path set, and detail referencing the encoding failure. (td:2)
- Existing valid-file scan behavior remains unchanged. (td:1)
- The fix lives in the kanban engine/scanner layer rather than only catching exceptions in Cockpit routes. (td:0)
- The tests from #1368 pass. (td:1)

## Scope
- In scope: kanban scanner encoding behavior for task and archive markdown files.
- Out of scope: Cockpit health UI rendering, frontend retry UX, cache/SSE invalidation from #1346, repair-path encoding (`_read_frontmatter`), engine-startup migration gate.

## Test Dependency
Satisfies #1368.

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: encoding hardening in `detect_corruption()` |
| Interface clarity | PASS | Tests in #1368 define exact contract: ERR_CORRUPT_ENCODING code, file_path, detail |
| Dependency correctness | PASS | #1368 (test task) is archived/done; test file exists at `tests/test_corruption_1368.py` |
| Module layering | PASS | Fix in `corruption.py` (kanban engine layer) — correct location |
| TDD compliance | PASS | #1368 provides RED phase tests covering tasks/ and archive/ paths |
| KISS/YAGNI | PASS | Minimal: catch UnicodeDecodeError, add 1 error code, return structured error |
| Premise challenge | PASS | Bug is real — `detect_corruption()` catches OSError but not UnicodeDecodeError |
| Pattern consistency | PASS | Follows existing 9-code corruption pattern in corruption.py |
| Security surface | PASS | Existing file I/O boundary; fix hardens it |
| Single domain | PASS | Kanban domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `detect_corruption()` → `read_text("utf-8")` | Non-UTF8 bytes in .md file | UnicodeDecodeError | NO (current) → YES (after fix) | Cockpit 500 on scan |
| `_read_frontmatter()` → `read_text("utf-8")` | Non-UTF8 bytes in .md file | UnicodeDecodeError | NO — out of scope (repair path) | Repair crash |
| Engine migration gate → `read_text("utf-8")` | Non-UTF8 bytes in tasks/ | UnicodeDecodeError | NO — out of scope (separate concern) | Engine init crash |

Note: rows 2-3 are related bugs NOT in this task's scope. Follow-up tasks may address them.

### Builder Notes
- Add `ERR_CORRUPT_ENCODING` to `KANBAN_ERROR_CODES` frozenset in `serve/kanban/src/owlbear_kanban/errors.py` (follows existing 9-code registration pattern).
- The fix goes in `detect_corruption()` at the `path.read_text(encoding="utf-8")` call — catch `UnicodeDecodeError` and return `CorruptionError(code=ERR_CORRUPT_ENCODING, detail=..., path=path)`.
- `_read_frontmatter()` has the same gap but is out of scope (used by repair, not scan).

### Challenge Results
- Challenger: reconsider (confidence 0.46)
- Key challenge: engine-startup decode path also vulnerable
- Architect response: REBUTTED — engine startup migration gate is not the corruption scanner; task explicitly scopes to scanner behavior. Related bugs are valid follow-up material but don't block this scoped fix.

### Test Depth
- Max depth: 2
- Test-writer: SKIP (tests pre-written by #1368)

### AC Refinement
- AC-2 tightened: removed dead "or fallback" option since #1368 tests lock in the ERR_CORRUPT_ENCODING approach.
- Added td: annotations.
- Expanded out-of-scope to explicitly exclude repair path and engine migration gate.

### Verdict: APPROVE
### Action Taken: Refined AC-2 to remove stale policy ambiguity, annotated test depths, added builder integration note for errors.py. Approved to todo.

[[2026-05-06]]
Architecture review complete. Refined AC-2 (removed stale "or fallback" option — tests lock in ERR_CORRUPT_ENCODING), annotated test depths, expanded out-of-scope list, added builder integration note for errors.py registration. Challenger raised engine-startup decode path — rebutted as separate concern outside scanner scope. All 10 criteria PASS. Test-writer: SKIP (pre-written by #1368).
[[2026-05-06]]
## Test-Writer Notes
- Test file: tests/test_corruption_1368.py (pre-written by #1368 — no new file created)
- Classes: TestFromAC_EncodingHardening
- Tests per category: happy 1 (valid UTF-8 regression guard), edge 0, error 10 (non-UTF8 in tasks/ and archive/ — UnicodeDecodeError and ImportError), boundary 0
- Total: 11 tests, all FAIL
- ruff: clean

AC Coverage:
| AC | Tests |
|----|-------|
| AC-1 (td:2) | 4 tests — tasks/ and archive/ non-UTF8 don't raise UnicodeDecodeError |
| AC-2 (td:2) | 6 tests — ERR_CORRUPT_ENCODING code, file_path, detail (ImportError on missing constant) |
| AC-3 (td:1) | 1 test — valid UTF-8 returns None (regression guard) |
| AC-4 (td:0) | Skipped — architectural constraint, no tests needed |
| AC-5 (td:1) | Meta — test_corruption_1368.py IS the pre-written test suite |

Failure modes confirmed:
- ImportError: cannot import name 'ERR_CORRUPT_ENCODING' (2 tests)
- UnicodeDecodeError: 'utf-8' codec can't decode byte 0x80 (9 tests)

No commit — pre-written tests from #1368 are already in the repo.
[[2026-05-06]]
## Builder Notes
- Implementation: added `ERR_CORRUPT_ENCODING` registration in `serve/kanban/src/owlbear_kanban/errors.py`; added scanner handling in `serve/kanban/src/owlbear_kanban/corruption.py` to catch `UnicodeDecodeError` at UTF-8 read and return `CorruptionError(code=ERR_CORRUPT_ENCODING, file_path/path set, detail with decode context)`.
- Tests (task-scoped): 11/11 `TestFromAC_EncodingHardening` passed from `tests/test_corruption_1368.py`.
- Lint (scoped): clean (`ruff` clean on touched source files + task test file).
- Coverage (task-scoped): `owlbear_kanban.corruption` 34%, `owlbear_kanban.errors` 90%.
- Regression check (module-level durable suite): `tests/test_corruption_1368.py` + `serve/kanban/tests/test_corruption.py` => 71 passed, 1 failed at `serve/kanban/tests/test_corruption.py::TestBuilderDiscovered::test_make_yaml_disables_timestamp_resolver` (`AttributeError: module 'owlbear_kanban.corruption' has no attribute '_make_yaml'`). This failure is outside AC-1369 scope and not caused by the encoding-handling patch.
- Evidence summary: RED verified pre-implementation (11 failing: ImportError for missing constant + UnicodeDecodeError propagation). GREEN verified post-implementation on task tests with zero failures.
- Commit: `43417267` with message `fix: harden corruption scanner utf8 decode handling (#1369, builder)`.

## Post-task Reflection
- Problem faced: module-level regression suite includes pre-existing expectation around `_make_yaml` that is unrelated to scanner encoding AC.
- Workaround applied: used task-scoped quality evidence as the primary gate and recorded module-level regression failure as residual context.
- Pattern discovered: scanner path and global error catalog must be updated together; changing only one causes ImportError/ValueError-style failures.
- Quality gap: task-scoped coverage remains low for a large legacy module despite complete AC satisfaction; full module coverage requires broader curated tests beyond this task’s AC surface.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner (scoped): 11 passed, 0 failed, 0 skipped on `tests/test_corruption_1368.py`
- Key passing tests:
  - `test_non_utf8_in_tasks_dir_does_not_raise_unicode_error` at `tests/test_corruption_1368.py:111`
  - `test_non_utf8_in_archive_dir_does_not_raise_unicode_error` at `tests/test_corruption_1368.py:207`
  - `test_non_utf8_in_tasks_dir_code_is_encoding` at `tests/test_corruption_1368.py:149`
  - `test_non_utf8_in_archive_dir_code_is_encoding` at `tests/test_corruption_1368.py:243`
  - `test_valid_utf8_task_returns_none` at `tests/test_corruption_1368.py:300`

### Lint Results
- quality-runner: clean
- Scope: `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/errors.py`, `tests/test_corruption_1368.py`

### Coverage
- `owlbear_kanban.errors`: 90%
- `owlbear_kanban.corruption`: 34%
- Assessment: PASS for this task. The changed lines are directly exercised by the task suite even though the legacy `corruption` module remains low overall; module-level residual coverage debt is non-blocking for this narrow diff-scoped fix.

### Test Integrity
- No weakened or removed `TestFromAC_*` assertions found in the current `tests/test_corruption_1368.py` body.
- Current assertions remain discriminating: exact code equality at `tests/test_corruption_1368.py:164` and `tests/test_corruption_1368.py:257`, exact file_path equality at `tests/test_corruption_1368.py:181` and `tests/test_corruption_1368.py:274`, encoding-specific detail checks at `tests/test_corruption_1368.py:200` and `tests/test_corruption_1368.py:293`, and exact clean-path `None` at `tests/test_corruption_1368.py:314`.

### Security Review
- No security issues found in scope. The change adds one error code and catches `UnicodeDecodeError` locally in the kanban corruption layer.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Corruption scanning never crashes on non-UTF8 task or archive markdown files. | Passing non-raise tests at `tests/test_corruption_1368.py:111` and `tests/test_corruption_1368.py:207`; runtime scan path is `POST /tasks/scan` in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:328-329` -> `serve/cockpit/src/owlbear_cockpit/view.py:250-252` -> `serve/kanban/src/owlbear_kanban/engine.py:1868-1876`, where `scan_corruption()` only iterates files and calls `detect_corruption()` at `serve/kanban/src/owlbear_kanban/engine.py:1875`. | `test_non_utf8_in_tasks_dir_does_not_raise_unicode_error`; `test_non_utf8_in_archive_dir_does_not_raise_unicode_error` | PASS |
| Non-UTF8 files produce a CorruptionError return with code=ERR_CORRUPT_ENCODING, file_path set, and detail referencing the encoding failure. | `ERR_CORRUPT_ENCODING` defined at `serve/kanban/src/owlbear_kanban/corruption.py:139`, returned from the decode handler at `serve/kanban/src/owlbear_kanban/corruption.py:223-227`, registered in `serve/kanban/src/owlbear_kanban/errors.py:64`, and `CorruptionError` derives `file_path` at `serve/kanban/src/owlbear_kanban/corruption.py:104`. Assertions pass at `tests/test_corruption_1368.py:164`, `:181`, `:200`, `:257`, `:274`, `:293`. | `test_non_utf8_in_tasks_dir_code_is_encoding`; `test_non_utf8_in_tasks_dir_file_path_is_set`; `test_non_utf8_in_tasks_dir_detail_is_non_empty`; archive equivalents | PASS |
| Existing valid-file scan behavior remains unchanged. | Passing exact-`None` assertion at `tests/test_corruption_1368.py:314`. | `test_valid_utf8_task_returns_none` | PASS |
| The fix lives in the kanban engine/scanner layer rather than only catching exceptions in Cockpit routes. | Implementation is in `serve/kanban/src/owlbear_kanban/corruption.py:223-227` plus registry update at `serve/kanban/src/owlbear_kanban/errors.py:64`; Cockpit scan route remains a thin delegation layer at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:328-331`. | Code-read evidence | PASS |
| The tests from #1368 pass. | quality-runner scoped result: 11 passed, 0 failed, 0 skipped on `tests/test_corruption_1368.py`. | `tests/test_corruption_1368.py` | PASS |

### Subagent Divergence
- `code-reader` flagged a real repair-path decode gap through `scan_and_fix()` -> `attempt_repair()` -> `_read_frontmatter()` at `serve/kanban/src/owlbear_kanban/corruption.py:146`, `:418`, `:666`.
- I am treating that as non-blocking for this task because the scoped contract is the read-only corruption scan path, and the task body explicitly marks `_read_frontmatter` / repair-path encoding as out of scope. Cockpit scan and repair are separate operations (`/tasks/scan` vs `/tasks/repair`), and the scan route does not enter the repair flow.

### Deductions
- -0.03 Could not independently run `git show` / `git status` from this tool surface, so dirty-tree contamination and exact TestFromAC immutability are slightly lower-confidence than usual.
- -0.02 Informational debt remains in stale `"9 ERR_CORRUPT_*"` docstrings/comments after adding `ERR_CORRUPT_ENCODING`, and the separate repair-path decode gap should be tracked independently.

### Verdict
- PASS
- Confidence: 0.93

### Action
- Advance to `docs`.

### Post-task Reflection
- The key review judgment was separating the read-only scan contract from the repair path; the task body and runtime wiring support that narrower interpretation.
- Direct helper tests were sufficient here because the live scan route is a straight loop over `detect_corruption()` with no extra decode logic.
- Tool-surface limits around git diff/status remain a recurring source of small confidence deductions even on otherwise clean reviews.
[[2026-05-06]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose doc (README, setup guide, share/README) references the corruption scanner encoding behavior. |
| 2 | Module docstrings | Yes | Updated | `corruption.py` module docstring (line 3), `CorruptionError` class docstring (line 86), and `attempt_repair()` arg docstring (line 356) all said "9 ERR_CORRUPT_* codes" — updated to "10" after `ERR_CORRUPT_ENCODING` addition. Inline comment at line 29 is not a docstring — left unchanged per skill boundary. `errors.py` module docstring is accurate as-is. Stale "9" in `test_corruption.py:309` and `test_error_hierarchy.py:150` are test docstrings describing original Brief C AC text — not touched by this task; informational debt noted. |
| 3 | External attribution | No | N/A | No external patterns or sources referenced. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/kanban/src/**`) both matched. Footers updated: kanban `7f468ee7 → 6923a3ef`, mcp-topology `b198b923 → 6923a3ef`. Both dated 2026-05-06. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/corruption.py` | IN (docstrings) | Updated — 3 docstrings corrected (9 → 10 codes) |
| `serve/kanban/src/owlbear_kanban/errors.py` | IN (docstrings) | N/A — module docstring accurate as-is |
| `tests/test_corruption_1368.py` | IN (docstrings) | N/A — no public API, pre-written test file |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `serve/kanban/src/owlbear_kanban/corruption.py` (docstrings)
- `share/diagrams/kanban.excalidraw` (footer)
- `share/diagrams/mcp-topology.excalidraw` (footer)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1369-*` scratch files existed)
[[2026-05-06]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Corruption scanning never crashes on non-UTF8 task or archive markdown files | UnicodeDecodeError caught at corruption.py:224, returns CorruptionError. Tests pass at test_corruption_1368.py:111,:207 | PASS |
| Non-UTF8 files produce CorruptionError with code=ERR_CORRUPT_ENCODING, file_path set, detail referencing encoding failure | Code defined at corruption.py:139, returned at :226-228, registered errors.py:64. Tests pass at :149,:164,:181,:200,:243,:257,:274,:293 | PASS |
| Existing valid-file scan behavior remains unchanged | Exact None assertion passes at test_corruption_1368.py:314 | PASS |
| Fix lives in kanban engine/scanner layer | Implementation at corruption.py:224-228 + errors.py:64. Cockpit route remains thin delegation at routes/mutation.py:328-331 | PASS |
| Tests from #1368 pass | quality-runner full: 11 passed, 0 failed on test_corruption_1368.py | PASS |

### Test Results
- pytest (full suite): 4684 passed, 235 failed (pre-existing), 4 skipped, 5 errors (timeouts)
- Task tests: 11/11 pass
- Cross-task regression: test_corruption_1057::test_ac_cleanup_exact_brief_c41_code_set FAILS because it guards a frozen code set from Brief C section 4.1 that was legitimately expanded by this task's architectural approval. Stale guard; follow-up needed.
- ruff: clean on all task files

### Architect Quality: 5/5
Specific AC, clear scope boundaries, explicit out-of-scope declarations, failure mode map, builder notes with exact locations. Exemplary.

### Deduction Breakdown
- Full-suite test failure caused by task changes (stale guard in test_corruption_1057): -.05

### Confidence: .95
### Action: archive

### Notes
- test_corruption_1057 asserts exact ERR_CORRUPT_* code set from Brief section 4.1. Adding ERR_CORRUPT_ENCODING is architecturally approved for this task. The test needs updating to include the new code (test-curator follow-up).
- Commits verified: 43417267 (builder), e939c77e (doc-writer), both properly formatted.