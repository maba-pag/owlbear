---
id: 512
title: Reconcile daemon retry with tool-level HookedToolset retry
status: done
priority: important
created: 2026-03-04T07:38:23.8578187+01:00
updated: 2026-03-08T02:52:39.3650456+01:00
started: 2026-03-06T23:40:09.5092711+01:00
completed: 2026-03-08T02:52:39.3650456+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

R-3 from docs/resilience-audit.md: daemon.py _recover_from_error() reimplements exp backoff (3 retries, base 1s) while HookedToolset already retries transient errors (3 attempts, base 0.5s). A transient tool error gets 3x3=9 total attempts. Clarify retry responsibilities and eliminate multiplicative retries.

See docs/resilience-audit.md R-3.

## Architecture Decision

Two layers serve different purposes:
- HookedToolset (inner): retries individual TOOL calls (httpx, subprocess, etc.)
- daemon _recover_from_error (outer): retries the full agent.turn() for MODEL-level errors (Copilot 503, timeout)

The fix: daemon transient retry should NOT retry when the error originated from a tool call (already retried by HookedToolset). Daemon retry should only fire for model-level transient errors (from agent.run/turn itself, not from tool execution).

## Acceptance Criteria

- [ ] daemon _recover_from_error TRANSIENT path only retries errors that originate from the model call (e.g. Copilot HTTP 503 during agent.turn), not from tool execution
- [ ] Tool-level transient errors retried by HookedToolset propagate as-is after exhaustion (no second retry layer in daemon)
- [ ] Mechanism: classify_error or a wrapper distinguishes model-level vs tool-level transient errors (e.g. check if exception is a RetryError from tenacity wrapping a transient, or add an attribute/subclass)
- [ ] Maximum total attempts for any single transient failure is 3 (not 9)
- [ ] _TRANSIENT_MAX_RETRIES, _TRANSIENT_BACKOFF_BASE constants in daemon.py are removed or repurposed (no dead config)
- [ ] All existing daemon tests pass unchanged or updated
- [ ] ruff clean
