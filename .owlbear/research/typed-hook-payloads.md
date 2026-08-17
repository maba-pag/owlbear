# Typed Payloads for Hook Events

> **Owning task:** #483 — Define typed payloads for hook events
> **Date:** 2026-03-08  **Status:** Complete

## 1. Context and Question

The hook system (`src/owlbear/core/hooks.py`) uses `Handler = Callable[[object], object]` for all hook handlers. This means:

- Emitters pass untyped `dict` payloads — no IDE completion, no static checking
- Consumers defensively `isinstance(data, dict)` on every handler entry
- POST_TOOL_USE shape diverges between HookedToolset and ApprovalGateToolset (INT-05)
- Handler return type is `object` but all handlers return `None` (F-18)

**Question:** What typing pattern best fits OwlBear's hook system for typed event payloads?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python TypedDict spec | `https://typing.python.org/en/latest/spec/typeddict.html` | .95 |
| 2 | Python typing docs | `https://docs.python.org/3/library/typing.html#typing.TypedDict` | .90 |
| 3 | Pluggy hook system | `https://github.com/pytest-dev/pluggy` | .75 |
| 4 | OwlBear test_hook.py | `src/owlbear/core/test_hook.py` (internal) | .90 |
| 5 | Python `NotRequired` (PEP 655) | `https://docs.python.org/3/library/typing.html#typing.NotRequired` | .90 |

## 3. Payload Shape Catalog (Current State)

| Event | Emitter(s) | Shape |
|-------|-----------|-------|
| PRE_TOOL_USE | HookedToolset, git_local, github_api, kanban, terminal | `{"tool_name": str, "args": dict}` |
| POST_TOOL_USE | HookedToolset | `{"tool_name": str, "result": object}` |
| POST_TOOL_USE | ApprovalGateToolset | `{"tool_name": str, "event_type": str, "approval_required": bool, "approval_decision"?: str}` |
| ON_MESSAGE | OwlBearAgent | `{"prompt": str}` |
| ON_ERROR | OwlBearAgent | `{"error": Exception, "prompt": str}` |
| SESSION_START | (enriched by ContextInjectionHook) | `{"context"?: dict}` |
| SESSION_END | (enriched by TestVerificationHook) | `{"test_results"?: list}` |
| SUBAGENT_COMPLETE | (consumed by SubagentVerificationHook) | `{"created_files"?: list, "test_files"?: list}` |
| TASK_COMPLETE | daemon.py | `{"task_id": str, "outcome": "success"\|"failure"}` |
| DAEMON_STARTUP | daemon.py | `{"channel": str, "config_dir": str}` |
| QUESTION_PENDING | (not yet emitted) | TBD |

**Key finding:** POST_TOOL_USE has two incompatible shapes (INT-05). All 10 consumer `__call__`
methods do `if not isinstance(data, dict): return` — pure boilerplate that typed payloads eliminate.

## 4. Analysis

### Pattern Comparison

| Criterion | TypedDict (.90) | dataclass (.65) | Pydantic BaseModel (.50) |
|-----------|-----------------|-----------------|--------------------------|
| Runtime cost | Zero — just a dict | Object instantiation | Validation overhead |
| Migration effort | None — existing dicts already match | Must change all `emit()` call sites | Must change all `emit()` call sites |
| IDE support | Full (Pylance strict) | Full | Full |
| Inheritance | Yes (class-based) | Yes | Yes |
| Optional fields | `NotRequired[]` | `field(default=...)` | `Field(default=...)` |
| Existing precedent | `TestResult` in test_hook.py [1] | None in codebase | Used for config/models, not events |
| KISS alignment | High — dicts stay dicts | Medium — new object type | Low — overkill for internal events |
| Backward compat | Full — TypedDict is structural | Breaking — different construction | Breaking — different construction |

[1] `src/owlbear/core/test_hook.py` already defines `class TestResult(TypedDict)`.

### Prior Art Patterns

