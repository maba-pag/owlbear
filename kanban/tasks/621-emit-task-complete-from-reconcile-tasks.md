---
id: 621
title: Emit TASK_COMPLETE from reconcile_tasks
status: archived
priority: needed
created: 2026-03-07T05:20:58.8815423+01:00
updated: 2026-03-07T18:08:24.629559+01:00
started: 2026-03-07T06:54:06.7230661+01:00
completed: 2026-03-07T18:08:24.629559+01:00
tags:
    - scope:core
    - phase-12
class: standard
---

reconcile_tasks() in daemon.py must emit HookEvent.TASK_COMPLETE with payload {task_id: str, outcome: 'success' | 'failure'} after popping completed tasks from state.running. Currently TASK_COMPLETE is defined in HookEvent but never emitted. hooks is not threaded into reconcile_tasks().

See docs/research/retrospective-learning-hook.md S3.2 for context.

## AC

- [ ] reconcile_tasks() accepts a hooks: HookRegistry | None parameter
- [ ] On successful task completion (no exception): await hooks.emit(HookEvent.TASK_COMPLETE, {'task_id': tid, 'outcome': 'success'})
- [ ] On failed task completion (exception): await hooks.emit(HookEvent.TASK_COMPLETE, {'task_id': tid, 'outcome': 'failure'})
- [ ] poll_tick() threads its hooks parameter through to reconcile_tasks()
- [ ] run_daemon() passes agent.hooks to poll_tick()
- [ ] Existing reconcile_tasks behavior (wip_store, kanban_move, claimed discard) unchanged
- [ ] Test: mock HookRegistry, complete a RunningTask successfully, verify emit called with {task_id, outcome='success'}
- [ ] Test: mock HookRegistry, complete a RunningTask with exception, verify emit called with {task_id, outcome='failure'}
- [ ] Test: hooks=None does not raise (graceful no-op)
- [ ] ruff clean

## Implementation Notes

- Follow the DAEMON_STARTUP emit pattern in run_daemon() (line ~615): await agent.hooks.emit(HookEvent.DAEMON_STARTUP, {...})
- reconcile_tasks already pops from state.running -- emit after pop, before claimed.discard()
- hooks parameter should default to None for backwards compat with existing callers
- Existing tests in test_daemon.py cover reconcile_tasks -- extend, don't duplicate
