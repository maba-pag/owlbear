# Hook Reaction Retry Delegation

> **Owning task:** #956 — Reuse daemon retry state for task-scoped HookReaction retries
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #955 introduced `HookReactionRouter` with noop executors for `retry`,
`notify`, and `escalate`. Task #956 asks how the `retry` executor should
delegate to the existing daemon retry mechanism (`reconcile_tasks`,
`OrchestratorState.retries`, `RetryEntry`, `_compute_retry_delay`) instead of
introducing new retry counters. The core challenges are: (a) extracting retry
scheduling from `reconcile_tasks` into a reusable function, (b) bridging a
timing gap — `build_hooks()` runs during bootstrap before `OrchestratorState`
exists, and (c) avoiding double-retries when both `reconcile_tasks` and the
hook reaction fire on the same failure.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Celery task retry docs | .90 | `self.retry()` reuses task-owned counters; signals can trigger retry through the same mechanism [S1] |
| S2 | Temporal Python failure detection docs | .85 | `RetryPolicy` is owned by the scheduler, not the activity; retry state lives at the orchestrator level [S2] |
| S3 | Prefect automations docs | .80 | Event-driven actions delegate to existing executors, not reimplementations [S3] |
| S4 | OwlBear `daemon.py` reconcile_tasks + RetryEntry | 1.0 | Existing retry engine: counter, backoff, exhaustion, budget bypass [S4] |
| S5 | OwlBear `hook_reaction_router.py` + `bootstrap/hooks.py` | 1.0 | Router injection of noop executors; mutable `self._executors` dict [S5] |
| S6 | OwlBear `config.py` HookReactionRule | 1.0 | Schema validation, allowed actions, scalar-only match [S6] |
| S7 | OwlBear `bootstrap/__init__.py` + `_types.py` | 1.0 | Bootstrap sequence, BootstrapResult fields, timing of hook assembly [S7] |

- [S1] <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying>
- [S2] <https://docs.temporal.io/develop/python/failure-detection>
- [S3] <https://docs.prefect.io/v3/automate/events/automations-triggers>

## 3. Analysis

### 3.1 Current retry flow

`reconcile_tasks()` at `daemon.py:509` does these steps for each failed task:

1. Emits `HookEvent.TASK_COMPLETE` with `{task_id, outcome: "failure"}`
2. Checks `BudgetExceededError` → blocks immediately (no retry)
3. Reads `state.retries[tid]` for the previous attempt count
4. If `next_attempt > max_retry_attempts` → blocks task, clears retry state
5. Otherwise → computes delay via `_compute_retry_delay()`, writes `RetryEntry`

The hook reaction router fires during step 1. If its `retry` executor also
schedules a retry, step 5 would overwrite it. This sequencing must be handled.

### 3.2 Timing gap

| Component | Created when | Needs state? |
|-----------|-------------|:------------:|
| `build_hooks()` | During `bootstrap()` | No — uses noops |
| `HookReactionRouter` | Inside `build_hooks()` | Holds mutable `_executors` dict |
| `OrchestratorState` | In `run_daemon()`, after bootstrap | Yes — owns `retries` dict |
| `poll_loop` | In `run_daemon()` via `TaskGroup` | Passes state + hooks together |

The router's `_executors` dict is captured by reference in handler closures
(`_make_handler`). Since Python dicts are mutable, replacing
`executors["retry"]` after construction updates all handler lookups at call
time. This is the simplest late-binding mechanism. [S5]

### 3.3 Design options

| Option | Description | Pros | Cons | Verdict |
|--------|-------------|------|------|---------|
| A. Extract function + mutable dict (.85) | Extract `schedule_task_retry()` from `reconcile_tasks`. Create `make_retry_executor()` factory in daemon.py. `build_hooks()` returns the executors dict alongside its existing return; `run_daemon()` replaces `executors["retry"]` with the real executor. | Minimal new code; leverages Python dict mutability; no new types; keeps retry logic in daemon.py where it belongs. [S1, S4, S5] | Changes `build_hooks()` return type (adds the dict); callers need updating. | **Best** |
| B. Late-binding slot class (.75) | Create a `RetryExecutorSlot` that starts as noop and gains a real impl via `slot.bind(...)`. | Explicit late-binding; self-documenting. | Extra class for a one-use pattern; over-engineering for Python when mutable dicts suffice. [S2] | Reject (YAGNI) |
| C. Move OrchestratorState to bootstrap (.70) | Create state in `bootstrap()` and pass it to both `build_hooks()` and `run_daemon()`. | Clean dependency flow. | Changes ownership boundary; state belongs to the daemon, not bootstrap. [S4, S7] | Reject |
| D. Router `update_executor()` method (.80) | Add `HookReactionRouter.update_executor(action, callable)` that updates `_executors`. | Clean API, no return-type change. | Requires accessing the router instance from `run_daemon()`, which currently can't reach it. [S5] | Viable alternative |

