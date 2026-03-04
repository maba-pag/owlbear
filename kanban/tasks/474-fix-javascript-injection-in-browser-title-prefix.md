---
id: 474
title: Fix JavaScript injection in browser title prefix
status: ideation
priority: needed
created: 2026-03-04T07:37:52.7515934+01:00
updated: 2026-03-04T07:37:52.7515934+01:00
tags:
    - audit
    - security
    - browser
class: standard
---

SEC-06: task_label interpolated directly into JS string via f-string in page.evaluate(). Single quote in label breaks JS or allows arbitrary code. Use page.evaluate() with argument passing instead. AC: title set safely with parameterized evaluate, test covers special chars. See docs/security-audit.md.
