---
id: 548
title: Move BlockedCommandError to core/errors.py
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:51.556187+01:00
updated: 2026-03-07T00:51:11.9873626+01:00
started: 2026-03-07T00:49:54.4409806+01:00
tags:
    - audit
    - architecture
    - scope:core
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
