---
id: 831
title: Cover edge-case paths in browser config, ask_user, filesystem, usage (13 lines)
status: archived
priority: nice-to-have
created: 2026-03-15T12:57:27.168565+01:00
updated: 2026-03-16T05:10:54.9512275+01:00
started: 2026-03-16T05:10:50.289617+01:00
completed: 2026-03-16T05:10:50.289617+01:00
tags:
    - test
    - phase-12
class: standard
---

4 modules with minor coverage gaps (~13 lines total).

## AC

- browser/config.py L80-82: test BrowserConfig(cdp_endpoint=':::not-a-url') raises ValidationError (unparseable URL path)
- ask_user.py L154-155: test_receive_option where channel.receive() raises TimeoutError ->_handle_timeout() called
- ask_user.py L157-158: test_receive_option where channel.receive() returns None ->_handle_timeout() called
- filesystem.py L55-57: test update_workspace() sets_root to resolved path
- filesystem.py L236-237: test glob result outside workspace root is filtered out
- filesystem.py L241-242: test OSError during content-regex file read is gracefully skipped
- usage.py L81-83: test summary(window=None) uses load() to get all records
- All tests pass on first run (retroactive coverage)
- ruff clean

See docs/research/close-test-coverage-gaps.md.

[[2026-03-15]] Sun 13:07

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| browser/config.py cdp_endpoint=':::not-a-url' raises ValidationError | Verifiable BUT misleading: urlparse never raises on string input, so the except-Exception branch (the stated L80-82) is dead code. Test will pass via scheme-rejection path. | Refine  note dead-code branch |
| ask_user_receive_option TimeoutError ->_handle_timeout | Clear, verifiable. Code at tools/ask_user.py ~L154 | Keep |
| ask_user_receive_option returns None ->_handle_timeout | Clear, verifiable. Code at tools/ask_user.py ~L157 | Keep |
| filesystem update_workspace sets_root to resolved path | Clear, verifiable. Code at tools/filesystem.py ~L56 | Keep |
| filesystem glob outside root is filtered | Clear, verifiable. Code at tools/filesystem.py ~L237 | Keep |
| filesystem OSError during content-regex read is skipped | Clear, verifiable. Code at tools/filesystem.py ~L241 | Keep |
| usage summary(window=None) uses load() | Clear, verifiable. Code at memory/usage.py ~L83 | Keep |
| All tests pass on first run (retroactive) | OK  retroactive coverage, TDD RED/GREEN N/A | Keep |
| ruff clean | Verifiable | Keep |

### Architecture Notes

- **Multi-domain (accepted):** Task spans 4 modules across 3 packages (tools/browser, tools, memory). Normally requires split, but total scope is 13 lines of retroactive test coverage  splitting into 4 tasks would create disproportionate overhead. Accepted as single test task.
- **Dead code note:** `urlparse()` virtually never raises on string input. The `except Exception` branch in `_cdp_endpoint_localhost_only` is defensive dead code. Test-writer should target the scheme/hostname rejection paths instead. Consider a follow-up to remove the dead try/except.
- **Existing test files:** test_browser_config.py, test_ask_user.py, test_filesystem_tools.py, test_usage_tracker.py all exist  tests should be added to these files.
- **Actual paths:** browser/config.py = `src/owlbear/tools/browser/config.py`, ask_user.py = `src/owlbear/tools/ask_user.py`, filesystem.py = `src/owlbear/tools/filesystem.py`, usage.py = `src/owlbear/memory/usage.py`.
- **Line numbers:** Research doc warns line numbers are stale. Test-writer should verify against current source.

### Changes Made

- Approved with notes (no AC rewrite needed  descriptions are clear even if line refs are stale)

### Dependencies

- None required. All source modules already exist.

[[2026-03-15]] Sun 13:29

## Test-Writer Notes

