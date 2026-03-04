---
id: 563
title: Add _SELECT_COLS constant to source_store.py
status: ideation
priority: someday
created: 2026-03-04T07:39:06.1335739+01:00
updated: 2026-03-04T07:39:06.1335739+01:00
tags:
    - audit
    - dry
    - knowledge
class: standard
---

DRY-11: SELECT column list inlined 6 times. BookmarkStore already uses _SELECT_COLS pattern. Follow same pattern. AC: single column-list definition. See docs/software-design-audit.md.
