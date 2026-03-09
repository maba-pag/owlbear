---
id: 649
title: Tests for ingest background task concurrency limit
status: done
priority: important
created: 2026-03-07T23:10:24.7703053+01:00
updated: 2026-03-07T23:47:30.7784418+01:00
started: 2026-03-07T23:47:30.7784418+01:00
completed: 2026-03-07T23:47:30.7784418+01:00
tags:
    - test
    - resilience
    - knowledge
class: standard
---

TDD test task for #516. Tests live in `tests/test_knowledge_ingest.py` (extend existing file).

## AC

1. **Semaphore bounds concurrency:** With `bg_concurrency=2` and 5 concurrent `_enrich_graph` calls, at most 2 run simultaneously (assert via counter + asyncio.Event).
2. **All tasks complete:** After semaphore throttling, all 5 enrichment calls eventually complete (no drops).
3. **Config validation rejects invalid:** `OwlBearSettings(ingest_bg_concurrency=0)` raises `ValidationError`; same for `-1`.
4. **Default value:** `OwlBearSettings().ingest_bg_concurrency == 5`.
5. **Constructor default:** `IngestPipeline(...)._ bg_semaphore._value == 5` when `bg_concurrency` not passed.
6. **Constructor override:** `IngestPipeline(..., bg_concurrency=3)._bg_semaphore._value == 3`.
7. **Both methods bounded:** `_enrich_inter_doc_graph` also respects the shared semaphore (same test pattern as AC-1).