### 3.4 Deduplication strategy

Both `reconcile_tasks` and the hook reaction retry executor can fire on the
same task failure. Celery solves this by having one retry call site per task
(`self.retry()`). Temporal owns all retry state server-side. [S1, S2]

For OwlBear, `schedule_task_retry()` should be **idempotent**: if
`state.retries[tid]` already has an entry at the same or higher attempt, skip.
This means whichever fires first (hook reaction or `reconcile_tasks`) wins,
and the second call is a no-op. No double-retry, no counter drift. [S4]

### 3.5 Task-scope guard

The retry executor must validate that `data.get("task_id")` is present. For
non-task-scoped events, it logs a warning and returns. This matches the AC
requirement of "task-scoped failure reactions." Budget-exceeded payloads
(detectable via `data.get("outcome") == "budget_exceeded"` if emitted) should
also skip retry. [S3, S4]

## 4. Recommendation (.85 confidence)

Use **Option A**: extract + mutable dict.

1. Extract `schedule_task_retry(state, kanban, task_id, error, max_attempts, backoff_base, backoff_max)` from `reconcile_tasks()` as a standalone async function. Make it idempotent.
2. Refactor `reconcile_tasks()` to call `schedule_task_retry()`.
3. Create `make_retry_executor(state, kanban, max_attempts, backoff_base, backoff_max)` → returns `Executor`.
4. Have `build_hooks()` return the executors dict (third element in tuple).
5. `bootstrap()` stores it in `BootstrapResult.reaction_executors`.
6. `run_daemon()` replaces `executors["retry"]` with the real executor from step 3.

Risk: `build_hooks()` return type change requires test updates (~5 call sites).
Mitigation: return `None` when no hook_reactions configured.

Alternative (if return-type change is too disruptive): use **Option D** + store
the router in `BootstrapResult.reaction_router` and call
`router.update_executor("retry", real_executor)`.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Extract schedule_task_retry from reconcile_tasks" --priority needed --status ideation --tags "daemon,hooks,scope:core,type:build" --depends-on 955 --body "Extract schedule_task_retry(state, kanban, task_id, error, max_attempts, backoff_base, backoff_max) as a standalone idempotent async function from reconcile_tasks(). Refactor reconcile_tasks to call it. See docs/research/hook-reaction-retry-delegation.md section 4 step 1-2. AC: (1) schedule_task_retry exists as standalone function, (2) reconcile_tasks calls it instead of inline logic, (3) function is idempotent — calling twice for same task_id at same attempt is a no-op, (4) all existing reconcile_tasks tests pass unchanged, (5) new unit tests for schedule_task_retry cover: schedule, exhaustion-block, budget-bypass, idempotency."
```

```
kanban\kanban-md.exe create "Wire real retry executor into HookReactionRouter" --priority needed --status ideation --tags "daemon,hooks,bootstrap,scope:core,type:build" --depends-on 955 --body "Create make_retry_executor factory in daemon.py and wire it into the HookReactionRouter's executors dict via late-binding from run_daemon(). See docs/research/hook-reaction-retry-delegation.md section 4 steps 3-6. AC: (1) make_retry_executor(state, kanban, config) returns Executor, (2) build_hooks or BootstrapResult exposes the executors dict, (3) run_daemon replaces noop retry with real executor, (4) retry executor validates task_id presence and skips non-task-scoped events, (5) integration test: hook reaction with retry action schedules a RetryEntry in OrchestratorState, (6) edge case: budget-exceeded payload skips retry."
```
