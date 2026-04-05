# Hook Protocol for Automated Event Registration

> **Owning task:** #564 — Consider Hook protocol for automated event registration
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

DRY-12 in `docs/software-design-audit.md` identified that 8 hook classes (originally 9; `escalation.py` was deleted by #484) each have a `register(hooks: HookRegistry)` method that manually calls `hooks.register(HookEvent.X, handler)`. The question: should we define a `Hook` protocol/ABC with `events: ClassVar` and automated registration, or keep the explicit approach?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| pluggy docs (v1.6) | <https://pluggy.readthedocs.io/en/stable/> | .85 — marker-based hook detection + PluginManager.register() auto-discovery |
| blinker docs (v1.9) | <https://blinker.readthedocs.io/en/stable/> | .70 — signal.connect() explicit registration, no auto-discovery |
| Django signals docs (v5.1) | <https://docs.djangoproject.com/en/5.1/topics/signals/> | .75 — explicit connect(), warns against implicit coupling |
| OwlBear hooks.py | `src/owlbear/core/hooks.py` | 1.0 — current implementation |
| OwlBear bootstrap.py L174-205 | `src/owlbear/bootstrap.py` | 1.0 — where hooks are wired |

## 3. Analysis

### 3.1 Current Registration Variance

Not all 8 hooks follow the same pattern — this is the critical finding:

| Pattern | Classes | Registrations | Handler |
|---------|---------|---------------|---------|
| Single event, `self` as callable | CommandSafetyGuard, URLSafetyGuard, AutoLintHook, SubagentVerificationHook, TestVerificationHook, ContextInjectionHook | 1 each | `hooks.register(EVENT, self)` |
| Single event, named method | ScreenshotOnErrorHook, ProgressReporter | 1 each | `hooks.register(EVENT, self.handle)` or `self.on_tool_complete` |
| Multi-event, closure factory | NotificationHook, ObservabilityHook | N (configurable or all) | `hooks.register(event, self._make_handler(event))` |

### 3.2 Option Comparison

| Criterion | A: Hook ABC + auto-register (.35) | B: Keep explicit (.80) | C: Protocol (structural) (.45) |
|-----------|-----|------|------|
| DRY savings | ~4 LOC per simple class (6 classes) | 0 | ~4 LOC per simple class |
| Complex hooks fit | Poor — NotificationHook/ObservabilityHook use closures and loops that don't fit `events: ClassVar` | N/A | Poor — same issue |
| New dependency | 0 | 0 | 0 |
| KISS | Adds abstraction layer for 6 simple cases | Current: each class self-documents its events | Adds protocol + auto-register util |
| YAGNI | Auto-registration solves no user-facing problem | No change needed | Same as A |
| Readability | Hides which events a hook subscribes to | `register()` is greppable, explicit | Protocol at least type-checkable |
| Django's advice | "Where possible opt for directly calling the handling code" | Aligns with Django's warning against implicit coupling | — |
| Pluggy's approach | Designed for external plugins, not internal wiring | — | — |
| Total boilerplate | 8 × ~5 LOC = ~40 LOC | Same ~40 LOC | Same ~40 LOC saved for 6, not for 2 |

### 3.3 Why the ABC/Protocol Doesn't Fit

1. **Only 6 of 8 hooks are uniform.** NotificationHook takes configurable event names from settings. ObservabilityHook registers a closure per event. ScreenshotOnErrorHook uses `self.handle` and has `unregister()`. These three can't use `events: ClassVar[list[HookEvent]]` without special-casing.
2. **Savings are minimal.** Each simple hook's `register()` method is 3 lines (import, call, docstring). Replacing with a ClassVar + auto-register loop saves ~12 net LOC across 6 classes while adding ~15 LOC for the ABC/protocol definition + `register_hooks()` utility.
3. **Explicitness is the feature.** The current pattern is greppable (`grep "hooks.register"` shows all subscriptions), discoverable (each class documents its own events), and has zero indirection.
4. **pluggy/blinker solve a different problem.** Pluggy enables external plugin discovery for projects like pytest with 1400+ plugins. Blinker provides named signal routing for decoupled components. OwlBear has 8 internal hooks wired in one function — not a plugin ecosystem.

## 4. Recommendation (.80 confidence): Keep Explicit

**Do not implement a Hook protocol.** The current explicit registration is the right approach for OwlBear's scale and internals.

**Rationale:**

- The hook set is small (8 classes), internal, and wired in one place (`_build_hooks()`)
- 3 of 8 hooks don't fit a uniform ClassVar pattern
- Net LOC savings would be negative (more code to support the abstraction than it eliminates)
- Django's own docs warn: "signals give the appearance of loose coupling, but they can quickly lead to code that is hard to understand" — same applies to auto-registration magic
- KISS and YAGNI both argue against this change

**One minor cleanup worth doing:** Update DRY-12 in `software-design-audit.md` to reflect that `escalation.py` was deleted (8 classes, not 9) and mark the finding as "accepted — explicit is preferred."

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe edit 564 --body "DECISION: Keep explicit hook registration. See docs/research/hook-protocol.md. The 8 hook classes (not 9 -- escalation.py deleted by #484) use 3 different registration patterns. Only 6/8 are uniform. Net LOC savings would be negative. KISS/YAGNI/Django all argue against auto-registration magic. AC satisfied: decision documented."
kanban\kanban-md.exe move 564 backlog
```

No implementation tasks are recommended — this is a "don't do it" decision.
