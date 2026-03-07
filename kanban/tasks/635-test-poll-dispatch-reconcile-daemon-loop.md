---
id: 635
title: Test poll-dispatch-reconcile daemon loop
status: archived
priority: needed
created: 2026-03-07T05:53:59.055541+01:00
updated: 2026-03-07T18:08:28.4140234+01:00
started: 2026-03-07T06:08:17.6944041+01:00
completed: 2026-03-07T18:08:28.4140234+01:00
tags:
    - scope:core
    - agent
    - test
class: standard
---

Test-first task for #614. File: tests/test_poll_dispatch.py

AC:

- [ ] Tests autonomous_mode config field (bool, default False) in OwlBearSettings
- [ ] Tests poll_interval config field (float, default 30.0, must be > 0) in OwlBearSettings
- [ ] Tests max_concurrent_tasks config field (int, default 3, must be > 0) in OwlBearSettings
- [ ] Tests dual-coroutine lifecycle: channel_loop + poll_loop run concurrently in TaskGroup
- [ ] Tests poll tick sequence: reconcile completed tasks, fetch todo, sort by priority, dispatch
- [ ] Tests dispatch: task moved to in-progress, asyncio.Task spawned via AgentRegistry.get('builder')
- [ ] Tests completed task moved to review via KanbanToolset
- [ ] Tests failed dispatch frees slot (error logged, task NOT moved to review)
- [ ] Tests autonomous_mode=False: poll_loop is not started, channel_loop runs alone
- [ ] Tests shutdown_event during poll tick exits cleanly
- [ ] Tests max_concurrent_tasks cap: no dispatch when all slots full
- [ ] Tests OrchestratorState tracks running dict and claimed set correctly
- [ ] All tests fail before #614 implementation exists

Pattern: follow existing test_daemon.py structure. Mock KanbanToolset._run_kanban and AgentRegistry.get at toolset/registry level — never shell out to real kanban-md.
Ref: docs/poll-dispatch-reconcile-research.md S3.8
