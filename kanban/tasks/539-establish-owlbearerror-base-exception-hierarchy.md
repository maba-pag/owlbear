---
id: 539
title: Establish OwlBearError base exception hierarchy
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:44.0984756+01:00
updated: 2026-03-15T05:03:06.3884805+01:00
started: 2026-03-07T00:36:39.5359602+01:00
completed: 2026-03-15T05:02:48.3433323+01:00
tags:
    - audit
    - resilience
    - scope:core
depends_on:
    - 791
blocked: true
block_reason: No implementation found. All 7 AC items fail. Only research docs exist. Task reached done without any code changes.
class: standard
---

E-1: Only 3 custom exceptions (BlockedCommandError, BlockedURLError, AskUserTimeoutError), no base class. Makes blanket catching difficult without except Exception. Create OwlBearError base class.

Research complete. See docs/research/owlbear-error-hierarchy.md.

**Recommendation (.90 confidence):** Single OwlBearError(Exception) base in core/exceptions.py. All 3 exceptions inherit from it. AskUserTimeoutError uses (OwlBearError, TimeoutError) for MRO compat. No subcategories (YAGNI).

**Bonus fix:** classify_error() should explicitly handle BlockedURLError (currently falls through to default).

AC:
- [ ] OwlBearError(Exception) defined in core/exceptions.py
- [ ] All 3 custom exceptions inherit from OwlBearError
- [ ] except OwlBearError catches all 3
- [ ] AskUserTimeoutError still caught by except TimeoutError
- [ ] classify_error() explicitly handles BlockedURLError
- [ ] Tests verify hierarchy with issubclass assertions
- [ ] Ruff clean, all tests pass

[[2026-03-10]] Tue 02:04
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| OwlBearError(Exception) defined in core/exceptions.py | No such file exists | FAIL |
| All 3 exceptions inherit from OwlBearError | All unchanged: Exception/TimeoutError | FAIL |
| except OwlBearError catches all 3 | OwlBearError does not exist | FAIL |
| AskUserTimeoutError still caught by except TimeoutError | Unchanged, trivially true | N/A |
| classify_error() handles BlockedURLError | No BlockedURLError in core/errors.py | FAIL |
| Tests verify hierarchy with issubclass | No issubclass tests for OwlBearError | FAIL |
| Ruff clean, all tests pass | No code changes | N/A |

### Confidence: .10
### Action: reject to backlog - zero implementation, only research docs exist

[[2026-03-13]] Fri 23:15
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| OwlBearError(Exception) in core/exceptions.py | Specific, verifiable. Leaf module avoids circular deps (errors.py -> command_guard.py cycle). | Keep |
| BlockedCommandError(OwlBearError) | Named explicitly, location specified. | Keep |
| BlockedURLError(OwlBearError) | Named explicitly, location specified. | Keep |
| AskUserTimeoutError(OwlBearError, TimeoutError) | MI pattern matches httpx/requests precedent. MRO trivial. | Keep |
| classify_error() handles BlockedURLError | Currently falls through to default PERMANENT. Making explicit is correct. | Keep |
| OwlBearError re-exported from core/__init__.py | Added during review. Root exception should be importable from core. | Added |
| Tests from #791 pass | TDD GREEN phase. Depends on #791. | Keep |
| Ruff clean, full suite passes | Standard gate. | Keep |

### Architecture Notes
- **Leaf module pattern:** core/exceptions.py must have zero owlbear imports. This breaks the potential cycle: core/errors.py imports BlockedCommandError from core/command_guard.py. If OwlBearError lived in errors.py, command_guard.py would import from errors.py -> circular.
- **MI precedent:** requests library uses same pattern (ConnectTimeout(ConnectionError, Timeout)). Python C3 MRO handles this trivially.
- **Scope boundary:** Only 3 of 8 custom exceptions are reparented. The other 5 (BudgetExceededError, CircuitOpenError, LintGateError, DiagramError, ContentInjectionError) are out of scope but could be a follow-up if full blanket-catch coverage is desired.
- **Interaction with #548:** Task #548 proposes moving BlockedCommandError to core/errors.py. These tasks are independent  #539 works regardless of #548 order.

### Changes Made
- Refined AC: named all 3 exceptions explicitly, added core/__init__.py re-export requirement
- Created #791 (test task, RED phase) at todo status
- Added depends_on #791 for TDD compliance
- Noted 5 additional exceptions as out-of-scope

### Dependencies
- Added: #791 (Tests for OwlBearError hierarchy)  preceding test task
- Verified: no other deps needed. core/exceptions.py is a new leaf module.

