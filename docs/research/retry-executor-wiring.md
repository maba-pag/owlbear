# Retry Executor Wiring for HookReactionRouter

> **Owning task:** #985 — Wire real retry executor into HookReactionRouter
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #984 extracted `schedule_task_retry()` as a standalone idempotent function
in `daemon.py`. Task #985 must create `make_retry_executor()` and wire it into
the `HookReactionRouter` executors dict so the noop retry placeholder becomes a
real executor at daemon startup. The core challenges are: (a) exposing the
executors dict created inside `build_hooks()` so `run_daemon()` can mutate it,
(b) detecting budget-exceeded events in the retry executor, and (c) preventing
double-retries when both `reconcile_tasks` and the hook reaction fire.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Celery task retry docs | .90 | `self.retry()` reuses task-owned counters; retry state is centralized [S1] |
| S2 | Temporal failure detection docs | .85 | RetryPolicy is scheduler-owned; non-retryable errors bypass it [S2] |
| S3 | Prefect automations docs | .80 | Event-driven actions delegate to existing executors via payload matching [S3] |
| S4 | OwlBear `daemon.py` schedule_task_retry | 1.0 | Existing idempotent retry engine (post-#984) [S4] |
| S5 | OwlBear `hook_reaction_router.py` | 1.0 | Router captures `_executors` dict by reference in closures [S5] |
| S6 | OwlBear `bootstrap/hooks.py` build_hooks | 1.0 | Creates local executors dict with noops; not exposed [S6] |
| S7 | OwlBear `bootstrap/_types.py` BootstrapResult | 1.0 | No field for executors or router; CLI passes fields individually [S7] |
| S8 | OwlBear `bearclaw/commands/daemon.py` | 1.0 | CLI calls run_daemon with individual BootstrapResult fields [S8] |

- [S1] <https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying>
- [S2] <https://docs.temporal.io/develop/python/failure-detection>
- [S3] <https://docs.prefect.io/v3/automate/events/automations-triggers>

## 3. Analysis

### 3.1 Exposing the executors dict

The executors dict is created locally in `build_hooks()` and passed to
`HookReactionRouter`. Handler closures capture it by reference — mutating the
dict after construction updates all handler lookups at call time [S5]. The
question is how to get the dict reference from `build_hooks()` to `run_daemon()`.

| Option | Description | Files changed | KISS |
|--------|-------------|:-------------:|:----:|
| A. 3-tuple return (.70) | `build_hooks()` returns `(hooks, reporter, executors)` | build_hooks, bootstrap, #955 tests | Low |
| B. BootstrapResult field (.75) | New `reaction_executors` on BootstrapResult + new run_daemon param | BootstrapResult, bootstrap, run_daemon, CLI | Med |
| C. HookRegistry attribute (.85) | Store executors as `hooks.reaction_executors` | build_hooks (1 line), run_daemon reads via agent.hooks | High |
| D. Router update_executor (.65) | Store router on BootstrapResult, add update method | Router, BootstrapResult, bootstrap, run_daemon, CLI | Low |

**Option C** wins on KISS: `run_daemon()` already accesses `agent.hooks`. One
line in `build_hooks()` (`hooks.reaction_executors = executors`), one line in
`HookRegistry.__init__` (`self.reaction_executors = None`), and `run_daemon()`
reads it directly. No signature changes, no new parameters, no BootstrapResult
changes. [S5, S6, S7, S8]

**Option B** is the cleaner alternative if Option C's coupling is rejected.

### 3.2 Budget-exceeded detection

Currently `reconcile_tasks` emits `outcome: "failure"` for ALL failures
including `BudgetExceededError` [S4, S6]. The budget check lives inside
`schedule_task_retry` via `isinstance(error, BudgetExceededError)`. The hook
fires BEFORE `schedule_task_retry`, so the retry executor receives only the
data dict with no exception object.

| Approach | Description | Verdict |
|----------|-------------|---------|
| Emit `outcome: "budget_exceeded"` | Change reconcile_tasks to distinguish budget-exceeded | **Best** (.85) |
| Add `error_type` field to emit | `{"task_id": tid, "outcome": "failure", "error_type": "BudgetExceededError"}` | Viable (.75) |
| Executor checks post-facto | Read state.retries after schedule_task_retry runs | Broken (hook fires before) |

Emitting `outcome: "budget_exceeded"` is cleanest because: (a) existing
consumers that check `outcome != "success"` still skip it correctly [S4],
(b) `HookReactionRule.match` predicates on `outcome: failure` naturally exclude
it [S3, S5], (c) the retry executor needs no special logic. This requires a
small change to `reconcile_tasks` (same file as `make_retry_executor`). [S1, S2]

### 3.3 Deduplication

Both `reconcile_tasks` and the hook reaction retry executor call
`schedule_task_retry`. The function is idempotent: if `state.retries[tid]`
already has an entry at the same or higher attempt, the second call is a no-op.
No double-retry, no counter drift. [S1, S4]

### 3.4 make_retry_executor design

```
make_retry_executor(state, kanban, *, max_attempts, backoff_base, backoff_max)
  -> async executor(data: dict) -> None:
       1. if not data.get("task_id"): log warning, return
       2. if data.get("outcome") == "budget_exceeded": return
       3. error = RuntimeError(data.get("error", "hook-reaction retry"))
       4. await schedule_task_retry(state, kanban, task_id, error, ...)
```

The factory lives in `daemon.py` alongside `schedule_task_retry`. The returned
closure captures `state`, `kanban`, and retry config. [S4]

## 4. Recommendation (.85 confidence)

Use **Option C** (HookRegistry attribute) + budget-exceeded outcome emission.

1. Add `self.reaction_executors: dict | None = None` to `HookRegistry.__init__`
2. In `build_hooks()`: store `hooks.reaction_executors = executors` after
   creating the HookReactionRouter
3. Create `make_retry_executor(state, kanban, *, max_attempts, backoff_base,
   backoff_max)` in `daemon.py`
4. In `run_daemon()` autonomous block: replace
   `agent.hooks.reaction_executors["retry"]` with the real executor
5. Change `reconcile_tasks` to emit `outcome: "budget_exceeded"` for
   BudgetExceededError (before calling `schedule_task_retry`)
6. The retry executor checks `task_id` presence and `budget_exceeded` outcome

**Risk:** Coupling HookRegistry to the reaction executors concept.
**Mitigation:** The attribute is optional (`None` by default) and only used by
the daemon wiring path. If this coupling is rejected, fall back to Option B.

## 5. Follow-up Tasks

See kanban commands below (executed at ideation).
