# Declarative Tool Registration for Toolsets

> **Owning task:** #538 — Evaluate declarative tool registration for toolsets
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

YAGNI-01 from `docs/software-design-audit.md`: all 14 `FunctionToolset` subclasses follow identical ceremony — `__init__` → `super().__init__()` → `_register_tools()` → N × `add_function(self._method, name=..., description=...)`. The question: should we replace this with a declarative pattern (decorator or `ClassVar`), or accept the explicitness?

**Scope:** 14 toolsets, 49 `add_function()` calls total. Largest: `GitLocalToolset` (7 tools), `KanbanToolset` (7 tools). Smallest: `AskUserToolset`, `DelegationToolset`, `TerminalToolset` (1 tool each).

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | PydanticAI Toolsets docs (v1.67) | <https://ai.pydantic.dev/toolsets/> | 1.0 |
| 2 | PydanticAI `FunctionToolset` source (v1.63) | `pydantic_ai/toolsets/function.py` (installed) | 1.0 |
| 3 | PydanticAI GitHub issues | <https://github.com/pydantic/pydantic-ai/issues?q=declarative+tool+registration> | 0.6 |
| 4 | pydantic-ai-skills (`SkillsToolset`) | <https://github.com/DougTrajano/pydantic-ai-skills> | 0.5 |

## 3. Analysis

### 3.1 What PydanticAI offers today

PydanticAI provides three ways to register tools on a `FunctionToolset`:

| Method | Level | How it works |
|--------|-------|--------------|
| `@toolset.tool` decorator | Instance | Decorate a function on an *instance* — not a class method |
| `tools=` constructor arg | Instance | Pass plain functions or `Tool` objects at instantiation |
| `add_function()` / `add_tool()` | Instance | Imperative call after construction (what OwlBear uses) |

**Key finding:** PydanticAI has **no class-level declarative API**. The `@toolset.tool` decorator works on instances, not on class method definitions. There is no `__init_subclass__` hook, metaclass, or `ClassVar`-based auto-registration in the framework. No GitHub issues request this feature (0 results for "declarative tool registration").

### 3.2 What a custom declarative system would require

| Option | Mechanism | LOC to build | Complexity | KISS-aligned? |
|--------|-----------|-------------|------------|---------------|
| A: `@tool` method decorator | Decorator stores metadata on the method; `__init_subclass__` or `__init__` scans `cls.__dict__` and calls `add_function()` per decorated method | ~60–80 | Medium — metaclass-adjacent, interacts with MRO | No |
| B: `tools: ClassVar[list]` | Tuples of `(method_name, tool_name, description)` in a class variable; `__init__` iterates and calls `add_function()` | ~30–40 | Low–Medium — moves ceremony from code to data | Marginal |
| C: Convention-based scan | Scan for methods matching `_tool_*` prefix; derive name/description from docstring | ~40–50 | Medium — implicit naming, fragile | No |

### 3.3 Cost-benefit comparison

| Criterion | Current pattern | Option A (@tool) | Option B (ClassVar) |
|-----------|----------------|-------------------|---------------------|
| Lines saved per toolset | 0 | ~3–5 LOC per tool | ~2–3 LOC per tool |
| Framework LOC added | 0 | ~60–80 | ~30–40 |
| Debugging transparency | High (explicit calls) | Lower (magic scan) | Medium |
| PydanticAI alignment | Native API | Custom layer on top | Custom layer on top |
| Upgrade risk | None | Must maintain compat with FunctionToolset internals | Same |
| Bug surface from ceremony | **None observed** | N/A | N/A |
| New contributor onboarding | Pattern is obvious | Must learn custom framework | Must learn convention |

### 3.4 Is the ceremony actually a problem?

| Check | Result |
|-------|--------|
| Has it caused bugs? | No — zero bugs traced to `_register_tools` pattern |
| Is it copy-paste error-prone? | No — each toolset has unique tools; no duplication |
| Does it slow development? | No — toolsets are write-once, rarely modified |
| Is it inconsistent across toolsets? | No — all 14 follow the exact same structure |
| Does PydanticAI discourage it? | No — `add_function()` is a documented, first-class API |

## 4. Recommendation

**Defer as YAGNI** (.90 confidence)

The registration ceremony is mechanical but harmless. It follows PydanticAI's native API, causes no bugs, and is consistent across all 14 toolsets. Building a custom declarative layer would:

- Add 30–80 LOC of framework code to save ~3 LOC per toolset (~42 LOC total)
- Introduce a non-standard abstraction that new contributors must learn
- Create an upgrade-risk surface if PydanticAI changes `FunctionToolset` internals
- Violate KISS and YAGNI — solving a non-problem with custom infrastructure

If PydanticAI adds a class-level declarative API in the future, we should adopt it. Until then, the explicit pattern is the right choice.

**Risk:** None. The status quo is stable and well-understood.

## 5. Follow-up Tasks

No implementation tasks needed — this is a "defer" decision. The task itself documents the decision.

```
kanban\kanban-md.exe edit 538 --body "YAGNI-01 evaluation complete. Decision: DEFER. The _register_tools ceremony is harmless — no bugs, consistent pattern, PydanticAI native API. Building a custom declarative layer (decorator or ClassVar) would add 30-80 LOC of framework code to save ~3 LOC per toolset, violating KISS/YAGNI. If PydanticAI adds class-level declarative registration, adopt it then. See docs/research/declarative-tool-registration.md."
kanban\kanban-md.exe move 538 backlog
```
