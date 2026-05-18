# Architectural Stance — Knowledge Source Lifecycle Fixes

## Architectural Stance

The 4-outcome plan is structurally sound. The outcomes touch distinct code paths and can be implemented independently. Two refinements are required: O3 is a genuine retype (not cosmetic), and O4 has a prerequisite bug fix in `delete_cascade`.

## Structural Reasoning

### Outcome Independence

O1 modifies `SourceInfo` TypedDict and `list_sources` in `server.py` (read path). O2 modifies `_update_source_record` in `refresh.py` (write path). O3 modifies `_direct_source_config` in `ingest.py` (creation path). O4 adds a new MCP tool wiring `source_store.delete_cascade` (deletion path). No two outcomes touch the same function or data flow.

### Ordering Recommendation

O2 should ship before or alongside O1. O1 exposes `last_refreshed_at` and `last_error` to agents. If O2 hasn't fixed the unconditional timestamp bump, agents will see dishonest health data — sources marked "recently refreshed" when all URLs actually failed. This isn't a hard dependency (the dishonest data already persists regardless of exposure), but exposing known-bad data to consumers is poor operational hygiene.

### Q1 — Retype Direct-Ingest HTTP Sources to `URL_LIST`

**Position: Retype.** `URL_LIST` already exists as a first-class `SourceType` enum value with its own refresh handler `_handle_url_list`. Direct-ingest HTTP sources are currently mistyped as `AUTHENTICATED_WEB`, which routes them through `_handle_authenticated_web` — a handler that requires a content fetcher injection (`self._content_fetcher`). The `_handle_url_list` handler does plain HTTP fetch via `_intake.read_url()` without needing a content fetcher at all.

This is not cosmetic. The mistyping:
- Routes sources through a more complex handler than necessary
- Creates a spurious dependency on content fetcher availability for plain HTTP sources
- Makes `source_type` unreliable as a classification signal (operators see "authenticated_web" for unauthenticated HTTP sources)

The fix is in `_direct_source_config` in `ingest.py`: change the return type from `SourceType.AUTHENTICATED_WEB` to `SourceType.URL_LIST` for non-local URLs. Existing `AUTHENTICATED_WEB` records from prior ingestions remain unchanged — they still refresh correctly via their current handler. New direct-ingest sources get the correct type going forward. No migration needed.

### Q2 — Qdrant Orphan Risk Is Real and Blocks O4

**Position: Fix `delete_cascade` before wiring it as an MCP tool.**

`source_store.delete_cascade()` deletes SQLite rows (chunks, entities, edges, document_status, documents, source_pages, knowledge_sources) but never touches Qdrant. The only Qdrant cleanup path is `document_store.delete_chunk_embeddings()` → `qdrant.delete_embedding()`, which `delete_cascade` does not call. Wiring the current implementation as `remove_source` would orphan Qdrant vectors on every source removal.

**Fix approach:** Add best-effort Qdrant vector cleanup directly to `delete_cascade`. Collect chunk IDs from SQLite before the cascade, call vector deletion (best-effort, swallowing exceptions consistent with existing `delete_chunk_embeddings` pattern), then execute the SQLite cascade in its existing single-commit transaction.

Do NOT delegate to `document_store.delete_document_data()`. That method commits per-document, which would fragment the currently-atomic SQLite transaction and create partial-deletion failure modes.

**Honest framing:** This fix adds best-effort vector cleanup, not guaranteed cleanup. `delete_chunk_embeddings` is already best-effort (swallows all exceptions). At the 10-50 source scale, best-effort is acceptable — occasional Qdrant orphans are operationally benign and self-limiting.

### Q3 — Three-Way Update Semantics for O2

**Position: The three-way distinction is correct.**

| Case | `last_refreshed_at` | `last_error` |
|------|---------------------|--------------|
| `refreshed > 0 or partial > 0` | Bump to now | Set if warnings, clear otherwise |
| `refreshed == 0 and failed > 0` | Leave unchanged | Set to joined error messages |
| `refreshed == 0 and failed == 0` | Leave unchanged | Set to "no content URLs configured" |

The semantic principle: `last_refreshed_at` means "last time we successfully acquired new content." The current unconditional bump destroys this signal.

**Acknowledged limitation:** `_record_ingest_outcome` coerces unknown IngestResult statuses (including `cancelled`, `blocked`) into `"ok"`, inflating the `refreshed` counter. This is a pre-existing issue outside O2's scope. The three-way fix at the RefreshResult level is still correct and improves the status quo.

### O4 — `remove_source` Structural Safety

Exposing cascade-delete to agents via MCP is sound:
- `destructiveHint=True` annotation lets agent frameworks gate the operation
- Pattern matches existing MCP tool conventions in `server.py`
- Tool should return deletion counts (documents, chunks, entities removed) for auditability, consistent with `refresh_source` returning detailed counters

**Non-recoverability warning:** Inline/manual sources (created via `ingest_document` with raw text, typed `INLINE`, `enabled=False`) have no fetch path to reconstruct content after deletion. `destructiveHint=True` is the correct gate, but the tool's docstring should explicitly warn that inline source data is not recoverable.

## Key Trade-offs

| Decision | Gains | Costs |
|----------|-------|-------|
| Retype to `URL_LIST` | Correct handler routing, honest taxonomy | Existing records stay `AUTHENTICATED_WEB` (cosmetic inconsistency for old data) |
| Best-effort Qdrant cleanup in `delete_cascade` | Closes the common-path orphan gap | Not guaranteed; adds Qdrant dependency to `source_store` |
| Three-way update semantics | `last_refreshed_at` becomes a reliable health signal | Slightly more complex conditional logic in `_update_source_record` |
| Expose `last_error` in `list_sources` | Agents can diagnose source health | `last_error` contains raw exception text — may need sanitization before exposure |

## Warnings

1. **O1 error text leakage.** `last_error` stores raw exception strings that may contain file paths, URLs, or internal error details. Before exposing via `list_sources`, verify that the error text is safe for agent consumption. Existing tests (`test_browser_fetcher_wiring`) already assert URL scrubbing in some paths — ensure consistent sanitization.

2. **O4 Qdrant dependency.** Adding Qdrant cleanup to `source_store.delete_cascade` introduces a new dependency direction (`source_store` → Qdrant client). Keep it minimal: pass a callable or the vector store instance, don't import the full document store.

3. **MCP tool-shape change.** O1 expands the `SourceInfo` TypedDict, which is an additive change. Existing consumers see new fields but don't break. Existing tests will need updates to reflect the expanded shape.

## Confidence

**0.78**

The plan is well-scoped and the outcomes are genuinely independent. The main uncertainty is the Qdrant cleanup injection into `source_store` — the dependency direction needs care during implementation to avoid coupling `source_store` to `document_store` internals.
