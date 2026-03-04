---
id: 536
title: Lazy-singleton OwlBearSettings in cli.py
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:41.3865662+01:00
updated: 2026-03-04T07:38:41.3865662+01:00
tags:
    - audit
    - dry
    - scope:cli
class: standard
---

DRY-05: OwlBearSettings() instantiated 12 times in cli.py. pydantic-settings re-reads env vars each time. Use Typer callback or functools.lru_cache for single construction. AC: settings constructed once, all commands use same instance. See docs/software-design-audit.md.
