---
id: 605
title: Test error_to_user_message() sanitization
status: archived
priority: needed
created: 2026-03-06T12:21:11.5838749+01:00
updated: 2026-03-06T19:28:35.8222589+01:00
started: 2026-03-06T12:52:27.8349337+01:00
completed: 2026-03-06T19:28:35.8222589+01:00
tags:
    - security
    - test
    - channels
class: standard
---

## Unit tests for error_to_user_message()

Preceding test task for #472 (TDD compliance).
Target: 100%% branch coverage on error_to_user_message().
File: `tests/test_error_sanitization.py`  

### Test cases

1. `httpx.HTTPStatusError` with token-bearing URL -> returns `'HTTP request failed (status 401)'` -- no URL, no token in output  
2. `httpx.ConnectError` with hostname detail -> returns `'Connection failed'` -- no hostname  
3. `httpx.TimeoutException` with URL -> returns `'Request timed out'` -- no URL  
4. `openai.AuthenticationError` -> returns `'Authentication failed'`  
5. `pydantic.ValidationError` -> returns `'Validation error'`  
6. Unknown exception with `https://api.example.com?token=secret` in message -> URL replaced with `[URL]`  
7. Unknown exception with `Bearer ghp_abc123` -> token replaced with `[REDACTED]`  
8. Unknown exception with `token=abc123&key=xyz` -> params replaced with `token=[REDACTED]&key=[REDACTED]`  
9. Unknown exception with `C:\Users\foo\bar.py` or `/home/foo/bar.py` -> path replaced with `[PATH]`  
10. `ValueError('bad input')` -> `'ValueError: bad input'` (benign, no patterns to scrub)  
11. Return type is always `str`
