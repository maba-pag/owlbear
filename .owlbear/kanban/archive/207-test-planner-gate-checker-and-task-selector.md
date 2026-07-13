---
id: 207
title: 'Test: planner gate checker and task selector'
status: archived
priority: medium
created: 2026-03-30 08:22:01.995930+02:00
updated: 2026-03-31 23:48:45.876889+02:00
started: 2026-03-31 23:48:45.375336+02:00
completed: 2026-03-31 23:48:45.375336+02:00
tags:
- phase-2
- scope:orchestrator
- type:test
- test
depends_on:
- 144
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-30]] Mon 18:44
## Test-Writer Notes
- Test file 1: tests/test_planner_gates.py
- Test file 2: tests/test_planner_selector.py
- Classes: TestFromAC_CheckAtomicity, TestFromAC_CheckTDD, TestFromAC_CheckClarity, TestFromAC_CheckGates, TestFromAC_Constants, TestFromAC_SelectTasks
- Tests per category: happy 19, edge 5, error 8, boundary 2
- Total: 34 tests, all FAIL (ModuleNotFoundError) ✓
- ruff: clean
- AC coverage:
  - check_atomicity ' and ' → False: test_title_with_and_joining_words_returns_false
  - check_atomicity no and → True: test_title_without_and_returns_true
  - check_atomicity word-boundary: test_title_with_and_inside_word_returns_true
  - check_tdd in-progress with notes → True: test_in_progress_with_tdd_notes_returns_true
  - check_tdd in-progress without notes → False: test_in_progress_without_tdd_notes_returns_false
  - check_tdd non-in-progress → True: test_todo_task_always_returns_true, test_review_task_always_returns_true, test_done_task_always_returns_true
  - check_clarity todo bullet → True: test_todo_with_bullet_ac_returns_true
  - check_clarity todo numbered → True: test_todo_with_numbered_ac_returns_true
  - check_clarity todo no bullets → False: test_todo_with_no_bullets_returns_false
  - check_clarity ideation exempt: test_ideation_with_no_ac_returns_true
  - check_clarity backlog exempt: test_backlog_with_no_ac_returns_true
  - check_gates all pass → True: test_task_passing_all_three_gates_returns_true
  - check_gates any fail → False: test_task_failing_atomicity_returns_false, test_task_failing_tdd_returns_false, test_task_failing_clarity_returns_false
  - PRIORITY_RANK: test_priority_rank_contains_all_five_priorities, test_priority_rank_correct_ordering
  - STATUS_RANK: test_status_rank_contains_all_seven_statuses, test_status_rank_correct_ordering
  - STATUS_AGENT_MAP: test_status_agent_map_has_all_seven_statuses, test_status_agent_map_correct_agents
  - DISPATCH_CAP=20: test_dispatch_cap_is_twenty
  - select_tasks empty: test_empty_input_returns_empty_dispatch_plan
  - select_tasks single task: test_single_passing_task_produces_correct_dispatch_entry
  - select_tasks gate fail excluded: test_gate_failing_task_is_excluded
  - select_tasks sorting: test_tasks_sorted_by_priority_then_pipeline_proximity
  - select_tasks cap 20: test_twenty_five_tasks_capped_at_twenty
  - select_tasks DECOMP override: test_decomp_override_maps_to_kanban_planner
  - select_tasks unknown priority fallback: test_unknown_priority_uses_fallback_rank_sorts_to_end
  - select_tasks unknown status fallback: test_unknown_status_uses_fallback_rank_sorts_to_end

[[2026-03-31]] Tue 12:28
## Review Evidence

### Test Results
- pytest: 34 passed, 0 failed (test_planner_gates.py + test_planner_selector.py)

### Lint Results
- ruff: All checks passed (gates.py, selector.py, both test files)

### Coverage
- owlbear/planner/gates.py: 100% (18 stmts)
- owlbear/planner/selector.py: 100% (25 stmts)
- owlbear/planner/models.py: 100%

### AC Compliance

All 27 AC lines covered. All pass. See detail below.

