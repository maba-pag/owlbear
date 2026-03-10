---
id: 512
title: Reconcile daemon retry with tool-level HookedToolset retry
status: archived
priority: important
created: 2026-03-04T07:38:23.8578187+01:00
updated: 2026-03-09T21:58:17.4794145+01:00
started: 2026-03-06T23:40:09.5092711+01:00
completed: 2026-03-09T21:58:17.4794145+01:00
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

[[2026-03-09]] Mon 21:58
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| daemon TRANSIENT path only retries model-level errors | daemon.py L305-310: guard checks `_tool_retries_exhausted` attr OR `not isinstance(exc, httpx.HTTPStatusError)`  only HTTPStatusError (429/502/503/504) proceeds to retry loop | PASS |
| Tool-level transients propagate as-is after exhaustion | hooked.py L85-91: `_mark_tool_exhausted` sets `_tool_retries_exhausted=True` on exc, then re-raises. daemon.py L305 checks this attr and returns without retry | PASS |
| Mechanism: classify_error or wrapper distinguishes model vs tool | Two-part mechanism: (1) hooked.py `retry_error_callback=_mark_tool_exhausted` sets `_tool_retries_exhausted` attr, (2) daemon.py checks attr + isinstance(httpx.HTTPStatusError) gate | PASS |
| Max total attempts for any single transient = 3, not 9 | HookedToolset: `_MAX_ATTEMPTS=3` (tool). Daemon: `_TRANSIENT_MAX_RETRIES=3` (model). Guard prevents both from firing on same error. test_no_multiplicative_retries asserts call_count==1 for tool-exhausted | PASS |
| `_TRANSIENT_MAX_RETRIES`, `_TRANSIENT_BACKOFF_BASE` removed or repurposed | daemon.py L67-70: constants retained with comment `apply only to model-level transients (#512)`  used in daemon retry loop for model-level errors. Not dead config | PASS |
| All existing daemon tests pass | 70 passed in test_daemon.py; 6 #512-specific tests (TestDaemonRetryReconciliation + TestTransientExhaustedChannelSendFails) all pass | PASS |
| ruff clean | `ruff check src/owlbear/daemon.py src/owlbear/tools/hooked.py src/owlbear/core/errors.py`  All checks passed | PASS |

### Test Results
- pytest: test_daemon.py 70 passed; test_hooked_toolset.py + test_error_classification.py + test_error_recovery.py + test_circuit_breaker.py 96 passed
- ruff: clean on task-specific files (3 pre-existing errors in unrelated files)

### Confidence: .97
### Action: archive
