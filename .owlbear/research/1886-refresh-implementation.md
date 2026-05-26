# IngestCoordinator.refresh() — Implementation Research

> **Owning task:** #1886 — Knowledge: IngestCoordinator.refresh() — implement refresh with fetcher
> **Date:** 2026-05-26  **Status:** Complete

## 1. Context and Question

Implement the currently-stubbed `IngestCoordinator.refresh()` method. Both dependencies are complete:
- #1884: `SourceUpdate.last_refreshed_at` write path exists
- #1885: `SourceFetcher` protocol defined at `protocols/fetcher.py`

Question: How should refresh orchestrate source listing, fetching, ingestion, and watermark updates within the existing coordinator pattern?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| IngestCoordinator protocol (refresh contract) | `protocols/ingest.py:240–255` | 1.0 |
| SourceFetcher protocol | `protocols/fetcher.py` | 1.0 |
| RefreshRequest/RefreshResult/RefreshError | `protocols/ingest.py:110–142` | 1.0 |
| SourceUpdate (last_refreshed_at) | `protocols/sources.py:157` | .95 |
| ConfiguredSourceRecord (refreshable field) | `protocols/sources.py:200` | .90 |
| SourceStore.list_sources / update_source | `protocols/sources.py:316,340` | .90 |
| Legacy refresh.py (pattern reference) | `refresh.py:155–200` | .75 |
| IngestCoordinator.ingest() (self-call target) | `ingest_coordinator.py:49–118` | .85 |
| Parent research #1877 | `.owlbear/research/1877-ingest-coordinator.md` | .70 |

## 3. Analysis

### 3.1 Design — Constructor Extension

| Option | Impact | Fit |
|--------|--------|-----|
| A) Add `fetcher: SourceFetcher \| None = None` to `__init__` | Minimal; backward-compatible default | KISS ✓ |
| B) Pass fetcher as arg to `refresh()` | Violates protocol signature | ✗ |
| C) Fetcher registry by FetchTransport | Over-engineering for v1 | YAGNI |

**Decision:** Option A. Optional 5th DI parameter. When `None`, `refresh()` returns empty `RefreshResult` (no sources refreshed, no errors).

### 3.2 Refresh Algorithm (~40 LOC)

```
1. Guard: if no fetcher → return empty RefreshResult
2. List sources: self._sources.list_sources(state=ACTIVE)
3. Filter:
   a. Only ConfiguredSourceRecord (skip WishedSourceRecord)
   b. If request.source_ids: filter to those IDs
   c. If not request.force: filter to refreshable=True
4. For each source:
   try:
     fetch_result = await self._fetcher.fetch_source(source)
     documents = convert FetchedDocument → IngestDocument
     if documents:
       ingest_result = await self.ingest(IngestRequest(...))
       ingest_results.append(ingest_result)
     self._sources.update_source(source.id, SourceUpdate(last_refreshed_at=now))
     sources_refreshed += 1
   except Exception as exc:
     errors.append(RefreshError(source_id=source.id, error=str(exc), timestamp=now))
5. Return RefreshResult(sources_checked, sources_refreshed, ingest_results, errors)
```

### 3.3 FetchedDocument → IngestDocument Mapping

| FetchedDocument field | IngestDocument field | Notes |
|----------------------|---------------------|-------|
| title | title | 1:1 |
| text | text | 1:1 |
| uri | uri | 1:1 |
| external_id | external_id | 1:1 |
| metadata | metadata | 1:1 |

Trivial mapping — no transformation needed.

### 3.4 Edge Cases

| Case | Behavior |
|------|----------|
| No fetcher injected | Return empty RefreshResult immediately |
| fetch_source returns empty documents | Still update watermark (source was checked) |
| fetch_source raises | Capture in RefreshError, continue batch |
| source_ids has invalid IDs | Skipped (not in list_sources result) |
| force=True + refreshable=False | Include the source |
| ingest raises LookupError | Should not happen (source verified) but captured by except |

### 3.5 Testing Strategy

- Mock `SourceFetcher.fetch_source` returning `FetchResult` with documents
- Mock `SourceStore.list_sources` returning active+refreshable sources
- Verify: `self.ingest()` called with correct `IngestRequest`
- Verify: `update_source` called with `last_refreshed_at`
- Verify: errors captured, batch continues
- Verify: `force=True` overrides refreshable filter
- Verify: no fetcher → empty result

## 4. Recommendation

Implement as described in §3.2. ~40 LOC addition to `ingest_coordinator.py`. No new files, no new dependencies beyond what's already in `protocols/`.

Confidence: .90 — all building blocks exist, protocol contract is explicit, pattern mirrors existing `ingest()` loop structure.

Challenge: skipped — trivial integration of existing protocols, no novel design decisions.

## 5. Follow-up Tasks

None needed — implementation is self-contained. The existing test at `test_ingest_coordinator_1877.py` has a placeholder test (AC8) that will need updating, but that's part of the implementation task itself.
