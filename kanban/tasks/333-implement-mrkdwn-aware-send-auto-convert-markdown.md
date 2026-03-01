---
id: 333
title: Implement mrkdwn-aware send — auto-convert markdown in SlackChannel.send()
status: archived
priority: needed
created: 2026-03-01T11:17:30.9498023+01:00
updated: 2026-03-01T17:10:03.6080808+01:00
started: 2026-03-01T11:21:30.2110385+01:00
completed: 2026-03-01T17:10:03.6080808+01:00
tags:
    - phase-12
    - slack
    - channels
depends_on:
    - 332
class: standard
---

## Acceptance Criteria
- [ ] Add markdown_to_mrkdwn(text: str) -> str conversion function in src/owlbear/channels/slack_templates.py
- [ ] Conversions: **bold**->*bold*, *italic*->_italic_, ~~strike~~->~strike~, [text](url)-><url|text>
- [ ] Code blocks (triple backtick) and inline code pass through unchanged
- [ ] Update SlackChannel.send() to call markdown_to_mrkdwn() before chat_postMessage
- [ ] Regex-based, ~20 LOC — handle common cases only, not full markdown parser
- [ ] No changes to ChannelPlugin protocol or CLIChannel

See docs/slack-rich-messaging-research.md S3.6
