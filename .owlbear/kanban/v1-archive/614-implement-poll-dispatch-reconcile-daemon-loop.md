---
id: 614
title: Implement poll-dispatch-reconcile daemon loop
status: archived
priority: needed
created: 2026-03-07T05:20:31.0317524+01:00
updated: 2026-03-07T18:08:21.4806904+01:00
started: 2026-03-07T05:43:55.9747168+01:00
completed: 2026-03-07T18:08:21.4806904+01:00
tags:
    - scope:core
    - agent
depends_on:
    - 635
class: standard
---

Extend run_daemon() with a poll-dispatch-reconcile loop that autonomously picks up kanban tasks. See docs/research/poll-dispatch-reconcile.md for full analysis.

AC:

- [ ] `autonomous_mode` config field (bool, default False) in OwlBearSettings — gates the poll loop
- [ ] `poll_interval` config field (float, default 30.0) in OwlBearSettings — must be > 0
- [ ] `max_concurrent_tasks` config field (int, default 3) in OwlBearSettings — must be > 0
- [ ] Extract existing receive-turn-send while-loop into `async def channel_loop(shutdown_event, sentinel, channel, agent, settings, error_journal)` coroutine in daemon.py
- [ ] Add `async def poll_loop(shutdown_event, settings, agent_registry, kanban_toolset, state)` coroutine in daemon.py
- [ ] `run_daemon()` runs both coroutines in `asyncio.TaskGroup` when `autonomous_mode=True`; runs `channel_loop` alone when `False`
- [ ] `OrchestratorState` dataclass in daemon.py: `running: dict[str, RunningTask]`, `claimed: set[str]`
- [ ] `RunningTask` dataclass: `task_id: str`, `asyncio_task: asyncio.Task`, `started_at: datetime`
- [ ] Each poll tick: reconcile completed/failed asyncio.Tasks, then fetch todo (`kanban_list --status todo --not-blocked`), sort by kanban priority, dispatch up to `max_concurrent_tasks` slots
- [ ] Dispatch: move task to in-progress via `KanbanToolset.kanban_move()`, build prompt from `kanban_show`, spawn `asyncio.create_task(agent.run(prompt, deps=deps))` using `AgentRegistry.get('builder')`
- [ ] On task success: move task to review via `KanbanToolset.kanban_move()`, remove from `running`/`claimed`
- [ ] On task failure: log error, remove from `running`/`claimed`, free slot (retry scheduling deferred to #625)
- [ ] Shutdown: `shutdown_event` cancels poll sleep, in-flight asyncio.Tasks cancelled with `asyncio.wait` grace period
- [ ] Stall detection deferred to #623; retry with backoff deferred to #625

Architecture notes:

- Dual-coroutine: channel_loop() + poll_loop() in asyncio.TaskGroup
- In-memory OrchestratorState (not persisted — YAGNI per research S4)
- Uses AgentRegistry.get('builder') for dispatch (returns Agent[OwlBearDeps, str])
- Uses KanbanToolset._run_kanban for board I/O (already async subprocess)
- run_daemon() signature gains: agent_registry (optional), kanban_toolset (optional), settings (already present)
- No workspace isolation (single repo, YAGNI)
- #615 (WIP continuity), #623 (stale detector), #625 (task retry) depend on this
