# Data Quality Stance — Knowledge Source Lifecycle

## Data Quality Stance

The four proposed outcomes carry one critical data integrity risk (O4 — Qdrant orphan vectors), one semantic modeling gap (O2 — refresh state model is under-specified), one behavioral change masquerading as a label fix (O3), and one genuinely low-risk schema expansion (O1). The fixes are directionally correct but the implementation details need tighter specification to avoid trading one class of silent data corruption for another.

## Schema and Validation Reasoning

### O1 — TypedDict Expansion: Low Risk

Adding `last_refreshed_at`, `last_error`, `enabled`, `fetch_method`, and `enrich` to the `SourceInfo` TypedDict is backwards-compatible for MCP consumers. MCP tool responses are JSON dicts — extra keys are ignored by consumers that don't request them. The existing schema tests in `test_outputschema.py` check for presence of specific required fields, not exclusive key sets; adding fields may not require test updates at all.

The real validation gap is structural: `SourceInfo` is hand-maintained separately from the `KnowledgeSource` Pydantic model. They can drift independently with no compile-time enforcement. The O1 fix should derive the health fields from the model programmatically or at minimum document the mapping.

### O2 — Conditional Update: Four-State Model Required

The proposed "only bump `last_refreshed_at` when `refreshed > 0 or partial > 0`" is correct as far as it goes but under-specifies three other states. The full state model for `_update_source_record`:

| State | Condition | `last_refreshed_at` | `last_error` |
|-------|-----------|---------------------|--------------|
| **Success** | `refreshed > 0 or partial > 0` | Bump | Set from errors+warnings (partial success carries warnings) |
| **Skipped-only** | `skipped > 0, refreshed == 0, failed == 0` | Bump (source was checked, found current) | Clear |
| **All failed** | `failed > 0, refreshed == 0, partial == 0` | Preserve | Set from errors+warnings |
| **Empty no-op** | All counters zero | Preserve | Preserve (do not clear previous error) |

**Complications the implementation must handle:**

1. **Mixed outcomes are the common case.** Handlers aggregate counts across multiple URLs/files. A source with 3 URLs might have `refreshed=1, failed=2`. This is "Success" by the table above (refreshed > 0), but `last_error` must capture the 2 failures. The current code already does this — `last_error` is built from `errors + warnings`, not just failures.

2. **`last_error` carries warnings, not just errors.** This is an existing tested contract (`test_ingest_partial_extraction.py` asserts partial-success warnings in `last_error`). The O2 fix must preserve this behavior. The field is semantically `last_diagnostic`, not `last_error`.

3. **The "empty no-op" bucket is ambiguous.** Three different situations produce all-zero counters: URL_LIST with no configured URLs (iterates zero times silently), FILE_GLOB with no matching files (returns zeros), and cancelled refresh (broken loop with partial counts). "Preserve previous state" is the least-harmful default for all three because it avoids hiding a previously-recorded error.

4. **Pre-existing upstream contamination:** `_record_ingest_outcome` aliases any ingest status not in `{ok, partial, skipped, failed}` to `"ok"`. This means `cancelled` ingest outcomes inflate the `refreshed` counter before `_update_source_record` runs. The O2 fix operates on already-contaminated counters. This is a separate bug (status aliasing) but the O2 implementation should not assume the counters are clean.

### O3 — Retyping Is a Behavioral Change

**This is not a label fix.** Refresh dispatches handler selection by `source_type`, not `fetch_method`:

- `URL_LIST` → `_handle_url_list` → calls `read_url` directly
- `AUTHENTICATED_WEB` → `_handle_authenticated_web` → uses injected content fetcher selected by `fetch_method`

Retyping direct-ingest HTTP sources from `AUTHENTICATED_WEB` to `URL_LIST` switches the handler path. For `fetch_method="http"` sources, both paths ultimately do HTTP GET, but via different code with different metadata stamps (authenticated_web vs url origin metadata) and different error handling patterns. The functional equivalence is narrow and fragile.

Additional evidence against retyping:
- `resolve_by_url` keys off `config.url` and `name+scope` is unique, so duplicate source creation from mixed types is not a real risk — the identity rules prevent it regardless of type
- Existing tests (`test_direct_ingest_delta.py`) explicitly expect `AUTHENTICATED_WEB` for HTTP direct-ingest sources

