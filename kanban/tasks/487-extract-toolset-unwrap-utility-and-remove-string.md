---
id: 487
title: Extract toolset unwrap utility and remove string type dispatch
status: ideation
priority: important
created: 2026-03-04T07:38:03.8534958+01:00
updated: 2026-03-04T07:38:03.8534958+01:00
tags:
    - audit
    - dry
    - refactor
    - scope:core
class: standard
---

DRY-07/DRY-08: while hasattr(inner,'wrapped') loop appears 4x in production. type(inner).__name__=='ProjectToolset' string dispatch 4x. Extract unwrap(toolset) utility. Use isinstance() instead of string comparison. AC: all unwrap loops replaced, isinstance used. See docs/software-design-audit.md.
