---
id: 145
title: Implement planner gate checker and task selector
status: todo
priority: needed
created: 2026-03-29T16:23:38.8707663+02:00
updated: 2026-03-30T08:23:55.8856413+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 144
    - 207
class: standard
---

See docs/research/planner-gate-checker-selector.md for validated research.
See docs/research/build-dispatch-planner.md S3.5 for parent design.

## Acceptance Criteria

### gates.py — packages/orchestrator/src/owlbear/planner/gates.py

- [ ] `check_atomicity(task: Task) -> bool` — returns `False` if `task.title` matches `r"\band\b"` word-boundary regex (flags potential multi-concern tasks). Returns `True` otherwise. Docstring notes this is a heuristic approximation; false positives re-enter next cycle.
- [ ] `check_tdd(task: Task) -> bool` — returns `False` if `task.status == "in-progress"` and `"## Test-Writer Notes"` is not in `task.body`. Returns `True` for all other statuses.
- [ ] `check_clarity(task: Task) -> bool` — returns `False` if `task.status` in `("todo", "in-progress", "review", "docs", "done")` and `task.body` lacks bullet or numbered AC (regex: `r"(?m)^\s*(-\s|\d+\.\s)"`). Returns `True` for `ideation` and `backlog` (AC not required yet).
- [ ] `check_gates(task: Task) -> bool` — composite: returns `check_atomicity(task) and check_tdd(task) and check_clarity(task)`. Docstring documents that gates 1 (status), 2 (dependency), and 6 (claim) are handled by CLI flags in `read_board()`.
- [ ] All functions are pure (no I/O, no subprocess calls). Import `Task` from `owlbear.planner.models`.

### selector.py — packages/orchestrator/src/owlbear/planner/selector.py

- [ ] `PRIORITY_RANK: dict[str, int]` — `{"critical": 0, "needed": 1, "important": 2, "nice-to-have": 3, "someday": 4}`
- [ ] `STATUS_RANK: dict[str, int]` — `{"done": 0, "docs": 1, "review": 2, "in-progress": 3, "todo": 4, "backlog": 5, "ideation": 6}` (pipeline proximity: closer to done = lower rank = dispatched first)
- [ ] `STATUS_AGENT_MAP: dict[str, str]` — `{"ideation": "researcher", "backlog": "architect", "todo": "test-writer", "in-progress": "builder", "review": "reviewer", "docs": "writer", "done": "auditor"}`
- [ ] `DISPATCH_CAP: int = 20`
- [ ] `def select_tasks(tasks: list[Task]) -> DispatchPlan`:
  - Filters input via `check_gates(task)` — tasks failing any gate are excluded
  - DECOMP routing override: if `"Needs decomposition:"` in `task.body`, agent is `"kanban-planner"` regardless of status
  - Sorts passing tasks by `(PRIORITY_RANK[task.priority], STATUS_RANK[task.status])` — dual-key ascending
  - Caps result at `DISPATCH_CAP` entries (top N from sorted list)
  - For each task, maps `task.status` to agent via `STATUS_AGENT_MAP` (unless DECOMP override applies)
  - Returns `DispatchPlan(entries=[DispatchEntry(task_id=..., agent=..., target_status=...) for ...])`
  - Unknown priority or status keys: use `max_rank + 1` as fallback rank (sort to end, still dispatchable)
- [ ] Import `Task`, `DispatchEntry`, `DispatchPlan` from `owlbear.planner.models` and `check_gates` from `owlbear.planner.gates`

### Infrastructure

- [ ] Update `packages/orchestrator/src/owlbear/planner/__init__.py` — add public imports: `check_gates`, `check_atomicity`, `check_tdd`, `check_clarity` from gates; `select_tasks`, `STATUS_AGENT_MAP`, `DISPATCH_CAP` from selector

### Patterns to follow

- Pure functions on Task model objects (no subprocess calls, no I/O)
- Import from owlbear.planner.models only (same package, no cross-layer deps)
- No new error types (gates return bool, selector returns DispatchPlan)
- Follow #144's code style (from __future__ import annotations, type hints, frozen models, docstrings)

[[2026-03-30]] Mon 08:22
## Architecture Review
**Verdict:** APPROVED (AC refined, TDD test task created)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 6 gate predicate functions | Misleading: only 3 need Python logic (gates 1,2,6 handled by CLI) | Rewritten: 3 predicates + 1 composite check_gates() |
| Gate checker in gates.py | Good location, but missing function signatures | Rewritten: exact signatures with types and behavior spec |
| Task selector with dual-key sort | Correct algorithm, no signatures, no file specified | Rewritten: selector.py with PRIORITY_RANK, STATUS_RANK, select_tasks() |
| Agent mapper dict | Vague reference to skill table | Rewritten: exact STATUS_AGENT_MAP dict with all 7 entries |
| 20-task dispatch cap | Clear | Kept: DISPATCH_CAP = 20 |
| Returns DispatchPlan | Good | Kept: select_tasks() returns DispatchPlan |
| Unit tests bundled with impl | Violates TDD convention | Removed: created test task #207 |
| (missing) DECOMP routing | Research S3.4 flagged this gap | Added: body check routes to kanban-planner |
| (missing) Unknown priority/status handling | Edge case for unknown values | Added: fallback rank (sort to end, still dispatchable) |
| (missing) selector.py file | Research S3.5 recommended split | Added: gates.py + selector.py separation |
| (missing) __init__.py updates | Not in original AC | Added: public imports for gates and selector |

### Architecture Notes
- Single domain: scope:orchestrator (planner/ subpackage only)
- Two-file split (gates.py + selector.py) follows #144's models.py + board.py pattern
- All functions are pure (no I/O, no subprocess). Input is Task models from #144's models.py
- No module layering concerns: gates.py and selector.py import only from owlbear.planner.models (same package leaf)
- No new error types: gates return bool, selector returns DispatchPlan
- No new user-input boundary: functions receive typed Python objects, not user strings
- DECOMP routing fills a gap vs. dispatch-planning skill (S3.4 from research)
- Gate 3 atomicity uses word-boundary regex heuristic. False positives acceptable (tasks re-enter next cycle)
- Gate 4 TDD fallback (linked test task lookup) deferred per research S3.3 recommendation (YAGNI)

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| check_atomicity() | False positive on "and" | N/A (returns False) | Yes, task re-enters next cycle | Minor delay, self-correcting |
| check_tdd() | TW notes present but malformed | N/A (string check passes) | Yes, passes gate | Potential quality gap caught by reviewer |
| check_clarity() | AC present but not bullet/numbered | N/A (returns False) | Yes, task excluded | Re-enters when AC reformatted |
| select_tasks() | Unknown priority key | KeyError | Yes, fallback rank | Sorts to end, still dispatched |
| select_tasks() | Unknown status key | KeyError | Yes, fallback rank | Sorts to end, agent map miss handled |

### Changes Made
- Rewrote task body with precise AC (exact function signatures, file locations, constants, DECOMP routing)
- Created test task #207 (Test: planner gate checker and task selector) at todo, depends on #144
- Added depends_on #207 to #145
- Removed bundled unit test AC from impl task (moved to #207)

### Dependencies
- Verified: #144 (planner data models + board reader) in review, code exists
- Added: #207 (TDD RED tests) at todo, #145 depends on it
- Verified: #20 (umbrella) depends on #145, unaffected
