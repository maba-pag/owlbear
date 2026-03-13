---
id: 571
title: Pin benchmark extra dependencies
status: backlog
priority: someday
created: 2026-03-04T07:39:13.3539198+01:00
updated: 2026-03-07T04:53:04.0189212+01:00
started: 2026-03-07T04:53:04.0189212+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-15: benchmark = ['beir', 'ranx'] has no version specifiers. Unpinned deps can break CI. See docs/config-dependency-audit.md.

## AC

- [ ] beir has minimum version specifier (e.g. beir>=2.0.0)
- [ ] ranx has minimum version specifier (e.g. ranx>=0.3)
- [ ] uv lock resolves successfully
