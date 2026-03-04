---
id: 513
title: Review Slack receive timeout behavior for daemon idle
status: ideation
priority: important
created: 2026-03-04T07:38:24.611626+01:00
updated: 2026-03-04T07:38:24.611626+01:00
tags:
    - audit
    - resilience
    - channels
class: standard
---

T-5: Slack channel receive returns None on timeout. Daemon interprets None as shutdown signal (correct for CLI). May cause premature daemon exit on Slack idle periods. AC: Slack channel handles idle correctly, daemon only exits on real shutdown. See docs/resilience-audit.md.
