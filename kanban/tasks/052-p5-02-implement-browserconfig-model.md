---
id: 52
title: 'P5-02: Implement BrowserConfig model'
status: done
priority: high
created: 2026-02-26T21:17:21.6260108+01:00
updated: 2026-02-26T21:40:16.3407333+01:00
started: 2026-02-26T21:21:25.5662337+01:00
completed: 2026-02-26T21:40:16.3407333+01:00
tags:
    - phase-5
    - browser
    - config
depends_on:
    - 51
class: standard
---

Pydantic BaseModel in src/owlbear/tools/browser/config.py. Fields: allowed_urls (list[str] regex patterns), blocked_urls (list[str] regex patterns), headless (bool, default False), viewport (tuple[int,int]), timeout_ms (int, default 30000). Must pass all P5-01 tests.
