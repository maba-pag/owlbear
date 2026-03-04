---
id: 495
title: Isolate browser context in CDP mode
status: ideation
priority: important
created: 2026-03-04T07:38:10.0052022+01:00
updated: 2026-03-04T07:38:10.0052022+01:00
tags:
    - audit
    - security
    - browser
class: standard
---

SEC-07: CDP mode attaches to users existing browser using contexts[0], gaining access to all authenticated sessions and cookies. Create new isolated context via browser.new_context() instead. AC: CDP mode uses isolated context, no cookie sharing. See docs/security-audit.md.
