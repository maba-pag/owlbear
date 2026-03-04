---
id: 510
title: Add prefix-stripping tests to copilot_multipliers
status: ideation
priority: important
created: 2026-03-04T07:38:21.6998228+01:00
updated: 2026-03-04T07:38:21.6998228+01:00
tags:
    - audit
    - test
class: standard
---

M2: copilot_multipliers.py at 80% coverage -- prefix-stripping loop body never exercised. No test calls get_premium_requests('openai:gpt-4o') or get_premium_requests('copilot:o1'). Trivial fix. AC: coverage 100%, prefix paths tested. See docs/test-quality-audit.md.
