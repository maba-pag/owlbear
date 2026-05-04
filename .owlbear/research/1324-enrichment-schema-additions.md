# Enrichment Schema Additions — Research

> **Owning task:** #1324 — P1-08: Enrichment schema additions (state, claims, edge uniqueness, WAL)
> **Date:** 2026-05-04 **Status:** Complete

## 1. Context and Question

Task #1324 is the TDD GREEN implementation pair for #1323. It must add schema elements to `serve/knowledge/src/owlbear_knowledge/schema.py` so all 21 failing tests pass. The additions are defined in Brief §4.4.

Key question: What's the minimal implementation approach within the existing migration framework?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/knowledge/src/owlbear_knowledge/schema.py` | 1.0 | Current schema v10, migration chain pattern, DDL strings, `init_db()` |
| 2 | `.owlbear/briefs/draft-knowledge-activation/brief.md` §4.4 | 1.0 | Exact spec: enrichment_state, claimed_at, reviewed_pairs, D17 constraint, WAL |
| 3 | `tests/test_enrichment_schema_1323.py` | 1.0 | 21 tests defining exact expected behavior |
| 4 | `serve/knowledge/src/owlbear_knowledge/graph_store.py` L197-214 | 0.8 | `insert_edge()` does NOT include `document_id` — needs downstream update (out of scope) |
| 5 | SQLite docs: ALTER TABLE, WAL mode | 0.9 | ALTER TABLE ADD COLUMN constraints, WAL on :memory: is no-op |

## 3. Analysis

### Current State (v10)

| Table | Relevant schema | Gap |
|-------|----------------|-----|
| chunks | `consolidated INTEGER DEFAULT 0` | Missing: `enrichment_state`, `claimed_at` |
| edges | No `document_id`, no UNIQUE constraint | Missing: `document_id` column, D17 index |
| (reviewed_pairs) | Does not exist | Entire table needed |

### Implementation Approach: Single Migration v10→v11

| Change | DDL | Method |
|--------|-----|--------|
| `enrichment_state` on chunks | `ALTER TABLE chunks ADD COLUMN enrichment_state TEXT DEFAULT 'pending'` | Migration |
| `claimed_at` on chunks | `ALTER TABLE chunks ADD COLUMN claimed_at TEXT` | Migration |
| `document_id` on edges | `ALTER TABLE edges ADD COLUMN document_id TEXT` | Migration |
| Edge UNIQUE index | `CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_unique_tuple ON edges(source_id, target_id, relation, document_id)` | Migration |
| `reviewed_pairs` table | New `_CREATE_REVIEWED_PAIRS` DDL + `conn.execute()` | Migration + `init_db()` |
| WAL mode | `PRAGMA journal_mode=WAL` in `init_db()` | Direct |
| Version bump | `_SCHEMA_VERSION = 11` | Constant |

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| UNIQUE index on edges with existing NULL document_id rows | Low | Fresh DBs: no existing rows. Migration: NULL != NULL in SQLite uniqueness (NULLs are distinct), so existing edges with NULL document_id won't conflict. |
| WAL on `:memory:` has no effect | Low | Tests use in-memory — WAL PRAGMA is safe but no-op. AC doesn't require a WAL test (none in #1323). File-backed usage gets WAL automatically. |
| DDL changes in `_CREATE_CHUNKS`/`_CREATE_EDGES` | None | Both fresh-DB creation AND migration must add columns — update DDL strings + migration function. |
| `insert_edge()` doesn't pass `document_id` | Low (out of scope) | Column is nullable TEXT. Existing code continues to work — NULL is acceptable default. Layer 2 tools will pass it. |

### Checklist of File Changes

1. **`schema.py`** — sole file to modify:
   - `_SCHEMA_VERSION`: 10 → 11
   - `_CREATE_CHUNKS`: add `enrichment_state TEXT DEFAULT 'pending'` and `claimed_at TEXT`
   - `_CREATE_EDGES`: add `document_id TEXT`
   - New `_CREATE_REVIEWED_PAIRS` DDL constant
   - New `_migrate_v10_to_v11()` function
   - Update `_apply_migrations()` to call v10→v11
   - Add UNIQUE index creation in `init_db()` (for fresh DBs)
   - Add `PRAGMA journal_mode=WAL` in `init_db()` (before foreign_keys)
   - Add `conn.execute(_CREATE_REVIEWED_PAIRS)` in `init_db()`

## 4. Recommendation

**Approach:** Single schema migration function following the exact pattern of v9→v10. Straightforward ALTER TABLE + CREATE TABLE + CREATE UNIQUE INDEX. WAL as PRAGMA.

**Confidence:** 0.95 — well-defined spec, existing pattern to follow, 21 tests provide precise acceptance criteria, no design decisions needed.

**Challenge:** SKIPPED — trivial implementation task with no design choices. All specs are defined by the brief and locked in by the RED tests.

## 5. Follow-up Tasks

None needed — #1324 itself IS the implementation follow-up. No design decisions, no ambiguity.
