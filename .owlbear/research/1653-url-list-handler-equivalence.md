# URL_LIST Handler Equivalence for Retype

> **Owning task:** #1653 — P1-04: Verify handler equivalence for URL_LIST retype
> **Date:** 2026-05-18 **Status:** Complete

## 1. Context and Question

`_direct_source_config` in `ingest.py` currently assigns `SourceType.AUTHENTICATED_WEB` with `fetch_method="http"` for HTTP URLs. The proposed retype (O3 from parent #1650) would change this to `SourceType.URL_LIST`. This research verifies whether `_handle_url_list` produces equivalent refresh results to `_handle_authenticated_web` for single-URL `fetch_method="http"` sources.

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| `_handle_url_list` | `refresh.py:199-242` | Primary handler under evaluation | 1.0 |
| `_handle_authenticated_web` | `refresh.py:317-390` | Comparison handler | 1.0 |
| `_read_authenticated_url` | `refresh.py:391-408` | AUTH_WEB sub-dispatch | 1.0 |
| `HttpxContentFetcher` | `fetcher.py:1-20` | HTTP fetch impl for AUTH_WEB | 1.0 |
| `_intake.read_url` | `intake.py:54-78` | HTTP fetch impl for URL_LIST | 1.0 |
| `IngestPipeline.ingest` | `ingest.py:368-460` | Shared ingest path | 0.9 |
| `content_safety.should_wrap` | `content_safety.py:22-40` | Only consumer of metadata.source_type | 0.9 |
| `TextChunker.chunk` | `chunker.py:50-58` | Metadata passthrough, no source_type logic | 0.7 |
| `DocumentStore.insert_document` | `document_store.py:52-79` | Metadata persistence | 0.7 |

## 3. Analysis

### Comparison Matrix

| Aspect | URL_LIST | AUTH_WEB | Equivalent? |
|--------|----------|---------|-------------|
| URL resolution | `_configured_urls(source)` | `_configured_urls(source)` | Yes |
| HTTP fetch | `_intake.read_url` → httpx GET | `HttpxContentFetcher.fetch` → httpx GET | Yes (same library, same call) |
| Content returned | `response.text` | `response.text` | Yes |
| Metadata: source_type | `"url"` | `"authenticated_web"` | **No** — differs |
| Metadata: fetched_at | Present | Absent | **No** — differs |
| should_wrap behavior | `True` (not in trusted set) | `True` (not in trusted set) | Yes |
| Metadata downstream use | None beyond should_wrap | None beyond should_wrap | Yes |
| Pipeline ingest call | Direct `await` | `inspect.isawaitable` guard | Yes (same result) |
| Empty URL behavior | 0-count success | Error result (failed=1) | **No** — differs |
| source_id in result | `source.id` (raw) | `str(source.id)` (cast) | Minor — no impact |
| Local file:// handling | Not supported (httpx only) | Supported via `_local_path_from_url` | N/A for HTTP retype |
| content_fetcher dep | None | Requires injected fetcher | URL_LIST simpler |
| Status counting | ok/partial/skipped/failed | ok/partial/skipped/failed | Yes |
| _record_ingest_outcome | Same call | Same call | Yes |
| Refresh counters | Identical math | Identical math | Yes |

### Metadata Persistence Impact

Both handlers route through `IngestPipeline.ingest()` which persists `intake.metadata` to documents (as JSON) and propagates it to chunks. The metadata differences ARE persisted. However:

1. **`source_type`** — Only consumed by `content_safety.should_wrap()` at line 442 of `ingest.py`. Both `"url"` and `"authenticated_web"` return `True`. No other code reads this field from stored documents/chunks.
2. **`fetched_at`** — Stored if present, absent if not. No code reads this field for any logic.

Neither field affects content, chunking, entity extraction, embeddings, or search results.

### Fetch Path Equivalence (Conditional)

Equivalence holds specifically when `fetch_method="http"`, which maps to `HttpxContentFetcher` via `select_content_fetcher()`. Both paths ultimately execute `httpx.AsyncClient().get(url)` + `response.raise_for_status()`. For `fetch_method="browser"`, AUTH_WEB would use a different fetcher — but `_direct_source_config` always sets `fetch_method="http"`, so this condition is always met.

## 4. Recommendation

**PASS — conditional equivalence.** (confidence: 0.82)

For sources created by `_direct_source_config` with `fetch_method="http"`:
- Content, chunks, entities, embeddings, and refresh counters are identical
- Metadata differences (`source_type`, `fetched_at`) are persisted but unused by any downstream logic
- URL_LIST handler is simpler (no content_fetcher dependency, no isawaitable guard)

Conditions for safe retype:
1. Apply to new sources only — existing AUTHENTICATED_WEB records continue via their handler
2. No migration needed — old and new sources coexist

Challenge: proceed — confidence in original: 0.82
Challenger raised valid concern about metadata persistence (I initially cited wrong ingest path for fetched_at backfill). Re-examined: metadata IS persisted but has zero runtime impact. Revised from categorical to conditional PASS.

## 5. Follow-up Tasks

- Follow-up task: retype `_direct_source_config` from `AUTHENTICATED_WEB` to `URL_LIST` for new HTTP sources (no migration). Delegated to planner.
