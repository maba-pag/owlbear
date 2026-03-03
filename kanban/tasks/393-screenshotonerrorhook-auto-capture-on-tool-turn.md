---
id: 393
title: ScreenshotOnErrorHook — auto-capture on tool/turn failure
status: archived
priority: important
created: 2026-03-01T20:16:38.4355629+01:00
updated: 2026-03-03T13:42:37.6663543+01:00
started: 2026-03-01T20:23:15.5748156+01:00
completed: 2026-03-03T13:42:37.6663543+01:00
tags:
    - phase-12
    - browser
    - reliability
class: standard
---

From #302 screenshot-visual-feedback-research.md. Hook (~40 LOC) registers on ON_ERROR event. If browser toolset available and has active page, captures + saves screenshot. Controlled by screenshot_mode config. Wrapped in try/except to handle bad browser state. AC: On tool/turn error with active browser, screenshot auto-captured to .owlbear/screenshots/; no-op when browser unavailable; respects screenshot_mode setting. Depends on #302, #391.
