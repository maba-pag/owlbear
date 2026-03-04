---
id: 515
title: Implement circuit breaker for Copilot API
status: ideation
priority: important
created: 2026-03-04T07:38:26.1410302+01:00
updated: 2026-03-04T07:38:26.1410302+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

CB-1: No circuit breakers anywhere. If Copilot API returns 503 for 10 minutes, every turn burns 3 retries with backoff. No fast-fail mechanism. Add lightweight circuit breaker (half-open after 60s, trip after 5 consecutive failures). AC: circuit breaker active, cascading delays prevented. See docs/resilience-audit.md.
