# Planner Agent Definition — Research Findings

> **Owning task:** #293 — Planner agent definition — decompose ideas into project plans
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

OwlBear has 5 agent definitions (orchestrator, coder, researcher, reviewer, writer) but no planner. The orchestrator routes tasks at runtime but doesn't turn raw ideas into structured project plans. Task #293 proposes a planner agent that takes vague user input and produces structured project definitions with requirements, AC, task decomposition, and dependency mapping. Key questions: (1) what frontmatter fields are needed? (2) what tools should the planner have? (3) what system prompt patterns work for planning? (4) what test updates are required?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| OwlBear agent_def.py | `src/owlbear/core/agent_def.py` | 1.0 | `AgentDefinition` Pydantic model: name, description, role, tools, skills, model, max_delegation_depth, system_prompt |
| OwlBear agent_registry.py | `src/owlbear/core/agent_registry.py` | 1.0 | `scan()` reads `*.md` from `agents_dir`, `get()` lazy-builds PydanticAI Agent |
| OwlBear existing agents (5 files) | `src/owlbear/agents/*.md` | 1.0 | Pattern: YAML frontmatter + markdown body (10–15 non-blank lines) |
| OwlBear test_agent_definitions.py | `tests/test_agent_definitions.py` | 1.0 | `EXPECTED_AGENTS` dict, `KNOWN_TOOLSETS`, parametrized tests, 10–25 line constraint |
| OwlBear roles.py | `src/owlbear/core/roles.py` | .95 | `AgentRole`: builder (full access) / validator (read-only) |
| PydanticAI multi-agent docs | `https://ai.pydantic.dev/multi-agent-applications/` | .85 | Agent delegation pattern, `instructions` param, structured output |
| PydanticAI Deep Agents docs | `https://ai.pydantic.dev/multi-agent-applications/#deep-agents` | .80 | Planning and progress tracking, task delegation, file operations |
| OwlBear plan.prompt.md | `.github/prompts/plan.prompt.md` | .90 | Existing VS Code planner prompt: decompose into kanban tasks, dependency graphs |
| OwlBear knowledge-toolset.md | `docs/research/knowledge-toolset.md` | .85 | `KnowledgeToolset` — task #291, backlog, not yet implemented |
| OwlBear web-search-tool.md | `docs/research/web-search-tool.md` | .85 | `WebSearchToolset` — task #292, backlog, not yet implemented |

## 3. Analysis

### 3.1 Planner vs. Orchestrator

| Aspect | Orchestrator | Planner |
|--------|-------------|---------|
| **When** | Runtime — during task execution | Upfront — before work begins |
| **Input** | Concrete tasks from the board | Vague ideas from the user |
| **Output** | Delegation calls, status updates | Project plans, requirements, AC, kanban tasks |
| **Tool needs** | delegation, filesystem, ask_user | filesystem, ask_user, delegation, knowledge, web_search |
| **Role** | builder | builder |
| **Delegation** | Delegates to coder/reviewer/writer | Delegates to researcher for investigations |
| **Overlap** | Routes existing tasks | Creates new tasks |

**Finding:** There is clear separation of concerns. The orchestrator coordinates runtime execution of existing tasks. The planner operates upstream — it produces the tasks that the orchestrator later executes. No overlap.

### 3.2 Tool Availability

