---
id: 396
title: Bootstrap wiring for screenshot toolset, hook, and config
status: backlog
priority: important
created: 2026-03-01T20:17:04.0977373+01:00
updated: 2026-03-01T20:23:20.3122802+01:00
started: 2026-03-01T20:23:20.3122802+01:00
tags:
    - phase-12
    - daemon
    - browser
class: standard
---

From #302 screenshot-visual-feedback-research.md. Register VisualFeedbackToolset, ScreenshotOnErrorHook, and screenshot_mode config in bootstrap assembly. Wire ScreenshotService with channel and browser refs. AC: Bootstrap creates and registers all screenshot components; screenshot toolset available to agents; ON_ERROR hook active when screenshot_mode != manual. Depends on #302, #391, #392, #393, #394.
