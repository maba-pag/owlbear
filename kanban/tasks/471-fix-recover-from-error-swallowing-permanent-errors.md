---
id: 471
title: Fix _recover_from_error swallowing PERMANENT errors
status: ideation
priority: needed
created: 2026-03-04T07:37:50.703621+01:00
updated: 2026-03-04T07:37:50.703621+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

P-2: daemon.py _recover_from_error logs exception + sends to channel. If channel.send fails, error is silently lost. No journal entry, no re-raise. AC: errors always recorded (to journal or fallback log), channel send failure handled gracefully. See docs/resilience-audit.md.
