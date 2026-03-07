# Stale Execution Detector for Daemon Loop

> **Owning task:** #623 — Stale execution detector for daemon loop
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

When OwlBear's autonomous poll-dispatch-reconcile loop (#614) dispatches agent tasks, those tasks can get stuck — an LLM may loop endlessly, a network call may hang, or the agent may deadlock on a tool. The question: **how should we detect and handle stale tasks?**

Two sub-questions:

1. What counts as "stale" — wall-clock timeout, lack of progress, or both?
2. What action to take — cancel, block on kanban, alert, or some combination?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | nWave `StaleExecutionDetector` | docs/nwave-research.md §3.3 P4 | .80 — exact pattern: scan IN_PROGRESS, configurable threshold |
| S2 | Quoroom Room stuck detection | docs/quoroom-room-research.md §3.4 | .75 — progress-based: tracks productive tool calls per cycle |
| S3 | Symphony reconciliation | docs/symphony-research.md §3.2 | .80 — per-tick reconcile detects stalls |
| S4 | Temporal heartbeat timeout | <https://docs.temporal.io/develop/go/failure-detection> | .70 — activity heartbeats + timeout; progress-aware |
| S5 | Celery task_time_limit | <https://docs.celeryq.dev/en/stable/userguide/configuration.html> | .65 — hard/soft dual timeout; SIGTERM then SIGKILL |

## 3. Analysis

### 3.1 Detection Strategy Comparison

| Criterion | Wall-clock timeout (S1, S3, S5) | Progress-based (S2, S4) | Hybrid |
|-----------|--------------------------------|------------------------|--------|
| Complexity | Low — compare `started_at` vs now | Medium — needs heartbeat/counter plumbing | Medium |
| False positives | Higher — slow-but-working tasks flagged | Lower — only flags truly idle tasks | Lowest |
| Integration effort | Trivial — `RunningTask.started_at` already exists | Needs hook into agent tool calls | Medium |
| KISS alignment | High | Medium | Lower |
| OwlBear fit | Good — sufficient for v1 | Good for v2 when agent instrumentation exists | Premature |

**Verdict:** Wall-clock timeout for v1 (KISS, YAGNI). Progress-based detection is a future enhancement when agent instrumentation is more mature — track as a separate follow-up task.

### 3.2 Action on Stale Detection

| Action | Pros | Cons | Source |
|--------|------|------|--------|
| Cancel asyncio.Task | Frees slot immediately | No explanation on board | S3, S5 |
| Block on kanban | Visible trail, human can review | Needs kanban-md CLI call | S1 |
| Alert via channel | Human awareness | No automated recovery | S1 |
| Cancel + Block + Alert | Full coverage | Most code, but each is ~5 LOC | All |

**Verdict:** Cancel + Block + Alert — all three actions are trivially cheap and orthogonal. Cancellation frees the slot, blocking leaves an audit trail, alerting notifies the user.

### 3.3 Where Detection Runs

| Option | Pros | Cons |
|--------|------|------|
| Inside `reconcile_tasks()` | Runs every tick already; natural location per S3 | Couples stale logic with completion logic |
| Separate `detect_stale_tasks()` called from `poll_tick` | Clean separation, testable in isolation | One more function call per tick |
| Separate coroutine on its own timer | Independent cadence | Over-engineering; YAGNI |

**Verdict:** Separate `detect_stale_tasks()` function called from `poll_tick` after `reconcile_tasks()`. This keeps concerns separated while staying inside the existing tick cadence (no new coroutine). Matches Symphony's reconcile-then-dispatch pattern (S3).

### 3.4 Configuration

| Setting | Default | Rationale |
|---------|---------|-----------|
| `stale_task_timeout` | 300.0 (5 min) | S1 uses 30min for human devs; agents are faster, 5min per task AC is reasonable |

A single float config field in `OwlBearSettings` is sufficient. No need for per-task-type thresholds yet (YAGNI). Celery's dual hard/soft timeout (S5) is over-engineering for v1 — the agent can't catch a soft signal anyway since it's running inside PydanticAI's `agent.run()`.

### 3.5 Cancellation Mechanics

`asyncio.Task.cancel()` raises `CancelledError` inside the task at the next `await` point. PydanticAI's `agent.run()` is async and will propagate the cancellation. After cancel, `asyncio.Task.done()` becomes True, so the next `reconcile_tasks()` call cleans it up normally.

Sequence per stale task:

1. `task.asyncio_task.cancel()` — request cancellation
2. `kanban.kanban_move(task_id, "in-progress")` is skipped (already there)
3. `kanban.kanban_edit(task_id, block="Stale: no progress for {threshold}s, auto-cancelled")` — mark blocked
4. `channel.send(f"⚠️ Task #{task_id} cancelled — stale after {threshold}s")` — alert user
5. Remove from `state.running` and `state.claimed` — free slot

## 4. Recommendation (.85 confidence)

Implement wall-clock timeout detection in a `detect_stale_tasks()` function called from `poll_tick`, with `stale_task_timeout` config (default 300s). On detection: cancel the asyncio.Task, block the kanban task with a reason, and alert via the active channel.

**Risk:** False positives on genuinely long tasks. Mitigation: 5min default is generous for per-task agent runs; config is tunable; blocked tasks are easily unblocked.

**Deferred to future:** Progress-based detection via agent heartbeats (Quoroom/Temporal pattern). This requires instrumenting tool calls with a `last_active_at` timestamp on `RunningTask`, which is a clean follow-up once we have basic detection working.

### Refined AC for #623

- [ ] `stale_task_timeout` config field (float, default 300.0) in `OwlBearSettings` — must be > 0
- [ ] `detect_stale_tasks()` async function in daemon.py — scans `state.running` for tasks where `now - started_at > stale_task_timeout`
- [ ] Stale tasks: cancel asyncio.Task, block kanban task with reason, alert via channel
- [ ] `detect_stale_tasks()` called in `poll_tick` after `reconcile_tasks()`
- [ ] Cancelled stale tasks removed from `state.running` and `state.claimed`
- [ ] `poll_tick` gains `channel` and `stale_timeout` parameters
- [ ] Tests: mock time to verify stale detection triggers at threshold
- [ ] Tests: verify cancellation, kanban blocking, and channel alert

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Progress-based stale detection via agent heartbeats" --priority nice-to-have --status ideation --tags "scope:core,agent" --body "Enhance stale detection with progress tracking. Add last_active_at to RunningTask, updated by POST_TOOL_USE hook. detect_stale_tasks() checks last_active_at instead of started_at when available. Pattern from Quoroom (docs/quoroom-room-research.md S3.4) and Temporal heartbeats.\n\nAC:\n- [ ] RunningTask gains last_active_at: datetime | None field\n- [ ] POST_TOOL_USE hook updates last_active_at on the matching RunningTask\n- [ ] detect_stale_tasks() prefers last_active_at over started_at when set\n- [ ] Tests cover heartbeat update and progress-aware stale detection" --depends-on 623
```
