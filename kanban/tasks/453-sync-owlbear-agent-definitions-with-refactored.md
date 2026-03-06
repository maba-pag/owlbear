---
id: 453
title: Sync OwlBear agent definitions with refactored agent inventory
status: archived
priority: critical
created: 2026-03-03T18:59:07.6376186+01:00
updated: 2026-03-04T07:58:27.9688189+01:00
started: 2026-03-03T19:08:38.2996199+01:00
completed: 2026-03-04T07:58:27.9688189+01:00
tags:
    - agent-refactor
    - agent
    - phase-refactor
class: standard
---

## Problem

The agent refactoring (#436-#451) updated .github/agents/*.agent.md but NOT src/owlbear/agents/*.md. AgentRegistry scans the latter at runtime, so delegation fails with KeyError (e.g. 'builder' not found, available: coder, orchestrator, planner...).

## Reference

See docs/agent-definitions-sync-research.md for full research findings and canonical mapping.

## Scope

1. Rename coder.md → builder.md, update all content (name, description, tools, skills, system prompt)
2. Rename planner.md → kanban-planner.md, update all content
3. Create architect.md (new — role: validator, tools: filesystem+kanban+ask_user)
4. Create closer.md (new — role: validator, tools: filesystem+terminal+kanban+ask_user)
5. Update orchestrator.md: add terminal tool, update agent catalog from 5→8 entries, update intent routing table
6. Update researcher.md: change role validator→builder, add web_search+knowledge+ask_user tools
7. Update reviewer.md: add code-review skill
8. Update writer.md: add terminal tool, add docs-gate skill
9. Delete coder.md and planner.md
10. Update tests/test_agent_definitions.py: EXPECTED_AGENTS 6→8, scan count 6→8, role parametrize lists, planner tracking test

## Agent Specification (canonical mapping)

| Agent | Role | Tools | Skills | Depth |
|-------|------|-------|--------|-------|
| orchestrator | builder | delegation, filesystem, ask_user, kanban, terminal | kanban-md, kanban-based-development | 5 |
| kanban-planner | builder | filesystem, ask_user, kanban | kanban-md, kanban-based-development, project-definition | 3 |
| builder | builder | filesystem, terminal | kanban-md, tdd-workflow | 2 |
| researcher | builder | filesystem, browser, web_search, knowledge, ask_user | (none) | 1 |
| architect | validator | filesystem, kanban, ask_user | kanban-md | 1 |
| reviewer | validator | filesystem, terminal | kanban-md, code-review | 0 |
| writer | builder | filesystem, terminal | kanban-md, docs-gate | 0 |
| closer | validator | filesystem, terminal, kanban, ask_user | kanban-md, task-verification | 0 |

## Acceptance Criteria

- [ ] All 8 agent .md files exist in src/owlbear/agents/: orchestrator, kanban-planner, builder, researcher, architect, reviewer, writer, closer
- [ ] Agent names in YAML frontmatter match filenames: builder (not coder), kanban-planner (not planner)
- [ ] Each agent's tools list matches the specification table above — verified by test_agent_definitions.py
- [ ] Each agent's role matches the specification table — researcher is builder (not validator)
- [ ] Each agent's skills list matches the specification table
- [ ] Orchestrator system prompt agent catalog lists all 8 agents with correct names and descriptions
- [ ] Orchestrator intent routing table uses builder (not coder), kanban-planner (not planner)
- [ ] AgentRegistry.scan() on src/owlbear/agents/ finds exactly 8 definitions
- [ ] AgentRegistry.get(name) returns an Agent for each of the 8 names without KeyError
- [ ] All tool names resolve via _aliases in bootstrap.py (no KeyError from tool resolver)
- [ ] Old files coder.md and planner.md are deleted from src/owlbear/agents/
- [ ] tests/test_agent_definitions.py updated: EXPECTED_AGENTS has 8 entries with correct metadata
- [ ] System prompts are 10-25 non-blank lines (<=70 for orchestrator) per existing test constraint
- [ ] uv run pytest -q --tb=short passes (all tests green)
- [ ] uv run ruff check src/owlbear/agents/ tests/test_agent_definitions.py passes

## Notes

- This is one atomic change — the files are tightly coupled (orchestrator references all others, test validates all)
- TDD approach: Update EXPECTED_AGENTS in test file first (watch it fail), then update agent definitions
- test_intent_routing.py uses old names (planner, coder) in synthetic tests — will still pass but consider updating SPECIALIST_AGENTS as optional cleanup
- test_integration_e2e.py uses coder in synthetic delegation test — will still pass, non-blocking
