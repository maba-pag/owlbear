---
id: 65
title: 'Test: Scaffold mcp-kanban MCP server package'
status: archived
priority: medium
created: 2026-03-26 19:58:03.542384+01:00
updated: 2026-03-27 22:15:43.851684+01:00
started: 2026-03-27 22:15:43.851684+01:00
completed: 2026-03-27 22:15:43.851684+01:00
tags:
- phase-1
- scope:mcp
- test
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write failing tests for #39 (mcp-kanban scaffold) before implementation.

## Acceptance Criteria
- [ ] test_server.py in packages/mcp-kanban/tests/ with pytest
- [ ] Test list_tasks tool returns subprocess stdout on success (mock subprocess)
- [ ] Test list_tasks tool returns error string on non-zero exit code (mock subprocess)
- [ ] Test lifespan raises FileNotFoundError when kanban binary is missing
- [ ] Test lifespan resolves KANBAN_BIN env var when set
- [ ] Test lifespan falls back to kanban/kanban-md.exe when env var unset
- [ ] All tests fail (RED phase, no implementation exists yet)

## Context
Precedes #39. See #39 AC for interface contract.
v1 prior art: v1/src/owlbear/tools/kanban.py for subprocess pattern.
