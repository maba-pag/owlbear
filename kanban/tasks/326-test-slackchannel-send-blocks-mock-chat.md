---
id: 326
title: Test SlackChannel.send_blocks — mock chat_postMessage with blocks
status: archived
priority: needed
created: 2026-03-01T11:16:03.834167+01:00
updated: 2026-03-01T17:09:58.7492992+01:00
started: 2026-03-01T11:20:56.7458315+01:00
completed: 2026-03-01T17:09:58.7492992+01:00
tags:
    - phase-12
    - slack
    - channels
    - test
class: standard
---

## Acceptance Criteria
- [ ] Test send_blocks() calls chat_postMessage with blocks= param and text= fallback
- [ ] Test blocks are passed as list[dict] matching Block Kit structure
- [ ] Test optional thread_ts param is forwarded to chat_postMessage
- [ ] Test send_blocks with empty blocks list raises ValueError
- [ ] Mock AsyncWebClient to verify exact API call params

See docs/slack-rich-messaging-research.md S3.1, S3.3
