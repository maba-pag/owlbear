---
id: 495
title: Isolate browser context in CDP mode
status: backlog
priority: important
created: 2026-03-04T07:38:10.0052022+01:00
updated: 2026-03-06T23:29:02.1758303+01:00
started: 2026-03-06T23:23:22.8991517+01:00
tags:
    - audit
    - security
    - browser
class: standard
---

SEC-07: CDP mode attaches to users existing browser using contexts[0], gaining access to all authenticated sessions and cookies. Create new isolated context via browser.new_context() instead.

Research complete - see docs/cdp-context-isolation-research.md

Findings:
- browser.new_context() works on CDP connections (delegates to Target.createBrowserContext)
- Provides full cookie/cache/localStorage isolation
- Minimal diff: ~10 lines in manager.py, ~30 lines in tests
- Bonus: current CDP path does not set viewport (fix included)

AC: CDP mode uses isolated context, no cookie sharing.

Implementation: Replace contexts[0] with browser.new_context(viewport=...) in _enter_cdp(). Close owned context in _exit_cdp(). Update tests.
