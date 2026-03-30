---
id: 207
title: 'Test: planner gate checker and task selector'
status: todo
priority: needed
created: 2026-03-30T08:22:01.9959303+02:00
updated: 2026-03-30T08:22:01.9959303+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:test
    - test
depends_on:
    - 144
class: standard
---

TDD RED tests for #145. Write failing tests that define the interface contract for gate
checker functions and task selector.

## Acceptance Criteria

### tests/test_planner_gates.py

- [ ] `check_atomicity()`: title with `" and "` joining words returns `False`
- [ ] `check_atomicity()`: title without `" and "` returns `True`
- [ ] `check_atomicity()`: title with "and" inside a word (e.g., "handler") returns `True` (word-boundary check)
- [ ] `check_tdd()`: in-progress task with `## Test-Writer Notes` in body returns `True`
- [ ] `check_tdd()`: in-progress task without `## Test-Writer Notes` in body returns `False`
- [ ] `check_tdd()`: non-in-progress task (e.g., todo, review) always returns `True`
- [ ] `check_clarity()`: todo task with bullet AC (`- item`) returns `True`
- [ ] `check_clarity()`: todo task with numbered AC (`1. item`) returns `True`
- [ ] `check_clarity()`: todo task with no bullet/numbered AC returns `False`
- [ ] `check_clarity()`: ideation task with no AC returns `True` (exempt)
- [ ] `check_clarity()`: backlog task with no AC returns `True` (exempt)
- [ ] `check_gates()`: task passing all 3 returns `True`
- [ ] `check_gates()`: task failing any one gate returns `False`

### tests/test_planner_selector.py

- [ ] `PRIORITY_RANK` contains all 5 priorities with correct ordering (critical=0 to someday=4)
- [ ] `STATUS_RANK` contains all 7 statuses with correct ordering (done=0 to ideation=6)
- [ ] `STATUS_AGENT_MAP` maps all 7 statuses to correct agent names per dispatch-planning skill
- [ ] `DISPATCH_CAP` is 20
- [ ] `select_tasks()`: empty input returns `DispatchPlan(entries=[])`
- [ ] `select_tasks()`: single passing task produces correct `DispatchEntry` with mapped agent
- [ ] `select_tasks()`: gate-failing task is excluded from output
- [ ] `select_tasks()`: tasks sorted by priority then pipeline proximity (critical+done before needed+backlog)
- [ ] `select_tasks()`: 25-task input capped at 20 entries
- [ ] `select_tasks()`: DECOMP override — task with `"Needs decomposition:"` in body maps to `"kanban-planner"` agent
- [ ] `select_tasks()`: unknown priority/status uses fallback rank (sorts to end, not excluded)
- [ ] All tests FAIL (RED phase) against stub/missing modules
- [ ] ruff clean

### Patterns

- Use canned `Task` objects from `owlbear.planner.models` (same fixtures as test_planner_models.py)
- Pure unit tests — no subprocess mocks needed (gates and selector are pure functions)
- Follow test_planner_models.py and test_planner_board.py naming conventions