[[2026-03-14]] Sat 04:28
## Test-Writer Notes
- Test file: tests/test_exception_hierarchy.py (extended)
- Classes: TestFromAC_IsSubclass (#791), TestFromAC_BlanketCatch (#791), TestFromAC_TimeoutErrorCompat (#791), TestFromAC_ClassifyBlockedURL (#791), TestFromAC_CoreReExport (NEW)
- Tests per category: happy 1, edge 1, boundary 1
- Total: 20 tests (17 pass from #791 impl, 3 NEW FAIL)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| OwlBearError(Exception) in core/exceptions.py | test_owlbear_error_is_subclass_of_exception (#791) | happy |
| All 3 inherit from OwlBearError | test_blocked_*_is_subclass, test_ask_user_timeout_error_is_subclass (#791) | happy |
| except OwlBearError catches all 3 | test_catches_*, test_isinstance_* (#791) | happy/edge |
| AskUserTimeoutError caught by except TimeoutError | test_is_subclass_of_timeout_error, test_caught_by_except_timeout_error, test_is_both (#791) | happy/edge |
| classify_error() handles BlockedURLError | test_classify_blocked_url_error_* (#791) | happy/edge |
| OwlBearError re-exported from core/__init__.py | test_importable_from_owlbear_core, test_in_core_all, test_identity_with_exceptions_module (NEW, FAIL) | happy/edge/boundary |
| Tests verify hierarchy with issubclass | covered by TestFromAC_IsSubclass (#791) | happy |

[[2026-03-14]] Sat 04:57
## Builder Notes
- Files changed: src/owlbear/core/__init__.py (2 lines added: import + __all__ entry)
- Tests: 20 passed (17 from #791 + 3 new CoreReExport), 0 failed
- Coverage: exceptions.py 100%, core/__init__.py 100%
- Lint: ruff clean
- Commit: e2a89d0

[[2026-03-14]] Sat 12:54
## Review Evidence

### Test Results
- pytest: 20 passed, 0 failed (tests/test_exception_hierarchy.py)

### Lint Results
- ruff: All checks passed! (7 files checked)

### Coverage
- core/exceptions.py: 100%
- core/__init__.py: 100%
- core/errors.py: 64% (misses in unrelated branches)

### Pass 1 -- CRITICAL

#### Security Review
- No security issues. Pure class hierarchy change, no I/O, no user input, no secrets.

#### Test Integrity
- Test file created in a848b0b (auditor commit for #791). Builder (e2a89d0) never touched it.
- git diff a848b0b..HEAD tests/test_exception_hierarchy.py: empty

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_IsSubclass (5 methods) | No change | PRESERVED |
| TestFromAC_BlanketCatch (7 methods) | No change | PRESERVED |
| TestFromAC_TimeoutErrorCompat (3 methods) | No change | PRESERVED |
| TestFromAC_ClassifyBlockedURL (2 methods) | No change | PRESERVED |
| TestFromAC_CoreReExport (3 methods) | No change | PRESERVED |

#### Test Quality
| Dimension | Rating |
|---|---|
| Assertion specificity | STRONG |
| Negative/error paths | STRONG |
| Mutation reasoning | STRONG |
| Test independence | STRONG |
| Descriptive names | STRONG |

#### Data Safety
- No data safety issues. Pure type hierarchy, no persistence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| OwlBearError(Exception) in core/exceptions.py | exceptions.py L13: class OwlBearError(Exception) | test_owlbear_error_is_subclass_of_exception | PASS |
| All 3 inherit from OwlBearError | command_guard.py L91, safety.py L25, ask_user.py L46 | TestFromAC_IsSubclass (3 tests) | PASS |
| except OwlBearError catches all 3 | 7 tests in TestFromAC_BlanketCatch | TestFromAC_BlanketCatch | PASS |
| AskUserTimeoutError caught by except TimeoutError | ask_user.py L46: (OwlBearError, TimeoutError) | TestFromAC_TimeoutErrorCompat (3 tests) | PASS |
| classify_error() handles BlockedURLError | errors.py L118: BlockedURLError in PERMANENT tuple | TestFromAC_ClassifyBlockedURL (2 tests) | PASS |
| Tests verify hierarchy with issubclass | TestFromAC_IsSubclass has 5 issubclass assertions | TestFromAC_IsSubclass | PASS |
| Ruff clean, all tests pass | ruff: All checks passed, pytest: 20/20 | -- | PASS |

### Verdict: PASS
### Confidence: .95

[[2026-03-15]] Sun 04:37
## Docs Gate
Checklist:

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Pass | Errors row already present at L55 with OwlBearError root exception, MI pattern, module path |
| 2 | Docstrings complete | Yes | Pass | core/exceptions.py: module + class docstring. BlockedCommandError, BlockedURLError, AskUserTimeoutError all have docstrings |
| 3 | sources/overview.md | Yes | Pass | Section 'Exception Hierarchy Research (Task #539)' present with 4 sources (httpx, requests, click, django) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/exception-hierarchy.md exists, linked from exceptions.py docstring and copilot-instructions.md |
| 6 | No impact | N/A | N/A | Items 1-3,5 apply |

Files Updated: None (all docs already current)
Scratch Files Cleaned: None found (docs/scratch/539-* empty)

[[2026-03-15]] Sun 05:02
## Audit (2026-03-15)
### AC Verification
- OwlBearError(Exception) in core/exceptions.py L13: PASS
- All 3 inherit: command_guard.py L91, safety.py L24, ask_user.py L45: PASS
- except OwlBearError catches all 3: 7 tests PASS
- AskUserTimeoutError TimeoutError compat: MI + 3 tests PASS
- classify_error() handles BlockedURLError: errors.py L117 PASS
- issubclass tests: 5 assertions PASS
- Ruff clean + pytest 20/20: PASS

### Test Results
- pytest: 20 passed (test_exception_hierarchy.py)
- ruff: All checks passed

### Confidence: .97
### Action: archive
