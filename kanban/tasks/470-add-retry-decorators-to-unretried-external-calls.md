---
id: 470
title: Add retry decorators to unretried external calls
status: archived
priority: needed
created: 2026-03-04T07:37:49.872598+01:00
updated: 2026-03-06T19:28:17.0491368+01:00
started: 2026-03-06T11:55:44.6920615+01:00
completed: 2026-03-06T19:28:17.0491368+01:00
tags:
    - audit
    - resilience
    - scope:core
blocked: true
block_reason: 'Umbrella  waiting on sub-tasks #600, #601, #602, #603, #604'
class: standard
---

**Umbrella task  split into atomic sub-tasks by the architect.**

Original scope: wrap all unretried external HTTP calls with tenacity retry. Split because it touches 5 modules with 3 different retry mechanisms (tenacity decorator, tenacity on extracted helper, Slack SDK handler).

### Sub-tasks
- #600  Create `core/retry.py` shared transient retry decorator (prerequisite)
- #601  Apply to `auth/copilot.py` (depends on #600)
- #602  Apply to `github_api.py` via `_api_request` helper (depends on #600)
- #603  Enable Slack SDK `RateLimitErrorRetryHandler` (independent, no tenacity)
- #604  Apply to `intake.py` + `web_search.py` (depends on #600)

### Done when
All 5 sub-tasks are done. This task can then be closed.

See `docs/research/retry-decorators.md` for full analysis.
