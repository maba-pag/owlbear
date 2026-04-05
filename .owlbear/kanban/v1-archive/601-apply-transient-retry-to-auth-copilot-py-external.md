---
id: 601
title: Apply TRANSIENT_RETRY to auth/copilot.py external calls
status: archived
priority: needed
created: 2026-03-06T12:12:51.9328861+01:00
updated: 2026-03-06T19:28:29.3975214+01:00
started: 2026-03-06T13:45:10.8053925+01:00
completed: 2026-03-06T19:28:29.3975214+01:00
tags:
    - resilience
    - auth
depends_on:
    - 600
class: standard
---

Decorate `request_device_code` and `exchange_for_copilot_token` in `auth/copilot.py` with `TRANSIENT_RETRY` from `core/retry.py`.

### AC
- [ ] `request_device_code` decorated with `TRANSIENT_RETRY`  retries on `ConnectError`, `TimeoutException`, transient `HTTPStatusError`
- [ ] `exchange_for_copilot_token` decorated with `TRANSIENT_RETRY`
- [ ] `poll_for_access_token` is NOT decorated (has its own polling loop)
- [ ] Existing `httpx.Timeout(10, connect=5)` kwargs remain unchanged
- [ ] Test: `respx` mock returning 502 twice then 200  verify 3 calls made, success returned
- [ ] Test: `respx` mock returning 401  verify 1 call only (non-transient), exception propagates
- [ ] Import path: `from owlbear.core.retry import TRANSIENT_RETRY`

### Architecture notes
- Both functions use `async with httpx.AsyncClient()` context managers  decorate the outer function, not the inner HTTP call
- `poll_for_access_token` excluded per research §3.5 (own retry loop)
- See `docs/research/retry-decorators.md`
