---
id: 469
title: Add ConnectError and TimeoutException to Copilot transport retry
status: archived
priority: needed
created: 2026-03-04T07:37:49.018614+01:00
updated: 2026-03-06T19:28:16.5625213+01:00
started: 2026-03-06T11:49:08.0158141+01:00
completed: 2026-03-06T19:28:16.5625213+01:00
tags:
    - audit
    - resilience
    - auth
class: standard
---

## Fix
Change the etry= argument in _build_retry_transport() (`src/owlbear/providers/copilot.py` line 58) from:
`python
retry=retry_if_exception_type(httpx.HTTPStatusError)
`
to:
`python
retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException))
`

Update the docstring of _build_retry_transport()  replace 'Only retries httpx.HTTPStatusError (transient codes)' with 'Retries httpx.HTTPStatusError (transient codes), httpx.ConnectError, and httpx.TimeoutException'.

## Acceptance Criteria
- [ ] _build_retry_transport() returns a transport whose config['retry'] matches httpx.HTTPStatusError, httpx.ConnectError, **and** httpx.TimeoutException
- [ ] _build_retry_transport() docstring lists all three exception types
- [ ] Existing retry behavior for transient HTTP status codes (429, 502, 503, 504) is unchanged  _validate_transient_response not modified
- [ ] Existing test 	est_retry_only_on_http_status_error renamed to 	est_retry_covers_transient_exception_types and asserts all three types
- [ ] New test: 	est_connect_error_triggers_retry  builds transport with a mock inner transport that raises httpx.ConnectError twice then succeeds; asserts 3 calls total
- [ ] New test: 	est_timeout_exception_triggers_retry  same pattern with httpx.TimeoutException
- [ ] uv run pytest tests/test_providers_copilot.py -q --tb=short all green
- [ ] uv run ruff check src/owlbear/providers/copilot.py clean

## Architecture Notes
- etry_if_exception_type accepts a tuple  no OR-combinator needed.
- httpx.TimeoutException is the base class for all httpx timeout errors (ReadTimeout, WriteTimeout, PoolTimeout, ConnectTimeout). Catching the base is intentional.
- httpx.ConnectError covers DNS failures, connection refused, TLS handshake errors.
- _validate_transient_response is unrelated  it only governs which HTTP **status codes** become HTTPStatusError. Network-level exceptions never reach that callback.
- Aligns with core/errors.py classify_error() which already classifies ConnectError and TimeoutException as TRANSIENT.
