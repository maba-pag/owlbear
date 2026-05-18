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
| HTTP fetch binding (`fetch_method="http"`) | `_intake.read_url` → `HttpxContentFetcher().fetch(url)` | `refresh_source` selects `select_content_fetcher(source.fetch_method)` and injects into `RefreshOrchestrator` | Yes (both resolve to `HttpxContentFetcher`) |
| Content returned | `response.text` | `response.text` | Yes |
| Metadata: source_type | `"url"` | `"authenticated_web"` | **No** — differs |
| Metadata: fetched_at | Present | Absent | **No** — differs |
| should_wrap behavior | `True` (not in trusted set) | `True` (not in trusted set) | Yes |
| Metadata downstream use | None beyond should_wrap | None beyond should_wrap | Yes |
| Pipeline ingest call | Direct `await` | `inspect.isawaitable` guard | Yes (same result) |
| Empty URL behavior | Error result (failed=1) | Error result (failed=1) | Yes |
| source_id in result | `source.id` | `str(source.id)` | Yes (`KnowledgeSource.id` is already `str`) |
| Local file:// handling | Not supported (httpx only) | Supported via `_local_path_from_url` | N/A for HTTP retype |
| content_fetcher dep | None | Requires injected fetcher | URL_LIST simpler |
| Status counting | ok/partial/skipped/failed | ok/partial/skipped/failed | Yes |
| _record_ingest_outcome | Same call | Same call | Yes |
| Refresh counters | Identical math | Identical math | Yes |

### Metadata Persistence Impact

Both handlers route through `IngestPipeline.ingest()` which persists `intake.metadata` to documents (as JSON) and propagates it to chunks via `TextChunker._build_chunks()`. The metadata differences ARE persisted. However:

1. **`source_type`** — Consumed by `content_safety.should_wrap()` in `ingest.py`, where only `"git"` and `"text"` are trusted. Both `"url"` and `"authenticated_web"` return `True`, so wrapper behavior is identical.
2. **`fetched_at`** — Stored if present, absent if not. No downstream runtime branch in `refresh.py`, `ingest.py`, or retrieval paths depends on this field.

Result: chunk metadata JSON differs between handlers, but no evaluated downstream logic branches on those differences.

### Fetch Path Equivalence (Scoped)

For the task scope (`_direct_source_config`-created HTTP/HTTPS sources), equivalence is established by runtime wiring:

1. `_direct_source_config` sets `fetch_method="http"` for non-local URLs.
2. `refresh_source` selects `select_content_fetcher(source.fetch_method)` and injects that fetcher into `RefreshOrchestrator`.
3. `select_content_fetcher("http")` returns `HttpxContentFetcher`.
4. URL_LIST path calls `_intake.read_url`, which directly uses `HttpxContentFetcher().fetch(url)`.

Outside this scope (for example `fetch_method="browser"`), AUTH_WEB may use a different fetcher and is out of scope for this verdict.

## 4. Recommendation

**PASS — scoped handler equivalence for the O3 retype path.** (confidence: 0.84)

For sources created by `_direct_source_config` with `fetch_method="http"`:
- Fetch-path binding, content delivery into `ingest()`, and RefreshResult counter math are equivalent.
- Metadata differs (`source_type`, `fetched_at`) and is persisted to document/chunk metadata, but no evaluated downstream runtime logic branches on those differences.
- URL_LIST handler is simpler (no content_fetcher dependency, no isawaitable guard)

Conditions for safe retype:
1. Apply to new sources only — existing AUTHENTICATED_WEB records continue via their handler
2. No migration needed — old and new sources coexist

Challenge: proceed — confidence in original: 0.82
Challenger raised valid concern about metadata persistence (I initially cited wrong ingest path for fetched_at backfill). Re-examined: metadata IS persisted but has zero runtime impact. Revised from categorical to conditional PASS.

## 5. Follow-up Tasks

- Follow-up task: #1656 (backlog) — retype `_direct_source_config` from `AUTHENTICATED_WEB` to `URL_LIST` for new HTTP sources (no migration). Delegated to planner.
