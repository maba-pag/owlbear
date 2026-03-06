# Eliminating SLF001 Suppressions via Public APIs

> **Owning task:** #466 — Add public APIs to eliminate SLF001 suppressions
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

The codebase has 10 `# noqa: SLF001` suppressions in production code where modules reach into private attributes of other classes. Should we add public APIs to eliminate these? What form should each API take?

## 2. Sources Studied

| Source | URL | Relevance |
|---|---|---|
| Ruff SLF001 rule docs | <https://docs.astral.sh/ruff/rules/private-member-access/> | 1.0 — Defines the violation and Pythonic fix: use public interface |
| PEP 8 §Designing for Inheritance | <https://peps.python.org/pep-0008/#designing-for-inheritance> | .95 — "use properties to hide functional implementation behind simple data attribute access syntax" |
| Real Python — property() | <https://realpython.com/python-property/> | .85 — Pattern reference for property/setter approaches |
| Python dataclasses docs | <https://docs.python.org/3/library/dataclasses.html> | .80 — `dataclasses.replace` semantics for renaming fields |

## 3. Analysis — Violation Inventory

| # | File | Private access | Accessor | Fix approach |
|---|---|---|---|---|
| 1 | `bootstrap.py:937` | `agent._deps.agent_registry = …` | Write | Make `agent_registry` already public (it is!) — remove `_deps` indirection |
| 2 | `bootstrap.py:814` | `inner._agent = agent` | Write | `ProjectToolset.bind_agent(agent)` method |
| 3 | `projects/toolset.py:152` | `inner._workspace_root = …` | Write | `WorkspaceAware` protocol with `update_workspace(path)` |
| 4 | `projects/toolset.py:154` | `inner._root = …` | Write | Same `update_workspace(path)` method — sets both |
| 5 | `delegation.py:97` | `ctx.deps._delegation_depth` | Read | `delegation_depth` property on `OwlBearDeps` |
| 6-10 | `dedup.py:124-144` | `graph._conn` (×4), `graph._dump_meta` (×1) | Read+Write | `GraphStore.merge_entities()` public method |

## 4. Recommendation per Violation Group

### 4a. OwlBearDeps._delegation_depth → property (.90 confidence)

**Current:** `_delegation_depth` is a dataclass field with `_` prefix. Read in `delegation.py`, replaced via `dataclasses.replace()`.

**Fix:** Rename field to `delegation_depth` (public). No property needed — it's a plain dataclass field. `dataclasses.replace()` works identically. Update the one read site and one replace site.

**Risk:** Tests access `_delegation_depth` directly — update references. Low risk.

### 4b. agent._deps.agent_registry → setter on OwlBearAgent (.85 confidence)

**Current:** Bootstrap reaches through `agent._deps` to set `agent_registry` after agent construction. `_deps` is the private `OwlBearDeps` on the agent.

**Fix:** Add `OwlBearAgent.set_agent_registry(registry)` method that delegates to `self._deps.agent_registry = registry`. Alternatively, accept `agent_registry` as a constructor parameter and restructure bootstrap order. Setter is the simpler fix.

**Risk:** Minimal — single call site.

### 4c. ProjectToolset._agent → bind_agent() (.90 confidence)

**Current:** Bootstrap patches `_agent` after creating the toolset (chicken-and-egg: toolset needs agent, but agent needs toolset list).

**Fix:** Public `ProjectToolset.bind_agent(agent)` method. Clear intent, single call site.

### 4d. _workspace_root/_root mutation → WorkspaceAware protocol (.85 confidence)

**Current:** `_update_toolset_roots()` uses `hasattr` duck-typing to find and mutate `_workspace_root` and `_root` on arbitrary toolset objects.

**Fix:** Define a `WorkspaceAware` `Protocol` with `update_workspace(self, workspace: Path) -> None`. Toolsets that need workspace switching implement it. The walker checks `isinstance(inner, WorkspaceAware)` instead of `hasattr`. Each toolset's `update_workspace()` sets its own internals.

Affected toolsets: `TerminalToolset`, `GitLocalToolset`, `FileToolset`, `KnowledgeToolset`, `KnowledgeSourceToolset`, `RefreshOrchestrator`.

**Risk:** Medium — touches 5-6 toolset classes. But each change is a 3-line method addition.

### 4e. GraphStore._conn/_dump_meta in dedup → merge_entities() (.90 confidence)

**Current:** `deduplicate_entities()` reaches into `GraphStore._conn` for raw SQL (metadata update, edge redirect, commit) and `_dump_meta` for serialization. 5 suppressions from one function.

**Fix:** Add `GraphStore.merge_entities(canonical_id, duplicate_ids, merged_metadata)` that encapsulates the SQL (update metadata, redirect edges, delete duplicates, commit). Dedup calls this instead of raw SQL. Eliminates all 5 suppressions at once.

**Risk:** Low — the SQL is already isolated in one function. Moving it into GraphStore is natural.

## 5. Trade-off: Public API vs. Restructuring

| Criterion | Add public APIs (.85) | Deep restructure (.60) |
|---|---|---|
| Diff size | ~100 LOC across 8 files | ~300+ LOC, constructor changes |
| Risk | Low — additive | Medium — bootstrap order, test rewrites |
| KISS | Simple methods/properties | Over-engineered for 10 suppressions |
| YAGNI | Solves exact problem | Solves hypothetical future needs |
| Test impact | Update ~10 test lines | Rewrite bootstrap integration tests |

**Verdict:** Add public APIs. It's the Pythonic approach per PEP 8 and Ruff docs.

## 6. Testing Strategy

1. After implementation: `uv run ruff check src/ --select SLF001` — must return 0 violations
2. Existing tests should continue to pass (public API is additive)
3. Tests using `_delegation_depth` directly: update to use `delegation_depth`
4. Can optionally remove `SLF001` from `pyproject.toml` test ignores if tests no longer need it

## 7. Follow-up Tasks

See section below for kanban commands — 4 atomic implementation tasks.
