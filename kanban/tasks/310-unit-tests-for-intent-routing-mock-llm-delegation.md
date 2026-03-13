---
id: 310
title: Unit tests for intent routing — mock LLM delegation paths
status: archived
priority: critical
created: 2026-03-01T06:16:26.5172351+01:00
updated: 2026-03-01T17:09:35.3703873+01:00
started: 2026-03-01T06:16:31.5473205+01:00
completed: 2026-03-01T17:09:35.3703873+01:00
tags:
    - phase-12
    - agent
    - routing
    - test
class: standard
---

Test each intent classification path using PydanticAI FunctionModel (see tests/test_integration_e2e.py TestDelegation for pattern):

- [ ] Test: 'I have an idea for a feature' -> delegates to planner
- [ ] Test: 'Fix the bug in config.py' -> delegates to coder
- [ ] Test: 'Research how others do X' -> delegates to researcher
- [ ] Test: 'Review the changes in PR #5' -> delegates to reviewer
- [ ] Test: 'What is the status of the board?' -> orchestrator handles directly (no delegation)
- [ ] Test: ambiguous message -> calls ask_user for clarification
- [ ] Test: mid-conversation reroute 'actually research this first' -> switches to researcher
- [ ] Each test uses FunctionModel returning ToolCallPart, asserts delegate_to_agent called with correct agent_name
- [ ] Test file: tests/test_intent_routing.py
- [ ] ruff clean

Pattern: follow TestDelegation in tests/test_integration_e2e.py — FunctionModel + ToolCallPart + OwlBearAgent.turn()
See docs/research/conversation-router.md S3.4 for intent taxonomy
