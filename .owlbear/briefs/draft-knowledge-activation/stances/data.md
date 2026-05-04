# Data Quality Stance — Knowledge Engine Activation

## Data Quality Stance

The converged approach's architecture — pull-based enrichment workers, deterministic consolidation candidates, dual-purpose `store_enrichment` — is the right shape. The schema is not ready for it. Six gaps must be addressed in the Brief; three are critical.

## Schema and Validation Reasoning

### 1. Phase 2 Consolidation SQL References Non-Existent Schema (CRITICAL)

The consolidation candidate SQL in D14 references `entities.source_id`. This column does not exist. Source ownership is resolved indirectly: `entities.document_id → documents.source_id`. The SQL must JOIN through `documents` to resolve source.

Additionally, the SQL emits entity-to-entity rows, but D14 defines the review unit as **source-pair per entity name** with all relevant chunks from both sources returned inline. The actual query shape must GROUP BY `(canonical_name, source_a, source_b)` and aggregate chunk content — not return one row per entity pair.

A `reviewed_pairs` table (or equivalent) does not exist in schema v9. Without it, `get_consolidation_candidates` returns the same candidates indefinitely. This table must be designed as part of the Brief.

Required additions:
- `reviewed_pairs` table: `(entity_name TEXT, source_a TEXT, source_b TEXT, reviewed_at TEXT, PRIMARY KEY (entity_name, source_a, source_b))`
- Consolidation query must JOIN through documents for source resolution and GROUP BY the review unit

### 2. Enrichment State Collides with Existing `consolidated` Semantics (CRITICAL)

`chunks.consolidated` (INTEGER 0/1) already means "batched into a consolidation insight" in current `consolidation.py`. The proposed Phase 1 enrichment workflow (entity extraction per chunk) is a **separate lifecycle track**:

| Track | States | Meaning |
|-------|--------|---------|
| Entity extraction (Phase 1) | pending → in_progress → enriched / failed | Has this chunk had entities extracted? |
| Consolidation insight (legacy) | 0 → 1 | Was this chunk included in a consolidation batch? |

Using `consolidated` for both corrupts existing semantics. A new column (`enrichment_state TEXT DEFAULT 'pending'`) or a separate tracking table is required.

### 3. Parallel Worker Queue Contract is Half-Specified (CRITICAL)

The Brief specifies `get_next_batch` marks chunks in-progress for 4-6 parallel workers. Two halves of the queue contract:

**Atomic claim (addressed in approach):** SELECT + UPDATE must be wrapped in an IMMEDIATE transaction to prevent two workers from claiming the same batch. SQLite's DEFERRED isolation does not prevent this.

**Lease expiry (not addressed):** If a worker crashes or VS Code session closes, in-progress chunks must revert to pending after a timeout. The research notes mention "unfinished chunks revert to unprocessed on timeout" but no mechanism is specified. Required: `claimed_at TIMESTAMP` column + periodic reaper query or stale-check in `get_next_batch` itself:

```sql
UPDATE chunks SET enrichment_state = 'pending'
WHERE enrichment_state = 'in_progress'
AND claimed_at < datetime('now', '-10 minutes')
```

### 4. `store_enrichment` Lacks Unit-of-Work Integrity (HIGH)

Current write plumbing inserts entities and edges one row at a time, committing incrementally. For the dual-purpose `store_enrichment`:

- **Phase 1:** A batch of 20 chunks produces ~N entities + M edges per chunk. If the worker fails mid-batch, some chunks are partially enriched (entities stored, edges missing). No way to detect or recover.
- **Phase 2:** A consolidation decision (match or dismiss) must be atomic with the `reviewed_pairs` insert. Partial writes mean the candidate may be consumed from the queue but the decision not recorded — or vice versa.

Required: batch-level transaction wrapping all writes for a single `store_enrichment` call. UPSERT or INSERT-OR-IGNORE for entity/edge writes to handle retries.

