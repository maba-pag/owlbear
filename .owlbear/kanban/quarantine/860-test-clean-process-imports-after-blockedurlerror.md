---
id: 860
title: 'Test: clean-process imports after BlockedURLError dependency inversion'
status: archived
priority: needed
created: 2026-03-19T15:10:14.7307424+01:00
updated: 2026-03-20T12:29:39.2102807+01:00
started: 2026-03-20T12:29:34.7120392+01:00
completed: 2026-03-20T12:29:34.7120392+01:00
tags:
    - test
    - bug
    - architecture
    - scope:core
parent: 850
class: standard
---

## TDD Red Phase for #850

Add failing tests that reproduce the clean-process import regression and guard the exception relocation contract.

## AC

- [ ] In tests/test_daemon_journal_async.py, remove the import owlbear.tools pre-seeding workaround and keep direct from owlbear.daemon import_log_to_journal
- [ ] Add tests/test_blocked_url_error_location.py with a structural assertion that src/owlbear/core/errors.py does not import owlbear.tools.browser.safety
- [ ] In tests/test_blocked_url_error_location.py, assert BlockedURLError.__module__ resolves to owlbear.core.exceptions and classify_error(BlockedURLError(...)) returns ErrorCategory.PERMANENT
- [ ] Add a clean-subprocess smoke test, following tests/test_knowledge_exports.py, proving a fresh subprocess can import owlbear.daemon without importing owlbear.tools first
- [ ] Add a clean-subprocess smoke test proving a fresh subprocess can import owlbear.config and then owlbear.daemon with no manual owlbear.tools pre-seeding
- [ ] Existing browser safety behavior coverage in tests/test_browser_safety.py remains green
- [ ] The new task-specific tests fail before #850 implementation changes are applied (TDD red)

[[2026-03-19]] Thu 16:14

## Test-Writer Notes

- Test file: tests/test_blocked_url_error_location.py (new)
- Modified: tests/test_daemon_journal_async.py (removed pre-seeding workaround)
- Classes: TestFromAC_BlockedURLErrorLocation, TestFromAC_DaemonCleanImport
- Tests per category: happy 0, edge 0, error 3, boundary 2
- Total: 5 tests, all FAIL (RED) in tests/test_blocked_url_error_location.py
- ruff: clean

### AC coverage

| AC Line | Test(s) | Category |
|---------|---------|----------|
| AC1: remove owlbear.tools pre-seeding | test_daemon_journal_async.py â€” workaround removed; existing tests pass in pytest context (other modules pre-load the chain), subprocess regression captured by AC4/AC5 | cleanup |
| AC2: errors.py must not import tools.browser.safety | test_errors_no_import_from_browser_safety | error |
| AC3: BlockedURLError.__module__ == owlbear.core.exceptions | test_blocked_url_error_module | error |
| AC3: classify_error returns PERMANENT | test_classify_error_returns_permanent | error |
| AC4: fresh subprocess imports owlbear.daemon without tools pre-seeding | test_daemon_import_without_tools_preseeding | boundary |
| AC5: fresh subprocess imports config then daemon with no pre-seeding | test_daemon_import_config_then_daemon | boundary |
| AC6: test_browser_safety remains green | Not a new test â€” constraint, not authoring scope | -- |
| AC7: tests fail before #850 | Confirmed: 5 FAILED, 0 passed in test_blocked_url_error_location.py | -- |

### Note on AC1

Removing the pre-seeding comment block (`import owlbear.tools`) from `test_daemon_journal_async.py` does not cause those tests to fail in a pytest session â€” pytest loads many modules before reaching this file, so the circular import is already resolved. The subprocess tests (AC4/AC5) reliably reproduce the fresh-process failure, which is the correct regression guard for #850.

[[2026-03-19]] Thu 16:55

## Builder Notes

- Files changed: src/owlbear/core/exceptions.py, src/owlbear/tools/browser/safety.py, src/owlbear/core/errors.py
- Tests: 71 passed (5 target + 66 related), ruff clean
- Coverage: exceptions.py 100%, safety.py 100%, errors.py 66% (unchanged)
- Lint: ruff clean on all 3 changed files
- Fixes applied: Moved BlockedURLError from owlbear.tools.browser.safety to owlbear.core.exceptions; safety.py now imports it from core (backward compat preserved); errors.py imports from core.exceptions instead of tools.browser.safety - resolves circular import that caused fresh-subprocess ImportError

[[2026-03-19]] Thu 17:30

## Review Evidence

## Review: #860 - Test: clean-process imports after BlockedURLError dependency inversion

### Test Results

