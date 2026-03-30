---
id: 20
title: Build dispatch planner
status: todo
priority: needed
created: 2026-03-26T17:22:22.8937692+01:00
updated: 2026-03-30T07:50:35.2753094+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 144
    - 145
    - 146
class: standard
---

## Objective

Umbrella task for the dispatch planner module. All implementation is delivered through
subtasks (#144, #145, #146). This task verifies the integrated result.

## Acceptance Criteria (verification)

- [ ] Planner subpackage exists at `packages/orchestrator/src/owlbear/planner/` with `__init__.py`
- [ ] `planner.models` exports `Task`, `DispatchEntry`, `DispatchPlan` Pydantic models (#144)
- [ ] `planner.board` exports `read_board()` returning `list[Task]` from kanban-md subprocess (#144)
- [ ] `planner.gates` exports 6 gate predicate functions matching dispatch-planning skill (#145)
- [ ] `planner.selector` exports task selector with dual-key sort and 20-task cap (#145)
- [ ] Agent mapper dict matches dispatch-planning skill status-to-agent table (#145)
- [ ] Orchestrator loop in `orchestrator/loop.py` consumes `DispatchPlan` via AcpClient (#146)
- [ ] All subtask unit tests pass (models, board reader, gates, selector, loop)
- [ ] Integration: `read_board() | check_gates() | select_tasks()` produces a valid `DispatchPlan`

## Subtask Map

| Subtask | Title | Status | Depends On |
|---------|-------|--------|------------|
| #144 | Planner data models and board reader | backlog | #14 |
| #145 | Planner gate checker and task selector | ideation | #144 |
| #146 | Orchestrator dispatch loop | ideation | #145, #19 |

## TDD Exemption

Umbrella/tracker task. All AC items map 1:1 to subtask deliverables with their own
TDD cycles. No additional test task needed.

## Context

Depends on #144, #145, #146 (subtask chain). Transitively depends on #14 (mcp-kanban,
archived) and #19 (ACP client, in-progress via #146). The planner module enables headless
orchestration without VS Code â€” both VS Code agent mode and ACP headless mode use the
same kanban board and the same dispatch-planning skill algorithm.

See docs/research/build-dispatch-planner.md for the full research findings.

[[2026-03-29]] Sun 19:14
## Architecture Review
**Verdict:** REFINE (umbrella conversion)

### AC Assessment

Original AC mixed planner and orchestrator concerns. Research (docs/research/build-dispatch-planner.md) correctly identified the separation and subtasks #144, #145, #146 were created to decompose #20.

- read_board(), select_task(), select_agent() are planner concerns delegated to #144 and #145
- format_prompt() and dispatch loop are orchestrator concerns delegated to #146
- Unit tests delegated to each subtask's own TDD cycle

All original AC lines are now covered by subtask AC. #20 converted to umbrella/tracker following #19 pattern.

### Architecture Notes

Module placement: `packages/orchestrator/src/owlbear/planner/` as a subpackage of owlbear, consistent with existing layout (owlbear.voice, owlbear.errors). The owlbear_orchestrator package holds ACP infrastructure (acp_client, process_supervisor); the planner is domain logic and belongs in owlbear.

Pattern compliance:
- Pydantic frozen models following voice/protocol.py convention
- Subprocess board reader following mcp-kanban _run_kanban() pattern
- Error hierarchy extends OwlBearError (owlbear.errors)
- Gate algorithm ports dispatch-planning skill to typed Python

Concern separation validated: planner produces DispatchPlan (data), orchestrator consumes it via AcpClient (infrastructure). Mirrors LLM mode separation (planner.agent.md produces JSON, orchestrator.agent.md dispatches).

### Changes Made

- Rewrote body as umbrella/tracker AC with verification criteria and subtask map
- Updated depends_on: removed [19, 14], added [144, 145, 146]
- Added TDD Exemption section (umbrella task, subtasks have own TDD)

### Dependencies

- Removed: #19 (ACP client, in-progress) -- transitively covered via #146
- Removed: #14 (mcp-kanban, archived) -- transitively covered via #144
- Added: #144, #145, #146 (subtask chain)
- Verified: #14 archived, #19 in-progress (only blocks #146, not #144 or #145)

### Notes for subtask reviews

When #144 reaches architect review, note:
1. Add explicit pydantic>=2.10.0 to orchestrator pyproject.toml (currently transitive only)
2. Handle `class` field name conflict via Field(alias=class) with populate_by_name=True
