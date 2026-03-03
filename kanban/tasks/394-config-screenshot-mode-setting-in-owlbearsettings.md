---
id: 394
title: 'Config: screenshot_mode setting in OwlBearSettings'
status: archived
priority: important
created: 2026-03-01T20:16:47.1072182+01:00
updated: 2026-03-03T13:42:38.3098867+01:00
started: 2026-03-01T20:23:16.8598161+01:00
completed: 2026-03-03T13:42:38.3098867+01:00
tags:
    - phase-12
    - config
    - browser
class: standard
---

From #302 screenshot-visual-feedback-research.md. Add screenshot_mode: Literal['auto', 'manual', 'on_error'] = 'on_error' to OwlBearSettings. 'auto' = capture after every browser action; 'manual' = only when agent calls tool; 'on_error' = auto-capture on failure. Screenshot dir derived from workspace (not user-configurable). AC: screenshot_mode field validated; default is on_error; hooks and toolset respect the setting. Depends on #302.
