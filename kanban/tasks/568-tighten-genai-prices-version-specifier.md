---
id: 568
title: Tighten genai-prices version specifier
status: ideation
priority: someday
created: 2026-03-04T07:39:10.6285864+01:00
updated: 2026-03-04T07:39:10.6285864+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-01: genai-prices >=0.0.1 accepts every version ever published. Pre-1.0, breaking change in 0.1->0.2 silently enters. Pin to >=0.0.1,<1.0 or tighter. AC: version ceiling added. See docs/config-dependency-audit.md.
