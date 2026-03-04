---
id: 535
title: Make logfire import conditional in daemon.py
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:40.4014439+01:00
updated: 2026-03-04T07:38:40.4014439+01:00
tags:
    - audit
    - config
    - scope:core
class: standard
---

F-25: import logfire unconditional at daemon.py top level. If logfire not installed, daemon import fails. Add try/except ImportError guard. AC: daemon importable without logfire. See docs/code-quality-audit.md.
