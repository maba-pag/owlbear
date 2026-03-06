---
id: 491
title: Fix dual error handling on ON_ERROR events
status: review
priority: important
created: 2026-03-04T07:38:06.9326328+01:00
updated: 2026-03-06T19:27:46.6092667+01:00
started: 2026-03-06T17:49:55.7317939+01:00
tags:
    - audit
    - resilience
    - scope:core
blocked: true
block_reason: 'test_error_recovery.py::test_on_error_uses_defaults_for_missing_tool_name_and_attempt still expects auto-registration. Fix: call register_on_error() before emit.'
class: standard
---

## Research Findings (2026-03-06)

See task body history for full research. Key insight: the dual error handling is
**latent** (not active) because EscalationHook is never wired in production.
The fix establishes the design rule before #484 wires it.

## Design Decision

**Single authority: daemon `_recover_from_error` owns all error recovery.**
EscalationHook must NOT auto-register on ON_ERROR. The `escalate()` method
remains available for explicit programmatic use.

## Scope

This task covers ONLY the auto-registration removal and the single-prompt
invariant test. Wiring `escalate()` into `_recover_from_error()` as an
interactive replacement for bare `channel.send(error)` is a separate
enhancement (out of scope).

## Files to Change

- `src/owlbear/core/escalation.py` -- remove `hooks.register()` from`__init__`, add explicit `register_on_error()` opt-in method
- `tests/test_escalation.py` -- verify no auto-registration, test opt-in path

## Acceptance Criteria

- [ ] `EscalationHook.__init__` does NOT call `hooks.register(ON_ERROR, ...)`  
- [ ] New `register_on_error()` method exists for explicit opt-in registration
- [ ] `escalate()` public API unchanged (signature, behavior, return type)
- [ ] `unregister()` still works when `register_on_error()` was called
- [ ] Unit test: instantiate EscalationHook, verify ON_ERROR has no handlers auto-registered
- [ ] Unit test: call `register_on_error()`, verify handler IS registered on ON_ERROR
- [ ] All existing escalation tests pass (updated for new constructor)
- [ ] No ruff violations
- [ ] Resolves #484 (wire-or-remove) -- resolved as 'keep explicit API, no auto-wire'
