---
id: 297
title: Slack rich messaging — images, proposals, status updates
status: archived
priority: needed
created: 2026-03-01T02:52:55.1536106+01:00
updated: 2026-03-01T17:09:23.2349966+01:00
started: 2026-03-01T09:56:40.4827703+01:00
completed: 2026-03-01T17:09:23.2349966+01:00
tags:
    - phase-12
    - slack
    - channels
class: standard
---

## Context
SlackChannel currently only sends plain text. For a real project management flow, OwlBear needs to send screenshots, structured proposals (with options), progress updates with formatting, and file attachments.

## Acceptance Criteria
- [ ] SlackChannel.send_image(path_or_bytes, caption) — upload screenshot/diagram
- [ ] SlackChannel.send_blocks(blocks) — send Slack Block Kit structured messages
- [ ] Proposal format: title, description, numbered options, request for feedback
- [ ] Status update format: task progress, current step, blockers, ETA
- [ ] send() auto-detects if message contains markdown and converts to Slack mrkdwn
- [ ] ChannelPlugin protocol extended with optional send_image() and send_blocks()
- [ ] Unit tests with mocked Slack API
- [ ] Backward compatible — CLI channel ignores rich features gracefully