| Tool | Status | Toolset Class | In KNOWN_TOOLSETS? |
|------|--------|---------------|-------------------|
| `filesystem` | Exists | `FileToolset` | Yes |
| `ask_user` | Exists | `AskUserToolset` | Yes |
| `delegation` | Exists | `DelegationToolset` | Yes |
| `knowledge` | Backlog (#291) | `KnowledgeToolset` (planned) | **No** |
| `web_search` | Backlog (#292) | `WebSearchToolset` (planned) | **No** |

**Decision point:** Should the planner definition reference `knowledge` and `web_search` before they exist?

| Option | Pros | Cons | Confidence |
|--------|------|------|------------|
| **A. Use only existing tools, add others later** | No test breakage, immediately testable | Planner is weaker without research tools | **.80** |
| **B. Include all tools, add `depends_on` to task** | Complete specification upfront | `TestToolsetNames` fails until #291/#292 done | .60 |
| **C. Include all tools, update KNOWN_TOOLSETS preemptively** | Tests pass, forward-looking | Tests assert tools exist that don't (misleading) | .40 |

**Recommendation (.80):** Option A. Define planner with `filesystem`, `ask_user`, `delegation` now. Add `knowledge` and `web_search` after tasks #291/#292 are done. Create a follow-up task for the tool expansion. This follows YAGNI — don't reference tools that don't exist.

### 3.3 YAML Frontmatter Fields

Based on analysis of all 5 existing agents:

| Field | Value | Rationale |
|-------|-------|-----------|
| `name` | `planner` | Consistent with single-word naming (coder, writer, reviewer) |
| `description` | `Decomposes ideas into structured project plans` | Verb-first, matches pattern |
| `role` | `builder` | Needs write access for plan documents |
| `tools` | `[filesystem, ask_user, delegation]` | Read/write files, ask user, delegate to researcher |
| `skills` | `[kanban-md, kanban-based-development]` | Task decomposition requires kanban board knowledge |
| `max_delegation_depth` | `3` | Planner → researcher → (browser), needs depth |
| `model` | (omitted, uses default) | No model specialization needed |

### 3.4 System Prompt Design

Existing prompts follow a pattern: persona → workflow (numbered steps) → constraints → output format. All have 10–15 non-blank lines. The test enforces 10–25.

Effective planning prompts must:

1. **Clarify before planning** — Ask for ambiguous requirements (using `ask_user`)
2. **Research before prescribing** — Delegate to researcher for unknowns
3. **Produce structured output** — Project name, goals, requirements, tasks, dependencies
4. **Write concrete AC** — Each task must have testable acceptance criteria
5. **Map dependencies** — Tasks linked via `depends_on`, not implied order

### 3.5 Skills Configuration

| Skill | Present in Other Agents | Needed by Planner |
|-------|------------------------|-------------------|
| `kanban-md` | orchestrator, coder, reviewer, writer | **Yes** — creates kanban tasks |
| `kanban-based-development` | orchestrator | **Yes** — understands task lifecycle |

### 3.6 Test Impact

Adding a 6th agent requires these test file updates:

1. `EXPECTED_AGENTS` dict: add `"planner"` entry with metadata
2. `TestRegistryScanAgentsDir`: count changes from 5 to 6
3. `TestRoleValues.test_builders`: add `"planner"` to parametrize list
4. `TestAgentDefinitionFiles.test_system_prompt_nonempty`: auto-covered by parametrize
5. `TestToolsetNames.test_tools_are_known`: auto-covered (all planner tools are in KNOWN_TOOLSETS)

## 4. Recommendation (.85 confidence)

Create `src/owlbear/agents/planner.md` with:

- **Role:** `builder` — needs filesystem write access for plan documents
- **Tools:** `[filesystem, ask_user, delegation]` — existing tools only; knowledge and web_search added post-#291/#292
- **Skills:** `[kanban-md, kanban-based-development]` — essential for task decomposition
- **max_delegation_depth:** `3` — planner delegates to researcher, who may use browser
- **System prompt:** ~15 non-blank lines following persona → workflow → constraints → output pattern

**Risks:**

- **Without knowledge/web_search:** Planner can't autonomously research prior art. **Mitigation:** Delegate to researcher agent, which has browser access. Add knowledge/web_search tools after #291/#292 complete.
- **Overlapping with orchestrator:** User might confuse the two. **Mitigation:** Clear description and prompt language that distinguishes "planning work" from "executing work."

## 5. Follow-up Tasks

1. **Implement planner.md agent definition** — Create `src/owlbear/agents/planner.md` with YAML frontmatter + system prompt
2. **Update test_agent_definitions.py** — Add planner to `EXPECTED_AGENTS`, update count assertions, add to builder parametrize
3. **Integration test** — Verify planner resolves from registry with correct tools
4. **Post-#291/#292: Add knowledge and web_search tools to planner** — Update frontmatter, update KNOWN_TOOLSETS, update EXPECTED_AGENTS tools list