**Pluggy (pytest):** Uses TypedDict for option structs (`HookspecOpts`, `HookimplOpts`) and typed function signatures for each hookspec. Hooks are called with `**kwargs: object`. The typed hookspec function signature provides the contract — callers pass keyword args matching the spec. This is Protocol-based typing.

**Python TypedDict spec:** Supports inheritance, `Required`/`NotRequired`, `ReadOnly`, and generic parameterization. Structural subtyping means a dict with extra keys is compatible with a TypedDict expecting fewer keys — perfect for our POST_TOOL_USE divergence case.

### POST_TOOL_USE Resolution

The two shapes share `tool_name: str`. Use a base with `NotRequired` optional fields:

```python
class PostToolUseData(TypedDict):
    tool_name: str
    result: NotRequired[object]  # from HookedToolset
    event_type: NotRequired[str]  # from ApprovalGateToolset
    approval_required: NotRequired[bool]
    approval_decision: NotRequired[str]
    grant_ttl: NotRequired[int]
    grant_max_uses: NotRequired[int]
```

This is backward-compatible — both existing dict shapes satisfy this TypedDict structurally.

### Handler Type Fix (F-18)

Current: `Handler = Callable[[object], object]`
Phase 1: `Handler = Callable[[dict[str, Any]], None]` — minimal fix, enables `.get()` without cast.
Phase 2: event-specific `@overload` on `emit()` tying `HookEvent` to payload type (deferred).

## 5. Recommendation (.90 confidence)

**TypedDict per event.** Rationale:

- Zero runtime cost — existing dicts already match the typed shapes
- Internal precedent (`TestResult` in test_hook.py) + external (pluggy `HookspecOpts`)
- Backward-compatible — no migration of emit call sites needed
- KISS-aligned — dicts stay dicts, we add type annotations
- `NotRequired` (PEP 655) available natively on Python 3.12

**Risk:** Without `@overload`, any payload type is accepted for any event.
Mitigation: Phase 2 adds overloads. Risk is low — mismatches caught at handler access.

## 6. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement TypedDict payloads for hook events" --status todo --priority needed --tags "phase-7,hooks,refactor,typing" --description "Create TypedDict classes in core/hooks.py: PreToolUseData, PostToolUseData (NotRequired for INT-05), OnMessageData, OnErrorData, SessionStartData, SessionEndData, SubagentCompleteData, TaskCompleteData, DaemonStartupData. Update Handler type alias to Callable[[dict[str, Any]], None]. Export from core/__init__.py. AC: all TypedDicts defined, Handler updated, mypy/pylance clean. See docs/research/typed-hook-payloads.md."

kanban\kanban-md.exe create "Annotate hook consumers with typed payloads" --status todo --priority needed --tags "phase-7,hooks,refactor,typing" --description "Replace data: object + isinstance guards in: command_guard.py, lint_hook.py, notification_hook.py, observability.py, context_hook.py, subagent_hook.py, test_hook.py, retrospective_hook.py, progress.py, screenshot_hook.py. Use specific TypedDict param type per handler. Remove redundant isinstance(data, dict) checks. AC: all 10 consumers typed, zero isinstance(data, dict) guards. See docs/research/typed-hook-payloads.md."

kanban\kanban-md.exe create "Unify POST_TOOL_USE payload shape (INT-05)" --status todo --priority needed --tags "phase-7,hooks,refactor,INT-05" --description "Resolve INT-05: gate.py emits POST_TOOL_USE with different shape than hooked.py. Both emitters use PostToolUseData TypedDict with NotRequired optionals. Update 5 emit sites in gate.py + 1 in hooked.py. AC: both emitters produce PostToolUseData, type-checker clean. See docs/research/typed-hook-payloads.md."

kanban\kanban-md.exe create "Add @overload to HookRegistry.emit for type-safe dispatch" --status backlog --priority nice-to-have --tags "phase-8,hooks,typing" --description "Phase 2: add @overload on emit() tying each HookEvent to its TypedDict. AC: Pylance flags wrong payload type for wrong event. See docs/research/typed-hook-payloads.md."
```
