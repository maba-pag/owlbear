# P8 Agent Framework — Definition, Registry, and Delegation

> **Owning tasks:** #128, #129, #130
> **Date:** 2026-02-27
> **Status:** Complete
> **Depends on:** #153 (OwlBearDeps), #127 (prior research — complete)

## 1. Context and Question

Phase 8 introduces OwlBear's multi-agent framework: how agents are *defined*, *registered*, and *delegated to*. Prior research (#127, `docs/research/pydantic-ai-multi-agent.md`) confirmed PydanticAI level-2 delegation, markdown definitions, and `OwlBearDeps` for DI. This document deepens those findings into implementation-ready specifications.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | .95 | Agent delegation pattern, deps/usage passing, UsageLimits |
| PydanticAI toolsets docs | <https://ai.pydantic.dev/toolsets/> | .90 | CombinedToolset, FilteredToolset, WrapperToolset |
| CrewAI agents docs | <https://docs.crewai.com/concepts/agents> | .85 | Agent attributes (role/goal/backstory), YAML config, `allow_delegation` |
| CrewAI crews docs | <https://docs.crewai.com/concepts/crews> | .80 | Crew orchestration, hierarchical process, manager agent |
| OwlBear SkillRegistry | `src/owlbear/skills/registry.py` | 1.0 | Existing YAML-frontmatter + markdown registry pattern |
| OwlBear RolePolicy | `src/owlbear/core/roles.py` | 1.0 | Existing `apply_role_policy` / `.filtered()` pattern |
| OwlBear #127 research | `docs/research/pydantic-ai-multi-agent.md` | .95 | Prior art analysis, 12 toolset types, DI, delegation |
| PydanticAI flight_booking example | `examples/flight_booking.py` in pydantic-ai repo | .90 | Real delegation: shared deps, usage tracking |
| Nanobot SubagentManager | <https://github.com/HKUDS/nanobot> | .75 | Restricted tool sets per subagent, max iterations |

## 3. Analysis

### 3.1 Agent Definition Format (#128)

**Question:** What format should agent definitions use?

| Approach | Description | Prior Art | KISS | OwlBear Fit |
|----------|-------------|-----------|------|-------------|
| A. **Markdown (YAML frontmatter + body)** | Frontmatter = config, body = system prompt | Claude `.agent.md`, OwlBear SkillRegistry | High | **Best** |
| B. YAML-only config | Separate YAML file, prompt in a field | CrewAI `agents.yaml` | Medium | Splits prompt from config |
| C. Python dataclass/code | `Agent(...)` in Python | PydanticAI native | Medium | Ties definitions to code |
| D. Pydantic model config file | TOML/JSON with Pydantic validation | pydantic-settings | Medium | Over-engineered for prompts |

**Recommendation (.90):** Approach A — markdown files. Body = system prompt (injected as PydanticAI `instructions`). Frontmatter validated by a Pydantic `AgentDefinition` model. Consistent with our SkillRegistry pattern.

**AgentDefinition fields:** `name` (str, required), `description` (str, required), `role` (str, default `"builder"`), `model` (str|None, default None), `tools` (list[str], default []), `skills` (list[str], default []), `max_delegation_depth` (int, default 3), `system_prompt` (str, populated from body).

**Example** (`.owlbear/agents/coder.md`):

```yaml
---
name: coder
description: Implements code changes using TDD
role: builder
tools: [filesystem, terminal]
skills: [kanban-md, kanban-based-development]
---
You are a coder agent. Implement kanban tasks using TDD.
```

**Parser:** `parse_agent_definition(path) -> AgentDefinition` — follows SkillRegistry `_parse_frontmatter` pattern. ~30 LOC.

### 3.2 Agent Registry (#129)

**Question:** How to register agents for lookup by name?

| Pattern | Description | Prior Art | Complexity |
|---------|-------------|-----------|------------|
| A. **Directory-scanning registry class** | Scan `.md` files, lazy instantiate on `get()` | OwlBear SkillRegistry | Low |
| B. Decorator-based | `@registry.agent` decorator on factory methods | CrewAI `@agent` decorator | Medium |
| C. Global dict singleton | `AGENTS: dict[str, Agent] = {}` | Simple but untestable | Low |
| D. DI-container service | Full DI framework manages lifecycle | Spring-style, over-engineered | High |

**Recommendation (.90):** Approach A — modeled after `SkillRegistry`. Scans a directory, stores `AgentDefinition` metadata, lazily instantiates PydanticAI `Agent` on first `get()`. Testable (inject dir), config-driven, avoids global state.

**Key design decisions:** (1) Lazy instantiation — definitions parsed at scan time, Agent built on first `get()`. (2) Tool resolution via injected `tool_resolver: Callable[[str], AbstractToolset]`. (3) Skill resolution via optional `SkillRegistry` passed at construction. (4) Role policy via `FilteredToolset` from existing `roles.py`.

**Registry API:** `AgentRegistry(agents_dir, tool_resolver, skill_registry?, default_model?)` with methods `scan()`, `get(name) -> Agent`, `list_agents() -> list[AgentDefinition]`, and `definitions` property.

### 3.3 Agent Delegation (#130)

**Question:** How does an orchestrator dispatch subtasks to inner agents?

