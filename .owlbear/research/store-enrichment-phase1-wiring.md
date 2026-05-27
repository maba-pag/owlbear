# MCP store_enrichment Phase-1 Wiring to submit_extractions

> **Owning task:** #1892 — Knowledge: MCP wire store_enrichment phase-1 to submit_extractions
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task 1892 replaces the old `_persist_phase1_enrichment()` helper (direct SQL against `entities`/`edges`/`chunks` tables) with `EnrichmentStore.submit_extractions()` (protocol-conformant store method using graph upserts + evidence + queue management). Key questions: what dict-to-model parsing is needed, are there enum/schema mismatches, and what error handling changes?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:211-275` | Codebase | Current store_enrichment tool (0.95) |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_enrichment.py:295-417` | Codebase | Old _persist_phase1_enrichment (0.95) |
| `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:306-423` | Codebase | New submit_extractions (0.95) |
| `serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py:52-92` | Codebase | ExtractedEntity/ExtractedRelation models (0.95) |
| `serve/knowledge/src/owlbear_knowledge/protocols/common.py:53-92` | Codebase | Protocol EntityType/RelationType enums (0.90) |
| `serve/knowledge/src/owlbear_knowledge/models.py:15-39` | Codebase | Legacy EntityType enum (0.85) |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py:48-80` | Codebase | _extract_entity_type/_extract_relation (0.85) |

## 3. Analysis

### 3.1 Dict-to-Model Field Mapping

| Input dict field | Model field | Notes |
|-----------------|-------------|-------|
| entity `id` or `local_ref` | `ExtractedEntity.local_ref` | Use provided value or generate UUID |
| entity `name` | `.name` | Required, strip whitespace |
| entity `entity_type` or `type` | `.entity_type` | Must use PROTOCOL enum (see §3.2) |
| entity `description` | `.description` | Default `""` |
| entity `confidence` | `.confidence` | Default `1.0`, range [0,1] |
| entity `metadata` | `.metadata` | Default `{}` |
| edge `source_ref` or `source_id` | `ExtractedRelation.source_ref` | Must match entity local_ref |
| edge `target_ref` or `target_id` | `.target_ref` | Must match entity local_ref |
| edge `relation` or `relationship` | `.relation_type` | Must use PROTOCOL enum |
| edge `weight` | `.weight` | Default `1.0` |
| edge `confidence` | `.confidence` | Default `1.0` |
| edge `metadata` | `.metadata` | Default `{}` |

### 3.2 EntityType Enum Divergence (Critical)

The protocol `EntityType` (12 values) and legacy `models.EntityType` (19 values) are **different enums** with partial overlap:

| Shared | Protocol-only | Legacy-only |
|--------|--------------|-------------|
| concept, person, process, standard, tool | document, event, location, metric, organization, product, technology | file, function, class_, decision, pattern, requirement, solution, procedure, policy, system, role, team, component, service |

**Impact:** The existing `_extract_entity_type()` helper validates against the legacy enum — it cannot be reused. The adapter needs a new validation that targets `owlbear_knowledge.protocols.common.EntityType`.

### 3.3 Queue State Prerequisite

`submit_extractions` requires `enrich_queue.state = 'in_progress'`. This state is set by `EnrichmentStore.claim_batch()`, which will be wired via task #1891 (`get_next_batch`). During transition: calling `submit_extractions` before 1891 is complete results in `LookupError` → `ToolError` per AC5. This is acceptable.

### 3.4 Error Handling Comparison

| Concern | Old path | New path |
|---------|----------|----------|
| Transaction | Explicit `BEGIN IMMEDIATE` / commit / rollback | Internal (`with self._db:`) inside submit_extractions |
| Chunk not claimable | `ToolError` from `_load_chunk_provenance` | `LookupError` from submit_extractions → catch as ToolError |
| Bad entity data | `ToolError` from validation helpers | `ValidationError` from Pydantic model construction → catch as ToolError |
| Bad edge refs | `ToolError` from endpoint resolution | `ValueError` from submit_extractions (ref not in local_ref map) → catch as ToolError |
| Failure marking | `_mark_failed_chunk_claim` on rollback (old chunks table) | `enrichment_store.mark_failed(chunk_id, error)` (enrich_queue table) |

### 3.5 Implementation Approach

1. Keep `_normalize_enrichment_items` — validates input is list-of-dicts
2. New parsing function: dict → `ExtractedEntity` / `ExtractedRelation` with protocol enum validation
3. Remove explicit transaction management for phase-1 (submit_extractions is internally transactional)
4. Catch `LookupError` and `ValueError` from submit_extractions as `ToolError`
5. On parsing failure, call `enrichment_store.mark_failed(chunk_id, str(exc))` before raising ToolError
6. `claim_token` parameter becomes unused for phase-1 path (kept in signature for phase-2 compatibility)

## 4. Recommendation

**Straightforward wiring** (confidence: .85). The dict-to-model parsing is mechanical, the store method exists and is tested. One non-trivial concern: the EntityType divergence requires validating against the protocol enum, not reusing `_extract_entity_type()`. Similarly, `_extract_relation()` validates against `models.RelationType` — a parallel helper targeting `protocols.common.RelationType` is needed.

Challenge: FALLBACK — T1 task with single valid approach; challenger value insufficient.

**No blockers.** The queue-state prerequisite (#1891) is handled gracefully by AC5 (LookupError → ToolError). The task is independently testable by pre-populating `enrich_queue` in test fixtures.

## 5. Follow-up Tasks

No new tasks needed — #1892 is itself the implementation task from parent research #1882. The AC is complete and validated against the codebase.
