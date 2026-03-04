---
id: 571
title: Pin benchmark extra dependencies
status: ideation
priority: someday
created: 2026-03-04T07:39:13.3539198+01:00
updated: 2026-03-04T07:39:13.3539198+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-15: benchmark = ['beir', 'ranx'] has no version specifiers. Unpinned deps can break CI. Add minimum versions. AC: beir>=2.0.0, ranx>=0.3 or similar. See docs/config-dependency-audit.md.
