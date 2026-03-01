---
id: 343
title: Fix CommandSafetyGuard enforcement — BlockedCommandError swallowed by emit()
status: archived
priority: needed
created: 2026-03-01T11:19:13.7914368+01:00
updated: 2026-03-01T17:10:12.0251501+01:00
started: 2026-03-01T11:21:15.4395342+01:00
completed: 2026-03-01T17:10:12.0251501+01:00
tags:
    - phase-12
    - agent
    - safety
class: standard
---

## Acceptance Criteria
- [ ] HookedToolset.call_tool() catches BlockedCommandError from PRE_TOOL_USE hook and re-raises it (or returns error message to model)
- [ ] Alternative: add dedicated check in HookedToolset.call_tool() before delegating — call CommandSafetyGuard.check directly
- [ ] Do NOT change HookRegistry.emit() semantics — the swallow-all design is correct for general hooks
- [ ] Test: when CommandSafetyGuard raises BlockedCommandError, HookedToolset returns error string to model instead of executing tool
- [ ] Test: other hooks (observability, notification) still swallow their exceptions
- [ ] Existing test_emit_blocked_command_swallowed_by_registry stays green (emit behavior unchanged)
- [ ] New test: HookedToolset with guard blocks dangerous commands before tool execution

See docs/approval-gates-research.md S3.1
