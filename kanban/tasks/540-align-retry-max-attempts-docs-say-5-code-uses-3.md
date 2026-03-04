---
id: 540
title: 'Align retry max attempts: docs say 5, code uses 3'
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:44.9656782+01:00
updated: 2026-03-04T07:38:44.9656782+01:00
tags:
    - audit
    - resilience
    - docs
class: standard
---

R-5: python.instructions.md says max 5 attempts but all retry code uses stop_after_attempt(3). Either update docs to 3 or code to 5. AC: docs and code agree. See docs/resilience-audit.md.
