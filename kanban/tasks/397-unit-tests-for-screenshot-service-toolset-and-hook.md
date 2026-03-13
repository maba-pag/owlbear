---
id: 397
title: Unit tests for screenshot service, toolset, and hook
status: archived
priority: important
created: 2026-03-01T20:17:12.4991548+01:00
updated: 2026-03-03T15:33:23.4883486+01:00
started: 2026-03-01T20:23:22.490465+01:00
completed: 2026-03-03T15:33:23.4883486+01:00
tags:
    - phase-12
    - test
    - browser
class: standard
---

From #302 screenshot-visual-feedback.md. Tests with mock browser, mock channel: ScreenshotService save/deliver, VisualFeedbackToolset share_screenshot/share_terminal_output, ScreenshotOnErrorHook fires on error, respects screenshot_mode, no-op without browser. AC: >= 90%% coverage for screenshot.py; all capture/save/deliver paths tested; hook behavior verified under each screenshot_mode. Depends on #302.
