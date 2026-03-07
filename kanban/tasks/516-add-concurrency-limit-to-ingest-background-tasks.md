---
id: 516
title: Add concurrency limit to ingest background tasks
status: backlog
priority: important
created: 2026-03-04T07:38:26.791016+01:00
updated: 2026-03-06T23:54:24.1968097+01:00
started: 2026-03-06T23:49:41.6591663+01:00
tags:
    - audit
    - resilience
    - knowledge
class: standard
---

CF-1: asyncio.create_task() stored in _background_tasks set. Task failures caught (BLE001) but many concurrent ingests spawn unlimited background tasks. No semaphore or concurrency limit.

## Research Findings

See docs/ingest-concurrency-limit-research.md for full analysis.

**Recommendation (.90 confidence):** asyncio.Semaphore wrapping _enrich_graph and _enrich_inter_doc_graph bodies. Default limit 5, configurable via ingest_bg_concurrency setting. ~10 LOC change, zero new deps, preserves fire-and-forget pattern.

**Rejected alternatives:** TaskGroup (blocks caller, breaks fire-and-forget), bounded queue + workers (YAGNI, adds lifecycle management).

## Research Checklist
- [x] Theoretical validity - Semaphore is the standard primitive for bounding concurrent access
- [x] Prior art - Python stdlib docs + SuperFastPython tutorial confirm pattern
- [x] Technical feasibility - asyncio.Semaphore works with create_task fire-and-forget
- [x] Architecture fit - Semaphore in IngestPipeline.__init__, config in OwlBearSettings
- [x] Implementation approach - Wrap enrichment coroutine bodies with async with self._bg_semaphore

AC: bounded concurrency, no unbounded task spawning, configurable limit.
