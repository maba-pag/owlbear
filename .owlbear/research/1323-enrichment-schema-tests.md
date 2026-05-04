# Enrichment Schema Tests — Research

> **Owning task:** #1323 — P1-07: Tests — Enrichment schema (state column, claim table, edge uniqueness)
> **Date:** 2026-05-04 **Status:** Complete

## 1. Context and Question

Task #1323 is a TDD RED phase task: write tests that verify schema additions defined in Brief §4.4. Tests must FAIL until #1324 implements the schema changes. The schema additions are:

1. `enrichment_state TEXT DEFAULT 'pending'` column on `chunks` table (values: pending, claimed, enriched)
2. `claimed_at TEXT` column on `chunks` table (lease timestamp)
3. `reviewed_pairs` table with columns: entity_name, source_a, source_b
4. `document_id TEXT` column on `edges` table (for provenance-aware uniqueness)
5. UNIQUE constraint on edges: `UNIQUE(source_id, target_id, relation, document_id)` (D17)

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/knowledge/src/owlbear_knowledge/schema.py` | 1.0 | Current schema v10, migration pattern, `init_db()` API |
| 2 | `.owlbear/briefs/draft-knowledge-activation/brief.md` §4.4 | 1.0 | Exact column/table specs, D17 constraint |
| 3 | `tests/test_qdrant_source_identity_1319.py` | 0.9 | Sibling test pattern: in-memory SQLite + `init_db()` |
| 4 | `serve/knowledge/tests/test_graph_store_counts.py` | 0.8 | Existing schema test fixture pattern |

## 3. Analysis

### Current Schema State (v10)

| Table | Relevant columns | Notes |
|-------|-----------------|-------|
| chunks | consolidated INTEGER DEFAULT 0 | Legacy ConsolidationService flag — NOT enrichment |
| edges | NO document_id, NO UNIQUE constraint | Only: id, source_id, target_id, relation, weight, metadata, created_at, scope |
| (no reviewed_pairs table) | — | Does not exist yet |

### Test Approach

**Pattern:** Use `PRAGMA table_info(table)` and `PRAGMA index_list(table)` on an in-memory SQLite DB after `init_db()` to verify schema structure.

| AC | Test method | What it verifies |
|----|------------|-----------------|
| AC1 | `PRAGMA table_info(chunks)` → check for `enrichment_state` col with TEXT type | Column exists |
| AC2 | Assert both `consolidated` AND `enrichment_state` present, different names | Separate columns |
| AC3 | `PRAGMA table_info(chunks)` → check for `claimed_at` col with TEXT type | Lease column |
| AC4 | `PRAGMA table_info(reviewed_pairs)` → check entity_name, source_a, source_b | Table + columns |
| AC5 | `PRAGMA index_list(edges)` + `PRAGMA index_info(idx)` for UNIQUE constraint | D17 uniqueness |
| AC6 | INSERT chunk without enrichment_state → SELECT → verify default = 'pending' | Default value |

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Schema version number unknown | Low | Tests verify column presence, not version number |
| UNIQUE constraint naming unknown | Low | Iterate all indexes, check column composition |
| Edge `document_id` could be TEXT or TEXT REFERENCES | Low | Brief says TEXT; test column existence only |

## 4. Recommendation

**Approach:** Direct schema introspection tests using SQLite PRAGMA statements after `init_db()`. No mocking needed — real in-memory DB, real schema initialization.

**Confidence:** 0.92 — straightforward schema testing, well-established pattern from sibling tasks, all specs documented in brief.

**Challenge:** SKIPPED — trivial TDD RED test task with no design decisions. All specs come directly from the approved brief.

## 5. Follow-up Tasks

None needed — #1324 (implementation) already exists as the TDD pair.
