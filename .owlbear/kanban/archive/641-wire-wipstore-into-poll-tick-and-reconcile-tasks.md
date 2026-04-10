---
id: 641
title: Wire WipStore into poll_tick and reconcile_tasks
status: archived
priority: needed
created: 2026-03-07T06:35:33.5430132+01:00
updated: 2026-03-07T18:08:31.0661396+01:00
started: 2026-03-07T16:51:53.1808262+01:00
completed: 2026-03-07T18:08:31.0661396+01:00
tags:
    - scope:core
    - agent
depends_on:
    - 639
class: standard
---

Integrate WipStore into the daemon poll-dispatch-reconcile loop.

AC:

- [ ] poll_tick accepts wip_store: WipStore parameter
- [ ] Before dispatching, load WIP: wip_store.load("builder", task_id)
- [ ] If WIP exists, prepend to prompt: CONTINUE_FORWARD_PREFIX + wip_summary + "\n\n" + original prompt
- [ ] If no WIP, prompt unchanged
- [ ] CONTINUE_FORWARD_PREFIX is a module-level constant string (Quoroom-inspired directive text)
- [ ] reconcile_tasks accepts wip_store: WipStore parameter
- [ ] On task success (no exception): wip_store.clear("builder", task_id) -- task done, no more cycles
- [ ] On task failure (any exception, no permanent-vs-transient distinction): wip_store.save("builder", task_id, summary) where summary = f"Failed: {type(exc).__name__}: {exc}" truncated to 500 chars
- [ ] poll_loop passes wip_store through to poll_tick
- [ ] run_daemon creates WipStore(config_dir) and passes to poll_loop
- [ ] _WIP_MAX_CHARS = 500 module-level constant for truncation limit
- [ ] All 6 tests from #639 pass (TestWipInjection: 2, TestWipReconciliation: 4)
- [ ] ruff check clean

Architecture notes:

- WIP save happens in reconcile_tasks when a task FAILS (so next cycle has context)
- WIP clear happens in reconcile_tasks when a task SUCCEEDS (moved to review, no more cycles)
- No classify_error in reconcile_tasks -- error classification is a concern of _handle_error (channel_loop), not reconcile_tasks (poll_loop). These are different abstraction layers. reconcile_tasks does not retry; it records outcomes.
- The auto-save extracts from asyncio_task.exception() -- formatted as "Failed: {type}: {msg}"
- Prompt format when WIP exists: CONTINUE_FORWARD_PREFIX + summary + "\n\n" + original prompt
- Patterns to follow: existing reconcile_tasks structure (pop from running, check exception, discard from claimed)
