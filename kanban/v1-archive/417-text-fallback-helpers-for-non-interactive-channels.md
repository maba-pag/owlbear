---
id: 417
title: Text fallback helpers for non-interactive channels
status: archived
priority: important
created: 2026-03-01T20:20:42.8705739+01:00
updated: 2026-03-03T13:42:50.9969941+01:00
started: 2026-03-01T20:24:08.4771688+01:00
completed: 2026-03-03T13:42:50.9969941+01:00
tags:
    - phase-13
    - channels
class: standard
---

From #307 slack-structured-proposals.md. Add format_proposal_text(), format_approval_text(), format_progress_text() for non-interactive channels (CLI, etc.). Template functions return both blocks and text_fallback. Caller uses hasattr(channel, 'send_blocks') to decide. AC: All interactive templates have text equivalents; CLI receives readable text versions of proposals/approvals/progress; ChannelPlugin protocol unchanged. Depends on #307.
