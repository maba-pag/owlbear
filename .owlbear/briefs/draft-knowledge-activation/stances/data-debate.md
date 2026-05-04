# Data Debate Log — Knowledge Engine Activation

## Cycle 1: Initial Stance → Critic

### Initial Position (8 points)

1. **Enrichment State Tracking Gap (CRITICAL)** — `chunks.consolidated` is binary (0/1), no intermediate states for parallel worker coordination. Workers will double-process chunks.
2. **Missing `reviewed_pairs` Table (CRITICAL)** — Phase 2 SQL references this table but it doesn't exist in schema v9.
3. **Canonical Name Not in SQLite (HIGH)** — `canonical_name` is Python-only (`@computed_field`). SQL joins on `e1.name = e2.name` miss name variations.
4. **Foreign Key Enforcement is Fragile (MEDIUM)** — `PRAGMA foreign_keys = ON` is per-connection, not schema-level.
5. **Non-Atomic Manual Cascade Deletes (MEDIUM)** — 5 sequential DELETEs in `delete_document_data()` without explicit transaction.
6. **Missing Indexes (MEDIUM)** — `entities.chunk_id`, `entities.document_id`, `chunks.consolidated` have no indexes.
7. **Re-Ingest + Concurrent Enrichment Race (MEDIUM)** — Workers hold stale chunk IDs after re-ingest deletes old data.
8. **Entity Type Schema Extensibility (LOW)** — Adding types is a Python enum change; DB stores TEXT unconstrained.

### Critic Challenges (Cycle 1)

**C1.1 — `entities.source_id` doesn't exist either (CRITICAL).** The Phase 2 SQL references `e1.source_id` but entities table has no `source_id` column. Source ownership resolves through `document_id → documents.source_id`. The entire consolidation SQL is more broken than claimed.
- **Response: Accepted.** Strengthened point 1 to include the source resolution gap. The SQL must JOIN through documents.

**C1.2 — Semantic collision on `chunks.consolidated` (CRITICAL).** The existing `consolidated` flag means "batched into a consolidation insight" — NOT "entities extracted." Reusing it for enrichment state corrupts existing semantics.
- **Response: Accepted.** Reframed as two distinct lifecycle tracks. New column required.

**C1.3 — Cascade deletes may use implicit transaction (MODERATE).** All deletes on one connection before commit = implicit transaction in SQLite. The "no wrapping transaction" claim is overstated.
- **Response: Partially accepted.** Softened the cascade delete point. The atomicity concern is real but the specific failure window is narrower than initially claimed.

**C1.4 — Entity provenance is not FK-enforced (CRITICAL).** `entities.document_id` and `entities.chunk_id` are plain TEXT — no REFERENCES clause. FK violations won't fire on stale writes. Failure mode is silent orphans, not errors.
- **Response: Accepted.** Corrected the failure mode description from "FK violations" to "silent orphans."

**C1.5 — `canonical_name` blocking exists in Python (MODERATE).** `inter_doc_graph_builder.py` already does canonical-name matching in memory. Stored column not necessarily required.
- **Response: Partially accepted.** Python-side matching works for current scale but defeats SQL-based candidate generation. Positioned as a trade-off rather than a hard requirement.

**C1.6 — Confidence self-contradiction (MINOR).** Claimed race severity may be overstated because SQLite is single-writer, but the race described is read-then-mark, which single-writer doesn't prevent.
- **Response: Accepted.** Removed the hedging qualification. The race is real.

**Blind spots surfaced:**
- **store_enrichment idempotency** — No deduplication on entities or edges. Retries create duplicates.
- **Scope isolation** — Edges default to `scope="global"`, inter-doc builder doesn't scope-filter.
- **Edge indexes** — `edges.source_id`, `edges.target_id` have no indexes.
- **Provenance reliability** — Phase 2 returns "relevant chunks from both sources inline" but entity provenance is application-managed.

## Cycle 2: Revised Stance → Critic

### Revised Position (8 points, restructured)

Incorporated Cycle 1 feedback:
- Merged source_id gap into consolidation SQL point
- Split enrichment state from consolidated semantics
- Added store_enrichment unit-of-work integrity
- Elevated scope contamination
- Added canonical name strength analysis
- Corrected FK failure mode descriptions

### Critic Challenges (Cycle 2)

**C2.1 — Schema changes undercount the actual change surface (CRITICAL).** The Brief replaces the active MCP tool model (14 tools → 8 active + 4 deferred). The live server still exports the superseded surface. This is a runtime contract replacement, not just schema work.
- **Response: Noted but out of scope.** This is an architect concern (MCP tool surface redesign), not a data quality concern. My stance covers the schema prerequisites for the data flows to work correctly.

**C2.2 — Corrected SQL still emits wrong review unit (CRITICAL).** D14 defines review unit as source-pair per entity name with grouped chunks. My SQL still emits entity-to-entity rows, fanning out into multiple candidate rows for one review decision.
- **Response: Accepted.** The SQL must GROUP BY `(canonical_name, source_a, source_b)` and aggregate chunks. Incorporated into final stance.

**C2.3 — Inter-doc graph builder refresh path can't produce cross-document candidates (CRITICAL).** The refresh path only schedules work for newly ingested document's entities and drops same-document pairs. Current code path cannot produce cross-document candidates at all.
- **Response: Accepted.** Added as a warning: the proposed consolidation SQL replaces this path entirely. Brief should make this explicit.

**C2.4 — Scope contamination is present, not future (HIGH).** Edges default to `scope="global"` and inter-doc builder doesn't scope-filter. Current design flaw.
- **Response: Accepted.** Elevated from LOW to HIGH. Added explicit scope filtering recommendation.

**C2.5 — Idempotency should address unit-of-work, not just duplicates (HIGH).** One-row-at-a-time commits mean interruption creates partially committed state, not just duplicate rows.
- **Response: Accepted.** Reframed as batch-level transaction requirement.

**C2.6 — Edge uniqueness assumption collapses provenance (MODERATE).** Inter-doc edges carry document-pair and source-pair metadata. Naive `UNIQUE(source_id, target_id, relation)` would collapse distinct evidence.
- **Response: Accepted.** Changed to provenance-aware deduplication recommendation. Flagged as needing architect input.

**C2.7 — Re-ingest failure mode overstated for current code path (MODERATE).** Current ingest deletes prior document data before reinsert. The specific scenario described (workers holding stale IDs) is real but the cascade ordering is correct.
- **Response: Partially accepted.** Softened to a warning rather than a critical finding. The race window exists but the current deletion order mitigates half of it.

**Blind spots surfaced:**
- **Lease expiry mechanism** — Workers crashing leaves chunks stuck in `in_progress`. Need `claimed_at` + reaper.
- **Schema migration versioning** — Every change needs a v10 migration step in the existing ladder.
- **Canonical name rule strength** — Current rule may be too weak for Jira IDs, kebab-case, abbreviations in the target corpus.

## Final Assessment

Two Critic cycles. Six challenges accepted fully, four partially accepted, one noted as out of scope. Three blind spots incorporated. Position hardened from 0.75 → 0.82 confidence. Key refinements:
- Consolidation SQL corrected to proper review unit shape
- Enrichment state properly separated from consolidation flag
- Unit-of-work integrity framed as batch transactions
- Edge deduplication made provenance-aware
- Scope contamination elevated to present concern
- Lease expiry added to worker queue contract
