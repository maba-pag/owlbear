# Eliminate Post-Construction Patching in Bootstrap

> **Owning task:** #523 — Eliminate post-construction patching in bootstrap
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

ARC-14 in `docs/architecture-audit.md` identifies two post-construction patching sites in `bootstrap()` that create temporal coupling — code running between construction and patching sees incomplete state:

1. **`agent_registry`** — `agent.set_agent_registry(agent_registry)` called after `OwlBearAgent` construction (bootstrap.py L978).
2. **`ProjectToolset._agent`** — placeholder object created at toolset build time, patched with real agent via `_patch_project_toolset_agent()` (bootstrap.py L982).

**Question:** What is the simplest way to eliminate both patching sites while preserving current behavior?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Fowler — DI and IoC | <https://martinfowler.com/articles/injection.html> | .85 — constructor injection as preferred DI form; avoid setter injection when constructor is feasible |
| python-dependency-injector docs | <https://python-dependency-injector.ets-labs.org/introduction/di_in_python.html> | .70 — DI principles in Python; constructor injection vs service locator trade-offs |
| OwlBear bootstrap.py | `src/owlbear/bootstrap.py` L866–993 | 1.0 — primary source; construction order analysis |
| OwlBear ProjectToolset | `src/owlbear/projects/toolset.py` L35–130 | 1.0 — actual agent access patterns |
| OwlBear OwlBearDeps | `src/owlbear/core/deps.py` | 1.0 — deps dataclass with optional `agent_registry` |
| OwlBear DelegationToolset | `src/owlbear/core/delegation.py` | 1.0 — runtime consumer of `agent_registry` |

## 3. Analysis

### 3.1 Root Cause — Is There a Real Circular Dependency?

**Site 1 (`agent_registry`): No circular dependency.** Bootstrap construction order:

| Step | Object | Depends On |
|------|--------|------------|
| 4 | `toolsets` | settings, workspace, hooks, channel |
| 6 | `agent_registry` | settings, **toolsets** |
| 8 | `OwlBearAgent` | model, session, context, **toolsets** |

The registry is built at step 6, the agent at step 8. The registry does NOT need the agent. The patching exists only because `OwlBearAgent.__init__` doesn't accept `agent_registry` — it constructs `OwlBearDeps` internally without it.

**Site 2 (`ProjectToolset._agent`): Apparent circular dependency, but false.** `ProjectToolset` accesses exactly three properties from `self._agent`:

| Access Site | What It Uses | Created At |
|-------------|--------------|------------|
| `self._agent.session.path = ...` | `SessionStore` | Step 7 |
| `getattr(self._agent, "context", None)` | `ContextManager` | Step 7 |
| `getattr(self._agent, "toolsets", [])` | `list[AbstractToolset]` | Step 4 |

All three exist before the agent. `ProjectToolset` doesn't need the agent — it needs `session`, `context`, and `toolsets`.

### 3.2 Options Comparison

| Criterion | A: Direct deps (.90) | B: Lazy callback (.65) | C: Protocol (.55) | D: Reorder (.40) |
|-----------|----------------------|------------------------|--------------------|-------------------|
| Eliminates patching | Yes — both sites | Site 1 only; site 2 still deferred | Yes — both sites | Requires PydanticAI Agent mutation |
| LOC changed | ~30 | ~15 | ~40 (new type + refactor) | Unknown — depends on PydanticAI API |
| KISS | High | Medium (closure capture) | Low (over-engineered) | Low (fragile) |
| YAGNI | High | Medium | Low (protocol not needed elsewhere) | Medium |
| Testability | High (explicit deps) | Medium (must mock callable) | High | Medium |
| Risk | Low — mechanical refactor | Low but still temporal coupling | Low but unnecessary abstraction | High — depends on upstream API |

### 3.3 Option A Detail — Direct Dependency Injection

**Site 1 fix:** Add `agent_registry: AgentRegistry | None = None` parameter to `OwlBearAgent.__init__`; pass it to `OwlBearDeps`. Delete `set_agent_registry()`.

**Site 2 fix:** Change `ProjectToolset.__init__` signature from `agent: object` to `session: SessionStore, context: ContextManager | None, toolsets: list[AbstractToolset]`. Replace `self._agent.session` → `self._session`, etc. Delete `bind_agent()`, `_add_project_toolset` placeholder logic, and `_patch_project_toolset_agent`.

Both are consistent with Fowler's recommendation: "my preference is to start with constructor injection" and "Constructors with parameters give you a clear statement of what it means to create a valid object."

## 4. Recommendation (.90 confidence)

**Option A — Direct dependency injection** for both sites.

- Site 1 is trivial: add constructor param, remove setter.
- Site 2 requires `ProjectToolset` to accept `session`, `context`, `toolsets` instead of an opaque `agent` reference. All three are available at construction time.
- Eliminates `_add_project_toolset` placeholder creation, `_patch_project_toolset_agent`, `bind_agent`, and `set_agent_registry`.
- Risk: low — mechanical refactor with clear test coverage path.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add agent_registry param to OwlBearAgent constructor" --priority needed --status backlog --tags "refactor,scope:core" --body "Remove set_agent_registry() setter. Add agent_registry: AgentRegistry | None = None to __init__, pass to OwlBearDeps. Update bootstrap() to pass agent_registry= at construction. Delete set_agent_registry(). See docs/research/bootstrap-patching-elimination.md."

kanban\kanban-md.exe create "Refactor ProjectToolset to accept direct deps instead of agent" --priority needed --status backlog --tags "refactor,scope:core" --body "Change ProjectToolset.__init__ to accept session: SessionStore, context: ContextManager | None, toolsets: list[AbstractToolset] instead of agent: object. Update all self._agent.X accesses. Delete bind_agent(), _add_project_toolset placeholder logic, _patch_project_toolset_agent. Update bootstrap() to pass direct deps. See docs/research/bootstrap-patching-elimination.md."

kanban\kanban-md.exe create "Add tests for ProjectToolset without agent placeholder" --priority needed --status backlog --tags "test,scope:core" --body "Write unit tests confirming ProjectToolset works with direct session/context/toolsets injection. Verify switch_project updates session path, context root, and toolset workspace roots. No placeholder or bind_agent needed. See docs/research/bootstrap-patching-elimination.md."
```
