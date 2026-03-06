---
id: 489
title: Fix NotificationHook signature mismatch
status: archived
priority: important
created: 2026-03-04T07:38:05.373334+01:00
updated: 2026-03-06T19:28:27.053405+01:00
started: 2026-03-06T17:38:49.4400419+01:00
completed: 2026-03-06T19:28:27.053405+01:00
tags:
    - audit
    - bugfix
    - hooks
class: standard
---

ARC-09: NotificationHook.__call__ takes (self, event, data) but HookRegistry.emit invokes handlers with single data arg.

## Research Findings

### The Problem

`HookRegistry.emit()` calls `handler(data)` — single arg (hooks.py L80).
The `Handler` type alias is `Callable[[object], object]` — single arg.

Every other hook follows this convention:

- `CommandSafetyGuard.__call__(self, data)` — registers self directly
- `SubagentVerificationHook.__call__(self, data)` — registers self directly
- `LintHook.__call__(self, data)` — registers self directly
- `EscalationHook._on_error(self, data)` — registers method directly
- `ScreenshotOnErrorHook.handle(self, data)` — registers method directly

`NotificationHook.__call__(self, event, data)` is the __only__ hook with a 2-arg signature.

### How It Works Today (the workaround)

`NotificationHook.register()` does NOT register `self` directly. It calls `_make_handler(event)` which creates a closure that captures `event` and adapts the 2-arg `__call__` to the 1-arg convention. It works, but:

1. Inconsistent with every other hook
2. Adds an indirection layer for no benefit
3. The event is already known at registration time

### Recommended Fix (.90 confidence)

Refactor `__call__` to single-arg `(self, data: object)`. The `_make_handler` closure injects event into the data dict before calling. Minimal diff:

1. `__call__(self, event, data)` → `__call__(self, data: object)`
2. Extract event: `event = data.get(event)` if present, else skip
3. `_make_handler` builds `{event: event, **original_data}` and calls `self(merged)`
4. Update tests that call `hook(event, data)` directly

### Files to Change

- `src/owlbear/core/notification_hook.py` — refactor `__call__` + `_make_handler`
- `tests/test_notification_hook.py` — update direct `__call__` invocations

### AC

- [ ] `NotificationHook.__call__` takes `(self, data: object)` — single arg like all other hooks
- [ ] `_make_handler` closure simplified or removed
- [ ] `NotificationHook.register()` consistent with other hooks
- [ ] All existing tests pass (updated as needed)
- [ ] No behavior change — same backends, same event filtering, same error isolation
