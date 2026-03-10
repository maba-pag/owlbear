---
id: 516
title: Add concurrency limit to ingest background tasks
status: archived
priority: important
created: 2026-03-04T07:38:26.791016+01:00
updated: 2026-03-09T22:27:23.6594809+01:00
started: 2026-03-06T23:49:41.6591663+01:00
completed: 2026-03-09T22:27:23.6594809+01:00
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

[[2026-03-09]] Mon 22:27
## Audit
### AC Verification
| AC | Evidence | Status |
|---|----------|--------|
| 1. Config field | config.py L165-168: default=5, description; L411-417: validator rejects <1 | PASS |
| 2. Semaphore | enrichment.py L50-68: GraphEnricher.__init__(bg_concurrency=5) -> _bg_semaphore | PASS |
| 3. _enrich_graph bounded | enrichment.py L119-123: async with self._bg_semaphore wraps body | PASS |
| 4. _enrich_inter_doc_graph bounded | enrichment.py L169-183: async with self._bg_semaphore wraps body | PASS |
| 5. Fire-and-forget | enrichment.py L71-86, L88-117: asyncio.create_task() preserved | PASS |
| 6. Bootstrap threading | toolsets.py L110: bg_concurrency=settings.ingest_bg_concurrency -> GraphEnricher | PASS |
| 7. Env-var override | pydantic-settings OWLBEAR_INGEST_BG_CONCURRENCY propagates to semaphore | PASS |

### Test Results
- pytest (task-specific): 115/115 passed
- pytest (full suite): 1334 passed, 1 failed (pre-existing Windows PermissionError in test_context_hydration.py), 2 skipped
- ruff: All checks passed

### Notes
- AC2/AC6 wording references IngestPipeline but semaphore lives on GraphEnricher (due to #672 extraction). Intent fully met.
- Dependency #517 superseded -> split into #672 (archived). Chain satisfied.

### Confidence: .96
### Action: archive
