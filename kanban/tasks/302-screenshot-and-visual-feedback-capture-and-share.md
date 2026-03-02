---
id: 302
title: Screenshot and visual feedback — capture and share project state
status: backlog
priority: important
created: 2026-03-01T02:53:47.9350608+01:00
updated: 2026-03-01T19:37:23.1461205+01:00
started: 2026-03-01T19:37:23.1461205+01:00
tags:
    - phase-12
    - browser
    - channels
class: standard
---

## Context
Users need to see what OwlBear is doing — screenshots of browser pages, terminal output, code diffs. The browser toolset has a screenshot action but there's no pipeline to share it with the user.

## Acceptance Criteria
- [ ] Screenshot capture tool: browser screenshot, terminal output capture, code diff rendering
- [ ] Screenshots saved to project workspace (.owlbear/screenshots/)
- [ ] Channel-aware delivery: Slack -> upload as image, CLI -> save path + open in viewer
- [ ] Agent can take and share screenshots voluntarily ('let me show you what I found')
- [ ] Screenshot on error: capture state when tool execution fails
- [ ] Configurable: auto-screenshot frequency, manual-only, or on-error-only
- [ ] Unit tests with mock browser and channel
