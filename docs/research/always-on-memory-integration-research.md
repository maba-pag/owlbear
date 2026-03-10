# Integrate Always-On Memory into OwlBear Knowledge Layer

> **Owning task:** #701 — Research: Integrate always-on memory into OwlBear knowledge layer
> **Date:** 2026-03-09  **Status:** Complete

## 1. Context and Question

Task #700 analyzed the GCP always-on-memory-agent pattern and recommended adapting
two ideas: periodic consolidation and importance scoring. This research answers the
follow-up: **how** should these integrate into OwlBear's existing knowledge
infrastructure (SQLite graph + Qdrant + BGE-M3 + RAG pipeline)?

Key constraints: OwlBear uses PydanticAI (not ADK), has a working hybrid-search RAG
pipeline, and follows KISS/YAGNI principles. We must not regress existing capabilities.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|-----------|-----------|
| S1 | GCP always-on-memory-agent research | `docs/research/gcp-always-on-memory-agent.md` | 1.0 |
| S2 | Mem0 architecture | https://github.com/mem0ai/mem0 | 0.85 — multi-level memory (user/session/agent), LLM-extracted facts |
| S3 | OwlBear GraphEnricher | `src/owlbear/memory/knowledge/enrichment.py` | 1.0 — existing background task pattern |
| S4 | OwlBear KnowledgeQueryService research | `docs/research/context-aware-knowledge-injection-research.md` | 0.90 |
| S5 | OwlBear MemoryConsolidator research | `docs/research/memory-consolidator-research.md` | 0.95 — consolidation was deleted as YAGNI |
| S6 | OwlBear session-memory-hook research | `docs/research/session-memory-hook-research.md` | 0.85 |
| S7 | OwlBear temporal memory research | `docs/research/temporal-memory-research.md` | 0.80 — decay scoring pattern |
| S8 | Generative Agents (Park et al.) | arxiv.org/abs/2304.03442 | 0.80 — recency × relevance × importance scoring |

## 3. Component Mapping: GCP Memory Agent → OwlBear Equivalents

| GCP Component | OwlBear Equivalent | Status | Gap |
|---------------|-------------------|--------|-----|
| `IngestAgent` (extract entities/topics/importance) | `IngestPipeline` + `EntityExtractor` | **Exists** | No importance scoring |
| `store_memory` (SQLite insert) | `DocumentStore.insert_document` + GraphStore | **Exists** | N/A |
| `ConsolidateAgent` (periodic cross-reference) | `GraphEnricher` (intra/inter-doc edges) | **Partial** | No insight synthesis, no timer-driven consolidation |
| `store_consolidation` (cross-cutting insights) | None | **Missing** | No consolidation/insight storage |
| `QueryAgent` (read all + synthesize) | `KnowledgeQueryService.query_for_context` | **Exists** | No consolidation insights in results |
| `read_all_memories` (brute-force) | `GraphAugmentedRetriever.retrieve` (embedding + graph) | **Exists, superior** | N/A |
| `Orchestrator` (route to sub-agents) | `OwlBearAgent.turn()` | **Exists** | N/A |
| `consolidated` flag | None | **Missing** | Need tracking for processed vs unprocessed |
| `importance` float (0.0–1.0) | None | **Missing** | Entity model lacks importance |
| File watcher (`watch_folder`) | `RefreshOrchestrator` (knowledge source refresh) | **Exists** | N/A |
| Periodic timer (`consolidation_loop`) | `GraphEnricher._bg_semaphore` (reactively scheduled) | **Partial** | No periodic timer, only triggered on ingest |

## 4. Gap Analysis

### Already covered by OwlBear

- Document ingestion with entity extraction (S1 §6.2)
- Embedding-based retrieval that scales beyond 50 memories (S1 §6.2)
- Per-turn context injection via `KnowledgeQueryService` (S4)
- Inter-document graph edge inference via `InterDocGraphBuilder` (S3)
- Temporal decay scoring for retrieval freshness (S7)

### Missing capabilities the always-on pattern provides

| Gap | Description | Value | Effort |
|-----|-------------|-------|--------|
| **G1: Periodic consolidation** | Timer-driven re-processing of stored knowledge to find cross-cutting insights | High — surfaces patterns hidden in individual documents | ~200-300 LOC |
| **G2: Insight storage** | Synthesized cross-document insights stored with back-links to sources | High — enriches query results beyond raw chunks | ~50-80 LOC (schema + model) |
| **G3: Importance scoring** | 0.0–1.0 importance per entity/chunk at ingest time | Medium — enables priority-weighted retrieval | ~20-40 LOC |
| **G4: Consolidated flag** | Tracking which records have been consolidation-processed | Low — bookkeeping for G1 | ~10 LOC (schema migration) |

## 5. Integration Design Sketch

### 5a. Where it lives

```
src/owlbear/memory/knowledge/
├── consolidation.py   ← NEW: ConsolidationService
├── document_store.py
├── enrichment.py      ← Extend: periodic timer support
├── ingest.py
├── models.py          ← Extend: importance field on Entity
├── schema.py          ← Extend: v8 migration (consolidated flag, importance)
└── ...
```

### 5b. ConsolidationService design

Modeled after `GraphEnricher` (S3) which already handles background task scheduling:

```
ConsolidationService
├── consolidate()          → reads unprocessed, LLM synthesizes, stores insights
├── schedule_periodic()    → asyncio timer loop (like GCP consolidation_loop)
└── _store_insight()       → SQLite insert + mark sources consolidated
```

