---
id: 512
title: Reconcile daemon retry with tool-level HookedToolset retry
status: ideation
priority: important
created: 2026-03-04T07:38:23.8578187+01:00
updated: 2026-03-04T07:38:23.8578187+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

R-3: daemon.py reimplements exp backoff (3 retries, base 1s) while HookedToolset already retries transient errors (3 attempts, base 0.5s). Transient tool errors get 3x3=9 total attempts. Clarify responsibilities and remove duplication. AC: single retry layer per error type, no multiplicative retries. See docs/resilience-audit.md.
