# Programmatic Agent Registration API

> **Owning task:** #559 — Add programmatic agent registration API
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

`AgentRegistry.scan()` discovers agents by globbing `*.md` files from a directory
(lines 90-107 of `agent_registry.py`). There is no `register(defn)` method — all agents
must be file-backed. ARC-16 in the architecture audit flagged this as a LOW concern.

**Research question:** Is a programmatic `register()` method needed, and if so, what's
the simplest implementation that doesn't break existing assumptions?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PydanticAI Agent docs | <https://ai.pydantic.dev/agents/> | .85 — PydanticAI agents are plain objects, no registry. Programmatic by default. |
| PydanticAI Multi-Agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | .80 — Delegation uses direct `Agent()` construction, no file scanning. |
| CrewAI Agents docs | <https://docs.crewai.com/concepts/agents> | .90 — Dual approach: YAML config (recommended) + direct code definition. Both first-class. |
| OwlBear `AgentRegistry` | `src/owlbear/core/agent_registry.py` | 1.0 — Current implementation, scan-only. |
| OwlBear `AgentDefinition` | `src/owlbear/core/agent_def.py` | 1.0 — Pydantic model, no file coupling. |
| OwlBear `bootstrap.py` | `src/owlbear/bootstrap.py:805-813` | 1.0 — Only caller; calls `scan()` then uses `get()`. |
| OwlBear agent registry tests | `tests/test_agent_registry.py` | 1.0 — All tests use scan(). No register() coverage. |

## 3. Analysis

### 3.1 Prior Art: Registration Patterns

| Framework | File-based | Programmatic | Registry object | Notes |
|-----------|-----------|-------------|----------------|-------|
| PydanticAI | No | Yes (only) | No | Agents are plain objects. No central registry. |
| CrewAI | YAML (recommended) | Direct `Agent()` | `@CrewBase` decorator | Both paths are first-class. YAML for config, code for dynamic. |
| OwlBear (current) | `scan()` globs `.md` | **Not supported** | `AgentRegistry` | Only path is file discovery. |

**Key insight:** Both PydanticAI (code-only) and CrewAI (YAML + code) treat programmatic
agent creation as a first-class citizen. OwlBear's file-only approach is the outlier.

### 3.2 Use Cases for Programmatic Registration

| Use case | Severity | Current workaround |
|----------|----------|-------------------|
| Unit tests creating agents without temp .md files | Medium | Tests must write `.md` files to disk |
| Dynamic agents (e.g., project-specific agent with runtime prompt) | Low | Not possible without file write |
| Agent composition in code (bootstrap wiring) | Low | Must go through file system |
| Plugin/extension agents from external packages | Future | Not possible |

### 3.3 Implementation Difficulty

| Aspect | Assessment |
|--------|-----------|
| `AgentDefinition` model | **Already decoupled** — Pydantic model, no file path dependency |
| `_definitions` dict | **Simple dict** — `register()` just does `self._definitions[defn.name] = defn` |
| `_build_agent()` | **No file dependency** — Takes `AgentDefinition`, doesn't touch filesystem |
| Cache invalidation | **Trivial** — Just pop the name from `_cache` if re-registering |
| `scan()` behavior | **Clears all** — `scan()` calls `_definitions.clear()` + `_cache.clear()` |
| Validation | **Pydantic handles it** — `AgentDefinition` validates on construction |

The only design question: should `scan()` wipe programmatic registrations?

### 3.4 `scan()` + `register()` Interaction

| Option | Behavior | KISS | Risk |
|--------|----------|------|------|
| A: `scan()` wipes everything | `scan()` clears all definitions including programmatic ones | High | Programmatic agents lost on re-scan |
| B: `scan()` only clears file-scanned | Track source (file vs programmatic), scan only clears file-sourced | Medium | Added complexity for tracking source |
| C: No change to `scan()` | `scan()` clears all; user calls `register()` after `scan()` | **Highest** | Ordering dependency, but explicit |

**Recommendation (.85 confidence): Option C.** KISS-aligned. `scan()` already clears everything,
and in practice `scan()` is called once at bootstrap. Programmatic registrations happen after.
If we need Option B later, it's a backward-compatible addition.

## 4. Recommendation (.85 confidence)

Add a single `register(defn: AgentDefinition)` method to `AgentRegistry`:

```python
def register(self, defn: AgentDefinition) -> None:
    """Register a programmatic agent definition.

    If *name* already exists, the cached Agent is evicted so the next
    ``get()`` call rebuilds it from the new definition.
    """
    self._cache.pop(defn.name, None)
    self._definitions[defn.name] = defn
    logger.debug("Registered agent definition (programmatic): %s", defn.name)
```

**Why this is sufficient:**

- `AgentDefinition` is already a standalone Pydantic model — no file path coupling
- `_build_agent()` only reads from `AgentDefinition` fields — no filesystem access
- Pydantic validation happens at `AgentDefinition` construction time
- Cache eviction on re-register prevents stale agents
- No changes needed to `scan()`, `get()`, `list_agents()`, or `definitions`
- ~8 LOC change + tests

**Risks:**

- `scan()` clears programmatic registrations — acceptable per Option C analysis
- Name collision between file-scanned and programmatic agents — last-write-wins is fine

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement AgentRegistry.register(defn) method" --priority nice-to-have --tags "refactor,scope:core" --body "Add register(defn: AgentDefinition) method to AgentRegistry. Cache-evict on re-register. ~8 LOC. AC: (1) register() adds definition to _definitions dict, (2) get() returns agent built from registered definition, (3) re-register evicts stale cache, (4) scan() still clears all including programmatic, (5) list_agents() includes programmatic definitions. See docs/programmatic-agent-registration-research.md"

kanban\kanban-md.exe create "Add tests for AgentRegistry.register()" --priority nice-to-have --tags "test,scope:core" --body "Test cases: (1) register then get returns valid Agent, (2) register appears in list_agents/definitions, (3) re-register evicts cache, (4) scan() clears programmatic registrations, (5) name collision file+programmatic last-write-wins. See docs/programmatic-agent-registration-research.md"
```
