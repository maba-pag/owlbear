---
id: 506
title: Batch-retrieve in qdrant _apply_temporal_boost
status: done
priority: important
created: 2026-03-04T07:38:18.4426963+01:00
updated: 2026-03-07T23:00:10.4356026+01:00
started: 2026-03-06T23:40:08.395678+01:00
completed: 2026-03-07T23:00:10.4356026+01:00
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
