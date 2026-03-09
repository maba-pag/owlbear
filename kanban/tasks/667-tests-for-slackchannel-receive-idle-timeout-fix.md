---
id: 667
title: Tests for SlackChannel.receive() idle timeout fix (#513)
status: done
priority: important
created: 2026-03-08T02:11:34.2390236+01:00
updated: 2026-03-08T02:36:02.9117006+01:00
started: 2026-03-08T02:36:02.9117006+01:00
completed: 2026-03-08T02:36:02.9117006+01:00
tags:
    - test
    - resilience
    - channels
class: standard
---

Test companion for #513. Verify SlackChannel.receive() loops on idle timeout instead of returning None.

depends_on: [513]

## Acceptance Criteria

- [ ] Test: SlackChannel.receive() does NOT return None on timeout -- loops and waits for next message
- [ ] Test: SlackChannel.receive() returns None when disconnect sentinel is queued
- [ ] Test: SlackChannel.receive() returns actual message after multiple idle timeouts (message arrives after 2+ timeout cycles)
- [ ] Test: CLIChannel.receive() still returns None on EOF (no regression)
- [ ] Tests in tests/test_slack_channel.py or tests/test_channels.py
- [ ] ruff clean, all tests pass
