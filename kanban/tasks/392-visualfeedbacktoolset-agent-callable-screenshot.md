---
id: 392
title: VisualFeedbackToolset — agent-callable screenshot/share tools
status: archived
priority: important
created: 2026-03-01T20:16:29.1337533+01:00
updated: 2026-03-03T13:42:37.0594554+01:00
started: 2026-03-01T20:23:14.393797+01:00
completed: 2026-03-03T13:42:37.0594554+01:00
tags:
    - phase-12
    - browser
    - agent
    - tooling
class: standard
---

From #302 screenshot-visual-feedback-research.md. FunctionToolset (~60 LOC) with: share_screenshot(caption) -> str (captures browser -> saves -> delivers -> returns path); share_terminal_output(output, caption) -> str (saves text -> delivers -> returns path). Injected with ScreenshotService, ChannelPlugin, BrowserToolset ref. AC: Agent can call share_screenshot to capture and deliver browser screenshot; share_terminal_output saves and delivers text output. Depends on #302, #391.
