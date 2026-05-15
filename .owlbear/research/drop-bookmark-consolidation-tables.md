# Drop Bookmarks and Consolidations Tables from Knowledge Schema

> **Owning task:** #1583 — Drop bookmarks and consolidations tables from knowledge schema
> **Date:** 2026-05-15 **Status:** Complete

## 1. Context and Question

Research #1576 classified `bookmarks` and `consolidations` tables as **retire** — zero active write/read paths. This task covers the schema-side cleanup: remove DDL, add a v12 migration that drops both tables, bump schema version.

Key question: what is the safest migration approach given the existing v1→v11 chain?

## 2. Sources Studied

| # | Source | Path | Relevance |
|---|--------|------|-----------|
| 1 | schema.py (current) | `serve/knowledge/src/owlbear_knowledge/schema.py` | 1.0 |
| 2 | #1576 research doc | `.owlbear/research/classify-inactive-knowledge-surfaces.md` | 1.0 |
| 3 | test_enrichment_schema.py (v10 fixture) | `tests/test_enrichment_schema.py` | 0.9 |
| 4 | SQLite DROP TABLE docs | sqlite.org/lang_droptable.html | 0.8 |
| 5 | consolidation.py (dead consumer) | `serve/knowledge/src/owlbear_knowledge/consolidation.py` | 0.7 |

## 3. Analysis

### 3.1 Current State

| Item | Location | Lines |
|------|----------|-------|
| `_CREATE_BOOKMARKS` DDL | schema.py:123–137 | 15 |
| `_CREATE_CONSOLIDATIONS` DDL | schema.py:140–148 | 9 |
| `_migrate_v6_to_v7` (creates bookmarks) | schema.py:249–258 | 10 |
| `_migrate_v7_to_v8` (creates consolidations) | schema.py:261–271 | 11 |
| `init_db` creates both tables | schema.py:373–374 | 2 |
| `init_db` creates bookmark indexes | schema.py:453–455 | 3 |

No FK references from other tables to `bookmarks` or `consolidations`.

### 3.2 Migration Strategy

| Approach | Pros | Cons | Confidence |
|----------|------|------|------------|
| **A: Add v12 DROP, keep v7/v8 intact** | Immutable migration history; correct for any source version | v7/v8 do wasted CREATE for pre-v7 DBs upgrading straight through | 0.90 |
| B: Modify v7/v8 to skip creation | Less runtime work | Breaks migration immutability principle; complicates reasoning about chain | 0.30 |
| C: Collapse old migrations | Fewer functions | Destroys audit trail; high risk for edge cases | 0.15 |

**Recommendation: Approach A** (confidence 0.90). Keep v7 and v8 migrations immutable. Add `_migrate_v11_to_v12` that issues `DROP TABLE IF EXISTS bookmarks` and `DROP TABLE IF EXISTS consolidations`. This is the standard SQLite migration pattern and matches how existing migrations in this codebase work.

### 3.3 Implementation Checklist

1. Bump `_SCHEMA_VERSION` from 11 → 12.
2. Remove `_CREATE_BOOKMARKS` and `_CREATE_CONSOLIDATIONS` DDL constants.
3. Remove `conn.execute(_CREATE_BOOKMARKS)` and `conn.execute(_CREATE_CONSOLIDATIONS)` from `init_db`.
4. Remove `idx_bookmarks_url_scope` and `idx_bookmarks_scope` index creation from `init_db` tail.
5. Add `_migrate_v11_to_v12` — `DROP TABLE IF EXISTS bookmarks; DROP TABLE IF EXISTS consolidations`.
6. Register `(12, _migrate_v11_to_v12)` in `_apply_migrations`.
7. Update module docstring to remove bookmarks/consolidations from table list.
8. `chunks.consolidated` column: **keep** — column removal requires table rebuild, out of AC scope, and #1582 handles the module that uses it.

### 3.4 Test Impact

| Test file | Impact | Action needed |
|-----------|--------|---------------|
| `test_enrichment_schema.py` | v10 fixture includes both tables + indexes; tests v10→v11 migration | Add v10→v12 or v11→v12 migration test verifying tables are dropped |
| `test_browser_fetcher_wiring.py` | Patches `BookmarkStore`/`ConsolidationService` in server.py | No impact — schema-only change; #1582 handles |
| `test_knowledge_guard_removal_1579.py` | Same patches | No impact |
| `test_mcp_knowledge_tool_surface.py` | Tests tool surface, not schema | No impact |

### 3.5 Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing DB has data in tables | Very low — #1576 confirmed no write path | `DROP TABLE IF EXISTS` is data-destructive but AC says "safe: no production data" |
| Migration runs on pre-v7 DB | Low | v7 creates → v12 drops; functionally correct |
| `init_db` on fresh DB creates broken refs | None | No FKs reference these tables |

## 4. Recommendation

Straightforward T1 cleanup. Approach A (add v12 migration, keep v7/v8 immutable). Confidence: **0.90**.

Challenge: SKIPPED — single viable approach, no alternatives worth challenging.

## 5. Follow-up Tasks

No additional follow-up tasks needed. The three sibling tasks from #1576 already cover the full scope:
- #1582 — Retire dead code modules (Phases A+B)
- #1583 — This task (Phase C)
- #1584 — Label deferred stubs (Phase D)
