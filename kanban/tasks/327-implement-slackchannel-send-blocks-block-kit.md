---
id: 327
title: Implement SlackChannel.send_blocks — Block Kit structured messages
status: archived
priority: needed
created: 2026-03-01T11:16:15.0710464+01:00
updated: 2026-03-01T17:09:59.4806523+01:00
started: 2026-03-01T11:21:27.6253332+01:00
completed: 2026-03-01T17:09:59.4806523+01:00
tags:
    - phase-12
    - slack
    - channels
depends_on:
    - 326
class: standard
---

## Acceptance Criteria
- [ ] Add send_blocks(blocks: list[dict], text_fallback: str, *, thread_ts: str | None = None) to SlackChannel
- [ ] Wraps chat_postMessage(channel=self._channel_id, blocks=blocks, text=text_fallback, thread_ts=thread_ts)
- [ ] Validates blocks is non-empty (raise ValueError if empty)
- [ ] text_fallback required — Slack uses it for notifications and accessibility
- [ ] Method is on SlackChannel only — ChannelPlugin protocol unchanged
- [ ] Callers use isinstance(channel, SlackChannel) or hasattr check

See docs/slack-rich-messaging-research.md S4
