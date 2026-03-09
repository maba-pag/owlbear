---
id: 516
title: Add concurrency limit to ingest background tasks
status: done
priority: important
created: 2026-03-04T07:38:26.791016+01:00
updated: 2026-03-08T00:49:24.3641139+01:00
started: 2026-03-06T23:49:41.6591663+01:00
completed: 2026-03-08T00:49:24.3641139+01:00
tags:
    - audit
    - resilience
    - knowledge
depends_on:
    - 649
class: standard
---

CF-1: asyncio.create_task() stored in_background_tasks set. Task failures caught (BLE001) but many concurrent ingests spawn unlimited background tasks. No semaphore or concurrency limit.

## Research Findings

See docs/ingest-concurrency-limit-research.md for full analysis.

**Recommendation (.90 confidence):** asyncio.Semaphore wrapping _enrich_graph and _enrich_inter_doc_graph bodies. Default limit 5, configurable via ingest_bg_concurrency setting. ~10 LOC change, zero new deps, preserves fire-and-forget pattern.

**Rejected alternatives:** TaskGroup (blocks caller, breaks fire-and-forget), bounded queue + workers (YAGNI, adds lifecycle management).

## AC

1. **Config field exists:** `ingest_bg_concurrency: int` field added to `OwlBearSettings` with `default=5`, `description`, and a `field_validator` rejecting values < 1.
2. **Semaphore created:** `IngestPipeline.__init__` accepts a `bg_concurrency: int = 5` parameter and stores `self._bg_semaphore = asyncio.Semaphore(bg_concurrency)`.
3. **_enrich_graph bounded:** The entire body of `_enrich_graph` runs inside `async with self._bg_semaphore:`.
4. **_enrich_inter_doc_graph bounded:** The entire body of `_enrich_inter_doc_graph` runs inside `async with self._bg_semaphore:`.
5. **Fire-and-forget preserved:** `_schedule_graph_enrichment` and `_schedule_inter_doc_enrichment` still use `asyncio.create_task()`  tasks are created immediately; the semaphore only gates execution, not creation.
6. **Bootstrap threading:** All 3 `IngestPipeline(...)` call sites in `bootstrap.py` pass `bg_concurrency=settings.ingest_bg_concurrency`.
7. **Env-var override works:** `OWLBEAR_INGEST_BG_CONCURRENCY=2` is picked up by pydantic-settings and propagates through bootstrap to the semaphore.

## Depends

Test task #517 must pass before this task is considered complete.
