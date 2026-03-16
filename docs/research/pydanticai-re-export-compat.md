# PydanticAI Compatibility: No Re-exports Decision

> **Owning task:** #813 — Add re-exports to auth, planning, projects, providers, safety `__init__.py`
> **Date:** 2026-03-15  **Status:** Complete

## 1. Context and Question

Decision #813 was resolved: Option A — do NOT add re-exports, remove existing ones.
The user's approval note: "Make sure Pydantic AI, which this project will run on,
once it leaves the initial VS Code dev stage, is fully compatible with this decision."

This doc validates that PydanticAI has **no requirements** on consumer package
`__init__.py` re-exports, confirming the decision is safe.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PydanticAI v1.63.0 source (installed) | `.venv/Lib/site-packages/pydantic_ai/` | 1.0 — direct inspection |
| PydanticAI Agent docs | <https://ai.pydantic.dev/agents/> | .95 — official API docs |
| PydanticAI Toolsets docs | <https://ai.pydantic.dev/toolsets/> | .95 — official toolset docs |
| OwlBear bootstrap module | `src/owlbear/bootstrap/` | 1.0 — how OwlBear wires PydanticAI |

## 3. Analysis

### 3.1 PydanticAI tool discovery mechanism

PydanticAI discovers tools through **explicit registration**, not import scanning:

| Mechanism | How it works | Scans `__init__.py`? |
|-----------|-------------|---------------------|
| `Agent(toolsets=[...])` | Caller passes toolset instances | No |
| `FunctionToolset.add_function()` | Explicit registration | No |
| `@agent.tool` decorator | Decorator on function | No |
| `Agent(tools=[...])` | Caller passes tool list | No |
| `@agent.toolset` | Dynamic builder from RunContext | No |

Verified via source inspection: `AbstractToolset` has no `__init_subclass__` registry,
no `pkgutil` scanning, no `importlib` discovery. `Agent.__init__` accepts explicit
parameters only.

### 3.2 OwlBear → PydanticAI integration is one-directional

```text
OwlBear imports from PydanticAI:  from pydantic_ai import Agent
PydanticAI imports from OwlBear:  NEVER (0 occurrences)
```

PydanticAI is a library OwlBear consumes. It never imports from `owlbear.*`.
Whether `owlbear.auth.__init__.py` has re-exports is invisible to PydanticAI.

### 3.3 OwlBear's wiring pattern (bootstrap)

OwlBear assembles PydanticAI components in `bootstrap/__init__.py`:

1. Creates toolsets: `FileToolset(...)`, `KanbanToolset(...)`, etc.
2. Wraps them: `HookedToolset(wrapped=ts)`, `ApprovalGateToolset(wrapped=ts)`
3. Passes to Agent: `Agent(model, toolsets=toolsets)`

All OwlBear imports are deep: `from owlbear.tools.filesystem import FileToolset`.
Zero imports go through `__init__.py` re-exports. This works identically whether
`__init__.py` files are empty or have re-exports.

### 3.4 Standalone daemon scenario

The daemon (`owlbear.daemon`) already runs outside VS Code. It imports:

- `from pydantic_ai import Agent` (PydanticAI)
- `from owlbear.core.errors import ...` (deep import)
- `from owlbear.providers.copilot import create_copilot_client` (deep import)

No daemon code path uses or requires `from owlbear.auth import X` short paths.

### 3.5 Why PydanticAI itself uses re-exports (not applicable to OwlBear)

PydanticAI's `__init__.py` has a massive `__all__` (180+ symbols) because it is a
**public library** — external users write `from pydantic_ai import Agent`. OwlBear is
an **application** with no external consumers. The pattern doesn't transfer.

## 4. Recommendation (.95 confidence)

**Decision A is fully PydanticAI-compatible.** No changes needed.

PydanticAI never scans, imports from, or inspects OwlBear's package structure.
Tool discovery is 100% explicit (caller-provided toolsets). The "leave VS Code"
scenario (standalone daemon) already works with deep imports and is unaffected
by `__init__.py` content.

Risk: If OwlBear ever exposes a public Python API (plugin SDK), re-exports would
be reconsidered — but that's a hypothetical future requirement (YAGNI).

## 5. Follow-up Tasks

No new tasks needed. Existing tasks #822 (implement removal) and #823 (close #813)
already have correct AC and can proceed unblocked.
