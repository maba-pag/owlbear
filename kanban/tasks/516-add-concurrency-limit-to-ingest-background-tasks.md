---
id: 516
title: Add concurrency limit to ingest background tasks
status: ideation
priority: important
created: 2026-03-04T07:38:26.791016+01:00
updated: 2026-03-04T07:38:26.791016+01:00
tags:
    - audit
    - resilience
    - knowledge
class: standard
---

CF-1: asyncio.create_task() stored in _background_tasks set. Task failures caught (BLE001) but many concurrent ingests spawn unlimited background tasks. No semaphore or concurrency limit. AC: bounded concurrency, no unbounded task spawning. See docs/resilience-audit.md.
