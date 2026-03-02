---
id: 307
title: Slack structured proposals — Block Kit for interactive decisions
status: backlog
priority: important
created: 2026-03-01T02:54:39.5274342+01:00
updated: 2026-03-01T19:58:23.1190876+01:00
started: 2026-03-01T19:58:23.1190876+01:00
tags:
    - phase-13
    - slack
    - channels
depends_on:
    - 297
class: standard
---

## Context
Beyond basic rich messages (#297), OwlBear should send properly structured proposals using Slack Block Kit with interactive elements: buttons for quick approval, dropdowns for scope selection, threaded conversations for task updates.

## Acceptance Criteria
- [ ] Proposal template: header, description, option buttons, feedback text input
- [ ] Approval template: action description, approve/deny buttons, reason field
- [ ] Progress template: task name, progress bar (emoji-based), current step, ETA
- [ ] Button interactions handled: Slack events -> channel -> agent decision
- [ ] Threaded conversations: each project/task gets its own Slack thread
- [ ] Fallback: non-interactive channels get markdown-formatted equivalent
- [ ] Unit tests with mocked Slack interactive endpoints

Depends on: #297 (Slack rich messaging)
