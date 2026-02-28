# Core Agent Definitions — System Prompts, Tools, Roles, and Delegation

> **Owning task:** #132 — Core agent definitions — orchestrator, coder, reviewer, researcher
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

Task #132 requires defining five core agent "souls" as markdown files that the `AgentRegistry` can scan and instantiate as PydanticAI agents. Each definition needs: system prompt, tool list (referencing registered toolset names), role policy (builder/validator), and delegation depth. This research answers five questions: (1) What system prompts work well? (2) What tools per agent? (3) What role policy? (4) What delegation depth? (5) Where should files live?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| CrewAI agents docs | <https://docs.crewai.com/concepts/agents> | .85 | role/goal/backstory triplet, `allow_delegation`, YAML config pattern |
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | .90 | Delegation via tools, deps/usage passing, UsageLimits |
| OwlBear `.github/agents/` | Local: `.github/agents/*.agent.md` | 1.0 | 7 existing VS Code agent definitions with detailed persona/workflow/boundaries |
| OwlBear agent-framework-research | Local: `docs/agent-framework-research.md` | .95 | AgentDefinition format, registry design, delegation pattern |
| OwlBear agent-patterns-research | Local: `docs/agent-patterns-research.md` | .90 | Builder/validator team pattern, restricted tool sets per role |
| claude-code-hooks-mastery | <https://github.com/disler/claude-code-hooks-mastery> | .80 | Builder/validator team, meta-agent factory, validator report pattern |
| Nanobot SubagentManager | <https://github.com/HKUDS/nanobot> | .75 | Restricted tool sets per subagent, max iteration limits |

## 3. Analysis

### 3.1 System Prompt Design

| Approach | Description | Tokens | Reliability | Source |
|----------|-------------|--------|-------------|--------|
| A. **Concise persona (10-30 lines)** | Role + constraints + output expectations | ~200-600 | High | CrewAI role/goal/backstory |
| B. Full agent spec (300+ lines) | Persona + workflow + examples + self-critique | ~2000+ | Medium (more to confuse) | Our `.github/agents/` |
| C. Minimal role (3-5 lines) | Single paragraph description | ~50-100 | Lower (insufficient guidance) | Basic Agent() init |

**Recommendation (.85):** Approach A — concise persona prompts. PydanticAI tool descriptions are auto-generated, so prompts don't need tool usage examples. The VS Code agent definitions (approach B) are optimized for Claude's chat interface with full XML-structured workflows; PydanticAI agents need shorter, more focused instructions. The prompt should cover: (1) who you are, (2) key constraints, (3) output expectations, (4) what NOT to do.

**Key insight from CrewAI:** The role/goal/backstory triplet works because it gives the LLM identity (role), direction (goal), and context (backstory) without over-specifying workflow steps. Our prompts should follow this pattern adapted to OwlBear's conventions.

### 3.2 Tool Assignment per Agent

Available toolset names (mapped by `tool_resolver`):

- `filesystem` → `FileToolset` (5 tools: read_file, write_file, create_file, list_directory, search_files)
- `terminal` → `TerminalToolset` (1 tool: run_command)
- `ask_user` → `AskUserToolset` (1 tool: ask_user)
- `browser` → `BrowserToolset` (6 tools: navigate, click, type, select, read_text, screenshot)
- `delegation` → `DelegationToolset` (1 tool: delegate_to_agent)

Skills are resolved separately via `skill_registry` param, not `tool_resolver`.

| Agent | Toolsets | Rationale |
|-------|----------|-----------|
| orchestrator | `delegation`, `filesystem`, `ask_user` | Reads context, delegates to specialists, asks user for decisions |
| coder | `filesystem`, `terminal` | Reads/writes code, runs tests and lint |
| reviewer | `filesystem`, `terminal` | Reads code, runs tests/lint independently (never writes) |
| researcher | `filesystem`, `browser` | Reads codebase, browses web for sources |
| writer | `filesystem` | Reads/writes documentation files only |

### 3.3 Role Policy Assignment

Current roles: `builder` (full access) and `validator` (denied: file_write, file_edit, file_delete, execute_command).

**CRITICAL FINDING — Role policy name mismatch (bug):**

The `VALIDATOR_POLICY` denies tool names that don't match actual registered names:

| Denied name (policy) | Actual tool name | Match? |
|----------------------|------------------|--------|
| `file_write` | `write_file` | **NO** |
| `file_edit` | _(no such tool)_ | **NO** |
| `file_delete` | _(no such tool)_ | **NO** |
| `execute_command` | `run_command` | **NO** |

