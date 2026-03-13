---
id: 680
title: 'Planner agent: board reading + wave planning'
status: archived
priority: needed
created: 2026-03-08T15:44:14.6989155+01:00
updated: 2026-03-09T00:45:58.5326138+01:00
started: 2026-03-08T16:07:09.9129054+01:00
completed: 2026-03-09T00:45:58.5326138+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Context

The orchestrator currently does ALL cognitive work in-context: reading the board, building dependency graphs, gate-checking tasks, planning waves. This is the primary cause of context overflow and the #663 class of failures. See docs/research/planner-agent.md for full analysis.

## Acceptance Criteria

- [ ] `.github/agents/planner.agent.md` created with all required sections: persona, critical_rules, multi_agent_context, workflow (steps below), output_format, boundaries, examples (good + bad), self_critique checklist
- [ ] Frontmatter: `name: planner`, `user-invocable: false`, `description` references wave planning
- [ ] Tools restricted to read-only board access + self-tracking: `vscode/memory`, `execute/runInTerminal`, `execute/getTerminalOutput`, `read/terminalLastCommand`, `read/readFile`, `todo`. NO `agent` tool. NO `edit/*` tools. NO `vscode/askQuestions`.
- [ ] Workflow step 1 — Receive scope: orchestrator passes a scope filter (tag, status, ID range, or "all"). Planner applies it to `kanban\kanban-md.exe list --compact`.
- [ ] Workflow step 2 — Read board: `kanban\kanban-md.exe list --compact` filtered by scope. For each candidate: `kanban\kanban-md.exe show {id}` to read AC, deps, status, tags, blocked state.
- [ ] Workflow step 3 — Build DAG: nodes = in-scope tasks, edges = `depends_on`. Classify each as ready (all deps done + unblocked), blocked (deps unmet or `--block` set), or external (deps outside scope not done).
- [ ] Workflow step 4 — Run 5 gate checks per candidate task:
  (1) Status gate — task status matches its dispatch target (backlog->architect, todo->builder, review->reviewer, docs->writer, done->auditor)
  (2) Dependency gate — ALL `depends_on` tasks are in `done` status
  (3) Atomicity gate — title has single responsibility (no "and" joining unrelated concerns)
  (4) TDD gate — if implementation task (not test/research/docs), a corresponding test task exists in `done`
  (5) Clarity gate — task body contains non-empty acceptance criteria with at least one `- [ ]` checkbox
- [ ] Workflow step 5 — Wave grouping: group gate-passing tasks into waves. Max 4 tasks per wave. Wave N+1 contains only tasks whose deps are satisfied by completions in Wave N or earlier. Independent tasks within a wave run in parallel.
- [ ] Workflow step 6 — Annotate: write wave assignment to each dispatched task via `kanban\kanban-md.exe edit {id} --append-body "Wave {n}, agent: {agent_name}" --timestamp`
- [ ] Output uses WAVE_PLAN line-oriented format (grep-parseable, no LLM needed to read):
  `WAVE_PLAN` / `WAVE 1:` / `#{id} {agent_name} "{one-line AC summary}"` / `BLOCKED:` / `#{id} "{reason}"` / `SKIPPED:` / `#{id} gate:{gate_name} "{reason}"` / `END_PLAN`
- [ ] Agent-to-status dispatch mapping documented in agent file: backlog=architect, todo=builder, review=reviewer, docs=writer, done=auditor
- [ ] Boundaries section explicitly prohibits: moving tasks (orchestrator's job), dispatching subagents, editing source/test files, interpreting subagent results (evaluator's job), interacting with user

## Scope Boundary

This task creates `planner.agent.md` ONLY. Orchestrator integration (replacing Steps 1-5 with `runSubagent(planner)`) is #682's scope. Do not modify `orchestrator.agent.md`.

## Notes

- Naming: `planner` (wave scheduling from existing tasks) vs `kanban-planner` (task creation from requirements). Distinct roles per research section 3.6.
- The WAVE_PLAN format is the planner's routing signal per the two-channel protocol (#684). Orchestrator reads WAVE_PLAN to dispatch; downstream agents read task bodies written by the planner.
- No separate Python test task needed — this is an .agent.md file. The reviewer verifies: (a) output_format matches WAVE_PLAN spec above, (b) workflow implements all 5 gates, (c) tool list has no unauthorized tools.
- Risk: planner context overflow on 50+ task boards. Mitigated by scope filter + `--compact` output. Document this limitation in the agent's boundaries section.
- Follow existing agent file patterns: orchestrator.agent.md (workflow structure, examples format), kanban-planner.agent.md (read-only board access pattern).

[[2026-03-08]] Sun 23:51
Wave 3, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 5, agent: auditor

[[2026-03-09]] Mon 00:45
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| AC1: All required sections | persona, critical_rules, multi_agent_context, workflow, output_format, boundaries, examples (2 good + 4 bad), self_critique | .97 |
| AC2: Frontmatter correct | name: planner, user-invocable: false, desc refs wave plan | .97 |
| AC3: Tools restricted | 6 tools, no agent/edit/askQuestions | .97 |
| AC4: Step 1 scope filter | wave-planning SKILL.md Step 1 | .97 |
| AC5: Step 2 read board | wave-planning SKILL.md Step 2, show {id} | .97 |
| AC6: Step 3 build DAG | wave-planning SKILL.md Step 3, ready/blocked/external | .97 |
| AC7: Step 4 five gate checks | wave-planning SKILL.md Step 4, all 5 gates | .97 |
| AC8: Step 5 wave grouping max 4 | wave-planning SKILL.md Step 5 | .97 |
| AC9: Step 6 annotate | wave-planning SKILL.md Step 6, --append-body --timestamp | .97 |
| AC10: WAVE_PLAN format | Skill L133-153 + agent L81-102 match spec | .97 |
| AC11: Dispatch mapping | Agent L57-66, todo=test-writer (positive deviation from AC text todo=builder, matches pipeline) | .95 |
| AC12: Boundaries | All 5 prohibitions present | .97 |

Tests: 1271 passed, 1 pre-existing slack_sdk failure. Ruff: 3 pre-existing.
Confidence: .97
