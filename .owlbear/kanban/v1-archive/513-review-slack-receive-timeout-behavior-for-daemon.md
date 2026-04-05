---
id: 513
title: Review Slack receive timeout behavior for daemon idle
status: archived
priority: important
created: 2026-03-04T07:38:24.611626+01:00
updated: 2026-03-09T21:58:13.2744049+01:00
started: 2026-03-06T23:49:40.0830939+01:00
completed: 2026-03-09T21:58:13.2744049+01:00
tags:
    - audit
    - resilience
    - channels
class: standard
---

T-5 from docs/resilience-audit.md: SlackChannel.receive() returns None on 30s timeout. Daemon interprets None as shutdown signal (correct for CLI, wrong for Slack). Causes premature daemon exit on Slack idle periods.

See docs/research/slack-receive-timeout.md for full analysis.

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

[[2026-03-09]] Mon 21:58
## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| SlackChannel.receive() wraps asyncio.wait_for in while True loop | slack.py L232-239: `while True:` wrapping `asyncio.wait_for` | PASS |
| On TimeoutError: continue, do NOT return None | slack.py L238-239: `except TimeoutError: continue` | PASS |
| On successful dequeue: return value (incl None sentinel) | slack.py L234-236: `return await asyncio.wait_for(...)` returns any value including None | PASS |
| Daemon stays alive during Slack idle periods | 3 dedicated tests in TestSlackReceiveIdleTimeout (L1272-1340): idle loop, disconnect sentinel, multi-cycle | PASS |
| CLIChannel.receive() unchanged | cli.py L42-53: still returns None on EOF, no changes | PASS |
| ChannelPlugin protocol docstring unchanged | base.py L28-35: `Returns None on EOF / disconnect`  no idle mention | PASS |
| ruff clean, all existing tests pass | ruff clean on channels code; 96 channel tests pass; 3 pre-existing ruff issues in unrelated files | PASS |

### Test Results

- pytest: 96 passed (test_channels.py + test_slack_channel.py)
- ruff: clean on src/owlbear/channels/ and related tests; 3 pre-existing issues in unrelated files (screenshot.py E501, test_bootstrap_structure.py I001 x2)

### Confidence: .97
### Action: archive
