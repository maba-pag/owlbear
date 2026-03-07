---
id: 506
title: Batch-retrieve in qdrant _apply_temporal_boost
status: backlog
priority: important
created: 2026-03-04T07:38:18.4426963+01:00
updated: 2026-03-06T23:42:22.7330797+01:00
started: 2026-03-06T23:40:08.395678+01:00
tags:
    - audit
    - performance
    - knowledge
class: standard
---

F-07: _apply_temporal_boost does N+1 retrieves -- one client.retrieve() per result. For top_k=20, that's 20 round-trips. Batch all point IDs in single retrieve(ids=[...]). AC: single batch retrieve, N+1 eliminated. See docs/code-quality-audit.md.

## Research Findings (2026-03-06)

### 1. Theoretical validity

Sound optimization. The current loop makes one `client.retrieve(ids=[single_id])` per result (qdrant.py:443-467). For top_k=20, that's 20 sequential HTTP/gRPC calls. `retrieve()` already accepts `ids: Sequence[...]` -- collapsing into a single call is the canonical batch pattern.

### 2. Prior art

- **Qdrant official docs** (https://qdrant.tech/documentation/concepts/points/#retrieve-points): REST API `POST /collections/{name}/points` with `ids: [0, 3, 100]` -- batch retrieve by design.
- **qdrant-client Python API** (https://python-client.qdrant.tech/qdrant_client.qdrant_client): `retrieve(collection_name, ids=Sequence[int|str|UUID], with_payload=True)` -- accepts list of IDs natively.

### 3. Technical feasibility

Fully feasible, zero risk. Our qdrant-client>=1.13 (pyproject.toml) has had batch retrieve since 1.0. The existing code already passes `ids=[_point_id(rid)]` (a one-element list). Changing to `ids=[_point_id(r) for r, _ in results]` is a mechanical refactor.

### 4. Architecture fit

Contained within `QdrantVectorStore._apply_temporal_boost()`. No interface changes. Return type `list[tuple[str, float]]` stays the same. No callers affected.

### 5. Implementation approach

1. Collect all point IDs: `all_ids = [_point_id(rid) for rid, _ in results]`
2. Single batch call: `points = self._client.retrieve(collection_name=..., ids=all_ids, with_payload=True)`
3. Build lookup dict: `payload_map = {str(p.id): p.payload for p in points if p.payload}`
4. Iterate results locally, applying recency boost from `payload_map`
5. ~10 lines changed, net diff near zero

### 6. Testing strategy

No existing test covers `_apply_temporal_boost` directly. Builder should add a unit test with a mock `QdrantClient` that asserts `retrieve` is called exactly once with all IDs (not N times).

### 7. Risk

None. The method is internal, return type unchanged, single call is strictly faster.
