# Phase 2 Consolidation Tool Tests — Research

> **Owning task:** #1329 — P2-13: Tests — Phase 2 + stats tools
> **Date:** 2026-05-06 **Status:** Complete

## 1. Context and Question

Task #1329 requires RED-phase tests for two Phase 2 tools: `get_consolidation_candidates` and an expanded `get_stats`. These tests must fail until #1330 implements the tools. The question: what test structure, assertions, and patterns produce discriminating tests that can only pass with correct implementations?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|---------------|
| 1 | `tests/test_mcp_knowledge_enrichment_tools_1327.py` | 1.0 | Test patterns: fixtures, mock context, SQL trace, helper functions |
| 2 | `tests/test_enrichment_schema_1323.py` | 0.9 | Schema test patterns, column assertions |
| 3 | `.owlbear/briefs/draft-knowledge-activation/brief.md` §4.4 | 1.0 | Spec: consolidation SQL, reviewed_pairs, get_stats fields |
| 4 | `serve/mcp-knowledge/src/.../server.py` L287–350 | 1.0 | Phase 1 store_enrichment impl — pattern for Phase 2 extension |
| 5 | `serve/knowledge/src/.../schema.py` L170–180 | 0.9 | reviewed_pairs table schema (PK: entity_name, source_a, source_b) |
| 6 | Task #1330 AC | 1.0 | Builder acceptance criteria — tests must cover these exactly |

## 3. Analysis

### 3.1 Test Structure for `get_consolidation_candidates`

The function must: (a) find entity names appearing in 2+ sources, (b) exclude pairs in `reviewed_pairs`, (c) exclude pairs with existing cross-source edges, (d) return entity_name + chunks from both sources inline.

**Testing approach:** Directly test the function against in-memory SQLite with `init_db`. Insert entities across sources, then verify SQL produces correct candidates.

| Test case | Discriminating proof | AC |
|-----------|---------------------|-----|
| Entity in 2 sources → returned | Only multi-source entities surface | AC1 |
| Entity in 1 source → excluded | Single-source filtered out | AC1 |
| Entity with reviewed_pair → excluded | LEFT JOIN + WHERE NULL or NOT IN | AC2 |
| Entity with cross-source edge → excluded | Edge existence check | AC2 |
| Returns entity_name + chunk text from both sources | Inline content verified | AC3 |
| limit parameter respected | Only N results returned | AC1 |
| Deterministic ordering (same result on repeat) | ORDER BY produces stable results | AC1 |

### 3.2 Test Structure for `store_enrichment` Phase 2 Mode

Phase 2 extends `store_enrichment` with consolidation semantics:
- **With edges:** writes cross-source edges (normal store_enrichment behavior)
- **With empty edges:** marks the entity-pair in `reviewed_pairs` (dismissal)

| Test case | Discriminating proof | AC |
|-----------|---------------------|-----|
| Consolidation call with edges → cross-source edges written | Edges in DB after call | AC4 |
| Empty edges → reviewed_pairs row inserted | reviewed_pairs populated | AC5 |
| Dismissed pair no longer returned by candidates | Integration: dismiss then re-query | AC5 |
| New source → new candidate pairs appear | Insert new source entities → candidates grow | AC6 |
| Old dismissals preserved across new ingests | reviewed_pairs rows survive new source add | AC6 |

### 3.3 Test Structure for `get_stats` (Expanded)

Current `get_stats` returns `{documents, entities, edges}`. Phase 2 spec requires: total sources, total chunks, chunks enriched/total, consolidation candidates remaining.

| Test case | Discriminating proof | AC |
|-----------|---------------------|-----|
| Returns total_sources count | Matches knowledge_sources row count | AC7 |
| Returns total_chunks count | Matches chunks row count | AC7 |
| Returns chunks_enriched / total ratio | Numerator = enrichment_state='enriched' count | AC7 |
| Returns consolidation_candidates_remaining | Matches get_consolidation_candidates count | AC7 |
| Stats update after enrichment progress | Before/after comparison | AC7 |

### 3.4 Import Strategy

Tests will import `get_consolidation_candidates` and an expanded `get_stats` from `owlbear_mcp_knowledge.server`. Since these don't exist yet → `ImportError` in RED phase (same pattern as #1327 tests).

**Alternative:** Import the existing `get_stats` and test for new fields → `KeyError`/assertion fail (less clean but works). Prefer `ImportError` approach — import a new `get_consolidation_candidates` function and test expanded `get_stats` return shape.

## 4. Recommendation

**Approach:** Single test file `tests/test_mcp_knowledge_phase2_tools_1329.py` following the exact patterns from `test_mcp_knowledge_enrichment_tools_1327.py`:
- Same fixtures (`conn`, `_make_mcp_ctx`, `_insert_source`, `_insert_document`, `_insert_chunk`, `_insert_entity`)
- Add `_insert_reviewed_pair` and `_insert_cross_source_edge` helpers
- Import `get_consolidation_candidates` from server (will fail RED until #1330)
- Test expanded `get_stats` return type for new fields

**Confidence:** 0.88 — well-constrained by brief spec and existing test patterns.

Challenge: FALLBACK — trivial test-structure research, no design trade-offs requiring adversarial review.

## 5. Follow-up Tasks

Task #1329 itself IS the test-writer task. No additional follow-ups needed — the builder task #1330 already depends on it and has matching AC.
