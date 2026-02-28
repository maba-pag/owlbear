---
id: 21
title: 'P3-06: SubagentComplete verification hook'
status: archived
priority: medium
created: 2026-02-24T15:12:41.8109498+01:00
updated: 2026-02-27T10:00:02.5423346+01:00
started: 2026-02-27T00:39:19.8670675+01:00
completed: 2026-02-27T10:00:02.5423346+01:00
tags:
    - phase-3
    - hooks
depends_on:
    - 16
    - 38
class: standard
---

PydanticAI hook that verifies subagent output after completion.

## AC
- Add SUBAGENT_COMPLETE event to HookEvent enum in src/owlbear/core/hooks.py
- SubagentVerificationHook class in src/owlbear/core/hooks/ registered on SUBAGENT_COMPLETE
- Inspects subagent result payload: checks files created exist, checks tests pass if task involved tests
- Reports verification results (pass/fail with details)
- Does NOT block (logs warning on failure, never raises)
- Follows URLSafetyGuard pattern: __call__(data), register(hooks)
- Tests: register, new HookEvent member, verify file existence check, verify test check, graceful failure
- Depends on HookRegistry (#38, done)
