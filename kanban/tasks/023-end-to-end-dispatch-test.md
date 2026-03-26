---
id: 23
title: End-to-end dispatch test
status: ideation
priority: needed
created: 2026-03-26T17:22:57.6175767+01:00
updated: 2026-03-26T17:25:19.5311273+01:00
tags:
    - phase-2
    - scope:orchestrator
    - type:test
depends_on:
    - 20
    - 22
    - 14
class: standard
---

## Objective
End-to-end integration test: dispatch a task via the CLI, agent works autonomously, kanban board updates.

## Acceptance Criteria
- [ ] Create a test task on the kanban board
- [ ] Run owlbear dispatch <id> targeting the test task
- [ ] Copilot CLI spawns, receives prompt, works on the task
- [ ] Agent uses MCP tools (kanban) during execution
- [ ] Task status updates on completion
- [ ] Audit log records the dispatch and outcome
- [ ] Repeatable: test can be run multiple times
- [ ] Document any manual steps required

## Context
Depends on O2 (dispatch planner), O4 (CLI triggers), and M1 (mcp-kanban). This is the proof that the entire stack works end-to-end. Success here means v2 is functional.
