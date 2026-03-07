---
id: 623
title: Stale execution detector for daemon loop
status: backlog
priority: important
created: 2026-03-07T05:21:07.8260541+01:00
updated: 2026-03-07T07:09:19.1993327+01:00
started: 2026-03-07T07:09:19.1993327+01:00
tags:
    - scope:core
    - agent
depends_on:
    - 614
class: standard
---

Periodic scan of in-progress tasks. If no agent activity for stale_timeout, cancel task, block on kanban, and alert user. See docs/stale-execution-detector-research.md for full analysis.

AC:
- [ ] stale_task_timeout config field (float, default 300.0) in OwlBearSettings - must be > 0
- [ ] detect_stale_tasks() async function in daemon.py - scans state.running for tasks where now - started_at > stale_task_timeout
- [ ] Stale tasks: cancel asyncio.Task, block kanban task with reason, alert via channel
- [ ] detect_stale_tasks() called in poll_tick after reconcile_tasks()
- [ ] Cancelled stale tasks removed from state.running and state.claimed
- [ ] poll_tick gains channel and stale_timeout parameters
- [ ] Tests: mock time to verify stale detection triggers at threshold
- [ ] Tests: verify cancellation, kanban blocking, and channel alert
