---
id: 17
title: 'P3-02: PostToolUse auto-lint hook'
status: done
priority: medium
created: 2026-02-24T15:10:07.746675+01:00
updated: 2026-02-27T00:54:12.8555569+01:00
started: 2026-02-27T00:39:19.831958+01:00
completed: 2026-02-27T00:54:12.8555569+01:00
tags:
    - phase-3
    - hooks
    - tooling
depends_on:
    - 16
    - 11
    - 38
class: standard
---

PydanticAI POST_TOOL_USE hook that auto-lints edited Python files.

## AC
- AutoLintHook class in src/owlbear/core/hooks/ registered on POST_TOOL_USE
- Inspects tool-call payload for file-edit operations (.py files only)
- Runs ruff check --fix on the edited file path
- Follows URLSafetyGuard pattern: __call__(data), register(hooks) method
- Skips non-Python files silently
- Logs lint results (warnings found, fixes applied)
- Error isolation: lint failures logged but never block the agent
- Tests: register, fire on .py edit, skip non-.py, ruff error isolation
- Depends on HookRegistry (#38, done)
