---
id: 88
title: Write tests for SlackChannel adapter
status: done
priority: high
created: 2026-02-27T01:45:13.9028582+01:00
updated: 2026-02-27T02:32:05.4378041+01:00
started: 2026-02-27T02:14:21.3940967+01:00
completed: 2026-02-27T02:32:05.4378041+01:00
tags:
    - phase-4
    - comms
    - slack
    - test
depends_on:
    - 87
class: standard
---

TDD tests for SlackChannel. See docs/slack-integration-research.md.

AC:
- Protocol compliance: isinstance(SlackChannel, ChannelPlugin)
- send() calls chat_postMessage with correct channel and text (mocked)
- receive() yields text from message.im event payload (mocked)
- Disconnect handling: clean shutdown
- All tests use AsyncMock, no real Slack connection
