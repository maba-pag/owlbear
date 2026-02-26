---
id: 64
title: 'P5-14: Implement URL safety guard'
status: done
priority: medium
created: 2026-02-26T21:18:35.3821565+01:00
updated: 2026-02-26T21:40:19.1948339+01:00
started: 2026-02-26T21:21:49.4203824+01:00
completed: 2026-02-26T21:40:19.1948339+01:00
tags:
    - phase-5
    - browser
    - tools
depends_on:
    - 63
class: standard
---

URLSafetyGuard class in src/owlbear/tools/browser/safety.py. Callable registered as PRE_TOOL_USE hook on HookRegistry. Inspects tool call args for URLs, checks against BrowserConfig blocked_urls regex patterns. Raises/returns block signal for denied URLs. Must pass P5-13 tests.
