# PydanticAI Multi-Agent Patterns and Tool Architecture

> **Owning task:** #127 — Research: PydanticAI multi-agent patterns and tool architecture
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

Phase 8 introduces OwlBear's autonomous agent framework: agent definitions, a registry, and delegation between specialist agents (orchestrator → coder/reviewer/researcher). Before building any of this, we need to understand what PydanticAI v1.63.0 offers natively for multi-agent orchestration, toolset composition, dependency injection across agent hierarchies, and structured inter-agent communication. This research gates all P8 implementation tasks (#128–#132).

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | .95 | 5 complexity levels, delegation pattern, programmatic hand-off, deep agents |
| PydanticAI toolsets docs | <https://ai.pydantic.dev/toolsets/> | .95 | 12 toolset types, composition (Combined, Filtered, Prefixed, Prepared, Wrapper, External, Dynamic), approval workflows |
| PydanticAI dependencies docs | <https://ai.pydantic.dev/dependencies/> | .90 | `deps_type`, `RunContext`, DI across agents, override for testing |
| PydanticAI output docs | <https://ai.pydantic.dev/output/> | .85 | Structured output, output functions for agent hand-off, union return types |
| PydanticAI message-history docs | <https://ai.pydantic.dev/message-history/> | .85 | `history_processors`, message serialization, context summarization |
| PydanticAI graph docs | <https://ai.pydantic.dev/graph/> | .70 | `pydantic-graph` FSM for complex workflows — typed nodes, `End`, state |
| PydanticAI cloned repo (v1.63.0) | <https://github.com/pydantic/pydantic-ai> | .95 | Source analysis: toolsets/, agent/, _agent_graph.py, examples/ |
| PydanticAI flight_booking example | examples/flight_booking.py in repo | .90 | Real multi-agent delegation: search → extraction, shared deps, usage tracking |
| OwlBear existing codebase | src/owlbear/ | 1.0 | OwlBearAgent, HookRegistry, RolePolicy, FileToolset, TerminalToolset, SkillRegistry |
| OwlBear prior research | docs/research/pydantic-ai-integration.md, docs/research/daemon-bootstrap.md | .90 | Confirmed patterns: loop-outside-agent, FunctionToolset, OpenAIProvider |

## 3. Analysis

### 3.1 Multi-Agent Orchestration — Five Complexity Levels

PydanticAI documents five levels of multi-agent complexity. OwlBear needs level 2 (agent delegation).

| Level | Pattern | Description | OwlBear Fit |
|-------|---------|-------------|-------------|
| 1 | Single agent | One agent, multiple tools | Current `bearclaw chat` — already works |
| 2 | **Agent delegation** | Agent A calls Agent B inside a tool, gets result back | **Best fit for orchestrator → specialist** |
| 3 | Programmatic hand-off | Application code calls agents sequentially | Useful for pipeline stages (build → review) |
| 4 | Graph-based FSM | `pydantic-graph` nodes/edges with typed state | Over-engineered for our needs (YAGNI) |
| 5 | Deep agents | Planning + files + delegation + sandbox | Aspirational — combines levels 1–4 |

**Key finding:** Agent delegation is the canonical PydanticAI pattern for our orchestrator. The outer agent defines a tool function that calls `inner_agent.run()` inside it, passing `ctx.usage` for unified usage tracking and `ctx.deps` for shared dependencies.

```python
# PydanticAI's documented pattern — this is exactly what we need
@orchestrator.tool
async def delegate_to_coder(ctx: RunContext[OwlBearDeps], task: str) -> str:
    result = await coder_agent.run(task, deps=ctx.deps, usage=ctx.usage)
    return result.output
```

### 3.2 Toolset Architecture — 12 Types Available

PydanticAI v1.63.0 ships 12 toolset types. OwlBear already uses `FunctionToolset` for all custom toolsets.

| Toolset | Purpose | OwlBear Usage |
|---------|---------|---------------|
| `FunctionToolset` | Register Python functions as tools | **Already used** — FileToolset, TerminalToolset, SkillRegistry, BrowserToolset |
| `CombinedToolset` | Merge multiple toolsets into one | Useful for agent composition |
| `FilteredToolset` | Filter tools by predicate | **Replace our `apply_role_policy`** — native `.filtered()` is simpler |
| `PrefixedToolset` | Add name prefix to avoid conflicts | Useful when agents share toolset instances |
| `RenamedToolset` | Rename specific tools | Niche — not needed yet |
| `PreparedToolset` | Modify tool definitions per-step | Niche — not needed yet |
| `WrapperToolset` | Override `call_tool()` for logging/hooks | **Candidate for hook integration** |
| `ApprovalRequiredToolset` | Human-in-the-loop approval | Future — approval gates for destructive ops |
| `ExternalToolset` | Frontend-executed tools (deferred) | Not applicable |
| `MCPServerStdio` / `FastMCPToolset` | MCP server integration | Future P10 |
| `AbstractToolset` | Base class for custom toolsets | We already subclass `FunctionToolset` |
| Dynamic toolsets | `@agent.toolset` decorator, per-run/step | **Useful for role-based tool switching** |

