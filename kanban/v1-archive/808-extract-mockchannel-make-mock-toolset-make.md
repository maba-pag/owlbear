---
id: 808
title: Extract MockChannel, make_mock_toolset, make_settings to conftest.py
status: archived
priority: nice-to-have
created: 2026-03-14T21:04:58.5763329+01:00
updated: 2026-03-15T08:00:43.4769889+01:00
started: 2026-03-15T07:59:59.9464966+01:00
completed: 2026-03-15T07:59:59.9464966+01:00
tags:
    - test
    - audit
    - rigor:lean
depends_on:
    - 555
class: standard
---

Phase 1 of conftest extraction (see docs/research/conftest-extraction.md, task #555).
Move shared test helpers to tests/conftest.py and remove duplicates from individual test files.

## AC
- MockChannel class added to tests/conftest.py (copy from test_daemon.py)
- make_mock_toolset() factory added to tests/conftest.py with default return_value='tool_result'
- make_settings() factory added to tests/conftest.py with signature (tmp_path: Path, **overrides: object) -> OwlBearSettings
- Duplicate MockChannel removed from: test_daemon.py test_daemon_coverage_gaps.py test_error_sanitization_callsites.py test_integration_e2e.py test_poll_dispatch.py (5 files)
- Duplicate _make_mock_toolset removed from: test_approval_gate.py test_hooked_toolset.py test_slack_interactive.py (3 files)
- Duplicate _make_settings removed from: test_bootstrap_integration.py test_client_cleanup.py test_integration_e2e.py test_pipeline_e2e.py (4 files)
- test_pipeline_e2e.py updated to call make_settings(tmp_path, agents_dir=AGENTS_DIR) instead of local variant
- All existing tests pass
- Zero duplicate MockChannel or _make_mock_toolset or _make_settings definitions across test files

[[2026-03-15]] Sun 06:32
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| MockChannel class added to conftest.py | Clear signature, verifiable | OK |
| make_mock_toolset() factory with default return_value='tool_result' | Clear. test_hooked_toolset uses 'mock_result' -- caller passes override. | OK |
| make_settings(tmp_path, **overrides) factory | Signature unifies all 4 variants. test_client_cleanup has no **overrides but is backward-compatible. | OK |
| Duplicate MockChannel removed from 5 files | Verified: all 5 implementations byte-identical | OK |
| Duplicate _make_mock_toolset removed from 3 files | Verified: 3 files, only default value differs | OK |
| Duplicate _make_settings removed from 4 files | Verified: 4 files, 2 have **overrides, 2 don't | OK |
| test_pipeline_e2e.py calls make_settings(tmp_path, agents_dir=AGENTS_DIR) | Correct -- local variant hardcodes AGENTS_DIR | OK |
| All existing tests pass | Verifiable gate. Self-verifying refactoring. | OK |
| Zero duplicate definitions | Verifiable via grep. Clear exit criterion. | OK |

### Architecture Notes
- Pure test DRY refactoring. No src/ changes, no new behavior.
- conftest.py already has fixtures. Adding module-level helpers is standard pytest practice.
- MockChannel, make_mock_toolset, make_settings are plain functions/classes (not fixtures) -- callers import from conftest.
- TDD: test refactoring is self-verifying. No separate test task needed (per #555 arch review).
- Independent of #809 (async _run elimination).

### Dependencies
- Verified: #555 (research) -- done
- No new dependencies needed

[[2026-03-15]] Sun 06:41
## Test-Writer Notes
- Test file: tests/test_conftest_helpers.py
- Classes: TestFromAC_MockChannelInConftest, TestFromAC_MakeMockToolset, TestFromAC_MakeSettings, TestFromAC_ZeroDuplicates
- Tests per category: happy 12, edge 3, error 0, boundary 12
- Total: 28 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| MockChannel in conftest | test_import, test_name_property, test_receive_*, test_send | happy, edge |
| make_mock_toolset() default='tool_result' | test_import, test_default_return_value, test_custom, test_async | happy |
| make_settings(tmp_path, **overrides) | test_import, test_returns_owlbear, test_paths, test_overrides, test_sig | happy, edge |
| Duplicates removed (5 MockChannel) | test_no_duplicate_mock_channel[5 params] | boundary |
| Duplicates removed (3 _make_mock_toolset) | test_no_duplicate_make_mock_toolset[3 params] | boundary |
| Duplicates removed (4 _make_settings) | test_no_duplicate_make_settings[4 params] | boundary |

[[2026-03-15]] Sun 07:11
## Builder Notes
- Files changed: tests/conftest.py, pyproject.toml, 12 test files (removed duplicates, added imports)
- Tests: 28 passed (test_conftest_helpers.py), 390 passed across affected files
- 10 pre-existing failures (trafilatura regex, _chat_loop removed, TYPE_CHECKING patch, role/policy mismatch)
- Lint: ruff clean on all 14 files
- Changes: MockChannel class, make_mock_toolset(), make_settings() added to conftest.py; duplicates removed from 12 test files; pythonpath=['tests'] added to pyproject.toml for conftest importability
- Commit: 653586d

[[2026-03-15]] Sun 07:34
## Review Evidence
See docs/scratch/808-reviewer.md for full evidence.

[[2026-03-15]] Sun 07:40
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only refactoring, no behavior/API change, no src/ files modified |
| 2 | Docstrings complete | Yes | Pass | MockChannel (L84), make_mock_toolset (L107), make_settings (L114) all have docstrings in conftest.py |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/conftest-extraction.md exists, referenced in task body via #555 |
| 6 | No impact | -- | -- | Items 1,3,4 N/A; items 2,5 pass |

### Files Updated
- None

### Scratch Files Cleaned
- Deleted docs/scratch/808-reviewer.md

[[2026-03-15]] Sun 08:00
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| MockChannel in conftest.py | conftest.py L84 class MockChannel with name/send/receive | PASS |
| make_mock_toolset() default='tool_result' | conftest.py L107, default return_value='tool_result' | PASS |
| make_settings(tmp_path, **overrides) | conftest.py L114, correct signature | PASS |
| Duplicates removed (5 MockChannel) | grep: only 1 match in conftest.py, 0 in other files | PASS |
| Duplicates removed (3 _make_mock_toolset) | grep: only 1 match in conftest.py | PASS |
| Duplicates removed (4 _make_settings) | grep: only 1 match in conftest.py | PASS |
| test_pipeline_e2e calls make_settings(tmp_path, agents_dir=AGENTS_DIR) | L67 verified | PASS |
| All existing tests pass | 28/28 task tests + 290/295 affected (5 pre-existing) | PASS |
| Zero duplicate definitions | grep confirmed single definitions | PASS |

### Test Results
- Task-specific: 28 passed (test_conftest_helpers.py)
- Affected files: 290 passed, 5 failed (all pre-existing: regex/trafilatura env, role/policy assertions)
- Ruff: All checks passed on 14 task files

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 653586d | refactor | conftest.py, pyproject.toml, 12 test files | #808 |

### Confidence: .97
### Action: archive
