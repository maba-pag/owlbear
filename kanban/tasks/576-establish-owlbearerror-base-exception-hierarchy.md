---
id: 576
title: Establish OwlBearError base exception hierarchy
status: archived
priority: nice-to-have
created: 2026-03-04T07:39:54.4286877+01:00
updated: 2026-03-13T09:10:30.3233711+01:00
started: 2026-03-07T04:13:47.9056856+01:00
completed: 2026-03-13T09:10:30.3233711+01:00
tags:
    - audit
    - resilience
    - scope:core
blocked: true
block_reason: 'Duplicate of #539 (already in backlog). Close or merge.'
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
