---
id: 469
title: Add ConnectError and TimeoutException to Copilot transport retry
status: ideation
priority: needed
created: 2026-03-04T07:37:49.018614+01:00
updated: 2026-03-04T07:37:49.018614+01:00
tags:
    - audit
    - resilience
    - auth
class: standard
---

R-2: providers/copilot.py retry only catches httpx.HTTPStatusError. ConnectError, TimeoutException bypass retry entirely. If Copilot API is briefly unreachable, first request fails permanently. AC: retry covers HTTPStatusError, ConnectError, TimeoutException. See docs/resilience-audit.md.