**The validator policy is currently non-functional.** None of the denied names match real tool names. This must be fixed before role policies work correctly.

**Recommended role assignments (once policy is fixed):**

| Agent | Role | Rationale |
|-------|------|-----------|
| orchestrator | `builder` | Needs full access for routing; delegation tool requires builder |
| coder | `builder` | Needs read + write + execute for TDD |
| reviewer | `validator` | Must be read-only + run commands (see §3.3.1) |
| researcher | `validator` | Read-only; browser tools are inherently read-only |
| writer | `builder` | Needs filesystem write access for docs editing |

**§3.3.1 Reviewer terminal access:** The reviewer needs `run_command` to independently run `uv run pytest` and `uv run ruff check`. The current validator policy (once fixed) would deny `run_command`. Options: (a) add a third role `auditor` that blocks writes but allows commands, (b) make validator only deny write tools, not execute, (c) give reviewer `builder` role with limited toolsets. Recommendation (.80): option (b) — remove `run_command` from validator denied tools. Reviewer safety comes from its toolset list (no write tools given), not from role policy blocking execution.

### 3.4 Delegation Depth

| Agent | Depth | Rationale |
|-------|-------|-----------|
| orchestrator | 5 | Top of chain, may route through multiple specialists |
| coder | 2 | Might delegate sub-tasks but limited chain |
| reviewer | 0 | Terminal node — only verifies, never delegates |
| researcher | 1 | Might delegate a focused sub-research, unlikely deep chains |
| writer | 0 | Terminal node — only edits docs, never delegates |

Sources: PydanticAI docs (delegation depth via deps), Nanobot (max iteration limits per subagent), OwlBear `MAX_DELEGATION_DEPTH = 5` in `delegation.py`.

### 3.5 File Location

| Option | Path | Pros | Cons |
|--------|------|------|------|
| A. **Package data** | `src/owlbear/agents/` | Ships with install, always available, version-controlled | Not user-customizable without editing source |
| B. User config | `~/.owlbear/agents/` | User-customizable | Not project-specific, empty by default |
| C. Workspace-local | `.owlbear/agents/` | Project-specific, user can override | Extra directory, needs gitignore decision |

**Recommendation (.85):** Option A for MVP — `src/owlbear/agents/`. These are OwlBear's built-in agent definitions, shipped as package data. A future task can add override support (scan user dir first, fall back to package dir). This aligns with KISS/YAGNI — don't build override mechanics until we need them.

Config wiring: Add `agents_dir: Path` to `OwlBearSettings` with default `Path(__file__).parent.parent / "agents"` (resolves to `src/owlbear/agents/`). `AgentRegistry` receives this path at construction.

### 3.6 Skills Assignment

| Agent | Skills | Rationale |
|-------|--------|-----------|
| orchestrator | `kanban-md`, `kanban-based-development` | Reads board, plans execution waves |
| coder | `kanban-md` | Reads task AC, moves task status |
| reviewer | `kanban-md` | Reads task AC, moves task status |
| researcher | — | No skill-heavy workflows needed for MVP |
| writer | `kanban-md` | Reads task AC, moves task status |

## 4. Recommendation (.85 confidence)

Create 5 markdown files in `src/owlbear/agents/` with concise 10-30 line system prompts following the persona/constraints/output pattern. Use toolset-level names in the `tools` field. Fix the VALIDATOR_POLICY name mismatch first (prerequisite). Add `agents_dir` to `OwlBearSettings`.

**Risk:** Role policy bug means validators currently have full access. **Mitigation:** Fix policy names before or alongside agent definitions (new task).

## 5. Follow-up Tasks

1. **Fix VALIDATOR_POLICY tool name mismatch** — Update denied tool names to match actual registered names (`write_file`, `create_file`, `run_command`). Remove `file_edit` and `file_delete` (nonexistent). This is a prerequisite for role-based security.

2. **Create 5 agent definition files** — Implement the markdown files in `src/owlbear/agents/` per the specs in §3.2–§3.6 with concise system prompts.

3. **Add `agents_dir` to OwlBearSettings** — New config field defaulting to package-relative path. Wire into daemon bootstrap and CLI chat.

4. **Wire AgentRegistry into daemon/CLI** — Construct `tool_resolver` callback mapping string names to toolset instances, instantiate `AgentRegistry`, inject into `OwlBearDeps`.

5. **Add writer agent definition** — The AC lists orchestrator, coder, reviewer, researcher. Writer is also needed per the pipeline but not in the AC title. Include it.
