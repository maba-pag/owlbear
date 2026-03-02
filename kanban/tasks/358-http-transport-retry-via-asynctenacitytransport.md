---
id: 358
title: HTTP transport retry via AsyncTenacityTransport
status: archived
priority: needed
created: 2026-03-01T20:11:27.8855689+01:00
updated: 2026-03-02T09:14:31.2163512+01:00
started: 2026-03-01T20:22:19.0286095+01:00
completed: 2026-03-02T09:14:31.2163512+01:00
tags:
    - phase-13
    - agent
    - reliability
class: standard
---

## HTTP Transport Retry

Wire retry into create_copilot_client() in src/owlbear/providers/copilot.py.

### Approach

Pass a custom httpx.AsyncClient with retry transport to AsyncOpenAI(http_client=...).
Verify PydanticAI AsyncTenacityTransport availability at impl time; fall back to
httpx.AsyncHTTPTransport(retries=N) + tenacity wrapper if needed.

### Acceptance Criteria

- [ ] HTTP requests retry on transient status codes: 429, 502, 503, 504
- [ ] Retry uses exponential backoff (base=1s, max=30s, multiplier=2)
- [ ] 429 responses respect Retry-After header when present
- [ ] Permanent HTTP errors (400, 404, 422) propagate immediately
- [ ] Auth errors (401, 403) propagate immediately (handled at daemon layer #360)
- [ ] Max 3 retry attempts per request
- [ ] Retry logic is in create_copilot_client(), transparent to callers
- [ ] Tests in tests/test_providers_copilot.py (extend existing, TDD)
- [ ] Ruff clean

### Architecture Notes

- Layer 1 (innermost) — retries before errors reach agent/daemon
- Independent of ErrorCategory (#357) — HTTP status codes determine retry
- tenacity already a project dependency
- See docs/error-recovery-research.md section 3.2 (L1) and 4.1
