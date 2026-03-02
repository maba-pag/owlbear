---
id: 391
title: ScreenshotService — core save/deliver logic
status: backlog
priority: needed
created: 2026-03-01T20:16:20.2166909+01:00
updated: 2026-03-01T20:23:13.2611053+01:00
started: 2026-03-01T20:23:13.2611053+01:00
tags:
    - phase-12
    - browser
    - channels
class: standard
---

From #302 screenshot-visual-feedback-research.md. Create src/owlbear/tools/screenshot.py (~80 LOC). Methods: save(image_bytes, name, workspace) -> Path (saves PNG to .owlbear/screenshots/{timestamp}_{name}.png); deliver(path, channel, caption) dispatches via send_image() (Slack) or send() with path (CLI); capture_browser(page) -> bytes (thin wrapper); capture_terminal(result) -> bytes. AC: Screenshots saved to correct path with timestamps; delivery works for Slack and CLI channels; capture from browser returns PNG bytes. Depends on #302.