check_atomicity ' and ' returns False: test_title_with_and_joining_words_returns_false â€” PASS
check_atomicity no and returns True: test_title_without_and_returns_true â€” PASS
check_atomicity word-boundary (handler): test_title_with_and_inside_word_returns_true â€” PASS
check_tdd in-progress+notes True: test_in_progress_with_tdd_notes_returns_true â€” PASS
check_tdd in-progress no-notes False: test_in_progress_without_tdd_notes_returns_false â€” PASS
check_tdd non-in-progress True: test_todo/review/done_task_always_returns_true (3 tests) â€” PASS
check_clarity todo bullet True: test_todo_with_bullet_ac_returns_true â€” PASS
check_clarity todo numbered True: test_todo_with_numbered_ac_returns_true â€” PASS
check_clarity todo no bullets False: test_todo_with_no_bullets_returns_false â€” PASS
check_clarity ideation exempt: test_ideation_with_no_ac_returns_true â€” PASS
check_clarity backlog exempt: test_backlog_with_no_ac_returns_true â€” PASS
check_gates all pass True: test_task_passing_all_three_gates_returns_true â€” PASS
check_gates any fail False: test_task_failing_atomicity/tdd/clarity_returns_false (3) â€” PASS
PRIORITY_RANK 5 priorities: test_priority_rank_contains_all_five + correct_ordering â€” PASS
STATUS_RANK 7 statuses: test_status_rank_contains_all_seven + correct_ordering â€” PASS
STATUS_AGENT_MAP 7 statuses: test_status_agent_map_has_all_seven + correct_agents â€” PASS
DISPATCH_CAP=20: test_dispatch_cap_is_twenty == 20 â€” PASS
select_tasks empty: test_empty_input_returns_empty_dispatch_plan â€” PASS
select_tasks single task: test_single_passing_task_produces_correct_dispatch_entry (task_id, agent, target_status) â€” PASS
select_tasks gate-fail excluded: test_gate_failing_task_is_excluded â€” PASS
select_tasks sorted: test_tasks_sorted_by_priority_then_pipeline_proximity â€” PASS
select_tasks cap 20: test_twenty_five_tasks_capped_at_twenty (len <= 20) â€” PASS
select_tasks DECOMP: test_decomp_override_maps_to_kanban_planner â€” PASS
unknown priority fallback: test_unknown_priority_uses_fallback_rank_sorts_to_end â€” PASS
unknown status fallback: test_unknown_status_uses_fallback_rank_sorts_to_end â€” PASS
All tests RED initially: TW notes confirm 34 ModuleNotFoundError, now 34 pass â€” PASS
ruff clean: confirmed above â€” PASS

### TestFromAC Integrity
All 34 TestFromAC_* methods preserved exactly. Two STRENGTHENING extras added by test-writer:
test_in_progress_empty_body_returns_false, test_todo_with_empty_body_returns_false.

### Test Quality
Assertion specificity: STRONG (is True/False, exact == checks, DispatchEntry field checks)
Error-path coverage: STRONG (gate failures, empty input, unknown priority/status)
Mutation resistance: STRONG
Test independence: STRONG (fresh _task() per test, no shared state)
Names: STRONG (all descriptive)

### Security
No issues. Pure functions, no I/O, no external input, no new deps.

### Verdict: PASS (confidence 0.95)

[[2026-03-31]] Tue 12:59
## Docs Gate
1. copilot-instructions.md - No - N/A: internal planner module, no behavior/API/convention change visible to agents
2. Docstrings - Yes - Pass: gates.py (module docstring + check_atomicity, check_tdd, check_clarity, check_gates) and selector.py (module docstring + select_tasks) all documented. All public symbols covered.
3. sources/overview.md - No - N/A: Task 145 section already covers re module and Pydantic v2 attributions. Test task introduces no new external patterns.
4. README.md - No - N/A: no CLI changes
5. Research doc - No - N/A: type:test task, no research phase
6. Scratch files - Clean: no docs/scratch/207-* files found

Files Updated: None
Scratch Files Cleaned: None