**Recommendation:** Keep `AUTHENTICATED_WEB` for direct-ingest HTTP sources. The semantic mismatch is real but harmless — `fetch_method="http"` already communicates the actual fetch behavior. A retype should only happen if there's a functional reason (e.g., the AUTHENTICATED_WEB handler gains browser-specific behavior that breaks plain HTTP sources). No migration needed.

### O4 — Critical: Neither Cascade Is Complete

**This is the most significant data integrity finding in this plan.** Two cascade implementations exist, each incomplete:

| Property | `source_store.delete_cascade()` | `document_store.delete_source_cascade()` |
|----------|--------------------------------|------------------------------------------|
| SQLite tables | All 7 (entities, edges, chunks, document_status, documents, source_pages, knowledge_sources) | 6 (not knowledge_sources) |
| Qdrant vectors | **NO** — skips vector cleanup entirely | **YES** — via `delete_chunk_embeddings` (best-effort) |
| Source row deletion | YES | NO |
| Transaction boundary | Single `commit()` | N+1 commits (one per document + one for source_pages) |

Neither method is currently called from the MCP layer — both are dead code waiting for O4 to wire them. The `remove_source` MCP tool **must not** wire directly to `source_store.delete_cascade()` as currently written. That path leaves orphaned vector embeddings in Qdrant permanently.

**Correct composition for the MCP tool:**
1. Call `document_store.delete_source_cascade(source_id)` — cleans vectors + docs + pages
2. Delete the `knowledge_sources` row (either via direct SQL or by extending the document_store method)

Or preferably: fix `source_store.delete_cascade` to call `delete_chunk_embeddings` for each document's chunks before deleting the SQLite rows, keeping its single-commit transaction advantage.

**Qdrant orphan risk is real but bounded:**
- `delete_chunk_embeddings` is best-effort — it catches all exceptions with `logger.debug`. A Qdrant failure leaves orphaned vectors while SQLite records are already deleted.
- The existing integrity audit (`integrity.py`) does not check for Qdrant vector orphans. It only audits SQLite-level orphans (chunks, entities, edges, document_status). There is no detection mechanism for vector-level inconsistency.
- Orphaned vectors are inert (they consume space but don't corrupt search results, since search joins on chunk IDs that no longer exist in SQLite). This makes the risk tolerable but it must be explicitly acknowledged and documented.

## Key Trade-offs

| Trade-off | Position |
|-----------|----------|
| Four-state update vs. simpler binary (success/failure) | Four-state is necessary. Binary hides the "source checked but unchanged" vs "all items failed" distinction, which is the whole point of O2. |
| Keep `AUTHENTICATED_WEB` typing vs. retype to `URL_LIST` | Keep current typing. Handler dispatch is by source_type; retyping changes behavior, not just labels. |
| Single-commit cascade (no vectors) vs. best-effort vectors (fragmented commits) | Prefer single-commit with added vector cleanup. The SQLite transaction integrity of `source_store.delete_cascade` is better; extend it with vector cleanup rather than switching to the fragmented document_store path. |
| Explicit Qdrant orphan detection vs. accept inert orphans | Accept inert orphans for now but add source-level and vector-level orphan checks to `integrity.py` as a follow-up. |

## Warnings

1. **Do not wire `remove_source` to `source_store.delete_cascade()` without adding vector cleanup.** This is the single most important data integrity constraint in this plan.
2. **Do not assume refresh counters are clean.** Status aliasing in `_record_ingest_outcome` contaminates counts before `_update_source_record` sees them.
3. **Do not retype direct-ingest sources as a cosmetic fix.** It switches handler dispatch paths and changes metadata stamps.
4. **The "empty no-op" state conflates benign no-work with silent misconfiguration.** The O2 fix should at minimum log a warning when all counters are zero, even if it preserves the previous `last_error`.

## Confidence

**0.80**

Evidence is strong for the critical findings (Qdrant orphan risk, handler dispatch by source_type). The four-state model is well-grounded in code but the "empty no-op" bucket remains semantically ambiguous — three different code paths produce it. The O1 and O3 assessments are straightforward with clear code evidence.