Edge deduplication is nuanced: inter-doc edges carry provenance metadata (document-pair, source-pair). A naive `UNIQUE(source_id, target_id, relation)` would collapse distinct evidence. Deduplication must be provenance-aware — e.g., `UNIQUE(source_id, target_id, relation, document_id)` or similar.

### 5. Scope Contamination is Present, Not Future (HIGH)

All tables have `scope` columns and scope indexes. But edges default to `scope = "global"` and the inter-doc graph builder does not scope-filter when deduplicating. This means enrichment in a scoped context can produce cross-scope edges or miss same-scope duplicates.

The Brief assumes global scope (single user, one laptop), which is correct for Phase 1. But the scope columns and deferred scope tools mean this assumption should be stated explicitly as a simplification, and enrichment queries should include `WHERE scope = ?` to prevent contamination if scope tools are activated later.

### 6. Canonical Name Matching Strength (MEDIUM)

The existing canonical-name rule (lowercase, whitespace-collapse, article-strip, edge-punct-trim) handles `"Authentication Service"` → `"authentication service"`. It does NOT handle:
- Jira-style IDs: `AUTH-1234` vs `Authentication Service`
- Kebab-case: `auth-service` vs `authentication_service`
- Abbreviations: `PDS` vs `Porsche Design System`

For the target corpus (SharePoint requirements ↔ Jira tickets ↔ Confluence standards), these variations are the norm, not edge cases. The deterministic SQL will produce false negatives.

This is acceptable for Phase 1 (the agent sees the misses and can manually bridge them). But the Brief should acknowledge this as a known limitation and note that Phase 2 may need fuzzy matching or LLM-assisted candidate expansion.

## Key Trade-offs

| Trade-off | Position |
|-----------|----------|
| New enrichment_state column vs. separate tracking table | Column preferred — co-located with chunk data, simpler queries, avoids junction table overhead. Add `claimed_at` for lease expiry. |
| SQL-native canonical_name vs. Python-side matching | Store `canonical_name` as a persisted column (denormalized). The enrichment pipeline will query it in SQL hot paths; computing it in Python defeats SQL-based candidate generation. Migration cost is one ALTER TABLE + backfill UPDATE. |
| Strict edge deduplication vs. provenance preservation | Provenance-aware deduplication. Don't collapse edges with different evidence chains. |
| Scope filtering now vs. later | Explicit `scope = 'global'` in all enrichment queries now. Zero cost, prevents future contamination. |

## Warnings

1. **Schema migration versioning.** Schema is at v9 with an explicit migration ladder. Every new column/table needs a v10 migration step with proper ordering. This is not just DDL — it's test surface too.
2. **The inter-doc graph builder's refresh path** only schedules work for the newly ingested document's entities, and drops same-document pairs. The current code path cannot produce cross-document candidates. The proposed consolidation SQL replaces this path entirely — the Brief should make this explicit rather than framing it as "using existing infrastructure."
3. **Re-ingest during active enrichment** is a race: `delete_document_data()` removes old chunks while workers may hold stale chunk IDs. Current code deletes entities before chunks (correct order), but workers with in-flight batch references will try to write entities for deleted chunks. Entity provenance columns (`document_id`, `chunk_id`) are plain TEXT — no FK violation fires. Silent orphans accumulate. Mitigation: `get_next_batch` should skip chunks whose `document_id` is absent from `documents`.

## Confidence

**0.82**

Schema gaps are verified against actual code (schema v9, `graph_store.py`, `document_store.py`, `consolidation.py`, `models.py`). The three critical items (consolidation SQL shape, enrichment state collision, worker queue contract) are demonstrated gaps, not speculative. The two high items (unit-of-work integrity, scope contamination) are evidenced from current write paths. The canonical-name weakness is medium because the current rule is adequate for initial activation — it becomes a real problem only at cross-source scale.

Residual uncertainty: edge provenance deduplication strategy needs architect input — I've identified the tension but the right constraint shape depends on how provenance will be queried downstream.
