---
id: 20
title: 'P3-05: SessionEnd test verification hook'
status: done
priority: medium
created: 2026-02-24T15:12:24.8904478+01:00
updated: 2026-02-27T01:30:09.784445+01:00
started: 2026-02-27T00:39:19.8580825+01:00
completed: 2026-02-27T01:30:09.784445+01:00
tags:
    - phase-3
    - hooks
    - test
depends_on:
    - 16
    - 11
    - 38
class: standard
---

PydanticAI SESSION_END hook that verifies tests pass before session ends.

## AC
- TestVerificationHook class in src/owlbear/core/hooks/ registered on SESSION_END
- Runs pytest (uv run pytest tests/ -m 'not api' --tb=short -q) as subprocess
- Reports test results in hook response (pass count, fail count, output summary)
- Does NOT block session end (logs warning on failure, never raises)
- Configurable pytest command and args
- Follows URLSafetyGuard pattern: __call__(data), register(hooks)
- Tests: register, fire on session end, test pass scenario, test fail scenario, subprocess mock
- Depends on HookRegistry (#38, done)
