# Typed Payloads for Hook Events

> **Owning task:** #483 — Define typed payloads for hook events
> **Date:** 2026-03-06 **Status:** Complete

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
| 5 | PydanticAI agent API | `https://ai.pydantic.dev/api/agent/` | .70 |

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
| TASK_COMPLETE | (not yet emitted) | TBD |
| QUESTION_PENDING | (not yet emitted) | TBD |

**Key finding:** POST_TOOL_USE has two incompatible shapes (INT-05). Resolution: use a base TypedDict with shared fields + handle optional fields via `NotRequired`.

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
    result: NotRequired[object]           # from HookedToolset
    event_type: NotRequired[str]          # from ApprovalGateToolset
    approval_required: NotRequired[bool]
    approval_decision: NotRequired[str]
```

This is backward-compatible — both existing dict shapes satisfy this TypedDict structurally.

### Handler Type Fix

Current: `Handler = Callable[[object], object]`
Proposed: `Handler = Callable[[HookData], None]` where `HookData` is a union type:

```python
HookData: TypeAlias = (
    PreToolUseData | PostToolUseData | OnMessageData
    | OnErrorData | SessionData | SubagentCompleteData
)
Handler = Callable[[HookData], None]
```

This also fixes F-18 (return type should be `None`).

## 5. Recommendation (.90 confidence)

**Use TypedDict per event.** Rationale:

- Zero runtime cost — existing dicts already match the typed shapes
- Internal precedent exists (`TestResult` in test_hook.py)
- Pluggy (most popular Python hook library) uses TypedDict for hook options
- Backward-compatible — no migration of emit call sites needed
- KISS-aligned — dicts stay dicts, we just add type annotations
- Pylance strict mode benefits immediately

**Risk:** Handler type union (`HookData`) makes `emit()` accept any event payload for any event. Mitigation: use `@overload` on `emit()` to tie `HookEvent` value to specific payload type (Phase 2 enhancement, not required for initial implementation).

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement TypedDict payloads for hook events" --status todo --priority needed --tags "phase-7,hooks,refactor" --description "Create TypedDict classes for each HookEvent in src/owlbear/core/hooks.py: PreToolUseData, PostToolUseData (with NotRequired fields for INT-05 divergence), OnMessageData, OnErrorData, SessionStartData, SessionEndData, SubagentCompleteData. Update Handler type alias to Callable[[HookData], None]. See docs/typed-hook-payloads-research.md."

kanban\kanban-md.exe create "Update hook consumers to use typed payloads" --status todo --priority needed --tags "phase-7,hooks,refactor" --depends-on 483 --description "Replace isinstance(data, dict) guards in command_guard.py, lint_hook.py, notification_hook.py, observability.py, context_hook.py, subagent_hook.py with typed parameter annotations. Remove defensive dict checks that become redundant with TypedDict typing. See docs/typed-hook-payloads-research.md."

kanban\kanban-md.exe create "Unify POST_TOOL_USE payload shape" --status todo --priority needed --tags "phase-7,hooks,refactor,INT-05" --depends-on 483 --description "Resolve INT-05: ApprovalGateToolset emits POST_TOOL_USE with different shape than HookedToolset. Standardize on PostToolUseData TypedDict with NotRequired optional fields. Update gate.py and hooked.py emit calls. See docs/typed-hook-payloads-research.md."

kanban\kanban-md.exe create "Add @overload to HookRegistry.emit for type-safe dispatch" --status backlog --priority nice-to-have --tags "phase-8,hooks,typing" --description "Phase 2 enhancement: add @overload signatures to HookRegistry.emit() that tie each HookEvent enum value to its specific TypedDict payload type. This ensures emit(HookEvent.PRE_TOOL_USE, data) only accepts PreToolUseData. See docs/typed-hook-payloads-research.md section 5 risk mitigation."
```