Integration point: Bootstrap creates `ConsolidationService` alongside `GraphEnricher`
in `_build_knowledge_toolset()`. Timer starts in daemon's event loop.

### 5c. Schema changes (v8 migration)

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| `entities` | `importance` | `REAL DEFAULT 0.5` | Priority-weighted retrieval (G3) |
| `chunks` | `consolidated` | `INTEGER DEFAULT 0` | Track consolidation status (G4) |
| `consolidations` (new table) | `id, source_ids, summary, insight, created_at` | — | Store synthesized insights (G2) |

### 5d. RAG pipeline impact

| Component | Change needed | Risk |
|-----------|--------------|------|
| `GraphAugmentedRetriever.retrieve()` | Include consolidation insights in expansion_text | Low — additive |
| `KnowledgeQueryService.query_for_context()` | Prepend most recent insights to injected context | Low — additive |
| `EntityExtractor` prompt | Add importance extraction instruction | Low — prompt change only |
| `QdrantVectorStore.search_similar()` | Weight by importance in scoring (optional) | Medium — scoring formula change |

## 6. Decision: with-RAG vs without-RAG vs Hybrid

| Approach | Description | KISS | Scale | Accuracy |
|----------|-------------|------|-------|----------|
| **Without-RAG** (GCP style) | LLM reads all memories, no embeddings | High | Poor (context window limit) | Medium |
| **With-RAG** (status quo) | Embedding search + graph expansion | Medium | Good (thousands of chunks) | Good |
| **Hybrid** (.80 confidence) | Status quo RAG + periodic consolidation insights injected | Medium | Good | **Best** — RAG precision + consolidation patterns |

**Recommendation (.80): Hybrid approach.** Keep the existing RAG pipeline intact.
Add consolidation as an enrichment layer that surfaces cross-document insights.
Consolidation insights are stored in SQLite and injected into query context alongside
RAG results. This matches both Mem0's approach (S2: LLM extraction + vector search)
and the Generative Agents pattern (S8: importance-weighted multi-factor retrieval).

**Risk:** MemoryConsolidator was previously deleted as YAGNI (S5, task #485). The
key difference: that consolidator targeted **session summaries** (conversation memory).
This proposal targets **knowledge graph consolidation** (document insights) — a
different scope with demonstrated value in production systems (Mem0, S2).

## 7. Recommendation (.75 confidence)

Implement the hybrid approach in three incremental tasks:

1. **Schema + model** (low risk): Add `importance`, `consolidated` fields and
   `consolidations` table via v8 migration. ~50 LOC.
2. **Importance scoring** (low risk): Update `EntityExtractor` prompt to output
   importance. Integrate into retrieval scoring. ~40 LOC.
3. **ConsolidationService** (moderate risk): Timer-driven background service that
   synthesizes cross-document insights. ~200-300 LOC. Default disabled, opt-in
   via config `consolidation_enabled: bool = False`.

**YAGNI guard:** Ship step 1+2 first (schema + importance). ConsolidationService
(step 3) ships behind a feature flag. This avoids the #485 mistake of building
consolidation before proven need, while laying the schema groundwork.

## 8. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Schema v8: add importance, consolidated, consolidations table" --priority needed --status backlog --tag "scope:core,memory,knowledge,schema" --body "## Goal\nExtend knowledge graph schema to support consolidation and importance scoring.\n\n## AC\n- [ ] v8 migration in schema.py adds importance REAL DEFAULT 0.5 to entities\n- [ ] v8 migration adds consolidated INTEGER DEFAULT 0 to chunks\n- [ ] v8 migration creates consolidations table (id, source_ids, summary, insight, created_at)\n- [ ] init_db handles v7->v8 migration idempotently\n- [ ] Tests verify migration from v7 to v8\n\n## References\n- docs/research/always-on-memory-integration-research.md §5c"

kanban\kanban-md.exe create "Add importance scoring to EntityExtractor" --priority needed --status backlog --tag "scope:core,memory,knowledge" --body "## Goal\nExtract a 0.0-1.0 importance score per entity during knowledge ingestion.\n\n## AC\n- [ ] Entity model includes importance: float = 0.5\n- [ ] EntityExtractor prompt requests importance rating\n- [ ] importance stored in SQLite graph\n- [ ] GraphAugmentedRetriever optionally weights by importance\n- [ ] Tests for importance extraction and scoring\n\n## References\n- docs/research/always-on-memory-integration-research.md §5d\n- GCP pattern: docs/research/gcp-always-on-memory-agent.md §6.4"

kanban\kanban-md.exe create "Implement ConsolidationService (feature-flagged)" --priority nice-to-have --status backlog --tag "scope:core,memory,knowledge,consolidation" --body "## Goal\nBuild a ConsolidationService that periodically synthesizes cross-document insights.\n\n## AC\n- [ ] ConsolidationService in src/owlbear/memory/knowledge/consolidation.py\n- [ ] Reads unconsolidated chunks, uses LLM to find patterns\n- [ ] Stores insight records in consolidations table with source back-links\n- [ ] Marks source chunks as consolidated\n- [ ] Configurable interval (default 30min)\n- [ ] Feature-flagged: consolidation_enabled config option, default False\n- [ ] KnowledgeQueryService includes insights in context injection\n- [ ] Tests with mocked LLM\n\n## References\n- docs/research/always-on-memory-integration-research.md §5b\n- GCP pattern: docs/research/gcp-always-on-memory-agent.md §6.3\n\n## Dependencies\n- Schema v8 migration task"
```
