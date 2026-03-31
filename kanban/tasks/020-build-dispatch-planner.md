---
id: 20
title: Build dispatch planner
status: todo
priority: needed
created: 2026-03-26T17:22:22.8937692+01:00
updated: 2026-03-30T23:04:45.0547735+02:00
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

[[2026-03-30]] Mon 18:48
## Test-Writer Notes
- Umbrella/tracker task — TDD Exemption declared in body.
- All AC items map 1:1 to subtask deliverables (#144, #145, #146) which each have their own TDD cycles.
- No test file applicable. Passing through to builder.

[[2026-03-30]] Mon 22:14
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear/planner/gates.py (new), planner/selector.py (full impl), planner/__init__.py (gates+selector exports), tests/test_planner_gates_selector.py (fixed datetime.UTC import)
- Tests: 73 passed, coverage 100% on gates.py and selector.py
- Lint: ruff clean
- Evidence: 73 passed in 0.20s, ruff all checks passed
- AC pending: orchestrator loop in loop.py (depends on #146, still in backlog)

[[2026-03-30]] Mon 23:03
## Review Evidence
See docs/scratch/20-reviewer.tmp for full evidence.

[[2026-03-30]] Mon 23:04
## Review Evidence (inline)

### Test Results
- pytest test_planner_gates_selector.py: 73 passed, 0 failed
- pytest test_orchestrator_loop.py: 51 passed, 0 failed

### Lint Results
- ruff planner scope: All checks passed!

### Subtask Status
- #144: archived
- #145: review (incomplete)
- #146: todo (loop not built by builder yet)

### AC Compliance

| AC Line | Status |
|---------|--------|
| Planner subpackage + __init__.py | PASS |
| planner.models (#144) | PASS |
| planner.board read_board (#144) | PASS |
| planner.gates exports (#145, 4 functions) | PASS (AC says 6 but #145 arch review revised to 4 - stale umbrella AC) |
| planner.selector dual-key sort 20-cap | PASS |
| STATUS_AGENT_MAP all 7 entries | PASS |
| loop.py consumes DispatchPlan (#146) | FAIL - #146 in todo; orchestrate() absent; run_loop has critical bug |
| All subtask tests pass including loop | FAIL - loop tests mask runtime bug via mocks |
| Integration read_board/check_gates/select_tasks | PARTIAL - gates+selector work; loop broken |

### PRIMARY FAIL: run_loop() incompatible select_tasks() call

loop.py run_loop() calls:
  select_tasks(tasks, crash_failures=state.crash_failures, stale_retried=state.stale_retried)

selector.py select_tasks() signature is:
  def select_tasks(tasks: list[Task]) -> DispatchPlan  (no kwargs)

Runtime result: TypeError. Tests pass only because TestFromAC_RunLoop fully mocks select_tasks.
#146 AC explicitly requires pre-filtering: select_tasks([t for t in tasks if t.id not in state.crash_failures])
stale_retried must be logging-only, not passed as kwarg.

### Secondary FAIL: Missing deliverables for #146
1. orchestrate() function absent from loop.py
2. run_loop() missing scope: str | None = None parameter (no scope forwarding to read_board)
3. orchestrator/__init__.py empty - missing orchestrate, run_loop, assemble_waves, format_prompt, Wave, LoopState, CycleResult exports

### Verdict: FAIL confidence .40 - back to todo until #146 is complete and bugs fixed

-t
