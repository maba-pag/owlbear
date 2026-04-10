---
id: 132
title: Core agent definitions — orchestrator, coder, reviewer, researcher
status: archived
priority: important
created: 2026-02-27T14:56:49.3714917+01:00
updated: 2026-02-28T23:52:54.6970227+01:00
started: 2026-02-27T20:30:20.6215481+01:00
completed: 2026-02-28T23:52:54.6970227+01:00
tags:
    - phase-8
    - agent
depends_on:
    - 129
    - 162
class: standard
---

Define the initial set of agent 'souls' as markdown files. These are configuration, not code — the registry instantiates them.

Research: docs/research/core-agent-definitions.md
Depends on: #128 (AgentDefinition — done), #129 (AgentRegistry — done), #162 (VALIDATOR_POLICY fix — todo)

## AC

- [ ] Create directory: `src/owlbear/agents/`
- [ ] 5 agent definition `.md` files with YAML frontmatter + concise system prompt body (10–25 lines each, persona/constraints/output pattern):

  **orchestrator.md:**
  name: orchestrator, description: Routes tasks to specialist agents and plans work,
  role: builder, tools: [delegation, filesystem, ask_user],
  skills: [kanban-md, kanban-based-development], max_delegation_depth: 5

  **coder.md:**
  name: coder, description: Implements code using TDD workflow,
  role: builder, tools: [filesystem, terminal],
  skills: [kanban-md], max_delegation_depth: 2

  **reviewer.md:**
  name: reviewer, description: Read-only quality verification of code and tests,
  role: validator, tools: [filesystem, terminal],
  skills: [kanban-md], max_delegation_depth: 0

  **researcher.md:**
  name: researcher, description: Investigates topics and produces structured findings,
  role: validator, tools: [filesystem, browser],
  skills: [], max_delegation_depth: 1

  **writer.md:**
  name: writer, description: Verifies and updates documentation,
  role: builder, tools: [filesystem],
  skills: [kanban-md], max_delegation_depth: 0

- [ ] Add `agents_dir` to `OwlBearSettings` (src/owlbear/config.py):
  `agents_dir: Path = Path(__file__).parent / "agents"` (resolves to src/owlbear/agents/ at install)

- [ ] Tool names in definitions must match registered toolset names:
  filesystem → FileToolset, terminal → TerminalToolset, ask_user → AskUserToolset,
  browser → BrowserToolset, delegation → DelegationToolset

- [ ] Tests (tests/test_agent_definitions.py):

  - All 5 `.md` files parse via `parse_agent_definition()` without error
  - `AgentRegistry.scan()` on agents dir loads all 5 definitions
  - Each definition's `role` value is a valid `AgentRole` enum member
  - Each definition's `tools` list contains only known toolset names
  - reviewer and researcher have role=validator
  - orchestrator, coder, writer have role=builder

- [ ] ruff clean

## Architecture

- System prompts follow CrewAI role/goal/backstory triplet adapted for PydanticAI
- Prompts should NOT include tool usage examples (PydanticAI auto-generates tool descriptions)
- reviewer uses role=validator → write_file and create_file denied by VALIDATOR_POLICY
- reviewer keeps terminal access (run_command NOT denied) for running tests/lint independently
- researcher uses role=validator → read-only file access, browser is inherently read-only
- writer needs role=builder because it must write documentation files
- Skill names reference skills in `.github/skills/` directory
- `agents_dir` config field enables future override (e.g. user-specific agents)
