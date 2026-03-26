---
id: 548
title: Move BlockedCommandError to core/errors.py
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:51.556187+01:00
updated: 2026-03-22T19:17:41.4504014+01:00
started: 2026-03-07T00:49:54.4409806+01:00
completed: 2026-03-22T19:17:41.4504014+01:00
tags:
    - audit
    - architecture
    - scope:core
blocked: true
block_reason: 'Stale task: change already implemented in repo and covered by tests; see commit 55faf0e and Architecture Review.'
class: standard
---

## Research (N/A  trivial move)

**Problem:** `errors.py` imports `BlockedCommandError` from `command_guard`  inverted dependency (errors depends on command_guard).

**Fix:** Move `BlockedCommandError` class (15 LOC) from `command_guard.py`  `errors.py`. Update `command_guard.py` to import from `errors`. Update 4 other import sites. No re-export needed.

**Import sites to update (5 total):**
- `src/owlbear/core/errors.py:32`  delete import (class now local)
- `src/owlbear/core/command_guard.py`  add `from owlbear.core.errors import BlockedCommandError`
- `src/owlbear/tools/hooked.py:41`  change to import from `owlbear.core.errors`
- `tests/test_command_guard.py:15`  change to import from `owlbear.core.errors`
- `tests/test_error_classification.py:14`  change to import from `owlbear.core.errors`
- `tests/test_error_recovery.py:22`  change to import from `owlbear.core.errors`

**AC:** No circular/inverted dependency. `command_guard`  `errors` (correct direction).

[[2026-03-21]] Sat 03:54
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| No circular/inverted dependency. `command_guard` -> `errors` (correct direction). | Already satisfied in the current repo: `src/owlbear/core/errors.py` defines `BlockedCommandError`; `src/owlbear/core/command_guard.py` imports it from `owlbear.core.errors`; `tests/test_blocked_error_location.py` verifies both conditions; `git log` shows `55faf0e refactor: move BlockedCommandError to core/errors.py (#548, builder)`. No implementation work remains. | Do not route to builder. Mark as stale/already-implemented board work. |

### Architecture Notes
- `core/errors.py` already owns `BlockedCommandError`, matching the core error-taxonomy pattern.
- `command_guard.py` already depends on `errors.py`; the inverted import described in the task no longer exists.
- The executable contract already exists in `tests/test_blocked_error_location.py`, but there is no active preceding RED task on the board for #548. Approving this task to `todo` would violate TDD flow and create duplicate no-op work.
- Related archived work confirms the area is already resolved: #539 documents the interaction with #548, and repository history contains an explicit #548 implementation commit.

### Changes Made
- Appended architecture review with repo-state and git-history evidence.
- Prepared the task for stale-card triage instead of builder dispatch.

### Dependencies
- Verified: no unresolved code dependency remains for the original change.
- Verified: no active TDD predecessor exists for #548; current tests already cover the landed behavior in `tests/test_blocked_error_location.py`.
