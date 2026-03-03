---
id: 395
title: CLIChannel.send_file() — file delivery for CLI channel
status: archived
priority: important
created: 2026-03-01T20:16:55.6962088+01:00
updated: 2026-03-03T13:42:38.9267375+01:00
started: 2026-03-01T20:23:18.627681+01:00
completed: 2026-03-03T13:42:38.9267375+01:00
tags:
    - phase-12
    - cli
    - channels
class: standard
---

From #302 screenshot-visual-feedback-research.md. Add send_file(path, caption) to CLIChannel. Prints path to console, optionally opens viewer via os.startfile on Windows. ChannelPlugin protocol stays minimal (duck typing via hasattr check in ScreenshotService). AC: CLIChannel.send_file() prints path and caption; os.startfile used on Windows; graceful fallback on other OS. Depends on #302.
