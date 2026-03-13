---
id: 359
title: Tool-level retry in HookedToolset for transient errors
status: archived
priority: needed
created: 2026-03-01T20:11:36.2007905+01:00
updated: 2026-03-02T09:14:33.703544+01:00
started: 2026-03-01T20:22:20.1990225+01:00
completed: 2026-03-02T09:14:33.703544+01:00
tags:
    - phase-13
    - agent
    - reliability
    - tooling
depends_on:
    - 357
class: standard
---

## Tool-Level Retry in HookedToolset

Add retry to call_tool() in src/owlbear/tools/hooked.py for infra-transient errors only.

### Scope

Retry ONLY when classify_error(exc) returns TRANSIENT. Do NOT retry:
- BlockedCommandError (guard rejection — PERMANENT)
- Auth errors (handled at daemon layer #360)
- Tool-semantic errors (use PydanticAI ModelRetry at L3, not our layer)

### Acceptance Criteria

- [ ] call_tool() retries when classify_error(exc) returns TRANSIENT
- [ ] Max 3 attempts with exponential backoff (base=0.5s, max=10s)
- [ ] PERMANENT/AUTH/TOOL_SEMANTIC errors propagate immediately — zero retries
- [ ] BlockedCommandError still returns BLOCKED string (existing behavior preserved)
- [ ] Each retry logged at WARNING: tool name, attempt N/max, error message
- [ ] After retries exhausted, original exception propagates (not swallowed)
- [ ] Guards still run once (before retry loop), not on every retry
- [ ] Tests in tests/test_hooked_toolset.py (extend existing, TDD)
- [ ] Ruff clean

### Architecture Notes

- Depends on #357 for classify_error() and ErrorCategory
- Layer 2 — catches infra errors L1 (HTTP transport) did not handle
- tenacity @retry with retry_if_exception predicate
- See docs/research/error-recovery.md section 3.2 (L2) and 4.2
