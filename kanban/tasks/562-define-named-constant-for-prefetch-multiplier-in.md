---
id: 562
title: Define named constant for prefetch multiplier in qdrant
status: ideation
priority: someday
created: 2026-03-04T07:39:05.1969981+01:00
updated: 2026-03-04T07:39:05.1969981+01:00
tags:
    - audit
    - code-quality
    - knowledge
class: standard
---

F-22: top_k * 10 used as prefetch limit without explanation. Define _PREFETCH_MULTIPLIER = 10 with docstring. AC: named constant with explanation. See docs/code-quality-audit.md.
