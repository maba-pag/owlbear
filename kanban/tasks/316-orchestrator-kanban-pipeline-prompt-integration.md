---
id: 316
title: Orchestrator kanban pipeline prompt + integration test
status: archived
priority: critical
created: 2026-03-01T06:24:04.7138882+01:00
updated: 2026-03-01T17:09:41.5765194+01:00
started: 2026-03-01T09:50:12.008996+01:00
completed: 2026-03-01T17:09:41.5765194+01:00
tags:
    - phase-12
    - agent
    - orchestrator
depends_on:
    - 315
class: standard
---

Prompt and integration test task for #301. Add kanban workflow knowledge to orchestrator and verify end-to-end.

## Acceptance Criteria

- [ ] `orchestrator.md` system prompt body updated with a 'Kanban Pipeline' section covering:
  - How to use `kanban_pick` to claim tasks (`--status todo --claim orchestrator --move in-progress`)
  - Task status lifecycle: `todo -> in-progress -> review` (builder does not move to done)
  - Dependency awareness: use `kanban_list --unblocked --status todo` to find ready tasks
  - Failure handling: `kanban_edit {id} --block 'reason'` and re-delegate or escalate
  - Delegation pattern: pick task -> read AC via `kanban_show` -> delegate to specialist -> verify result -> `kanban_move` to review
- [ ] Integration test in `tests/test_kanban_pipeline.py`:
  - `KanbanToolset` instantiated with mocked subprocess (real toolset, fake binary)
  - Verify `kanban_pick` -> `kanban_show` -> `kanban_move` sequence produces correct CLI calls
  - Verify error from `kanban_move` returns error string (not exception)
  - Verify `kanban_edit --block` called when task processing fails
- [ ] Existing agent definition tests still pass (orchestrator prompt changes don't break parsing)
- [ ] ruff clean

## Architecture Notes

The integration test does NOT require a running LLM — it tests the toolset mechanics (subprocess calls, flag assembly, error handling) in a realistic multi-step sequence. The orchestrator's prompt additions are behavioral guidance, not code — they tell the LLM how to use the kanban tools.