**Key insight — `WrapperToolset` for hooks:** Our `HookRegistry` emits `PRE_TOOL_USE` and `POST_TOOL_USE` hooks from outside PydanticAI. A `WrapperToolset` subclass could emit these hooks natively from within PydanticAI's tool execution pipeline, giving us proper integration without wrapping the entire agent:

```python
class HookedToolset(WrapperToolset):
    async def call_tool(self, name, tool_args, ctx, tool):
        await hooks.emit(PRE_TOOL_USE, {"tool_name": name, "args": tool_args})
        result = await super().call_tool(name, tool_args, ctx, tool)
        await hooks.emit(POST_TOOL_USE, {"tool_name": name, "result": result})
        return result
```

**Key insight — `FilteredToolset` replaces `apply_role_policy`:** Our current `roles.py` implements custom filtering. PydanticAI's native `.filtered()` method does the same thing more idiomatically:

```python
# Current OwlBear pattern (custom):
filtered = apply_role_policy(toolset, VALIDATOR_POLICY)

# PydanticAI native (simpler):
filtered = toolset.filtered(lambda ctx, td: td.name not in denied_tools)
```

### 3.3 Tool Sharing vs. Restriction by Role

Three approaches for giving different agents different tools:

| Approach | Description | Complexity | OwlBear Fit |
|----------|-------------|------------|-------------|
| A. Separate toolset instances | Each agent gets its own toolsets at construction | Low | **Best for MVP** |
| B. `FilteredToolset` per role | One shared toolset, filtered per agent | Medium | Good for roles (builder/validator) |
| C. Dynamic `@agent.toolset` | Tools change per-step based on context | High | Future — adaptive tooling |

**Recommendation (.85):** Approach A for MVP. Each agent definition specifies which toolset *names* it needs (e.g., `["filesystem", "terminal", "skills"]`). The registry resolves names to instances and passes them via `toolsets=`. For role restrictions (validator = read-only), wrap with `.filtered()`.

### 3.4 Structured Output for Agent Communication

PydanticAI supports typed outputs via `output_type`. This is how agents exchange structured data:

| Pattern | Description | Use Case |
|---------|-------------|----------|
| `output_type=str` (default) | Plain text response | Chat, general conversation |
| `output_type=SomeModel` | Pydantic model output | Structured delegation results |
| `output_type=[TypeA, TypeB]` | Union — model picks | Success/failure branching |
| Output functions | Function called as final action | Agent hand-off (orchestrator → specialist result post-processing) |

**For delegation results**, the inner agent should return a Pydantic model. This gives the orchestrator structured data to reason about:

```python
class TaskResult(BaseModel):
    status: Literal["success", "failure", "needs_review"]
    summary: str
    files_changed: list[str] = []

coder_agent = Agent("model", output_type=TaskResult, ...)
```

### 3.5 Dependency Injection Across Agent Hierarchies

PydanticAI's `deps_type` + `RunContext` is the mechanism for passing shared state:

- **Parent deps propagate to child:** `ctx.deps` is passed to `inner_agent.run(deps=ctx.deps)`
- **Usage tracking aggregates:** `ctx.usage` is passed to `inner_agent.run(usage=ctx.usage)`
- **Deps type must match or be a subset** of the parent's deps type
- **Override for testing:** `agent.override(deps=test_deps)` context manager

For OwlBear, we need a shared deps type that all agents can access:

```python
@dataclass
class OwlBearDeps:
    workspace_root: Path
    hooks: HookRegistry
    session: SessionStore
    tracker: UsageTracker | None = None
```

This replaces passing hooks/session/tracker via `OwlBearAgent.__init__`. Instead, PydanticAI's native DI handles it. Each agent tool accesses `ctx.deps.hooks`, `ctx.deps.session`, etc.

### 3.6 Agent Definition — Config-Driven vs. Code-Driven

| Approach | Description | Prior Art | KISS |
|----------|-------------|-----------|------|
| A. **Markdown files** (YAML frontmatter + body) | Body = system prompt, frontmatter = tools/role/model | Claude `.agent.md`, OwlBear task #128 | High |
| B. Python code | `Agent("model", instructions=..., toolsets=[...])` | PydanticAI native | Medium |
| C. YAML/TOML config | Separate config file referencing Python code | CrewAI config | Medium |
| D. Hybrid | Markdown for prompt, Python for wiring | Common pattern | Medium |

