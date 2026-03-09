---
id: 625
title: Task-level retry with exponential backoff
status: archived
priority: important
created: 2026-03-07T05:21:17.2220292+01:00
updated: 2026-03-09T16:14:54.1054782+01:00
started: 2026-03-07T13:58:57.0420683+01:00
completed: 2026-03-09T16:14:54.1054782+01:00
tags:
    - scope:core
    - agent
depends_on:
    - 614
    - 512
    - 679
class: standard
---

When an agent run fails on a kanban task in the poll-dispatch-reconcile loop, schedule retry with exponential backoff instead of immediately discarding. See docs/symphony-research.md S3.2.

Distinct from #512 (message-level retry within a single agent turn). This is task-level retry across agent dispatches in the autonomous loop.

AC:

- [ ] `RetryEntry` dataclass in `daemon.py` (alongside `RunningTask`): `task_id: str`, `attempt: int` (starts at 1), `next_due: datetime`, `last_error: str`
- [ ] `OrchestratorState` gains `retries: dict[str, RetryEntry]` field (default empty dict)
- [ ] `task_retry_max_attempts` config field (`int`, default `5`) in `OwlBearSettings` with `@field_validator` ensuring > 0 -- follows `max_concurrent_tasks` pattern
- [ ] `task_retry_backoff_base` config field (`float`, default `10.0`) in `OwlBearSettings` with `@field_validator` ensuring > 0 -- base delay in seconds
- [ ] `task_retry_backoff_max` config field (`float`, default `320.0`) in `OwlBearSettings` with `@field_validator` ensuring > 0 -- max delay cap in seconds
- [ ] Backoff formula: `delay = min(base * 2 ** (attempt - 1), max_backoff)` -- no jitter (jitter is for network-level calls; task-level retry intervals are coarse enough)
- [ ] `reconcile_tasks()` failure path changes: instead of discarding from `claimed`, create/update `RetryEntry` in `state.retries` with `next_due = now + timedelta(seconds=delay)`; keep task in `claimed` to prevent re-fetch from kanban; preserve existing WIP save behavior
- [ ] When `attempt > max_attempts`: remove from `state.retries` and `state.claimed`, call `kanban.kanban_edit(task_id, block=f"Retry exhausted ({max_attempts} attempts): {last_error}")` to auto-block the task on the kanban board
- [ ] `poll_tick()` gains retry dispatch step between reconcile and fetch-todo: scan `state.retries` for entries where `next_due <= datetime.now(UTC)`, re-dispatch each (task stays in-progress on kanban during retries), build prompt with WIP context (via `wip_store.load()`), spawn `asyncio.create_task` into `state.running`; remove entry from `state.retries` on re-dispatch
- [ ] `reconcile_tasks()` signature gains keyword-only `max_retry_attempts: int`, `backoff_base: float`, `backoff_max: float` params (threaded from settings via `poll_tick`)
- [ ] `poll_tick()` signature gains keyword-only `task_retry_max_attempts: int`, `task_retry_backoff_base: float`, `task_retry_backoff_max: float`, `agent_registry: AgentRegistry` (already present) params threaded from settings via `poll_loop`
- [ ] `poll_loop()` threads new config fields from `settings` to `poll_tick()`
- [ ] All existing `test_poll_dispatch.py` tests pass unchanged or with minimal signature updates
- [ ] ruff clean

Architecture notes:

- `RetryEntry` is a `@dataclasses.dataclass` following the `RunningTask` pattern in daemon.py
- Retry state is in-memory only (in `OrchestratorState`) -- no persistence (YAGNI, same rationale as OrchestratorState itself)
- Config fields follow existing `poll_interval`/`max_concurrent_tasks` pattern with `@field_validator`
- Task stays in-progress on kanban during retries (no status churn); only blocked on exhaustion
- WIP store already saves failure context -- retry dispatch loads it via existing `wip_store.load()` path
- Original AC #4 "continuation retry after success" removed: in current architecture `reconcile_tasks` always moves success to review; no scenario where success leaves task active. YAGNI -- add if needed later.

[[2026-03-09]] Mon 16:14
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| RetryEntry dataclass | daemon.py L106-113: correct fields | PASS |
| OrchestratorState.retries | daemon.py L121: dict[str, RetryEntry] | PASS |
| task_retry_max_attempts config | config.py L231 + validator L316 | PASS |
| task_retry_backoff_base config | config.py L235 + validator L325 | PASS |
| task_retry_backoff_max config | config.py L239 + validator L334 | PASS |
| Backoff formula | daemon.py L479: min(base*2^(a-1), max) | PASS |
| reconcile failure path | daemon.py L530-551: retry + keep claimed | PASS |
| Retry exhaustion | daemon.py L533-541: block + remove | PASS |
| poll_tick retry dispatch | daemon.py L649-672: scan+WIP+create_task | PASS |
| reconcile_tasks signature | daemon.py L493-495: kw-only retry params | PASS |
| poll_tick signature | daemon.py L612-615: kw-only retry params | PASS |
| poll_loop threads config | daemon.py L744-746: settings threaded | PASS |
| Existing tests pass | 82 passed, 0 failed in test_poll_dispatch | PASS |
| ruff clean | All checks passed on affected files | PASS |

### Test Results
- pytest (full): 1271 passed, 1 failed (pre-existing slack_sdk import), 20 skipped
- pytest (scoped): 82 passed in test_poll_dispatch.py
- ruff: clean on daemon.py, config.py, test_poll_dispatch.py

### Confidence: .97
### Action: archive
