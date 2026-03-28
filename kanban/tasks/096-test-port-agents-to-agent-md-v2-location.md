---
id: 96
title: 'Test: Port agents to agent-md v2 location'
status: todo
priority: needed
created: 2026-03-28T03:42:21.9792291+01:00
updated: 2026-03-28T03:44:36.6939867+01:00
tags:
    - phase-1
    - scope:agents
    - type:test
    - test
class: standard
---

## Objective
Write file-content assertion tests for the agent port (task #8).

## Acceptance Criteria
- [ ] Test all 11 .agent.md files exist in agents/ directory (architect, auditor, builder, curator, kanban-planner, orchestrator, planner, researcher, reviewer, test-writer, writer)
- [ ] Test each of the 11 agent files contains todos (not todo) in tools: list
- [ ] Test curator.agent.md does NOT contain resolveMemoryFileUri in tools: list
- [ ] Test researcher.agent.md contains microsoft/markitdown/* in tools: list
- [ ] Test orchestrator.agent.md agents: field includes Explore
- [ ] Test researcher.agent.md agents: field is [Explore]
- [ ] Test 9 leaf agents have agents: [] (empty list)
- [ ] Test .github/agents/ contains no .agent.md files (v1 cleanup complete)
- [ ] All tests FAIL in RED phase
- [ ] ruff clean
