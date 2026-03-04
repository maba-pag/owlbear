---
id: 473
title: Fix URL safety guard tool name mismatch
status: ideation
priority: needed
created: 2026-03-04T07:37:52.0224627+01:00
updated: 2026-03-04T07:37:52.0224627+01:00
tags:
    - audit
    - security
    - browser
class: standard
---

SEC-10: URLSafetyGuard hook checks tool_name=='navigate' but registered name is 'browser_navigate'. Hook path never matches -- defense-in-depth broken. Direct check_url() call in actions.py still works. AC: hook checks correct tool name, integration test verifies. See docs/security-audit.md.
