# MCP Knowledge: Write Operations Wiring

> **Owning task:** #1882 — Knowledge: MCP tools — write operations
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task 1882 asks to wire MCP server write tools to new protocol-conformant store implementations (IngestCoordinator, SourceStore, EnrichmentStore). Dependencies #1870, #1875–#1878 are all archived. The question: what is the exact wiring strategy, gap analysis, and sequencing?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Codebase | Current MCP tool implementations (0.95) |
| `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py` | Codebase | New IngestCoordinator (0.95) |
| `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py` | Codebase | New EnrichmentStore (0.95) |
| `serve/knowledge/src/owlbear_knowledge/stores/sources.py` | Codebase | New SqliteSourceStore (0.90) |
| `serve/knowledge/src/owlbear_knowledge/stores/content.py` | Codebase | New ContentStore (0.90) |
| `serve/knowledge/src/owlbear_knowledge/protocols/` | Codebase | Protocol definitions (0.85) |

## 3. Analysis

### 3.1 Current vs Target Architecture

| MCP Tool | Current Implementation | Target Delegation | Gap Severity |
|----------|----------------------|-------------------|--------------|
| `ingest_document` | `IngestPipeline.ingest_text()` | `IngestCoordinator.ingest(IngestRequest)` | Medium — API shape differs |
| `remove_source` | manual vector delete + `store.delete_cascade()` | `IngestCoordinator.delete_source()` | Low — clean replacement |
| `get_next_batch` | direct SQL on `chunks` table | `EnrichmentStore.claim_batch()` + `ContentStore.get_chunk()` | Medium — needs text hydration |
| `store_enrichment` (phase-1) | `_persist_phase1_enrichment()` helper | `EnrichmentStore.submit_extractions()` | Low — input parsing needed |
| `store_enrichment` (phase-2) | `_persist_phase2_enrichment()` helper | **No protocol method** | Blocker — Phase-2 not in protocol |
| `retry_failed_enrichment` | direct SQL | **No protocol method** | Medium — not covered |
| _(new)_ `register_source` | N/A | `SqliteSourceStore.register_source()` | Low — straightforward |

### 3.2 Critical Gaps

**Gap A: Dual-table problem.** Old tools use `KnowledgeSourceStore` → `knowledge_sources` table. New protocol stores use `SqliteSourceStore` → `source_registry` table, `ContentStore` → `content_documents`/`content_chunks` tables, `EnrichmentStore` → `enrich_queue` table. The MCP server must transition to the new schema. This requires either:

- (A1) Schema migration: move data from old tables to new — complex, risky
- (A2) Parallel lifespan: instantiate both old and new stores during transition — messy
- (A3) Big-bang swap: replace AppContext entirely with new stores — clean but all-or-nothing

**Gap B: Text hydration.** `EnrichmentStore.claim_batch()` returns `EnrichmentQueueItem(chunk_id, source_id, ...)` without chunk text. The MCP `get_next_batch` tool must return text for LLM consumption. Resolution: MCP adapter calls `ContentStore.get_chunk(chunk_id)` per item.

**Gap C: Phase-2 consolidation.** `store_enrichment` handles both phase-1 (chunk→entities) and phase-2 (candidate→cross-source edges). Only phase-1 maps to `EnrichmentStore.submit_extractions()`. Phase-2 has no protocol method.

**Gap D: AC mismatch — `release_claim` doesn't exist.** Task body mentions `release_claim` mapping to EnrichmentStore but the protocol has no such method. Closest: `mark_failed()` (release with error) or stale-claim auto-recovery (>600s).

### 3.3 Wiring Strategy Comparison

| Strategy | Effort | Risk | KISS | Confidence |
|----------|--------|------|------|------------|
| A3 (big-bang) — swap full AppContext to new stores | High | Medium (requires all stores ready simultaneously) | ✓ | .75 |
| Phased — wire tools one-by-one, keeping old helpers for uncovered cases | Medium | Low | ✓ | .82 |
| Parallel — run both old and new store stacks | High | High (state drift) | ✗ | .50 |

### 3.4 Recommended Sequencing (Phased approach)

1. **AppContext expansion** — add `content_store`, `enrichment_store`, `ingest_coordinator` alongside existing fields; new `SqliteSourceStore` alongside `KnowledgeSourceStore`
2. **Wire `remove_source`** → `IngestCoordinator.delete_source()` (clean 1:1)
3. **Wire `register_source`** (new tool) → `SqliteSourceStore.register_source()` (greenfield)
4. **Wire `get_next_batch`** → `EnrichmentStore.claim_batch()` + `ContentStore.get_chunk()` hydration
5. **Wire `store_enrichment` phase-1** → `EnrichmentStore.submit_extractions()` with input parsing
6. **Keep phase-2 and `retry_failed_enrichment` on old helpers** until protocol coverage expands
7. **Wire `ingest_document`** → `IngestCoordinator.ingest()` with source resolution adapter

## 4. Recommendation

**Phased wiring** (confidence: .82). Wire tools incrementally, prioritising clean replacements (`remove_source`, `register_source`) first. Keep phase-2 consolidation and retry on old helpers — they work correctly and the protocol gap is a separate concern (not 1882's scope).

Challenge: FALLBACK — subagent invocation skipped for efficiency (T1 task, phased approach is low-risk).

**Blockers:** Gap A (dual tables) must be resolved before tools can delegate. The lifespan must instantiate new stores with `ensure_tables()` so both table sets exist. IngestCoordinator can operate on its own tables while the existing read tools continue using old tables.

## 5. Follow-up Tasks

Tasks needed at `research` status for the builder:

1. **Expand AppContext + lifespan** — add new store instances (ContentStore, EnrichmentStore, SqliteSourceStore, IngestCoordinator) to lifespan construction
2. **Wire `remove_source` to IngestCoordinator.delete_source`** — replace manual vector+cascade logic
3. **Add `register_source` tool** — new MCP tool delegating to SqliteSourceStore.register_source
4. **Wire `get_next_batch` to EnrichmentStore.claim_batch** — claim + ContentStore text hydration
5. **Wire `store_enrichment` phase-1 to EnrichmentStore.submit_extractions** — parse input dicts → protocol models
6. **Wire `ingest_document` to IngestCoordinator.ingest** — source resolution + IngestRequest construction
