# Task-Level Retry with Exponential Backoff

> **Owning task:** #625 — Task-level retry with exponential backoff
> **Date:** 2026-03-07  **Status:** Complete

## 1. Context and Question

When an autonomous agent dispatch fails (exception from `builder.run()`), `reconcile_tasks()` currently logs the error, saves a WIP summary, emits a TASK_COMPLETE/failure hook, and discards the task — permanently. There is no mechanism to schedule a retry. Should we add task-level retry with exponential backoff, and how should it integrate with the existing retry layers?

**Key distinction:** This is *task-level* retry (re-dispatch an entire agent run across poll cycles) — NOT message-level retry (#512, which deduplicates retries within a single `agent.turn()` call). The two are complementary, not overlapping.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| OpenAI Symphony SPEC.md | `docs/research/symphony.md` S3.2 (captured from GitHub) | .95 |
| AWS Builders' Library — Timeouts, retries, and backoff with jitter | <https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/> | .95 |
| Celery task retry (autoretry_for, retry_backoff) | <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying> | .85 |
| OwlBear daemon-retry-reconciliation.md | `docs/research/daemon-retry-reconciliation.md` (#512) | .90 |
| OwlBear orchestration-agent-frameworks.md | `docs/research/orchestration-agent-frameworks.md` S3.2 | .85 |
| OwlBear poll-dispatch-reconcile.md | `docs/research/poll-dispatch-reconcile.md` (#614) | .90 |

## 3. Analysis

### 3.1 Retry Layer Boundaries

| Layer | Scope | Owner | Location |
|-------|-------|-------|----------|
| L1: HTTP transport | Single HTTP request to Copilot | httpx retry transport | `providers/copilot.py` |
| L2: Tool-level | Single tool invocation | HookedToolset/tenacity | `tools/hooked.py` |
| L3: Message-level | Single `agent.turn()` call | daemon `_recover_from_error` | `daemon.py` (channel_loop) |
| **L4: Task-level (NEW)** | **Entire agent dispatch cycle** | **reconcile_tasks + RetryState** | **`daemon.py` (poll_loop)** |

L1–L3 handle transient HTTP/tool/turn errors within a single cycle. L4 handles the case where the entire agent run fails after L1–L3 are exhausted — e.g., persistent API outage, bad task decomposition, or agent crash. These layers do not compound because L4 re-dispatches a fresh `builder.run()` in a new poll cycle, not an inner retry of the same call.

### 3.2 Prior Art Comparison

| Criterion | Symphony | Celery | AWS Best Practice |
|-----------|----------|--------|-------------------|
| Backoff formula | `min(10s * 2^(n-1), max)` | `base * 2^n`, cap at `retry_backoff_max` (600s) | Capped exponential + full jitter |
| Max retries | Configurable per task | `max_retries=3` default, `None` = forever | "Limit retries, handle failure earlier" |
| Jitter | Not specified | `retry_jitter=True` (random 0..delay) | Full jitter strongly recommended |
| On exhaustion | Block task | Raise `MaxRetriesExceededError` | Fail fast, escalate |
| Continuation | 1s retry after success if task still active | N/A | N/A |
| State storage | In-memory (process lifetime) | Broker message (persistent) | N/A |

### 3.3 Design Trade-offs

| Criterion | In-memory dict | Persistent file/DB |
|-----------|---------------|-------------------|
| Complexity | Low — single dict on OrchestratorState | Medium — JSONL or SQLite |
| Survives restart | No | Yes |
| KISS/YAGNI | Aligned — daemon is long-running | Over-engineering for current scale |
| Matches #614 pattern | Yes — OrchestratorState is in-memory | Diverges from existing pattern |

**Decision (.90):** In-memory `dict[str, RetryEntry]` on `OrchestratorState`. Matches YAGNI — if the daemon restarts, retry state resets and tasks resume from their kanban status (still `in-progress`). The daemon already has no persistent state (per #614 research S4).

### 3.4 Jitter Strategy

AWS strongly recommends jitter for distributed retry. However, OwlBear's poll loop runs on a single process — no thundering herd risk from task retries. Still, jitter prevents retry pile-ups when multiple tasks fail simultaneously. Use **full jitter**: `delay = random(0, min(base * 2^(n-1), max))`.

## 4. Recommendation (.90 confidence)

### RetryEntry model

Add a `RetryEntry` dataclass to `daemon.py` alongside `RunningTask`:

```python
@dataclass
class RetryEntry:
    task_id: str
    attempt: int  # 1-indexed, starts at 1 on first failure
    next_due: datetime  # UTC timestamp when retry becomes eligible
    last_error: str  # truncated exception string
```

### OrchestratorState extension

Add `retries: dict[str, RetryEntry]` to `OrchestratorState` (default empty dict).

### Config fields

Add to `OwlBearSettings`:

- `task_retry_max: int = 5` — max retry attempts before auto-blocking
- `task_retry_backoff_base: float = 10.0` — base delay in seconds
- `task_retry_backoff_max: float = 300.0` — cap at 5 minutes (Celery caps at 600s; 5min is enough for OwlBear's scale)

### Integration points

1. **`reconcile_tasks()`**: On failure, instead of discarding, create/update `RetryEntry` in `state.retries`. If `attempt >= task_retry_max`, block the task via `kanban.kanban_edit(tid, blocked="Auto-blocked: {max} retries exhausted — {error}")` and remove from retries.

2. **`poll_tick()`**: After reconcile, before dispatching new tasks, check `state.retries` for entries where `datetime.now(UTC) >= next_due`. Re-dispatch those tasks (they're still `in-progress` on the board). Count retry dispatches against `max_concurrent` slots.

3. **Backoff formula**: `delay = random(0, min(base * 2^(attempt-1), max))` — full jitter per AWS recommendation. Each retry increments `attempt`.

4. **Continuation retry**: After success in `reconcile_tasks()`, if the builder agent's output indicates the task needs more work (still active / not fully complete), schedule a 1s continuation before moving to review. This is Symphony's "continuation turn" pattern. **Defer to a follow-up task** — it requires output parsing that doesn't exist yet.

### What NOT to build

- **Persistent retry state** — YAGNI. In-memory is sufficient.
- **Per-task retry config** — All tasks use global settings. Per-task overrides are YAGNI.
- **Error-type-aware retry** — L4 retries all failures. L1–L3 already handle transient vs permanent within a cycle. If L1–L3 exhausted retries and the agent still failed, L4 retries the whole dispatch regardless of error type.
- **Continuation retry** — Needs output parsing; separate task.

## 5. Follow-up Tasks

```sh
kanban\kanban-md.exe create "Implement RetryEntry model and OrchestratorState.retries" --priority needed --status todo --tags "scope:core,agent" --body "Add RetryEntry dataclass and retries dict to OrchestratorState in daemon.py. Add task_retry_max (int, default 5), task_retry_backoff_base (float, default 10.0), task_retry_backoff_max (float, default 300.0) config fields to OwlBearSettings.\n\nSee docs/research/task-level-retry.md S4\n\nAC:\n- [ ] RetryEntry dataclass: task_id (str), attempt (int), next_due (datetime), last_error (str)\n- [ ] OrchestratorState gains retries: dict[str, RetryEntry] field (default empty)\n- [ ] task_retry_max, task_retry_backoff_base, task_retry_backoff_max in OwlBearSettings with validators\n- [ ] Unit tests for RetryEntry creation and config validation\n- [ ] ruff clean"
```

```sh
kanban\kanban-md.exe create "Wire retry scheduling into reconcile_tasks" --priority needed --status todo --tags "scope:core,agent" --depends-on 625 --body "Modify reconcile_tasks() to schedule retries on failure instead of discarding tasks. On failure: compute next_due with full jitter backoff, add/update RetryEntry in state.retries. When attempt >= task_retry_max, auto-block the task via kanban_edit and remove from retries.\n\nSee docs/research/task-level-retry.md S4\n\nAC:\n- [ ] On task failure, RetryEntry created with attempt=existing+1, next_due=now+delay, last_error=str(exc)[:500]\n- [ ] Backoff: delay = random(0, min(base * 2^(attempt-1), max)) — full jitter\n- [ ] When attempt >= task_retry_max, task blocked via kanban_edit with error summary\n- [ ] Task remains in-progress on kanban during retry window\n- [ ] Unit tests: retry scheduling, backoff formula, exhaustion auto-block\n- [ ] ruff clean"
```

```sh
kanban\kanban-md.exe create "Wire retry dispatch into poll_tick" --priority needed --status todo --tags "scope:core,agent" --depends-on 625 --body "Modify poll_tick() to check state.retries for due entries and re-dispatch them before picking new todo tasks. Retry dispatches count against max_concurrent slots.\n\nSee docs/research/task-level-retry.md S4\n\nAC:\n- [ ] poll_tick checks state.retries for entries where now >= next_due\n- [ ] Due retries re-dispatched via same builder.run() path as new tasks\n- [ ] Retry dispatch injects WIP context from wip_store (Quoroom pattern)\n- [ ] Retry dispatches count against available slots (max_concurrent - running)\n- [ ] On re-dispatch, RetryEntry removed from state.retries, task added to state.running\n- [ ] Unit tests: retry dispatch timing, slot accounting, WIP injection\n- [ ] ruff clean"
```

```sh
kanban\kanban-md.exe create "Research continuation retry after successful task completion" --priority nice-to-have --status ideation --tags "research,scope:core,agent" --body "Symphony uses continuation turns: after an agent completes a task successfully, a 1s follow-up checks if the task needs more work. Research how to detect 'task still active' from builder agent output and whether a continuation dispatch is worthwhile.\n\nSee docs/research/task-level-retry.md S4\n\nAC:\n- [ ] Research checklist completed\n- [ ] Decision on whether to adopt continuation turns\n- [ ] Follow-up kanban tasks if adopted"
```

## 6. Dependency Status

- **#614 (poll-dispatch-reconcile):** Done. All infrastructure (`OrchestratorState`, `RunningTask`, `reconcile_tasks`, `poll_tick`, `poll_loop`) is in place.
- **#512 (reconcile daemon retry with tool-level):** Backlog. This is *message-level* dedup (L3 vs L2), not task-level (L4). #625 does not depend on #512 being resolved — the layers are independent. However, #512 should be resolved before #625 implementation to avoid the current L3 transient retry still being active when L4 re-dispatches (multiplicative risk at L3×L4). **Recommendation:** Implement #512 first (remove L3 transient retry), then implement #625 (add L4 task retry). Update `depends_on` accordingly.
