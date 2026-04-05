# ContextInjectionHook Dead Code Analysis

> **Owning task:** #772 — Fix ContextInjectionHook: wire kanban_summary to system prompt
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

`ContextInjectionHook` fires at `SESSION_START`, reads `.github/copilot-instructions.md`
and runs `kanban-md context`, then stores both under `data["context"]` on the event
payload. However, **no code reads this payload data**. The task asks: wire it through
or remove the dead code?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| OwlBear `ContextInjectionHook` | `src/owlbear/core/context_hook.py` | .95 |
| OwlBear `ContextManager` | `src/owlbear/memory/context.py` | .95 |
| OwlBear `agent.turn()` | `src/owlbear/core/agent.py` | .90 |
| OwlBear `bootstrap/hooks.py` | `src/owlbear/bootstrap/hooks.py` | .90 |
| OwlBear `daemon.py` SESSION_START emit | `src/owlbear/daemon.py` L930-937 | .85 |
| Prior research: compact-board-context | `docs/research/compact-board-context.md` S3.3 | .95 |
| Prior research: wire-board-context | `docs/research/wire-board-context-into-turn.md` | .90 |
| PydanticAI — Instructions (runtime) | <https://ai.pydantic.dev/agents/#instructions> | .85 |

## 3. Analysis

### 3.1 Dead Code Audit

A `grep` for `["context"]` and `['context']` across `src/` finds only `context_hook.py`
**writing** to the payload — zero readers. The daemon emits SESSION_START, the hook
mutates the event dict, and the dict is discarded. Both `instructions` and
`kanban_summary` are write-only.

### 3.2 Redundancy

The `instructions` field duplicates `ContextManager.instructions` which is already
wired into the agent at init time via `Agent(instructions=...)`. There is no value
in also storing instructions in the event payload.

### 3.3 Option Comparison

| Option | Description | Pros | Cons | KISS |
|--------|-------------|------|------|------|
| A: Remove hook entirely | Delete class + registration + tests | Eliminates dead code, no subprocess at startup | Loses hook attachment point | **High** |
| B: Remove kanban, keep instructions | Partial cleanup | Keeps instructions for observability | instructions still unused | Medium |
| C: Wire kanban_summary into prompt | Read payload in daemon, inject | Makes existing code functional | Session-start data is stale; #770/#771 do this better per-turn | Low |
| D: Keep as-is | Do nothing | Zero risk | Dead code remains | N/A |

### 3.4 Why NOT wire it through (Option C)

The prior research (`compact-board-context.md` S3.4, Option D) evaluated wiring
`ContextInjectionHook` and rated it inferior to the `BoardContextProvider` approach:

- Session-start injection is **stale** — board changes during a session are invisible
- `kanban-md context` produces **8,276 tokens** (full board + bodies) vs ~220 tokens
  from `kanban-md list --compact` (active only)
- Per-turn injection (#770/#771) is fresher and cheaper

Wiring #772 as Option C would create a redundant, inferior injection path that
# 770/#771 will supersede. This violates YAGNI.

## 4. Recommendation (.90 confidence)

**Option A — Remove `ContextInjectionHook` entirely.**

- Delete `src/owlbear/core/context_hook.py`
- Remove registration from `src/owlbear/bootstrap/hooks.py`
- Delete or update `tests/test_context_hook.py`
- Remove the `ContextInjectionHook` test from `tests/test_session_hooks.py`
- Clean up `SessionStartData.context` optional field if no other hook uses it

**Rationale:**

1. Both outputs (`instructions`, `kanban_summary`) are dead — zero readers
2. `instructions` is redundant with `ContextManager` (DRY violation)
3. `kanban_summary` will be superseded by `BoardContextProvider` (#770/#771)
4. Removing dead code is simpler than maintaining or wiring it (KISS)

**Risk:** If some future hook wants session-start context data, it would need
a new mechanism. This is a YAGNI concern — build it when needed.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Remove dead ContextInjectionHook" --priority nice-to-have --status ideation --tags "agent,scope:core,cleanup" --body "Delete ContextInjectionHook class, bootstrap registration, and tests since both outputs (instructions, kanban_summary) have zero readers. instructions is redundant with ContextManager; kanban_summary is superseded by BoardContextProvider (#770/#771). See docs/research/context-injection-hook-dead-code.md.\n\nAC:\n- [ ] src/owlbear/core/context_hook.py deleted\n- [ ] ContextInjectionHook() removed from src/owlbear/bootstrap/hooks.py\n- [ ] tests/test_context_hook.py deleted or tests removed\n- [ ] ContextInjectionHook test removed from tests/test_session_hooks.py\n- [ ] SessionStartData.context field retained (other hooks may use it)\n- [ ] All existing tests pass (no regressions)\n- [ ] ruff clean"
```
