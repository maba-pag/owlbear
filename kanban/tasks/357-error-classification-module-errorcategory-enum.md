---
id: 357
title: Error classification module (ErrorCategory enum + classify_error)
status: archived
priority: needed
created: 2026-03-01T20:11:20.1731874+01:00
updated: 2026-03-02T09:14:28.7632716+01:00
started: 2026-03-01T20:22:17.5064697+01:00
completed: 2026-03-02T09:14:28.7632716+01:00
tags:
    - phase-13
    - agent
    - reliability
class: standard
---

## Error Classification Module

Create `src/owlbear/core/errors.py`.

### ErrorCategory (StrEnum, 4 members)

- TRANSIENT — retry with backoff
- AUTH — refresh token, retry once
- PERMANENT — do not retry, escalate
- TOOL_SEMANTIC — model self-correction via PydanticAI ModelRetry

### classify_error(exc: Exception) -> ErrorCategory

Pure function (~30 LOC). isinstance-based classification:

- httpx.ConnectError, httpx.TimeoutException -> TRANSIENT
- httpx.HTTPStatusError 429/502/503/504 -> TRANSIENT
- TimeoutError, ConnectionError -> TRANSIENT
- httpx.HTTPStatusError 401/403 -> AUTH
- openai.AuthenticationError, openai.PermissionDeniedError -> AUTH
- FileNotFoundError, PermissionError, BlockedCommandError -> PERMANENT
- pydantic.ValidationError -> PERMANENT
- ValueError, KeyError, TypeError -> TOOL_SEMANTIC
- Unknown/default -> PERMANENT

### Acceptance Criteria

- [ ] ErrorCategory is a StrEnum with exactly 4 members: TRANSIENT, AUTH, PERMANENT, TOOL_SEMANTIC
- [ ] classify_error maps httpx.ConnectError -> TRANSIENT
- [ ] classify_error maps httpx.TimeoutException -> TRANSIENT
- [ ] classify_error maps httpx.HTTPStatusError(429) -> TRANSIENT
- [ ] classify_error maps httpx.HTTPStatusError(401) -> AUTH
- [ ] classify_error maps openai.AuthenticationError -> AUTH
- [ ] classify_error maps FileNotFoundError -> PERMANENT
- [ ] classify_error maps pydantic.ValidationError -> PERMANENT
- [ ] classify_error maps BlockedCommandError -> PERMANENT
- [ ] classify_error maps ValueError -> TOOL_SEMANTIC
- [ ] Unknown exception types default to PERMANENT
- [ ] Function is pure — no side effects, no I/O, no logging
- [ ] Tests in tests/test_error_classification.py (TDD)
- [ ] Ruff clean

### Architecture Notes

- Subsumes daemon.py _is_auth_error() — daemon will use classify_error in #360
- Imported by #358, #359, #360, #363
- See docs/error-recovery-research.md section 3.1
