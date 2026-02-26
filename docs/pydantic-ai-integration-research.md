# PydanticAI Integration Research — P2 Agent Core

> **Owning tasks:** #37, #38, #39, #40, #41, #42, #43, #44, #45
> **Date:** 2026-02-26
> **Status:** Complete

## 1. Research Scope

Every P2 task asks: "Do we need to build this, or does PydanticAI already provide it?" This research answers that question definitively by examining PydanticAI's source code (installed v0.1.x) and the most relevant prior art project, `pydantic-deepagents`.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| [PydanticAI](https://github.com/pydantic/pydantic-ai) (15k stars) | Installed dependency, source code examined | Foundation framework — Agent, messages, tools, providers, toolsets |
| [pydantic-deepagents](https://github.com/vstorm-co/pydantic-deepagents) (357 stars) | Cloned into `docs/research/pydantic-deepagents/` | Prior art for skills, hooks, memory, context, middleware on top of PydanticAI |
| PydanticAI `providers/openai.py` | Source file | OpenAIProvider with custom `base_url` — directly usable for Copilot API |
| PydanticAI `providers/github.py` | Source file | GitHubProvider for `models.github.ai` — NOT for Copilot, but shows provider pattern |
| PydanticAI `messages.py` (2121 lines) | Source file | Complete message system: ModelRequest, ModelResponse, SystemPromptPart, UserPromptPart, TextPart, ToolCallPart, ToolReturn, streaming deltas |
| PydanticAI `tools.py` + `toolsets/` | Source files | Tool class, @tool decorator, ToolDefinition, RunContext, FunctionToolset, AbstractToolset, FilteredToolset, etc. |
| PydanticAI `_agent_graph.py` | Source file | Graph-based agent loop: UserPromptNode → ModelRequestNode → CallToolsNode → End. Retries, history processing, state management. |

## 3. Key Findings

### 3.1 PydanticAI Already Provides (DO NOT REBUILD)

| Capability | PydanticAI Module | Size/Maturity | OwlBear Impact |
|-----------|------------------|---------------|----------------|
| **Message types** | `messages.py` | 2121 LOC, dataclass-based, OpenTelemetry-integrated | **#37 redefined**: No custom Message model. Use PydanticAI's `ModelRequest`, `ModelResponse`, `UserPromptPart`, `TextPart`, etc. directly. |
| **Tool system** | `tools.py` + `toolsets/` | `Tool` class, `@tool` decorator, `ToolDefinition`, `RunContext`, `FunctionToolset`, `AbstractToolset`, 9 toolset variants | **#39 redefined**: No custom Tool ABC. Use PydanticAI's `@tool` decorator and `FunctionToolset`. |
| **Agent loop** | `agent/__init__.py` + `_agent_graph.py` | Graph-based execution, retries, streaming, tool calling, history processing | **#45 redefined**: No custom agent loop. Use PydanticAI's `Agent.run()` / `Agent.iter()`. Wrap with OwlBear session/channel integration. |
| **Provider abstraction** | `providers/openai.py` | OpenAIProvider with custom `base_url` and `api_key` | **#44 MERGED into #30-31**: `OpenAIProvider(base_url='https://api.individual.githubcopilot.com/v1', api_key=token)` confirmed working. Provider is just auth + config. |
| **System prompts** | `_system_prompt.py` | Dynamic system prompt functions, injected at runtime | Supports `instructions` parameter + `@agent.system_prompt` decorator for context injection. |
| **History processing** | `_agent_graph.py` | `HistoryProcessor` type — functions that transform message history before model calls | Useful for memory/context management (task #42). |
| **Retries** | `agent/__init__.py` | `retries` parameter, `max_result_retries`, `max_tool_retries` | Built-in retry logic — no custom retry layer needed beyond tenacity for HTTP. |
| **OpenTelemetry** | `_instrumentation.py` + `models/instrumented.py` | Full OTel span instrumentation for agent runs and tool calls | Free observability. |

### 3.2 Genuine Gaps (MUST BUILD)

| Gap | OwlBear Task | What to Build | pydantic-deepagents Reference |
|-----|-------------|---------------|-------------------------------|
| **Session persistence** | #41 | JSONL-based session store that serializes PydanticAI's `ModelMessage` history to disk and reloads it | `pydantic_deep/toolsets/checkpointing.py` — saves conversation state |
| **Channel abstraction** | #43 | `ChannelPlugin` Protocol with `send()`/`receive()` + CLI adapter. PydanticAI has no I/O channel concept — it expects the caller to provide user prompts. | Not in pydantic-deepagents (they use stdin/stdout directly) |
| **Hooks/middleware** | #38 | Event system for pre_tool_use, post_tool_use, on_session_start, etc. PydanticAI has `HistoryProcessor` and OTel but no general-purpose hook system. | `pydantic_deep/middleware/hooks.py` — Claude Code-style hooks with HookEvent enum, HookInput, HookResult. Uses exit codes (0=allow, 2=deny). |
| **Skill registry** | #40 | Progressive skill loading — markdown files with YAML frontmatter, summaries in system prompt, full content loaded on demand. | `pydantic_deep/toolsets/skills/` — 7 files, SkillsToolset extending FunctionToolset, directory scanning, YAML frontmatter parsing. |
| **Context/memory** | #42 | Two-layer memory: (1) always-loaded context file injected via `instructions`/system prompt, (2) session history. | `pydantic_deep/toolsets/memory.py` — MEMORY.md with read/write tools + system prompt injection. `pydantic_deep/toolsets/context.py` — auto-discover context files. |

### 3.3 Copilot Provider — Confirmed Trivial

```python
from pydantic_ai.providers.openai import OpenAIProvider

# This is ALL we need for the provider. The real work is OAuth device-flow.
provider = OpenAIProvider(
    base_url="https://api.individual.githubcopilot.com/v1",
    api_key=copilot_token,  # from OAuth device-flow
)
agent = Agent("openai:gpt-4o", provider=provider)
```

Tested and confirmed working. Task #44 collapses entirely.

### 3.4 pydantic-deepagents — Patterns to Study, NOT to Depend On

**Why not depend on it:**

- Small startup (vstorm-co), likely to abandon or diverge
- May not track PydanticAI releases quickly
- 357 stars — not battle-tested at scale
- Brings its own dependency tree (pydantic-ai-backend, pydantic-ai-todo, subagents-pydantic-ai, summarization-pydantic-ai, pydantic-ai-middleware)

**What to learn from it:**

| Pattern | deepagents Implementation | OwlBear Adaptation |
|---------|--------------------------|-------------------|
| Skills | `SkillsToolset(FunctionToolset)` — markdown files with YAML frontmatter, `list_skills` + `load_skill` tools | Adopt the markdown/YAML pattern. Implement as PydanticAI `FunctionToolset`. |
| Hooks | `HookEvent` enum, `HookInput`/`HookResult` dataclasses, command hooks via subprocess, Python handler hooks | Adopt the Python handler approach (no subprocess overhead). Simpler — just `dict[HookEvent, list[Callable]]`. |
| Memory | `MemoryFile` dataclass, `load_memory()`, `format_memory_prompt()`, FunctionToolset with tools | Adopt the MEMORY.md pattern. Inject via PydanticAI `instructions` parameter. |
| Context files | Auto-discover `.md` files, inject into system prompt | Adopt pattern — scan for `context.md` in workspace root. |
| Agent factory | `create_deep_agent()` — massive factory function (855 lines, 50+ params) | **ANTI-PATTERN for us**. KISS — no god function. Compose at the orchestrator level instead. |

## 4. Revised Architecture

### 4.1 What We Build

```
src/owlbear/
├── core/
│   ├── hooks.py          # HookRegistry — dict[HookEvent, list[Callable]]
│   └── config.py         # OwlBearSettings (already exists)
├── skills/
│   └── registry.py       # SkillRegistry — markdown YAML frontmatter + progressive loading
├── channels/
│   ├── base.py           # ChannelPlugin Protocol (send, receive)
│   └── cli.py            # CLI adapter (stdin/stdout)
├── memory/
│   ├── session.py        # JSONL session store (serialize PydanticAI ModelMessage)
│   └── context.py        # ContextManager — loads context.md into instructions
├── providers/
│   └── copilot.py        # CopilotProvider — OAuth device-flow + OpenAIProvider wrapper
└── (tools/, voice/ — later phases)
```

### 4.2 What We Use From PydanticAI Directly

- `Agent` — the agent loop, retries, streaming
- `ModelRequest`, `ModelResponse`, message types — canonical message format
- `Tool`, `@tool`, `FunctionToolset` — tool registration and execution
- `OpenAIProvider` — HTTP client for Copilot API
- `RunContext` — dependency injection into tools
- `HistoryProcessor` — message history transforms (for session/context management)
- `instructions` parameter — system prompt injection

## 5. Follow-up Tasks

### Tasks to REDEFINE (validate PydanticAI meets need + add thin integration)

1. **#37 → "Validate PydanticAI message types for OwlBear"** — Verify PydanticAI's ModelMessage types cover our needs (role, content, timestamp, tool_calls). Write integration tests that serialize/deserialize messages to JSONL. Add OwlBear metadata envelope if needed.

2. **#39 → "Validate PydanticAI tool system for OwlBear"** — Verify @tool decorator and FunctionToolset work for our use cases. Write smoke tests. Document the pattern in copilot-instructions.md.

3. **#45 → "Implement OwlBear agent wrapper"** — Thin wrapper that creates a PydanticAI `Agent` with OwlBear-specific config: CopilotProvider, session persistence, channel integration, hook emission. NOT a custom loop — a factory/config layer.

### Tasks to MERGE

4. **#44 → Merge into #30-31** — Provider is `OpenAIProvider(base_url=..., api_key=...)`. The work is OAuth, not provider.

### Tasks to KEEP (genuine gaps)

5. **#38 (HookRegistry)** — Build as `dict[HookEvent, list[Callable]]` with `register()` and `emit()`. Reference pydantic-deepagents pattern. Async-safe.
6. **#40 (SkillRegistry)** — Build as FunctionToolset. Markdown files with YAML frontmatter. Progressive loading via `list_skills` + `load_skill` tools.
7. **#41 (Session persistence)** — JSONL store that serializes PydanticAI's `ModelMessage` history. Backup before compaction.
8. **#42 (Context/memory)** — ContextManager that loads context.md via PydanticAI `instructions` parameter.
9. **#43 (Channel Protocol + CLI)** — `ChannelPlugin` Protocol with CLI adapter. Async I/O.
