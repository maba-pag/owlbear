---
id: 649
title: Tests for ingest background task concurrency limit
status: archived
priority: important
created: 2026-03-07T23:10:24.7703053+01:00
updated: 2026-03-09T22:49:31.0458193+01:00
started: 2026-03-07T23:47:30.7784418+01:00
completed: 2026-03-09T22:49:31.0458193+01:00
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

[[2026-03-09]] Mon 22:49
## Audit

### AC Verification
| AC | Evidence | Status |
|-----|----------|--------|
| AC-1 Semaphore bounds concurrency | test_enrich_graph_bounded_by_semaphore: bg_concurrency=2, 5 tasks, asserts max_concurrent<=2. Source: _enrich_graph uses async with self._bg_semaphore | PASS |
| AC-2 All tasks complete | test_all_tasks_complete: asserts len(completed)==5 and correct set | PASS |
| AC-3 Config rejects invalid | test_rejects_zero + test_rejects_negative: ValidationError raised for 0 and -1. Validator at config.py L411 | PASS |
| AC-4 Default value 5 | test_default_value_is_5: settings.ingest_bg_concurrency == 5. Field default=5 in config.py | PASS |
| AC-5 Constructor default semaphore | test_constructor_default_semaphore_value: _bg_semaphore._value == 5 | PASS |
| AC-6 Constructor override | test_constructor_override_semaphore_value: bg_concurrency=3 sets _value==3 | PASS |
| AC-7 Inter-doc also bounded | test_enrich_inter_doc_graph_bounded_by_semaphore: same pattern as AC-1 for _enrich_inter_doc_graph | PASS |

### Test Results
- pytest (scoped): 8 passed (BgConcurrency tests)
- pytest (full): 1334 passed, 1 failed (unrelated PermissionError in test_context_hydration), 2 skipped
- ruff: All checks passed on #649 files

### Confidence: .97
### Action: archive
