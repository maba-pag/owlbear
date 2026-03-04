---
id: 509
title: Replace module-level _shutdown flag with asyncio.Event
status: ideation
priority: important
created: 2026-03-04T07:38:20.7731329+01:00
updated: 2026-03-04T07:38:20.7731329+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

F-16: daemon.py uses module-global bool _shutdown toggled by signal handler. Problems: global statement code smell, signal handler to asyncio technically unsafe without loop.call_soon_threadsafe. Use asyncio.Event set via call_soon_threadsafe. AC: no global _shutdown, event-based shutdown. See docs/code-quality-audit.md.
