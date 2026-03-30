---
id: 201
title: Add tests for canonical tool registry validation
status: backlog
priority: nice-to-have
created: 2026-03-30T03:21:27.7619329+02:00
updated: 2026-03-30T06:13:54.4480171+02:00
tags:
    - phase-1
    - tooling
    - test
depends_on:
    - 198
class: standard
---

## Objective
Test the expanded validate_agents.py tool name validation.

## AC
- [ ] Test valid tool set names pass (agent, edit, search, etc.)
- [ ] Test valid individual built-in tools pass
- [ ] Test MCP server patterns pass (e.g. owlbear-kanban/*)
- [ ] Test unknown tool names are flagged
- [ ] Parametrized regression test over all 11 agent files
- [ ] Existing todo and resolveMemoryFileUri tests still pass
- [ ] ruff clean

See docs/research/canonical-tool-registry-validation.md

[[2026-03-30]] Mon 06:13
## Research

[[2026-03-30]] Mon 06:13
- **Overlap analysis:** #198 TDD already covers 3 of 7 AC items (unknown tools flagged, existing tests pass, ruff clean)
- **Genuine gaps:** happy-path tests for valid toolsets, valid prefixed tools, MCP patterns; parametrized per-agent regression
- **Hard dependency:** depends_on [198] added. KNOWN_TOOLSETS and _check_unknown_tools do not exist on HEAD until #198 builder lands
- **Implementation pattern:** follow test_rename_todo_to_todos.py parametrize idiom; reuse existing _write_agent/_agent_content helpers
- **Estimated scope:** ~25 LOC, 4 new test functions
- **Doc:** docs/research/test-canonical-tool-registry-coverage.md
