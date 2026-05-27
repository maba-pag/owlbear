# Consolidation Migration: CP1 Architectural Conflict

> **Owning task:** #1899 — Knowledge: Migrate consolidation logic into EnrichmentStore (Phase B1)
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task #1899 asks to migrate `_consolidation.py` (539 LOC) from mcp-knowledge into `EnrichmentStore` (knowledge package). However, the v2 knowledge architecture (CP1 — Canonical Identity) explicitly eliminates consolidation workflows. Should this code be migrated into the v2 layer, or deleted entirely?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/knowledge/src/owlbear_knowledge/protocols/DESIGN_DECISIONS.md` — CP1 | Architecture | 1.0 |
| `serve/knowledge/src/owlbear_knowledge/protocols/ARCHITECTURE.md` — CP1 | Architecture | 1.0 |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_consolidation.py` (539 LOC) | Codebase | 1.0 |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — call sites | Codebase | 1.0 |
| `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py` — target | Codebase | 0.9 |
| `.owlbear/research/mcp-knowledge-v2-migration.md` — parent research | Prior research | 0.8 |

## 3. Analysis

### 3.1 CP1 Contradiction

CP1 (DESIGN_DECISIONS.md) states:
> "Deterministic entity identity via `(canonicalize_name(name), entity_type)`. Two extractions producing the same canonical name + type ARE the same entity row. No SAME_AS edges, no consolidation workflows."

The `_consolidation.py` module implements the cross-source entity-pair review workflow that CP1 explicitly retires.

### 3.2 Table Architecture Conflict

| Component | Tables used | Layer |
|-----------|-------------|-------|
| `_consolidation.py` queries | `entities`, `edges`, `documents`, `knowledge_sources`, `chunks` | Legacy (schema.py) |
| `EnrichmentStore` operates on | `enrich_queue`, `enrich_batches`, `enrich_extractions` + GraphStore protocol | v2 |
| `SqliteGraphStore` manages | `graph_entities`, `graph_edges`, `graph_evidence`, `graph_aliases` | v2 |

Consolidation queries legacy `entities`/`edges` — tables that Phase B2 will remove. Moving this code into the v2 layer would either require:
- EnrichmentStore to query dying legacy tables (incoherent architecture), or
- Rewriting queries for v2 tables (moot — CP1 means v2 graph has no duplicates to consolidate)

### 3.3 Current Usage (3 call sites in server.py)

| Call site | Function | Impact of deletion |
|-----------|----------|-------------------|
| `get_consolidation_candidates` MCP tool | `_fetch_consolidation_candidate_rows` + `_encode_candidate_id` | Remove tool |
| `store_enrichment` phase-2 branch | `_persist_phase2_enrichment` | Remove branch (chunk_id=None path) |
| `get_stats` | `_count_consolidation_candidates` | Return 0 or remove field |

### 3.4 Test Coverage

Zero dedicated tests for consolidation logic. Only coverage: `test_mcp_knowledge_read_tools_1881.py` asserts `consolidation_candidates_remaining` appears in stats output (and equals 0).

### 3.5 Trade-off Matrix

| Option | Aligns w/ CP1 | Risk | Effort | Confidence |
|--------|---------------|------|--------|-----------|
| **A: Delete consolidation** | Yes | Transitional legacy data loses review tool | Low (~50 LOC removal + stats field) | 0.80 |
| **B: Keep at MCP layer only** | Partial | Dead code persists; can't outlive legacy tables | Low (no change) | 0.55 |
| **C: Migrate to EnrichmentStore** | No | Embeds retired pattern in v2 layer; contradicts CP1 | Medium (~200 LOC new) | 0.25 |

## 4. Recommendation (confidence: 0.80)

**Option A: Delete consolidation entirely.** Rationale:
- CP1 is a settled commitment point; consolidation is explicitly retired
- v2 graph uses canonical identity — no duplicate entities to consolidate
- Zero test coverage means zero regression risk from deletion
- `reviewed_pairs` table remains in schema.py (harmless; cleaned in B2)
- `get_stats` can set `consolidation_candidates_remaining: 0` statically

Challenge: N/A — no challenger invoked; outcome is T3 requiring user decision before any implementation proceeds.

## 5. Follow-up Tasks

Deferred pending DR resolution:
- If Option A: Create task "Delete `_consolidation.py` and consolidation MCP tool" (replaces #1899)
- If Option B: Archive #1899 as superseded; no action needed
- If Option C: Proceed with #1899 as-is (not recommended)
