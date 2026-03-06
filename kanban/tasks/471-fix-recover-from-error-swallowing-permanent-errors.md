---
id: 471
title: Fix _recover_from_error swallowing PERMANENT errors
status: archived
priority: needed
created: 2026-03-04T07:37:50.703621+01:00
updated: 2026-03-06T19:28:17.5216579+01:00
started: 2026-03-06T11:59:31.0587956+01:00
completed: 2026-03-06T19:28:17.5216579+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

## Problem
In src/owlbear/daemon.py, _recover_from_error() has 3 terminal channel.send() calls that report errors to the user. If the channel is dead (e.g. Slack socket disconnected), the channel.send() raises, and the **original error is silently lost**  no log, no fallback.

Affected lines (current):
1. L225: transient-retries-exhausted path  wait channel.send(f'Error: {last_exc}')`n2. L234: auth-refresh-failed path  wait channel.send(f'Error: {retry_exc}')`n3. L238: permanent/tool-semantic path  wait channel.send(f'Error: {exc}')`n
## Approach
Wrap each of the 3 terminal channel.send() calls in its own 	ry/except Exception with logger.exception() fallback that logs the **original error** (not just the channel failure).

Do **not** introduce ErrorJournal here  that is a separate concern and not yet wired into daemon.py.

## Acceptance Criteria
- [ ] AC1: Each of the 3 terminal channel.send() calls in _recover_from_error is wrapped in 	ry/except Exception.
- [ ] AC2: Each except block calls logger.exception() with a message that includes the **original** exception (the one being reported, not the channel failure).
- [ ] AC3: The channel failure exception is also logged (it is the exc_info on logger.exception).
- [ ] AC4: No exception propagates out of _recover_from_error  the function always returns None.
- [ ] AC5: Existing behavior is preserved when channel.send() succeeds (error message still sent to channel).
- [ ] AC6: Tests: patch channel.send to raise, verify logger.exception is called with original error context. One test per error category (TRANSIENT exhausted, AUTH failed, PERMANENT).
- [ ] AC7: ruff clean, no new lint warnings.

## Architecture Notes
- Pattern: simple try/except guard, no new imports or dependencies.
- Follow existing logger usage in daemon.py (logger = logging.getLogger(__name__)).
- Do not change the retry logic or backoff behavior  only guard the final send calls.

Ref: docs/resilience-audit.md