PydanticAI's canonical delegation pattern is: a tool function on the outer agent calls `inner_agent.run()`, passing `ctx.deps` and `ctx.usage`. This is documented, tested, and exactly what we need.

**Delegation patterns compared:**

| Pattern | Description | Prior Art | OwlBear Fit |
|---------|-------------|-----------|-------------|
| A. **Tool-based delegation** | Outer agent has a `delegate_to_agent` tool | PydanticAI docs, flight_booking | **Best** |
| B. Output-function hand-off | Outer agent terminates, inner takes over | PydanticAI output functions | Wrong — we need results back |
| C. Programmatic sequencing | Application code calls agents in order | PydanticAI hand-off pattern | Useful for pipelines, not orchestration |
| D. Graph FSM | Typed nodes/edges with state machine | pydantic-graph | YAGNI for MVP |

**Recommendation (.92):** Approach A — a `delegate_to_agent` tool function. Looks up the agent in `AgentRegistry`, checks depth limit, calls `inner.run(task, deps=ctx.deps, usage=ctx.usage)`, returns result or error string.

```python
async def delegate_to_agent(ctx: RunContext[OwlBearDeps], agent_name: str, task: str) -> str:
    depth = getattr(ctx.deps, "_delegation_depth", 0)
    if depth >= MAX_DELEGATION_DEPTH:
        return f"Error: max delegation depth reached."
    inner = registry.get(agent_name)  # KeyError → error message
    inner_deps = replace(ctx.deps, _delegation_depth=depth + 1)
    result = await inner.run(task, deps=inner_deps, usage=ctx.usage)
    return result.output  # exceptions caught → error string
```

**Key decisions:** (1) Depth tracking via `_delegation_depth: int = 0` on `OwlBearDeps`. (2) Inner failures caught and returned as error strings — never propagated. (3) Usage aggregates via `usage=ctx.usage` (PydanticAI native). (4) MVP returns `str`; structured `TaskResult` output is YAGNI for now. (5) Context isolation — each inner agent gets fresh message history.

### 3.4 Dependency Flow

```text
Orchestrator → delegate_to_agent tool (ctx.deps, ctx.usage)
  └─ inner Agent.run(task, deps=inner_deps, usage=ctx.usage)
      └─ inner tools access ctx.deps.hooks, ctx.deps.tracker
```

`OwlBearDeps` fields needed (per #153 + this research): `hooks: HookRegistry`, `tracker: UsageTracker | None`, `agent_registry: AgentRegistry | None`, `_delegation_depth: int = 0`. Note: `workspace_root` and `session` stay on `OwlBearAgent` (per-agent, not shared).

### 3.5 Research Checklist Summary

All 7 checklist items pass for all three tasks:

| Item | #128 (Definition) | #129 (Registry) | #130 (Delegation) |
|------|-------------------|-----------------|-------------------|
| 1. Theoretical validity | YAML+md separates config/prose | Dir-scanning proven (SkillRegistry) | PydanticAI documented level-2 |
| 2. Prior art (2+) | SkillRegistry, CrewAI YAML, Claude .agent.md | SkillRegistry, CrewAI @CrewBase, Nanobot | PydanticAI flight_booking, CrewAI, Nanobot |
| 3. Technical feasibility | yaml.safe_load + Pydantic BaseModel | ~80 LOC, no new deps | Single tool function, ~25 LOC |
| 4. Architecture fit | Mirrors SkillRegistry pattern | Injected into OwlBearDeps | Uses AgentRegistry + OwlBearDeps |
| 5. Implementation approach | AgentDefinition model + parser | Scan→store, lazy get() | Tool on orchestrator, depth via deps |
| 6. Testing strategy | Parse valid/invalid, defaults | Load 2+ defs, lookup, missing error | Delegation, not found, depth limit |
| 7. Documented | §3.1 | §3.2 | §3.3 |

## 4. Recommendation (.90 confidence)

Build P8 as three thin layers: (1) **Agent definitions** (#128) — markdown files parsed into `AgentDefinition` Pydantic models, ~50 LOC; (2) **Agent registry** (#129) — `AgentRegistry` class, lazy instantiation, ~80 LOC; (3) **Agent delegation** (#130) — `delegate_to_agent` tool using PydanticAI native delegation, ~25 LOC.

**Risks:** Deps coupling (mitigate: keep minimal) · Circular delegation (mitigate: depth cap) · Runtime tool resolution failure (mitigate: scan-time validation).

## 5. Follow-up Tasks

**#128 refinements:** Add `max_delegation_depth` field; parser should warn on unresolvable tool names.

**#129 refinements:** Add `tool_resolver` callback injection; validate tools/skills at scan time; `scan()` as explicit method.

**#130 refinements:** Requires `_delegation_depth` and `agent_registry` on OwlBearDeps (#153 update needed).

**New tasks:**

1. **Update #153 AC** — add `agent_registry: AgentRegistry | None = None` and `_delegation_depth: int = 0` to OwlBearDeps.

2. **Create initial agent definition files** — `.owlbear/agents/{orchestrator,coder,reviewer,researcher,writer}.md` adapted from existing `.github/agents/*.agent.md`.

3. **Integrate AgentRegistry into daemon bootstrap** — wire registry into startup so delegation works.
