# Agent Definitions Sync Research

> **Owning task:** #453 — Sync OwlBear agent definitions with refactored agent inventory
> **Date:** 2026-03-03 **Status:** Complete

## 1. Context and Question

The agent refactoring (#436–#451) updated `.github/agents/*.agent.md` (8 agents) but NOT
`src/owlbear/agents/*.md` (still 6 agents with old names). `AgentRegistry` scans the latter
at runtime, so delegation fails with `KeyError` (e.g. `'builder' not found`).

**Research question:** What are the exact YAML fields, valid tool names, valid roles, and
correct content for all 8 agent definitions in `src/owlbear/agents/*.md`?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| `AgentDefinition` model | `src/owlbear/core/agent_def.py` | YAML schema: required/optional fields |
| `build_agent_registry()` | `src/owlbear/bootstrap.py:674` | `_aliases` dict = valid tool resolver names |
| `AgentRole` / `RolePolicy` | `src/owlbear/core/roles.py` | Two roles: builder, validator |
| `FileToolset._register_tools` | `src/owlbear/tools/filesystem.py:75` | Tool names: `read_file`, `write_file`, `create_file`, `list_directory`, `search_files` |
| `KanbanToolset` | `src/owlbear/tools/kanban.py` | Tool names: `kanban_list`, `kanban_show`, `kanban_create`, `kanban_move`, `kanban_edit`, `kanban_pick`, `kanban_context` |
| `AgentRegistry` | `src/owlbear/core/agent_registry.py` | Scan, build, role policy application |
| VS Code agent definitions | `.github/agents/*.agent.md` (8 files) | Canonical agent personas/workflows |
| Existing OwlBear agents | `src/owlbear/agents/*.md` (6 files) | Current state to diff against |
| Test file | `tests/test_agent_definitions.py` | Existing validation expectations |

## 3. YAML Schema (from `AgentDefinition`)

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `name` | str | **yes** | — | Must match filename stem |
| `description` | str | **yes** | — | One-line purpose |
| `role` | str | no | `"builder"` | `"builder"` or `"validator"` |
| `tools` | list[str] | no | `[]` | Keys from `_aliases` dict |
| `skills` | list[str] | no | `[]` | Skill directory names |
| `model` | str\|null | no | `null` | Override default model |
| `max_delegation_depth` | int | no | `3` | 0 = no sub-delegation |

Body after `---` becomes `system_prompt`.

## 4. Valid Tool Resolver Names (`_aliases` in bootstrap.py)

| Alias | Class | Used by agents? |
|-------|-------|----------------|
| `filesystem` | `FileToolset` | All 8 |
| `terminal` | `TerminalToolset` | orchestrator, builder, reviewer, writer, closer |
| `ask_user` | `AskUserToolset` | orchestrator, kanban-planner, researcher, architect, closer |
| `browser` | `BrowserToolset` | researcher |
| `delegation` | `DelegationToolset` | orchestrator only |
| `git_local` | `GitLocalToolset` | None currently |
| `github` | `GitHubToolset` | None currently |
| `kanban` | `KanbanToolset` | orchestrator, kanban-planner, architect, closer |
| `knowledge` | `KnowledgeToolset` | researcher |
| `web_search` | `WebSearchToolset` | researcher |
| `skills` | `SkillRegistry` | (handled implicitly when `skills` list is non-empty) |

## 5. Role Impact on Tool Access

| Role | Denied tools | Effect |
|------|-------------|--------|
| `builder` | _(none)_ | Full access to all tools |
| `validator` | `write_file`, `create_file` | Cannot write/create via FileToolset; kanban + terminal unaffected |

**Key insight:** Kanban tool names (`kanban_create`, `kanban_edit`, etc.) are NOT blocked by
validator policy. So validator-role agents can still create/edit kanban tasks. Only FileToolset
write operations are blocked.

## 6. Proposed Agent Mapping (8 agents)

| Agent | Description | Role | Tools | Skills | Depth |
|-------|-------------|------|-------|--------|-------|
| orchestrator | Routes tasks to specialist agents and tracks progress | builder | delegation, filesystem, ask_user, kanban, terminal | kanban-md, kanban-based-development | 5 |
| kanban-planner | Entry gate for task creation and feature decomposition | builder | filesystem, ask_user, kanban | kanban-md, kanban-based-development, project-definition | 3 |
| builder | Implements code using TDD workflow | builder | filesystem, terminal | kanban-md, tdd-workflow | 2 |
| researcher | Investigates topics and produces structured findings | **builder** | filesystem, browser, web_search, knowledge, ask_user | _(none)_ | 1 |
| architect | Reviews researched tasks and approves for development | validator | filesystem, kanban, ask_user | kanban-md | 1 |
| reviewer | Read-only quality verification of code and tests | validator | filesystem, terminal | kanban-md, code-review | 0 |
| writer | Verifies and updates documentation | builder | filesystem, terminal | kanban-md, docs-gate | 0 |
| closer | Verifies done tasks, archives, commits and pushes | validator | filesystem, terminal, kanban, ask_user | kanban-md, task-verification | 0 |

### Changes from current state

| File | Action | Key changes |
|------|--------|-------------|
| `coder.md` | **Delete** | Replaced by `builder.md` |
| `planner.md` | **Delete** | Replaced by `kanban-planner.md` |
| `builder.md` | **Create** | Was `coder`; add `tdd-workflow` skill |
| `kanban-planner.md` | **Create** | Was `planner`; remove `delegation`, `knowledge`, `web_search`; add `kanban` |
| `architect.md` | **Create** | New; role: validator; tools: filesystem, kanban, ask_user |
| `closer.md` | **Create** | New; role: validator; tools: filesystem, terminal, kanban, ask_user |
| `orchestrator.md` | **Update** | Add `terminal`; update agent catalog to 8 agents |
| `researcher.md` | **Update** | Change role: validator→builder; add web_search, knowledge, ask_user |
| `reviewer.md` | **Update** | Add `code-review` skill |
| `writer.md` | **Update** | Add `terminal`; add `docs-gate` skill |

## 7. Concerns

### 7a. Researcher role: validator → builder

The researcher must write `docs/*.md` files. Validator role blocks `write_file` and `create_file`
from FileToolset. **Recommendation (.90):** Change to `builder`. The writer agent already uses
builder role for doc-only edits; prompt discipline prevents code changes.

### 7b. System prompt length limits

The test enforces 10–25 non-blank lines (70 for orchestrator). The VS Code agent definitions
are 100+ lines each with detailed `<workflow>` sections. The OwlBear definitions should be
**condensed summaries** (not ports of the full VS Code prompts) to stay within bounds, or the
test limits need raising.

### 7c. Test file requires significant updates

`tests/test_agent_definitions.py` must change:

- `EXPECTED_AGENTS`: 6 → 8 entries with new names (builder, kanban-planner, architect, closer)
- `KNOWN_TOOLSETS`: unchanged (all proposed tools are already covered)
- `TestRegistryScanAgentsDir.test_scan_loads_all_six`: assert count 6 → 8
- `TestRoleValues.test_builders`: add kanban-planner, remove coder/planner
- `TestRoleValues` parametrize: add architect, closer as validators
- Planner tracking resolver test: rename to kanban-planner, update expected tools

### 7d. `git_local` toolset not used

The closer could benefit from `git_local` (structured git operations) instead of raw `git`
via terminal. **Recommendation (.60):** Keep terminal for now (KISS), evaluate git_local later.

## 8. Available Skills Reference

| Skill | Used by |
|-------|---------|
| kanban-md | orchestrator, kanban-planner, builder, architect, reviewer, writer, closer |
| kanban-based-development | orchestrator, kanban-planner |
| project-definition | kanban-planner |
| tdd-workflow | builder |
| code-review | reviewer |
| docs-gate | writer |
| task-verification | closer |

## 9. Follow-up Tasks

Commands below — do NOT execute; present for user review.

```powershell
# Single implementation task (as stated in #453 — this is one atomic change)
kanban\kanban-md.exe move 453 backlog

# If the architect decides to split:
kanban\kanban-md.exe create "P-ref-01: Update test_agent_definitions.py for 8-agent inventory" --priority needed --tags "agent-refactor,test,phase-refactor" --depends-on 453 --body "Update EXPECTED_AGENTS to 8 agents (builder, kanban-planner, architect, closer replace coder, planner). Update scan count 6→8. Update role parametrize lists. Update planner tracking test."
```
