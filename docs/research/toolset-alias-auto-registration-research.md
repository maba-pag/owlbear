# Toolset Alias Auto-Registration

> **Owning task:** #488 — Auto-register toolset aliases instead of hardcoded map
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`build_agent_registry()` in `bootstrap.py` (L782-793) has a hardcoded `_aliases` dict mapping 11 short names (e.g. `"filesystem"` → `"FileToolset"`) so agent `.md` definitions can reference tools by alias. Adding a toolset requires manually updating this dict. Four toolsets are already missing: `BookmarkToolset`, `VisualFeedbackToolset`, `KnowledgeSourceToolset`, `ProjectToolset`.

**Question:** What is the simplest way to make the alias map derive automatically from the toolset classes themselves?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PEP 487 — `__init_subclass__` | https://peps.python.org/pep-0487/ | .90 — Canonical Python pattern for subclass auto-registration |
| Python Data Model — `__init_subclass__` | https://docs.python.org/3/reference/datamodel.html#object.__init_subclass__ | .85 — Official reference for the hook |
| PydanticAI `FunctionToolset` source | `.venv/Lib/site-packages/pydantic_ai/toolsets/function.py` | .80 — Base class; no built-in alias/name mechanism |
| OwlBear `bootstrap.py` L759-830 | `src/owlbear/bootstrap.py` | 1.0 — Current implementation to replace |
| OwlBear architecture/integration audits | `docs/architecture-audit.md`, `docs/integration-audit.md` | .70 — ARC-15 / INT-12 describe the problem |

## 3. Analysis

### Current flow

1. `build_agent_registry()` receives `toolsets: list[AbstractToolset]`
2. Unwraps wrapper chain (`HookedToolset` → `ApprovalGateToolset` → inner)
3. Builds `tool_map: {ClassName → toolset_instance}`
4. `_resolve(name)` checks `tool_map` first, then falls back to `_aliases` dict
5. Agent `.md` files list tools by alias: `- filesystem`, `- kanban`, etc.

### Options

| Criterion | A: `tool_alias` class attr | B: `__init_subclass__` registry | C: Derive from class name |
|-----------|---------------------------|--------------------------------|--------------------------|
| KISS | **High** — one line per class | Medium — need mixin in hierarchy | Medium — needs fallback map |
| Accuracy | Exact — author sets alias | Exact — author sets alias | Partial — 3 of 15 fail |
| YAGNI | Minimal — no new infra | Adds global registry dict | Adds snake_case util |
| Invasiveness | 1 attr per toolset class | Mixin or base class change | Change resolver only |
| Discoverability | Grep `tool_alias` | Grep registry dict | Implicit — hard to trace |
| FunctionToolset compat | Works — plain attr | Need mixin (can't modify PydanticAI) | N/A |
| Edge cases | None | Import-order sensitivity | `FileToolset→file` ≠ `filesystem`, `GitHubToolset→git_hub` ≠ `github`, `SkillRegistry` has no `Toolset` suffix |

### Option A detail (recommended)

Each `FunctionToolset` subclass declares:

```python
class FileToolset(FunctionToolset):
    tool_alias = "filesystem"
```

In `build_agent_registry()`, replace the hardcoded dict with:

```python
_aliases: dict[str, str] = {}
for ts in toolsets:
    inner = ts
    while hasattr(inner, "wrapped"):
        inner = inner.wrapped
    cls = type(inner)
    name = cls.__name__
    tool_map[name] = ts
    alias = getattr(cls, "tool_alias", None)
    if alias:
        _aliases[alias] = name
```

### Option B detail

A mixin `RegisteredToolset` with `__init_subclass__` that collects into a module-level dict. Problem: `FunctionToolset` is from PydanticAI — we can't modify it. We'd need a mixin between FunctionToolset and our subclasses, touching every toolset's inheritance. More churn for same result.

### Option C detail

Auto-derive `KanbanToolset` → `kanban`, `TerminalToolset` → `terminal` by stripping `Toolset` suffix and snake_casing. Fails for `FileToolset` (want `filesystem`, derive `file`), `GitHubToolset` (want `github`, derive `git_hub`), `SkillRegistry` (no suffix). Would still need an override map for exceptions — partial solution at best.

## 4. Recommendation (.90 confidence)

**Option A: `tool_alias` class attribute.** Simplest, most explicit, zero infrastructure. Each of the 15 toolset classes gets one line. The resolver in `build_agent_registry()` reads it dynamically. No new modules, no metaclass tricks, no import-order issues.

Risk: Forgetting to set `tool_alias` on a new toolset means it's only discoverable by class name (existing behavior). Mitigation: add a unit test that asserts every `FunctionToolset` subclass in the toolsets list has a `tool_alias`.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add tool_alias class attribute to all FunctionToolset subclasses" --priority needed --tags "refactor,scope:core,phase-12" --description "Add tool_alias = '...' to each of the 15 toolset classes (FileToolset='filesystem', TerminalToolset='terminal', AskUserToolset='ask_user', BrowserToolset='browser', DelegationToolset='delegation', GitLocalToolset='git_local', GitHubToolset='github', KanbanToolset='kanban', KnowledgeToolset='knowledge', WebSearchToolset='web_search', BookmarkToolset='bookmark', VisualFeedbackToolset='visual_feedback', KnowledgeSourceToolset='knowledge_source', ProjectToolset='project'). SkillRegistry gets tool_alias='skills'. AC: every FunctionToolset subclass has tool_alias set. See docs/toolset-alias-auto-registration-research.md."

kanban\kanban-md.exe create "Replace hardcoded _aliases dict with dynamic tool_alias discovery" --priority needed --tags "refactor,scope:core,phase-12" --description "In build_agent_registry(), replace the hardcoded _aliases dict with a loop that reads tool_alias from each toolset class. Delete the static dict. AC: no hardcoded alias map, resolver still works for all 15 toolsets, existing tests pass. See docs/toolset-alias-auto-registration-research.md." --depends-on 488

kanban\kanban-md.exe create "Add test: every toolset has tool_alias" --priority important --tags "test,scope:core,phase-12" --description "Unit test that iterates all toolsets passed to build_agent_registry and asserts each inner class has a non-empty tool_alias attribute. Catches missing aliases on new toolsets. AC: test exists, passes, covers all 15 current toolsets. See docs/toolset-alias-auto-registration-research.md."
```
