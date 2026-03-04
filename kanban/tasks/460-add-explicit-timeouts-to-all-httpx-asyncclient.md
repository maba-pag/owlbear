---
id: 460
title: Add explicit timeouts to all httpx.AsyncClient calls
status: ideation
priority: critical
created: 2026-03-04T07:37:40.338076+01:00
updated: 2026-03-04T07:37:40.338076+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

T-1/T-2/T-3: auth/copilot.py (3 calls), tools/github_api.py (4 calls), memory/knowledge/intake.py read_url all lack timeouts. Corporate proxy or slow API blocks daemon indefinitely. Add timeout=httpx.Timeout(10, connect=5) or similar. AC: every httpx.AsyncClient has explicit timeout. See docs/resilience-audit.md.
