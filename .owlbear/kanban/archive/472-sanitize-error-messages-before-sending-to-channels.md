---
id: 472
title: Sanitize error messages before sending to channels
status: archived
priority: needed
created: 2026-03-04T07:37:51.3590676+01:00
updated: 2026-03-06T19:28:18.0142928+01:00
started: 2026-03-06T12:06:58.3773828+01:00
completed: 2026-03-06T19:28:18.0142928+01:00
tags:
    - audit
    - security
    - channels
depends_on:
    - 605
class: standard
---

## error_to_user_message() helper in core/errors.py

Add a pure function that converts any exception into a safe, user-facing string.
Full exception details stay in server-side logs (already handled by logger.exception).

### Acceptance Criteria

1. `error_to_user_message(exc: Exception) -> str` exists in `src/owlbear/core/errors.py`  
2. Type-based mapping (`_SAFE_MESSAGES` dict, module-level, private):  
   - `httpx.HTTPStatusError` -> `'HTTP request failed (status {code})'` where code = `exc.response.status_code`  
   - `httpx.ConnectError` -> `'Connection failed'`  
   - `httpx.TimeoutException` -> `'Request timed out'`  
   - `openai.AuthenticationError` -> `'Authentication failed'`  
   - `openai.PermissionDeniedError` -> `'Permission denied'`  
   - `pydantic.ValidationError` -> `'Validation error'`  
   - `FileNotFoundError` -> `'File not found'`  
   - `PermissionError` -> `'Permission denied'`  
3. Regex scrub fallback (`_SCRUB_PATTERNS` list, module-level, private) for types not in the map:  
   - URLs (`https?://\S+`) -> `[URL]`  
   - Bearer tokens (`Bearer\s+\S+`) -> `[REDACTED]`  
   - Secret query params (`(?i)(token|key|secret|password)=\S+`) -> `\1=[REDACTED]`  
   - File paths (Windows `X:\..` and Unix `/foo/bar.py`) -> `[PATH]`  
4. Fallback output format: `'{TypeName}: {scrubbed_message}'`  
5. Pure function -- no I/O, no logging, no side effects  
6. Follows existing `classify_error()` pattern in same module  

### Architecture notes

See docs/research/error-message-sanitization.md. This task is the helper only;
call-site replacement is a separate task.

### Out of scope

Replacing `channel.send(f'Error: {exc}')` call sites -- see follow-up task.
