---
id: 293
title: Planner agent definition — decompose ideas into project plans
status: archived
priority: critical
created: 2026-03-01T02:52:13.4900784+01:00
updated: 2026-03-01T17:08:17.8684431+01:00
started: 2026-03-01T03:35:48.1173584+01:00
completed: 2026-03-01T17:08:17.8684431+01:00
tags:
    - phase-11
    - agent
class: standard
---

## Context

No agent definition exists for the planning role. The orchestrator delegates but doesn't plan. Need a planner agent that takes vague user ideas and produces structured project definitions with requirements, AC, task decomposition.
See `docs/planner-agent-definition-research.md` for full research findings.

## Acceptance Criteria

### Agent definition file
- [ ] `src/owlbear/agents/planner.md` with YAML frontmatter + markdown body
- [ ] `name: planner`
- [ ] `description: Decomposes ideas into structured project plans`
- [ ] `role: builder` (needs write access for creating plan documents)
- [ ] `tools: [filesystem, ask_user, delegation]` -- existing tools only; knowledge/web_search deferred to follow-up task after #291/#292
- [ ] `skills: [kanban-md, kanban-based-development]` -- essential for task decomposition
- [ ] `max_delegation_depth: 3` -- supports planner -> researcher -> browser chain

### System prompt (markdown body)
- [ ] 10-25 non-blank lines (existing test enforces this constraint)
- [ ] Structure follows existing pattern: persona -> workflow (numbered steps) -> constraints -> output format
- [ ] Persona: 'You are the planner' -- distinguishes from orchestrator (planner creates tasks, orchestrator executes them)
- [ ] Workflow steps cover: idea clarification (ask_user), requirement elicitation, AC writing, task decomposition, dependency mapping
- [ ] Constraints: delegate research to researcher agent, never implement code, produce actionable kanban tasks not documents
- [ ] Output format: structured project definition with name, goals, requirements, tasks with AC, dependencies, priority

### Test updates (tests/test_agent_definitions.py)
- [ ] Add `planner` to `EXPECTED_AGENTS` dict with: description='Decomposes ideas into structured project plans', role='builder', tools=['filesystem', 'ask_user', 'delegation'], skills=['kanban-md', 'kanban-based-development'], max_delegation_depth=3
- [ ] `TestRegistryScanAgentsDir.test_scan_loads_all_five` count assertion: 5 -> 6
- [ ] `TestRoleValues.test_builders` parametrize list: add `planner`
- [ ] New test in `TestRegistryScanAgentsDir`: `registry.get('planner')` returns `Agent` instance (verifies tool resolution for all 3 tools)

### TDD flow
- [ ] Update EXPECTED_AGENTS and test assertions first -- tests fail (planner.md missing)
- [ ] Create `planner.md` -- all tests pass
- [ ] Run `uv run ruff check` clean

## Implementation Notes
- Follow existing agent `.md` pattern (see coder.md, orchestrator.md for structure)
- System prompt pattern: persona -> workflow (numbered steps) -> constraints -> output format (all 5 existing agents follow this)
- No separate test task needed -- test changes are parametrized additions to existing infrastructure, not a new test module
- TDD within task: builder writes EXPECTED_AGENTS entry first (tests fail), then creates the .md file (tests pass)
- Future follow-up: create task to add `knowledge` + `web_search` tools after #291/#292 complete
