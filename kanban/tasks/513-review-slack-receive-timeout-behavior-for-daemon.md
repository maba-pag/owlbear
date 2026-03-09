---
id: 513
title: Review Slack receive timeout behavior for daemon idle
status: done
priority: important
created: 2026-03-04T07:38:24.611626+01:00
updated: 2026-03-08T02:52:13.4091098+01:00
started: 2026-03-06T23:49:40.0830939+01:00
completed: 2026-03-08T02:52:13.4091098+01:00
tags:
    - audit
    - resilience
    - channels
class: standard
---

T-5 from docs/resilience-audit.md: SlackChannel.receive() returns None on 30s timeout. Daemon interprets None as shutdown signal (correct for CLI, wrong for Slack). Causes premature daemon exit on Slack idle periods.

See docs/slack-receive-timeout-research.md for full analysis.

## Architecture Decision

Approach A (recommended by research, .90 confidence): Loop inside SlackChannel.receive() on timeout. The fix is entirely within the Slack channel adapter -- no daemon or protocol changes needed.

- Change except TimeoutError in SlackChannel.receive() from 'return None' to 'continue' in a while True loop
- receive() only returns None when the disconnect sentinel (None on queue from disconnect()) is dequeued
- ChannelPlugin protocol contract unchanged: None still means EOF/disconnect
- CLI channel unaffected
- Known trade-off: up to 30s shutdown delay on SIGINT (acceptable for daemon; follow-up task can wire channel.disconnect() into signal handler)

## Acceptance Criteria

- [ ] SlackChannel.receive() wraps the asyncio.wait_for call in a while True loop
- [ ] On TimeoutError: continue (loop again), do NOT return None
- [ ] On successful dequeue: return the value (including None sentinel from disconnect())
- [ ] Daemon stays alive during Slack idle periods (no premature exit)
- [ ] CLIChannel.receive() unchanged (still returns None on EOF)
- [ ] ChannelPlugin protocol docstring unchanged (None = EOF/disconnect, not idle)
- [ ] ruff clean, all existing tests pass
