# Research Notes — Knowledge Source Lifecycle Ownership

## Verified Findings

### F1: `list_sources` hides 9 of 13 fields

`SourceInfo` TypedDict has 4 fields (`id`, `name`, `source_type`, `scope`). The `KnowledgeSource` model has 13. The missing fields that carry health/operational data: `last_refreshed_at`, `last_error`, `enabled`, `fetch_method`, `enrich`, `priority`, `config`, `created_at`, `updated_at`.

**Files:** `server.py:97-104` (TypedDict), `server.py:1314-1331` (list_sources), `models.py:111-132` (full model)

### F2: `_update_source_record` always updates `last_refreshed_at`

The method unconditionally sets `last_refreshed_at = now` regardless of whether the refresh result has any successful items. A result with `refreshed=0, failed=0, skipped=0` still marks the source as freshly refreshed.

The `last_error` field is set to the joined errors+warnings string or `None` — so when a refresh does nothing (zero-count, zero-error), `last_error` is cleared and `last_refreshed_at` is bumped. This is the "silent success" bug.

**File:** `refresh.py:435-451`

### F3: `refresh()` always calls `_update_source_record`

Line 146 calls `_update_source_record(source, result)` after every handler dispatch, regardless of result content. No conditional path exists to skip the update on failure or no-op.

**File:** `refresh.py:115-146`

### F4: `_handle_authenticated_web` does fail on missing fetcher — but at the per-URL level

When `content_fetcher` is None, `_read_authenticated_url` raises `RuntimeError("content fetcher not available")`. This is caught by the per-URL `except Exception` block in `_handle_authenticated_web`, which increments `failed += 1` and appends the error. So the handler does return `failed=N, errors=[...]` — it doesn't silently return zeros.

However, F2/F3 then update `last_refreshed_at` anyway, making the source look recently refreshed despite all URLs failing.

**Files:** `refresh.py:381` (raise), `refresh.py:379` (catch), `refresh.py:146` (update)

### F5: Direct-ingest URL sources are typed `AUTHENTICATED_WEB` with `fetch_method="http"`

`_direct_source_config` assigns `SourceType.AUTHENTICATED_WEB` and `fetch_method="http"` with `config={"url": source_url, "urls": [source_url]}` for any non-local URL. This makes direct-ingest records refreshable by the authenticated web handler, which selects a content fetcher via `select_content_fetcher(source.fetch_method)`.

Since `fetch_method="http"` routes to `HttpxContentFetcher` (not the browser), direct-ingest URL sources are actually refreshable via HTTP. The original audit concern about config shape incompatibility (`url` vs `urls`) is already resolved — `_configured_urls` merges both.

**Files:** `ingest.py:114-132`, `server.py:864-870` (select_content_fetcher), `refresh.py:31-41` (_configured_urls)

### F6: `delete_cascade` is comprehensive and ready to wire

Cascade chain: `knowledge_sources` → `source_pages` → `documents` → `entities`, `edges`, `chunks`, `document_status`. All deletions happen in a single transaction with `commit()` at the end. Returns `True` if source existed, `False` otherwise.

No `remove_source` MCP tool exists. Wiring is straightforward — same pattern as `refresh_source`.

**File:** `source_store.py:198-227`

### F7: `refresh_source` MCP tool already returns errors and warnings

The tool returns a dict with `source_id`, `refreshed`, `partial`, `skipped`, `failed`, `errors`, and `warnings`. Audit constraint 3 (error visibility in refresh response) is already resolved.

**File:** `server.py:1408-1450`

## Candidate Implications

### I1: O2 fix is primarily in `_update_source_record`

The fix is to make `_update_source_record` conditional: only bump `last_refreshed_at` when `result.refreshed > 0 or result.partial > 0`. When all items failed, set `last_error` but leave `last_refreshed_at` unchanged. This preserves the "when was the last *successful* refresh?" semantics.

### I2: O3 may be partially resolved already

F5 shows that direct-ingest URL sources have config shapes compatible with refresh (both `url` and `urls` keys present) and route to `HttpxContentFetcher`. The remaining question is whether `AUTHENTICATED_WEB` is the right type for a source that was ingested via plain HTTP. A `URL_LIST` type with `fetch_method="http"` might be more accurate.

### I3: O1 doesn't need all 9 missing fields

The minimum useful health fields are: `last_refreshed_at`, `last_error`, `enabled`, `fetch_method`. Adding `enrich` is low-cost and operationally useful. `priority`, `config`, `created_at`, `updated_at` are less important for the "at a glance" health view and could stay internal.

### I4: `remove_source` needs a destructive-hint annotation

The existing MCP tools use `ToolAnnotations(destructiveHint=True/False)`. `remove_source` should use `destructiveHint=True` since it cascade-deletes all downstream data.

## Open Research Questions

### Q1: Should direct-ingest sources use `URL_LIST` instead of `AUTHENTICATED_WEB`?

Changing `_direct_source_config` to assign `URL_LIST` for HTTP URLs would be more semantically accurate. But it would change the type of *all future* direct-ingest web sources, and any existing `AUTHENTICATED_WEB` sources created by prior ingestions would remain. Need to decide if this is worth a migration or if the current typing is acceptable given the refresh path works.

### Q2: What about Qdrant vector cleanup in `delete_cascade`?

`delete_cascade` handles SQLite tables but doesn't mention Qdrant vector store cleanup. If chunks have associated vectors in Qdrant, those would become orphaned after cascade delete. Need to verify whether `DocumentStore` deletion handles this or if `delete_cascade` needs to be extended.

### Q3: Should `_update_source_record` distinguish "attempted but all failed" from "nothing to do"?

I1 proposes skipping the `last_refreshed_at` update when `refreshed == 0`. But there's a semantic gap: is "0 refreshed, 0 failed, 0 skipped" (no URLs configured) different from "0 refreshed, 3 failed" (all URLs broken)? Both would leave `last_refreshed_at` unchanged under I1, but the second case should probably update `last_error`.
