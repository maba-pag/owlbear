---
id: 480
title: Split bootstrap.py into focused submodules
status: backlog
priority: important
created: 2026-03-04T07:37:58.1734377+01:00
updated: 2026-03-06T23:22:14.0010406+01:00
started: 2026-03-06T23:05:03.8938338+01:00
tags:
    - audit
    - refactor
    - modularity
    - scope:core
class: standard
---

ARC-12/ARC-13/F-02/MOD-03: bootstrap.py is 894 lines. build_toolsets has C901 complexity and 2 concerns (construction + wrapping). Uses magic class-name strings for destructive detection. Split into bootstrap/ package: hooks.py, toolsets.py, knowledge.py, registry.py. AC: bootstrap.py <200 lines, no C901, no magic strings. See docs/architecture-audit.md, docs/code-quality-audit.md.
