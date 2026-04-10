---
id: 604
title: Apply TRANSIENT_RETRY to intake.py read_url and web_search.py _web_read
status: archived
priority: needed
created: 2026-03-06T12:13:37.9728671+01:00
updated: 2026-03-06T19:28:35.3575416+01:00
started: 2026-03-06T14:19:50.5586022+01:00
completed: 2026-03-06T19:28:35.3575416+01:00
tags:
    - resilience
    - knowledge
depends_on:
    - 600
class: standard
---

Decorate `intake.read_url` with `TRANSIENT_RETRY`. In `web_search._web_read`, extract the `httpx.AsyncClient.get` call into a decorated inner function so the existing error-string-return pattern is preserved.

### AC
- [ ] `intake.read_url` decorated with `TRANSIENT_RETRY`  retries on transient HTTP/connection errors
- [ ] `web_search._web_read`: HTTP fetch extracted into `_fetch_url(url: str) -> httpx.Response` (or similar), decorated with `TRANSIENT_RETRY`
- [ ] `_web_read` outer function still returns error strings (`'Timeout fetching {url}'`, `'HTTP {status}: ...'`)  not changed
- [ ] Existing `httpx.Timeout(30, connect=5)` in `intake.py` preserved
- [ ] Existing `timeout=30, follow_redirects=True` in `web_search.py` preserved
- [ ] Test (intake): `respx` mock returning 502 twice then 200  verify `IntakeResult` returned with correct content
- [ ] Test (web_search): `respx` mock returning `ConnectError` once then 200  verify extracted text returned
- [ ] Test (web_search): `respx` mock returning 404  verify 1 call only, error string returned
- [ ] Bonus: also decorate `bookmark_pipeline._default_web_read` if it exists

### Architecture notes
- `_web_read` is tricky because it catches exceptions and returns strings. The retry must wrap the HTTP call only, not the catch block.
- Pattern: inner decorated function raises on failure  outer function catches and returns error string
- See `docs/research/retry-decorators.md` §3.6
