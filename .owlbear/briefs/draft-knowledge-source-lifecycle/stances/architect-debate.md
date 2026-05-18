# Architect — Critic Debate Log

## Cycle 1

### Draft Position Summary

- O1–O4 are structurally independent but O2 should ship before O1 (ordering dependency)
- Q1: Don't retype direct-ingest sources — `fetch_method` already disambiguates
- Q2: Confirmed Qdrant orphan bug — refactor `delete_cascade` to delegate to `document_store.delete_document_data()`
- Q3: Three-way distinction (`refreshed > 0`, `all failed`, `empty source`) is correct
- `remove_source` is safe with `destructiveHint=True`
- Confidence: 0.82

### Critic Challenges (5 critical, 1 moderate, 3 blind spots)

**C1 (moderate) — O2-before-O1 ordering is weaker than claimed.** The dishonest data already persists at write time via `_update_source_record`, before any list exposure. O1 makes it visible but doesn't create the problem. This is a rollout recommendation, not a structural dependency.

**C2 (critical) — URL_LIST already exists.** `SourceType.URL_LIST` is a first-class enum value with its own refresh handler `_handle_url_list`. Direct-ingest HTTP sources typed as `AUTHENTICATED_WEB` go through `_handle_authenticated_web` which requires a content fetcher injection, when `_handle_url_list` does plain HTTP via `_intake.read_url()` without one. The "don't retype" position was factually wrong on two counts: (a) `URL_LIST` is not a hypothetical new type, and (b) the typing mismatch causes behavioral routing through the wrong handler.

**C3 (critical) — Qdrant cleanup is best-effort.** `delete_chunk_embeddings` swallows all exceptions via `except Exception`. Delegating to `delete_document_data` does not close the orphan class — it adds best-effort cleanup, not guaranteed cleanup. Framing the fix as "closing the orphan risk" overstates what the code actually delivers.

**C4 (critical) — Transaction fragmentation.** `source_store.delete_cascade` uses a single `commit()` at the end. `document_store.delete_document_data` commits per document. Naive delegation changes failure behavior from all-or-nothing to partial-progress-may-be-durable, while creating split ownership of source-level deletion.

**C5 (critical) — IngestResult status coercion.** `_record_ingest_outcome` coerces unknown statuses (including `cancelled`, `blocked`) into `"ok"`, counting them as successes before the proposed refreshed/failed/empty matrix. The three-way distinction solves a narrower problem than the code actually has.

**C6 (moderate) — last_error is an overloaded prose field.** The proposed three-way state distinction collapses into string parsing on one text column. The architecture doesn't carry structured states.

**Blind spots:**
- O1 exposes raw exception strings (possibly containing URLs/paths) via `last_error`
- Inline/manual sources are not recoverable after cascade delete — no fetch path to reconstruct content
- O1 is an MCP tool-shape change (TypedDict expansion) that existing tests codify

### Revisions Made

**C1 — Accepted (softened).** Changed "O2 must ship before O1" to "strongly recommended." The ordering is about observability quality, not structural correctness.

**C2 — Accepted (reversed position).** Q1 position changed from "don't retype" to "retype to URL_LIST." The existing `URL_LIST` type and `_handle_url_list` handler are the correct path for plain HTTP sources. This is a bug fix, not a cosmetic change.

**C3 + C4 — Accepted (changed fix approach).** Abandoned the "delegate to `delete_document_data`" recommendation. New approach: add best-effort Qdrant vector cleanup directly to `delete_cascade`, collecting chunk IDs before the SQL cascade, then deleting vectors while preserving the single-commit SQLite transaction. Explicitly frame as best-effort, consistent with existing cleanup patterns.

**C5 — Partially accepted.** The IngestResult coercion is a separate concern from O2's `_update_source_record` fix. The three-way distinction at the RefreshResult level is still correct and useful. Noted the coercion as a pre-existing issue that O2's scope does not cover.

**C6 — Acknowledged, not revised.** The `last_error` column is prose, yes. But the primary fix in O2 is the conditional `last_refreshed_at` update, not structured state in `last_error`. The prose distinction between "all URLs failed: ..." and "no content URLs configured" is adequate for operator diagnostics at this scale.

**Blind spots — Incorporated:**
- Added warning about `last_error` sanitization for O1
- Added non-recoverability note for inline sources in O4 section
- Noted MCP contract expansion as additive (backward-compatible for TypedDict consumers)

### Post-Revision Confidence: 0.78
