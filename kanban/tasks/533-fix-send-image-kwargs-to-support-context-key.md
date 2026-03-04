---
id: 533
title: Fix send_image kwargs to support context_key threading
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:38.4297337+01:00
updated: 2026-03-04T07:38:38.4297337+01:00
tags:
    - audit
    - code-quality
    - channels
class: standard
---

F-23: Slack send_image handles thread_ts but ignores context_key, breaking thread auto-creation for images. Add context_key parameter matching send/send_blocks pattern. AC: images threaded correctly by context_key. See docs/code-quality-audit.md.
