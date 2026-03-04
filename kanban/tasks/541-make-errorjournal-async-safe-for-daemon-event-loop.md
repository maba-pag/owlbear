---
id: 541
title: Make ErrorJournal async-safe for daemon event loop
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:45.7339339+01:00
updated: 2026-03-04T07:38:45.7339339+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

J-2: ErrorJournal uses blocking file I/O (path.open('a')). In async daemon loop, rotation of 10K entries blocks event loop. Use aiofiles or asyncio.to_thread. Depends on J-1 wiring first. AC: journal I/O non-blocking. See docs/resilience-audit.md.
