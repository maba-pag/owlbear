---
id: 199
title: Ban manage_todo_list/todos tool from agents and validator
status: archived
priority: medium
created: 2026-03-30 02:43:08.658569+02:00
updated: 2026-03-30 03:13:59.330299+02:00
started: 2026-03-30 03:13:59.330299+02:00
completed: 2026-03-30 03:13:59.330299+02:00
tags:
- phase-1
- tooling
- agent
- config
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Disable the todos/manage_todo_list tool across the codebase. The tool does not function in subagent context (see docs/research/manage-todo-list-subagent-removal.md).

## Acceptance Criteria
- [ ] validate_agents.py: flag 'todos' in tools: line as disabled tool
- [ ] validate_agents.py: flag 'manage_todo_list' anywhere in file (like resolveMemoryFileUri check)
- [ ] validate_agents.py: update existing bare 'todo' check message from 'should be todos' to 'tool disabled for subagents'
- [ ] .github/copilot-instructions.md: remove the manage_todo_list process habit line
- [ ] tests/test_validate_agents.py: add tests for todos detection, manage_todo_list detection
- [ ] tests/test_validate_agents.py: update existing todo check tests if error message changed
- [ ] Run validator on all 11 agent files -- clean pass

## Context
See docs/research/manage-todo-list-subagent-removal.md for full findings.
Parent: #193. Related: #198 (broader validator expansion, still valid).

## Files to touch
- scripts/validate_agents.py
- tests/test_validate_agents.py
- .github/copilot-instructions.md

## Constraints
- Scope is ~50 LOC across 3 files
- Do NOT touch docs/research/*.md historical references

[[2026-03-30]] Mon 03:12
## Research
Research gate validated (2026-03-30, researcher). Checklist: all 7 items passed. Full findings in docs/research/manage-todo-list-subagent-removal.md.
Key verifications: copilot-instructions.md L27 manage_todo_list habit confirmed. validate_agents.py bare todo check needs message update. No agent files have todos/manage_todo_list in tools: (0 refs). argument-hint todos in orchestrator + planner are natural language, no false positive risk. Scope accurate: 3 files, approx 50 LOC.