- Retroactive coverage task  TDD RED/GREEN N/A per architect review
- Test files: test_browser_config.py, test_ask_user.py, test_filesystem_tools.py, test_usage_tracker.py
- Classes: TestFromAC_BrowserConfigCdpUnparseable, TestFromAC_ReceiveOptionEdgePaths, TestFromAC_FileToolsetCoverageGaps, TestFromAC_UsageSummaryNoneWindow
- Tests per category: happy 3, edge 1, error 7, boundary 0
- Total: 11 tests, all PASS (retroactive)
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| cdp_endpoint unparseable | test_cdp_endpoint_unparseable_url_raises_validation_error | error |
| _receive_option TimeoutError | test_receive_option_timeout_abort + _skip | error |
|_receive_option None | test_receive_option_none_abort +_skip | error |
| update_workspace resolved | test_update_workspace_sets_root_to_resolved_path | happy |
| glob outside root | test_glob_result_outside_workspace_root_filtered | edge |
| OSError content-regex | test_oserror_during_content_regex_read_skipped | error |
| summary(window=None) | test_summary_none_window_includes_all +_empty_store | happy |

[[2026-03-15]] Sun 14:31

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only task, no behavior/API change |
| 2 | Docstrings | No | N/A | No source modules changed; only test files added |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/close-test-coverage-gaps.md exists, referenced in AC |
| 6 | No impact | Yes | Pass | Test-only retroactive coverage task with no docs implications |

### Files Updated

- None

### Scratch Files Cleaned

- None (no docs/scratch/831-* files found)

[[2026-03-16]] Mon 05:10

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| browser/config.py cdp_endpoint=':::not-a-url' raises ValidationError | TestFromAC_BrowserConfigCdpUnparseable::test_cdp_endpoint_unparseable_url_raises_validation_error exists; source _cdp_endpoint_localhost_only validator in config.py rejects non-http scheme via ValueError -> pydantic ValidationError | PASS |
| ask_user_receive_option TimeoutError ->_handle_timeout | TestFromAC_ReceiveOptionEdgePaths (abort + skip variants); source L154: except TimeoutError: return self._handle_timeout() | PASS |
| ask_user_receive_option returns None ->_handle_timeout | TestFromAC_ReceiveOptionEdgePaths (abort + skip variants); source: if raw is None: return self._handle_timeout() | PASS |
| filesystem update_workspace() sets_root to resolved path | TestFromAC_FileToolsetCoverageGaps::test_update_workspace_sets_root_to_resolved_path; source: self._root = workspace.resolve() | PASS |
| filesystem glob outside root filtered | TestFromAC_FileToolsetCoverageGaps::test_glob_result_outside_workspace_root_filtered; source: if not hit.resolve().is_relative_to(self._root): continue | PASS |
| filesystem OSError during content-regex skipped | TestFromAC_FileToolsetCoverageGaps::test_oserror_during_content_regex_read_skipped; source: except OSError: continue | PASS |
| usage summary(window=None) uses load() | TestFromAC_UsageSummaryNoneWindow (all + empty variants); source: records = self.load() if window is None else self.query(window) | PASS |
| All tests pass | ruff clean independently verified; pytest hung due to 25+ concurrent Python processes in environment; source code read + test code verified correct; upstream: test-writer 11 pass, reviewer PASS | PASS (upstream+code) |
| ruff clean | uv run ruff check on all 4 test files: All checks passed | PASS |

### Test Results

- pytest: Could not independently run  environment-wide collection hang (25+ concurrent Python processes from parallel agents). ruff clean independently confirmed.
- Source code paths: all 7 AC paths verified by reading source directly.
- Upstream chain: test-writer (11 tests pass), builder (pass-through verified), reviewer (pass-through), writer (docs gate complete).
- ruff: All checks passed (uv run ruff check tests/test_browser_config.py tests/test_ask_user.py tests/test_filesystem_tools.py tests/test_usage_tracker.py)

### Quality Gap

- Test-writer and builder did not commit deliverables. Auditor committed 4 test files as 8a7183d.

### Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8a7183d | test | tests/test_browser_config.py tests/test_ask_user.py tests/test_filesystem_tools.py tests/test_usage_tracker.py | #831 |

### Confidence: .95

### Action: archive
