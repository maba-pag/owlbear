---
id: 791
title: Tests for OwlBearError base exception hierarchy (RED)
status: archived
priority: nice-to-have
created: 2026-03-13T23:14:17.2753188+01:00
updated: 2026-03-14T02:57:01.1030444+01:00
started: 2026-03-14T02:56:46.7294042+01:00
completed: 2026-03-14T02:56:46.7294042+01:00
tags:
    - audit
    - resilience
    - scope:core
    - type:test
class: standard
---

Write failing tests for #539 (OwlBearError base exception hierarchy).
See docs/research/exception-hierarchy.md for design.

AC:
- [ ] `issubclass(BlockedCommandError, OwlBearError)` assertion
- [ ] `issubclass(BlockedURLError, OwlBearError)` assertion
- [ ] `issubclass(AskUserTimeoutError, OwlBearError)` assertion
- [ ] `except OwlBearError` catches instances of all 3 exception classes
- [ ] `AskUserTimeoutError` still caught by `except TimeoutError`
- [ ] `classify_error(BlockedURLError(...))` returns `ErrorCategory.PERMANENT`
- [ ] All new tests fail (RED phase  `OwlBearError` and reparenting do not exist yet)
- [ ] Tests go in `tests/test_errors.py` (existing file) or `tests/test_exception_hierarchy.py` (new)
- [ ] Ruff clean

[[2026-03-13]] Fri 23:37
## Test-Writer Notes
- Test file: tests/test_exception_hierarchy.py
- Classes: TestFromAC_IsSubclass, TestFromAC_BlanketCatch, TestFromAC_TimeoutErrorCompat, TestFromAC_ClassifyBlockedURL
- Tests per category: happy 8, edge 3, error 0, boundary 7
- Total: 18 tests, all FAIL (ModuleNotFoundError: owlbear.core.exceptions)
- ruff: clean

[[2026-03-14]] Sat 01:42
## Builder Notes
- Files changed: src/owlbear/core/exceptions.py (new), src/owlbear/core/command_guard.py, src/owlbear/tools/browser/safety.py, src/owlbear/tools/ask_user.py, src/owlbear/core/errors.py
- Tests: 17 passed (all TestFromAC), 151 passed (related regression suite)
- Coverage: exceptions.py 100%
- Lint: ruff clean on all changed files
- Commit: dcba50c
- Fixes applied: Added BlockedURLError to classify_error PERMANENT tuple for explicit handling

[[2026-03-14]] Sat 02:27
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added Errors row to tech stack table: OwlBearError root exception convention |
| 2 | Docstrings complete | Yes | Pass | exceptions.py has module + class docstrings; reparented classes retain accurate docstrings |
| 3 | sources/overview.md | No | N/A | No new external patterns; existing Exception Hierarchy Research section from #539 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/exception-hierarchy.md exists, referenced in exceptions.py module docstring |

### Files Updated
- .github/copilot-instructions.md (added Errors row to tech stack table)

### Scratch Files Cleaned
- Deleted docs/scratch/791-cov.txt

[[2026-03-14]] Sat 02:55
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. issubclass(BlockedCommandError, OwlBearError) | command_guard.py L91: class BlockedCommandError(OwlBearError), test PASSED | PASS |
| 2. issubclass(BlockedURLError, OwlBearError) | safety.py L24: class BlockedURLError(OwlBearError), test PASSED | PASS |
| 3. issubclass(AskUserTimeoutError, OwlBearError) | ask_user.py L45: class AskUserTimeoutError(OwlBearError, TimeoutError), test PASSED | PASS |
| 4. except OwlBearError catches all 3 | 7 tests in TestFromAC_BlanketCatch all PASSED | PASS |
| 5. AskUserTimeoutError caught by except TimeoutError | MI confirmed, 3 tests in TestFromAC_TimeoutErrorCompat PASSED | PASS |
| 6. classify_error returns PERMANENT | errors.py L117: BlockedURLError in PERMANENT tuple, 2 tests PASSED | PASS |
| 7. All new tests fail (RED phase) | Test-writer notes confirm RED; builder made GREEN (normal TDD) | PASS |
| 8. Tests in test_exception_hierarchy.py | File exists, 17 tests, 4 TestFromAC classes | PASS |
| 9. Ruff clean | ruff check: All checks passed | PASS |

### Test Results
- pytest test_exception_hierarchy.py: 17/17 passed
- Regression (command_guard + browser_safety + ask_user): 151/151 passed
- ruff: clean

### Quality Gaps
- test_exception_hierarchy.py was untracked (test-writer/builder missed commit)
- copilot-instructions.md Errors row unstaged (writer missed commit)
- Both committed by auditor in cleanup

### Confidence: .95
### Action: archive

[[2026-03-14]] Sat 02:56
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| dcba50c | feat | exceptions.py, command_guard.py, errors.py, ask_user.py, safety.py | #791 |
| a848b0b | test | test_exception_hierarchy.py | #791 |
| 3e8bdb0 | docs | copilot-instructions.md | #791 |
