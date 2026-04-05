---
id: 600
title: Create core/retry.py shared transient retry decorator
status: archived
priority: needed
created: 2026-03-06T12:12:41.5640051+01:00
updated: 2026-03-06T19:28:28.9324336+01:00
started: 2026-03-06T12:52:10.1938841+01:00
completed: 2026-03-06T19:28:28.9324336+01:00
tags:
    - resilience
    - scope:core
class: standard
---

Create `src/owlbear/core/retry.py` exporting:
- `TRANSIENT_RETRY`  pre-configured `@retry` decorator for `async` functions making external HTTP calls.
- `_is_transient_http(exc)`  predicate using `classify_error` from `core/errors.py`.

### AC
- [ ] `core/retry.py` exists with `TRANSIENT_RETRY` exported in `__all__`
- [ ] Policy: `stop_after_attempt(3)`, `wait_exponential_jitter(initial=1, max=30, jitter=5)`, `reraise=True`
- [ ] Predicate: returns `True` for `httpx.ConnectError`, `httpx.TimeoutException`, `httpx.HTTPStatusError` with status in {429, 502, 503, 504}; `False` for all other exceptions
- [ ] `before_sleep` logs at WARNING with function name and attempt number (use `before_sleep_log(logger, logging.WARNING)`)
- [ ] `retry` kwarg uses `retry_if_exception(_is_transient_http)`
- [ ] Unit test `tests/test_retry.py`: verify predicate returns correct bool for each exception type; verify decorator retries a mock async function that fails twice then succeeds (3 calls total); verify non-transient exception propagates immediately (1 call only)
- [ ] Follows existing pattern from `tools/hooked.py` (`_is_transient` + tenacity constants)

### Architecture notes
- Reuses `classify_error` from `core/errors.py` to stay DRY with `ErrorCategory`
- Module is pure infrastructure  no side effects, no I/O beyond logging
- See `docs/research/retry-decorators.md` §4
