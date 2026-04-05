---
id: 336
title: Implement ProgressReporter — hook-based accumulator with background timer
status: archived
priority: needed
created: 2026-03-01T11:18:01.690447+01:00
updated: 2026-03-01T17:10:06.3774918+01:00
started: 2026-03-01T11:21:37.2196699+01:00
completed: 2026-03-01T17:10:06.3774918+01:00
tags:
    - phase-12
    - daemon
    - channels
depends_on:
    - 335
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/core/progress.py with ProgressReporter class
- [ ] Constructor: channel (ChannelPlugin), interval (float), detail (brief|detailed)
- [ ] on_tool_complete(data) callback: increments _tool_count, records _last_tool, _last_args
- [ ] start() spawns asyncio.Task that wakes every interval seconds
- [ ] Timer sends update via channel.send() only if _tool_count changed since last send (activity gate)
- [ ] stop() cancels the background task, swallows CancelledError
- [ ] Brief format: 'Working on task... (N tools called, last: {tool}, {elapsed}s elapsed)'
- [ ] Detailed format: 'Progress: N tools in {elapsed}s | Last: {tool} (args: ...) | Agent: {name}'
- [ ] register(hooks) method: hooks POST_TOOL_USE -> on_tool_complete
- [ ] channel.send() wrapped in try/except — errors logged, never interrupt agent
- [ ] State reset on each start() call (for next turn)

See docs/research/progress-reporting.md S4
