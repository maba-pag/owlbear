---
id: 639
title: Test WIP injection into poll_tick dispatch prompt
status: archived
priority: needed
created: 2026-03-07T06:35:17.9606652+01:00
updated: 2026-03-07T18:08:29.9832142+01:00
started: 2026-03-07T08:00:56.6101286+01:00
completed: 2026-03-07T18:08:29.9832142+01:00
tags:
    - scope:core
    - agent
    - test
depends_on:
    - 637
class: standard
---

TDD test task for WIP injection into daemon poll loop.
AC:
- [ ] test_poll_tick_loads_wip_and_prepends_to_prompt: mock WipStore.load returns summary, builder.run() receives prompt containing WIP text and CONTINUE FORWARD directive
- [ ] test_poll_tick_no_wip_clean_prompt: mock WipStore.load returns None, prompt does NOT contain CONTINUE FORWARD
- [ ] test_reconcile_saves_wip_on_success: task completes successfully, auto-save calls wip_store.save before kanban_move
- [ ] test_reconcile_clears_wip_on_success: task completes successfully, wip_store.clear called
- [ ] test_reconcile_clears_wip_on_failure: task fails, wip_store.clear called, state.claimed discarded
- [ ] test_auto_save_truncates_output: agent output over 500 chars, saved summary truncated to 500 chars

Notes:
- Mock KanbanToolset, AgentRegistry, WipStore
- Follow existing test_daemon.py patterns
