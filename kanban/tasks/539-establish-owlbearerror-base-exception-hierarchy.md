---
id: 539
title: Establish OwlBearError base exception hierarchy
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:44.0984756+01:00
updated: 2026-03-10T02:04:42.7862231+01:00
started: 2026-03-07T00:36:39.5359602+01:00
tags:
    - audit
    - resilience
    - scope:core
blocked: true
block_reason: No implementation found. All 7 AC items fail. Only research docs exist. Task reached done without any code changes.
class: standard
---

E-1: Only 3 custom exceptions (BlockedCommandError, BlockedURLError, AskUserTimeoutError), no base class. Makes blanket catching difficult without except Exception. Create OwlBearError base class.

Research complete. See docs/owlbear-error-hierarchy-research.md.

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
