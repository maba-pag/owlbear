---
id: 332
title: Test mrkdwn-aware send — markdown to Slack mrkdwn conversion
status: archived
priority: needed
created: 2026-03-01T11:17:18.9673211+01:00
updated: 2026-03-01T17:10:02.6788251+01:00
started: 2026-03-01T11:20:58.8319472+01:00
completed: 2026-03-01T17:10:02.6788251+01:00
tags:
    - phase-12
    - slack
    - channels
    - test
class: standard
---

## Acceptance Criteria
- [ ] Test **bold** -> *bold* conversion
- [ ] Test *italic* -> _italic_ conversion (when not already bold)
- [ ] Test ~~strike~~ -> ~strike~ conversion
- [ ] Test [text](url) -> <url|text> link conversion
- [ ] Test code blocks and inline code pass through unchanged
- [ ] Test plain text without markdown passes through unchanged
- [ ] Test mixed formatting in a single message
- [ ] Tests are for the conversion function only (pure function, no API mock)

See docs/research/slack-rich-messaging.md S3.6
