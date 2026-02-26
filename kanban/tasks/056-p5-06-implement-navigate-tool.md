---
id: 56
title: 'P5-06: Implement navigate tool'
status: done
priority: high
created: 2026-02-26T21:17:42.6380509+01:00
updated: 2026-02-26T22:17:37.5387921+01:00
started: 2026-02-26T21:21:35.6486176+01:00
completed: 2026-02-26T22:17:37.5387921+01:00
tags:
    - phase-5
    - browser
    - tools
depends_on:
    - 55
class: standard
---

browser_navigate(url: str) -> str in src/owlbear/tools/browser/actions.py. Validates URL against BrowserConfig allowed_urls/blocked_urls before calling page.goto(). Returns 'Navigated to {title} ({url})'. Must pass all P5-05 tests.
