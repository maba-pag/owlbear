---
id: 623
title: Stale execution detector for daemon loop
status: archived
priority: important
created: 2026-03-07T05:21:07.8260541+01:00
updated: 2026-03-09T16:15:43.2489241+01:00
started: 2026-03-07T07:09:19.1993327+01:00
completed: 2026-03-09T16:15:43.2489241+01:00
tags:
    - scope:core
    - agent
depends_on:
    - 614
class: standard
---

Periodic scan of in-progress tasks. If no agent activity for stale_timeout, cancel task, block on kanban, and alert user. See docs/stale-execution-detector-research.md for full analysis.

AC:
- [ ] `stale_task_timeout` config field (float, default 300.0) in `OwlBearSettings` with `@field_validator` ensuring > 0  follows `poll_interval` pattern
- [ ] `detect_stale_tasks()` async function in daemon.py with signature: `async def detect_stale_tasks(*, state: OrchestratorState, kanban: KanbanToolset, channel: ChannelPlugin, stale_timeout: float) -> None`
- [ ] Scans `state.running` for tasks where `datetime.now(UTC) - rt.started_at > timedelta(seconds=stale_timeout)`
- [ ] Per stale task, in order: (1) `rt.asyncio_task.cancel()`, (2) remove from `state.running` and `state.claimed`, (3) `kanban.kanban_edit(task_id, block=f'Stale: no progress for {stale_timeout}s, auto-cancelled')`, (4) `channel.send(...)` alert  log and continue on (3)/(4) failure so remaining stale tasks are still processed
- [ ] `detect_stale_tasks()` called in `poll_tick` after `reconcile_tasks()` and before fetch/dispatch
- [ ] `poll_tick` gains keyword-only `channel: ChannelPlugin` and `stale_timeout: float` parameters
- [ ] `poll_loop` gains keyword-only `channel: ChannelPlugin` parameter (threaded from `run_daemon`)
- [ ] `run_daemon` passes `channel` to `poll_loop`
- [ ] Tests: mock `datetime.now(UTC)` to verify stale detection triggers at exact threshold boundary (not before, yes at)
- [ ] Tests: verify cancel called, state cleaned, kanban_edit(block=...) called with reason string, channel.send called with alert
- [ ] Tests: verify kanban_edit failure on one stale task does not prevent processing of remaining stale tasks

[[2026-03-09]] Mon 16:15
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| stale_task_timeout config field (float, default 300.0) with @field_validator > 0 | config.py L224-231: Field(default=300.0), L307-313: @field_validator rejects <=0 | PASS |
| detect_stale_tasks() async function in daemon.py with correct signature | daemon.py L564-570: exact signature match | PASS |
| Scans state.running for datetime.now(UTC) - rt.started_at >= stale_timeout | daemon.py L580-584: list comprehension with >= check | PASS |
| Per stale task: (1) cancel, (2) remove running+claimed, (3) kanban_edit(block=...), (4) channel.send; log+continue on 3/4 failure | daemon.py L585-601: exact order, try/except on steps 3 and 4 with logger.warning | PASS |
| detect_stale_tasks() called in poll_tick after reconcile_tasks() before fetch/dispatch | daemon.py L633-641: comment '# 2. Detect and cancel stale tasks' after '# 1. Reconcile' | PASS |
| poll_tick gains keyword-only channel: ChannelPlugin and stale_timeout: float | daemon.py L610-611: both keyword-only params present | PASS |
| poll_loop gains keyword-only channel: ChannelPlugin parameter | daemon.py L729: channel param present | PASS |
| run_daemon passes channel to poll_loop | daemon.py L887: channel=channel in poll_loop call | PASS |
| Tests: mock datetime.now(UTC) boundary detection (not before 299s, yes at 300s) | test_poll_dispatch.py: test_stale_task_cancelled_at_exact_boundary + test_not_stale_just_before_boundary | PASS |
| Tests: cancel, state cleaned, kanban_edit(block=...), channel.send | test_poll_dispatch.py: test_cancel_and_state_cleaned â€” all 4 asserted | PASS |
| Tests: kanban_edit failure does not block remaining stale tasks | test_poll_dispatch.py: test_kanban_edit_failure_does_not_block_remaining + test_channel_send_failure_does_not_block_remaining | PASS |

### Test Results
- pytest (scoped): 10 passed, 0 failed (StaleTaskTimeoutConfig: 4, DetectStaleTasks: 6)
- pytest (full): 1271 passed, 1 failed (unrelated slack_sdk), 20 skipped
- ruff: 3 pre-existing errors unrelated to #623

### Confidence: .97
### Action: archive
