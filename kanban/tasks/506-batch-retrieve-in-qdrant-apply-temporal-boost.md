---
id: 506
title: Batch-retrieve in qdrant _apply_temporal_boost
status: archived
priority: important
created: 2026-03-04T07:38:18.4426963+01:00
updated: 2026-03-09T21:13:27.1902679+01:00
started: 2026-03-06T23:40:08.395678+01:00
completed: 2026-03-09T21:13:27.1902679+01:00
tags:
    - audit
    - performance
    - knowledge
class: standard
---

F-07: _apply_temporal_boost does N+1 retrieves. Batch into single call.
See docs/code-quality-audit.md.

## Acceptance Criteria

1. `_apply_temporal_boost` makes exactly ONE call to `self._client.retrieve()` regardless of `len(results)` (currently N calls for N results).
2. All point IDs are collected upfront: `ids=[_point_id(rid) for rid, _ in results]`.
3. A `dict[str, dict]` lookup is built from the batch response, keyed by `str(point.id)`.
4. The per-result loop reads from the local dict instead of calling retrieve.
5. Return type `list[tuple[str, float]]` and sort behavior are unchanged.
6. When `results` is empty, `retrieve` is NOT called (guard clause).
7. Points missing from the batch response (deleted between search and retrieve) get no boost -- same as current behavior.
8. Existing test `TestRecencyWeight.test_recency_boost_applied` still passes.
9. New unit test: mock `QdrantClient.retrieve`, pass 3+ results, assert `retrieve` called exactly once with all 3+ IDs.
10. `uv run ruff check src/owlbear/memory/knowledge/qdrant.py` clean.

## Architecture Notes

- Change is contained within `QdrantVectorStore._apply_temporal_boost()` in qdrant.py (lines 442-467).
- No interface changes. No callers affected.
- `_point_id()` helper (line 52) already produces deterministic UUID5 strings -- reuse as-is.
- `qdrant_client.retrieve()` already accepts `ids: Sequence[...]` -- this is the canonical batch pattern.
- Follow existing test patterns in `tests/test_qdrant_vector_store.py` (`TestRecencyWeight` class at line 266).

[[2026-03-09]] Mon 21:13
## Audit
### AC Verification
| # | AC Line | Evidence | Status |
|---|---------|----------|--------|
| 1 | Single retrieve() call | qdrant.py L456 | PASS |
| 2 | IDs collected upfront | qdrant.py L455 | PASS |
| 3 | dict lookup built | qdrant.py L463-466 | PASS |
| 4 | Loop reads from dict | qdrant.py L469 | PASS |
| 5 | Return type + sort | qdrant.py L449,L479 | PASS |
| 6 | Empty guard clause | qdrant.py L451 | PASS |
| 7 | Missing points no boost | qdrant.py L476 | PASS |
| 8 | Existing test passes | 29 passed | PASS |
| 9 | New batch test | test L287-318 4 IDs | PASS |
| 10 | Ruff clean | All checks passed | PASS |

### Test Results
- pytest scoped: 29 passed
- pytest full: 1334 passed 1 failed (pre-existing #712)
- ruff: clean

### Confidence: .97
### Action: archive