- uv run pytest tests/test_blocked_url_error_location.py -q --tb=short: 5 passed, 0 failed (2 optional-dependency warnings).
- uv run pytest tests/test_browser_safety.py -q --tb=short: 21 passed, 0 failed (2 optional-dependency warnings).
- uv run pytest tests/test_daemon_journal_async.py -q --tb=short: 13 passed, 0 failed (2 optional-dependency warnings).
- First browser-safety attempt returned KeyboardInterrupt during pytest startup; immediate diagnostic showed no stale python/pytest processes, and a single retry completed successfully.

### Lint Results

- Repo-wide lint (uv run ruff check src/ tests/) currently fails with 7 pre-existing issues outside this task's files.
- Task-scoped lint on reviewed files passes:
  - src/owlbear/core/exceptions.py
  - src/owlbear/core/errors.py
  - src/owlbear/tools/browser/safety.py
  - ests/test_blocked_url_error_location.py
  - ests/test_daemon_journal_async.py

### Coverage

- Scoped coverage run:
  - Command: uv run pytest tests/test_blocked_url_error_location.py tests/test_browser_safety.py tests/test_daemon_journal_async.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
  - Result: 39 passed
  - src/owlbear/core/exceptions.py: 100%
  - src/owlbear/tools/browser/safety.py: 100%
  - src/owlbear/core/errors.py: 62%
- Note: core/errors.py has pre-existing broad-branch coverage debt; AC-targeted behavior is directly covered by explicit tests below.

### Pass 1 - CRITICAL

#### Security Review

- Hardcoded secrets: none found in reviewed files.
- Injection vectors (SQL/shell/template): no unsafe patterns introduced.
- Path traversal: none introduced.
- Insecure deserialization/eval: none introduced.
- Input validation at boundaries: URL checks remain pattern-gated in URLSafetyGuard.check_url.
- Dependency risk: no new dependencies added.
- Secret leakage via logs/errors: no sensitive-token logging introduced.
- Verdict: No security issues found.

#### Test Integrity (TestFromAC comparison)

- Builder commit for #860 (c2790d8) changes only source files (core/errors.py, core/exceptions.py,  ools/browser/safety.py), with no test-file edits.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_BlockedURLErrorLocation::test_errors_no_import_from_browser_safety | No change (builder commit touched no test files) | PRESERVED |
| TestFromAC_BlockedURLErrorLocation::test_blocked_url_error_module | No change (builder commit touched no test files) | PRESERVED |
| TestFromAC_BlockedURLErrorLocation::test_classify_error_returns_permanent | No change (builder commit touched no test files) | PRESERVED |
| TestFromAC_DaemonCleanImport::test_daemon_import_without_tools_preseeding | No change (builder commit touched no test files) | PRESERVED |
| TestFromAC_DaemonCleanImport::test_daemon_import_config_then_daemon | No change (builder commit touched no test files) | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Tests assert exact module path, exact enum classification, exact subprocess return code + stderr context. |
| Negative/error paths | STRONG | Structural dependency inversion assertion plus subprocess cold-start failure guard rails exercise regression paths. |
| Mutation reasoning | STRONG | Import edge reversal, category misclassification, or daemon import regression would fail specific assertions. |
| Test independence | STRONG | Tests are isolated; subprocess smoke tests avoid shared interpreter-state coupling. |
| Descriptive names | STRONG | Test names explicitly state scenario and expected outcome (e.g.,  est_daemon_import_config_then_daemon). |

#### Data Safety

- Unvalidated LLM output persistence: none in reviewed changes.
- Race-condition risk: none introduced.
- Atomicity/inconsistent state risk: none introduced.
- Unbounded input/resource risk: no new unbounded operations introduced.
- Verdict: No data safety issues found.

### Pass 2 - INFORMATIONAL

- Repo-wide
uff debt exists outside task scope:
  - src/bearclaw/commands/auth.py:34 (BLE001)
  - src/owlbear/tools/screenshot.py:22 (E501)
  - ests/conftest.py:27,39 (RUF100)
  - ests/test_blocked_error_location.py:14,56 (N801)
  - ests/test_loop_detection.py:8 (I001)