**Recommendation (.85):** Approach A — markdown files. The body is the system prompt (injected as `instructions`). Frontmatter fields: `name`, `description`, `role` (maps to `RolePolicy`), `model` (optional override), `tools` (list of toolset names), `skills` (list of skill names). This matches our existing `.agent.md` pattern and task #128's AC.

```yaml
---
name: coder
description: Implements code changes using TDD
role: builder
model: null  # use default
tools: [filesystem, terminal, skills]
skills: [kanban-md, kanban-based-development]
---
You are a coder agent. You implement kanban tasks using TDD...
```

### 3.7 Message History and Context Management

PydanticAI v1.63.0 adds `history_processors` — a list of callables that transform message history before each model request. This is critical for long-running sessions:

| Strategy | Description | Tokens Saved |
|----------|-------------|-------------|
| Keep recent N messages | `messages[-N:]` | High |
| Summarize old messages | Use cheap model to compress | High |
| Filter by type | Remove `ModelResponse`, keep requests only | Medium |
| Context-aware | Use `RunContext.usage.total_tokens` to decide | Adaptive |

**For OwlBear:** Add a `history_processors` parameter to `OwlBearAgent` forwarded to the inner `Agent`. This replaces any manual session truncation and is natively supported.

### 3.8 Logfire / Agent Playground

PydanticAI has built-in OpenTelemetry instrumentation (`logfire.instrument_pydantic_ai()`). For multi-agent systems it traces:

- Which agent handled which part of a request
- Delegation decisions and latencies
- Token usage and costs per agent
- Tool call internals (DB queries, HTTP requests)

**For OwlBear:** Logfire is optional (cloud-hosted observability). We already have `UsageTracker` for cost tracking. Logfire can be enabled later without code changes — just `logfire.configure()` + `logfire.instrument_pydantic_ai()`. Not a P8 blocker.

## 4. Recommendation (.88 confidence)

**Use PydanticAI's native delegation pattern for OwlBear's multi-agent system.** Specifically:

1. **Agent delegation** (level 2) — orchestrator calls specialist agents via tool functions
2. **Markdown agent definitions** — YAML frontmatter + body for system prompt
3. **Agent registry** — scans definitions, resolves toolsets by name, lazy instantiation
4. **Shared deps via `deps_type`** — `OwlBearDeps` dataclass replaces manual `__init__` params
5. **`FilteredToolset`** for role policies — replaces custom `apply_role_policy`
6. **`WrapperToolset`** for hook integration — emit PRE/POST_TOOL_USE natively
7. **`history_processors`** for context management — native truncation/summarization

**Risks and mitigations:**

- **Deps type coupling:** All agents share `OwlBearDeps`. If an agent needs unique deps, use a superset dataclass. Mitigation: keep deps minimal (workspace_root, hooks, tracker).
- **Delegation depth:** Recursive delegation can loop. Mitigation: max depth counter in deps or in the delegation tool itself (task #130 already has this AC).
- **Agent definition format:** Parsing YAML + markdown is simple but needs validation. Mitigation: Pydantic model for frontmatter validation.

## 5. Follow-up Tasks

### Task #128 refinements (Agent definition format)

- AC validated: YAML frontmatter + markdown body is the right pattern
- Add: `deps_type` awareness — agent definitions declare which deps fields they need
- Add: `history_processors` field (optional list of processor names)

### Task #129 refinements (Agent registry)

- Tool resolution: map `tools: [filesystem, terminal]` → actual toolset instances
- Use `FilteredToolset` for role-based restriction instead of `apply_role_policy`
- Consider `WrapperToolset` subclass for hook integration into toolsets

### Task #130 refinements (Agent delegation)

- Use PydanticAI's native delegation pattern: `inner_agent.run(task, deps=ctx.deps, usage=ctx.usage)`
- Return structured `TaskResult` from inner agents (not raw strings)
- Max delegation depth via deps counter (not a separate config)

### New tasks to create

1. **Refactor role policy to use FilteredToolset** — replace `apply_role_policy` with PydanticAI native `.filtered()`. ~20 LOC diff, simplifies roles.py.
2. **Implement OwlBearDeps dataclass** — shared dependency type for all agents. Replaces manual OwlBearAgent params. ~30 LOC.
3. **Add history_processors support to OwlBearAgent** — forward to inner Agent. ~10 LOC diff.
4. **Implement HookedToolset (WrapperToolset)** — emit PRE/POST_TOOL_USE hooks from within PydanticAI's tool pipeline. ~40 LOC.
