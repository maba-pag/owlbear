---
id: 60
title: 'P5-10: Implement content extraction tools'
status: done
priority: medium
created: 2026-02-26T21:18:07.9205102+01:00
updated: 2026-02-26T22:17:39.3258941+01:00
started: 2026-02-26T21:21:45.7394452+01:00
completed: 2026-02-26T22:17:39.3258941+01:00
tags:
    - phase-5
    - browser
    - tools
depends_on:
    - 59
class: standard
---

browser_read_text(selector: str | None = None) -> str and browser_screenshot(selector: str | None = None, full_page: bool = True) -> str in src/owlbear/tools/browser/actions.py. Text returns cleaned inner_text; screenshot returns base64 PNG. Must pass P5-09 tests.