- Coverage for src/owlbear/core/errors.py remains below 90%; additional classifier-branch tests would reduce residual risk.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: remove owlbear.tools pre-seeding in  ests/test_daemon_journal_async.py and keep direct daemon import |  ests/test_daemon_journal_async.py:20 imports_log_to_journal directly; search confirms no owlbear.tools string in file | TestFromAC_DaemonCleanImport::test_daemon_import_without_tools_preseeding, TestFromAC_DaemonCleanImport::test_daemon_import_config_then_daemon | PASS |
| AC2: add structural assertion that src/owlbear/core/errors.py does not import owlbear.tools.browser.safety |  ests/test_blocked_url_error_location.py:22 defines structural AST assertion; src/owlbear/core/errors.py has no  ools.browser.safety import | TestFromAC_BlockedURLErrorLocation::test_errors_no_import_from_browser_safety | PASS |
| AC3: BlockedURLError.__module__ == owlbear.core.exceptions and classify_error(...) == PERMANENT | src/owlbear/core/exceptions.py:17 defines BlockedURLError; src/owlbear/core/errors.py:33 imports it from core; targeted tests passed | TestFromAC_BlockedURLErrorLocation::test_blocked_url_error_module, TestFromAC_BlockedURLErrorLocation::test_classify_error_returns_permanent | PASS |
| AC4: clean-subprocess import of owlbear.daemon without tools pre-seeding | Subprocess smoke test present at  ests/test_blocked_url_error_location.py:56; pytest pass confirms return code 0 | TestFromAC_DaemonCleanImport::test_daemon_import_without_tools_preseeding | PASS |
| AC5: clean-subprocess import owlbear.config then owlbear.daemon without pre-seeding | Subprocess smoke test present at  ests/test_blocked_url_error_location.py:74; pytest pass confirms return code 0 | TestFromAC_DaemonCleanImport::test_daemon_import_config_then_daemon | PASS |
| AC6: existing browser safety coverage remains green | uv run pytest tests/test_browser_safety.py -q --tb=short -> 21 passed |  ests/test_browser_safety.py suite | PASS |
| AC7: task-specific tests were RED before #850 implementation | Task body ## Test-Writer Notes (2026-03-19 16:14) records 5 failing tests in  ests/test_blocked_url_error_location.py prior to implementation | Historical RED evidence from test-writer gate | PASS |

### Verdict: PASS

- Confidence: .91

### Action Taken

- Appended this ## Review Evidence section.

[[2026-03-19]] Thu 18:30

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Errors row already documents exceptions in \owlbear.core.exceptions\ -- BlockedURLError now lives there; no convention change |
| 2 | Docstrings complete | Yes | Pass | exceptions.py: module + OwlBearError + BlockedURLError all have full docstrings; safety.py: module + URLSafetyGuard complete; errors.py: module + all public classes complete |
| 3 | docs/sources/overview.md | No | N/A | #860 is a test task; attribution for the dependency inversion patterns was already added for #850 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for #860; blockedurlerror-dependency-inversion.md was produced for #850 and linked there |

### Files Updated

- None

### Scratch Files Cleaned

- None (no docs/scratch/860-* files found)

[[2026-03-20]] Fri 12:29

## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC1: remove owlbear.tools pre-seeding from test_daemon_journal_async.py | grep confirms no 'owlbear.tools' string in file; L20 imports_log_to_journal directly | PASS |\n| AC2: errors.py must not import tools.browser.safety | grep confirms no 'tools.browser.safety' in errors.py; AST test validates at runtime | PASS |\n| AC3: BlockedURLError.__module__ == owlbear.core.exceptions + classify_error PERMANENT | core/exceptions.py:17 defines BlockedURLError; errors.py:33 imports from core; tests pass | PASS |\n| AC4: fresh subprocess imports owlbear.daemon without tools pre-seeding | test_daemon_import_without_tools_preseeding passes (subprocess rc=0) | PASS |\n| AC5: fresh subprocess imports config then daemon with no pre-seeding | test_daemon_import_config_then_daemon passes (subprocess rc=0) | PASS |\n| AC6: browser safety tests remain green | 21 passed in test_browser_safety.py | PASS |\n| AC7: tests fail before #850 (TDD red) | Test-Writer Notes confirm 5 FAILED prior to implementation | PASS |\n\n### Test Results\n- Task-scoped: 39 passed, 0 failed (test_blocked_url_error_location + test_browser_safety + test_daemon_journal_async)\n- Full suite: pre-existing failures in unrelated modules (numpy compat, other in-progress tasks); no regressions from #860\n- ruff: all task-scoped files clean\n\n### Confidence: .97\n### Action: archive\n\n### Quality Note\nTest-writer and builder failed to commit test deliverables. Auditor committed orphaned test files (9a6768a)

[[2026-03-20]] Fri 12:29

## Commits\n| Commit | Type | Files | Tasks |\n|--------|------|-------|-------|\n| 9a6768a | test | tests/test_blocked_url_error_location.py, tests/test_daemon_journal_async.py | #860 |
