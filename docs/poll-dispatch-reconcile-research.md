# Poll-Dispatch-Reconcile Daemon Loop — Implementation Research

> **Owning task:** #614 — Implement poll-dispatch-reconcile daemon loop
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear's daemon loop (`run_daemon()` in `daemon.py`) currently runs a receive→turn→send loop: it waits for user input from a channel, processes it through a single `OwlBearAgent`, and sends the response back. This is purely reactive — the daemon does nothing unless prompted.

**Question:** How should we extend `run_daemon()` to autonomously poll the kanban board for `todo` tasks, dispatch them to agents, and reconcile running tasks each tick — while preserving the existing interactive channel loop?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| openai/symphony SPEC.md | <https://github.com/openai/symphony/blob/main/SPEC.md> | 1.0 |
| OwlBear symphony-research.md | `docs/symphony-research.md` (#584) | .95 |
| OwlBear orchestration-agent-frameworks-research.md | `docs/orchestration-agent-frameworks-research.md` (#580) | .95 |
| quoroom-ai/room (WIP continuity) | `docs/quoroom-room-research.md` (#588) | .80 |
| Python asyncio.TaskGroup docs | <https://docs.python.org/3.12/library/asyncio-task.html#task-groups> | .85 |
| PydanticAI Agent.run() docs | <https://ai.pydantic.dev/agents/> | .90 |

## 3. Analysis

### 3.1 Current Architecture vs Target

| Aspect | Current (`run_daemon`) | Target |
|--------|----------------------|--------|
| Trigger | User message via channel | User message **+ periodic poll tick** |
| Concurrency | Sequential — one turn at a time | Up to `max_concurrent_tasks` async tasks |
| Board awareness | None — agent has `kanban_list` tool | Daemon reads board state each tick |
| Task lifecycle | Manual — user/agent moves kanban | Daemon claims→dispatches→reconciles |
| Error recovery | Per-turn retry in `_recover_from_error` | Per-turn retry **+ per-task retry with backoff** |

### 3.2 Dual-Loop Architecture

The key design decision: **two concurrent coroutines sharing a shutdown event**.

| Option | Description | Complexity | KISS |
|--------|-------------|------------|------|
| A. Single merged loop | `asyncio.wait` on channel + sleep timer | Medium | High |
| B. Two coroutines via TaskGroup | `channel_loop()` + `poll_loop()` in `asyncio.TaskGroup` | Medium | **High** |
| C. Background scheduler | `apscheduler` or custom scheduler | High | Low |

**Recommendation (.85):** Option B — two coroutines in a `TaskGroup`. The channel loop handles interactive messages (existing behavior). The poll loop runs on a timer and handles autonomous dispatch. Both check `shutdown_event`.

```
TaskGroup:
  channel_loop()  →  receive → turn → send  (existing behavior, extracted)
  poll_loop()     →  sleep(interval) → reconcile → fetch todo → dispatch
```

### 3.3 Poll Tick Sequence (adapted from Symphony §8.1)

Each tick follows this order:

1. **Reconcile** — Check running tasks: stalled? moved externally? done?
2. **Fetch candidates** — `kanban-md list --status todo --not-blocked --json`
3. **Sort by priority** — critical > needed > important > nice-to-have > someday
4. **Dispatch** — For each candidate while slots available: claim → spawn worker
5. **Log/notify** — Emit observability events

### 3.4 Data Structures

**Orchestrator state (in-memory, not persisted):**

| Field | Type | Purpose |
|-------|------|---------|
| `running` | `dict[str, RunningTask]` | task_id → running entry |
| `claimed` | `set[str]` | task IDs reserved (running or retry-queued) |
| `retry_queue` | `dict[str, RetryEntry]` | task_id → retry state |

**RunningTask:**

| Field | Type |
|-------|------|
| `task_id` | `str` |
| `asyncio_task` | `asyncio.Task` |
| `started_at` | `datetime` |
| `last_activity` | `datetime` |

**RetryEntry (from Symphony §4.1.7):**

| Field | Type |
|-------|------|
| `task_id` | `str` |
| `attempt` | `int` |
| `due_at` | `float` (monotonic) |
| `error` | `str | None` |

### 3.5 Config Fields Needed

| Field | Type | Default | Source |
|-------|------|---------|--------|
| `poll_interval` | `float` | `30.0` | Symphony default 30s |
| `max_concurrent_tasks` | `int` | `3` | Conservative; Symphony default 10 |
| `stall_timeout` | `float` | `300.0` | Symphony default 5min |
| `max_task_retries` | `int` | `5` | Symphony uses exponential up to max |
| `max_retry_backoff` | `float` | `300.0` | Symphony default 5min cap |
| `autonomous_mode` | `bool` | `False` | Gate — disable polling entirely |

### 3.6 Agent Dispatch — How to Run a Task

Symphony uses subprocess isolation. OwlBear uses PydanticAI `Agent.run()` in-process. The dispatch flow:

1. Move task to `in-progress` via `KanbanToolset.kanban_move()`
2. Build prompt from task body + AC (read via `kanban-md show <id> --json`)
3. Look up target agent via `AgentRegistry.get("builder")`
4. Call `await agent.run(prompt, deps=deps)` — PydanticAI handles the turn loop
5. On success: move task to `review`, update `RunningTask.last_activity`
6. On failure: schedule retry with backoff, or block task after max retries

**Integration with existing code:**

- `AgentRegistry` already resolves agents by name with role policies
- `DelegationToolset` already handles agent→agent dispatch (for orchestrator→builder)
- `OwlBearDeps` carries `hooks`, `tracker`, `agent_registry`
- `KanbanToolset._run_kanban()` provides the board I/O

### 3.7 Reconciliation (from Symphony §8.5)

Each tick, before dispatching new work:

| Check | Action |
|-------|--------|
| Task moved externally to `done`/`review` | Cancel asyncio.Task, remove from running |
| Task blocked externally | Cancel asyncio.Task, remove from running |
| `elapsed > stall_timeout` | Cancel asyncio.Task, schedule retry |
| asyncio.Task completed (success) | Move task to `review`, remove from running |
| asyncio.Task completed (exception) | Schedule retry with backoff |

### 3.8 Testing Strategy

| Test | Approach | Mock |
|------|----------|------|
| Poll loop timing | `asyncio.Event` + fake clock (`trio.testing` style) | `asyncio.sleep` |
| Candidate fetch | Inject canned `kanban-md list` output | `KanbanToolset._run_kanban` |
| Dispatch and claim | Verify task moves to in-progress, asyncio.Task created | `AgentRegistry.get` → `FunctionModel` |
| Reconciliation | Inject changed board state between ticks | `KanbanToolset` |
| Stall detection | Set `stall_timeout=0.1`, verify task cancelled | Real asyncio |
| Retry backoff | Verify delay formula: `min(10 * 2^(attempt-1), max_backoff)` | Unit test |
| Shutdown during poll | Set shutdown_event mid-tick, verify clean exit | `asyncio.Event` |
| autonomous_mode=False | Verify poll loop is a no-op | Config |

Key: tests never shell out to real `kanban-md`. Mock `_run_kanban` at the toolset level.

## 4. Recommendation (.85 confidence)

Implement a **dual-coroutine architecture**: the existing channel loop runs alongside a new poll loop in an `asyncio.TaskGroup`. The poll loop follows Symphony's tick sequence (reconcile→fetch→sort→dispatch) adapted for OwlBear's single-workspace, kanban-md-based, PydanticAI-agent stack.

**Scope for #614:** Core poll-dispatch-reconcile loop with configurable interval, concurrency, and stall detection. No workspace isolation (YAGNI — single repo). No retry persistence across restarts (YAGNI — in-memory state is sufficient per Symphony §14.3).

**Risks:**

1. **kanban-md CLI overhead** — shelling out each tick. Acceptable: `kanban-md list` completes in <100ms.
2. **Shared workspace** — concurrent agents editing same files. Mitigation: `max_concurrent_tasks=3` default + approval gates on destructive ops.
3. **Token budget** — multiple concurrent agent runs consume Copilot quota. Mitigation: configurable concurrency cap.

**What NOT to build (YAGNI):**

- Workspace isolation (single repo)
- HTTP dashboard / REST API
- Dynamic config reload (use restart)
- Per-state concurrency limits
- Retry persistence across restarts

## 5. Refined AC for Implementation

```
- [ ] `autonomous_mode` config field (bool, default False) gates the poll loop
- [ ] `poll_interval` config field (float, default 30.0s)
- [ ] `max_concurrent_tasks` config field (int, default 3)
- [ ] `stall_timeout` config field (float, default 300.0s)
- [ ] `max_task_retries` config field (int, default 5)
- [ ] `max_retry_backoff` config field (float, default 300.0s)
- [ ] Poll loop runs as concurrent coroutine alongside channel loop
- [ ] Each tick: reconcile → fetch todo → sort by priority → dispatch
- [ ] Dispatched tasks moved to in-progress via kanban-md
- [ ] Completed tasks moved to review via kanban-md
- [ ] Stall detection cancels tasks exceeding stall_timeout
- [ ] Retry with exponential backoff: min(10 * 2^(attempt-1), max_backoff)
- [ ] Tasks blocked after max_task_retries exceeded
- [ ] autonomous_mode=False disables poll loop entirely
- [ ] Tests cover: poll timing, dispatch, reconciliation, stall, retry, shutdown
```

## 6. Follow-up Tasks

See Section 5 for refined AC — the implementation task is #614 itself. Dependent tasks already exist:

- #615 — WIP continuity store (enhances dispatch with resume context)
- #623 — Stale execution detector (integrates into reconcile phase)
