# Brief — Knowledge Engine Activation

## 1. Problem

Pipeline agents cannot retrieve curated domain knowledge. All context must come from instruction files, skills, or inline prompts — no vector-semantic retrieval, no graph-augmented cross-source relationships. The operator needs cross-source relationship awareness across Confluence, SharePoint, Jira, and Porsche DS for compliant project documentation — vector search alone does not surface these relationships.

A knowledge engine library exists (`serve/knowledge/`, ~35 modules) with vector store, graph store, embeddings, and ingest pipeline. An MCP server exists (`serve/mcp-knowledge/`) but is non-functional (startup crash from copilot_auth device-flow in stdio context). The existing code provides foundational components, but activating end-to-end knowledge retrieval requires significant new construction: an enrichment worker subsystem, browser integration wiring, content guard activation, search provenance contract, and a revised MCP tool surface.

## 2. Project Type and Tier

- **Type:** Existing-feature/refactor — substantial implementation exists with approved architecture decisions (DR #616). This is activation + refinement with significant new construction for the enrichment worker subsystem.
- **Tier:** Shared — multi-consumer artifact (all pipeline agents use it), external integration complexity (Confluence, SharePoint, Jira, Porsche DS), operational concerns (DB storage, model lifecycle).

## 3. Outcomes

| # | Outcome | Verification |
|---|---------|-------------|
| O1 | MCP server starts cleanly — no auth loop, copilot_auth removed from lifespan, vector search works on ingested content | Server starts, `search_knowledge` returns results for ingested content |
| O2 | Ingest pipeline works end-to-end — local files, public URLs (HTTP fetch), authenticated pages (Playwright + Edge SSO) | Ingest local file, public URL, and authenticated URL successfully |
| O3 | Browser detection: HTTP-first with user validation — agent shows preview, user confirms or rejects, browser fallback if needed, `fetch_method` saved to sources.yaml manifest | Ingest an authenticated URL: HTTP fetch shows login page → user rejects → browser re-fetch succeeds → fetch_method persisted |
| O4 | Enrichment via VS Code agents — pull-based workers, Phase 1 (entity extraction via `get_next_batch`/`store_enrichment`) + Phase 2 (cross-source consolidation via `get_consolidation_candidates`/`store_enrichment`) | Workers extract entities from ingested chunks; consolidation finds cross-source entity matches |
| O5 | Graph-augmented retrieval works — `search_knowledge` returns results with provenance showing which entities, edges, and cross-source relationships contributed to each result | Search results include machine-readable provenance fields |
| O6 | DB is local state — Qdrant persisted to filesystem, SQLite on disk, both gitignored | MCP server restart preserves all vectors and graph data |
| O7 | MCP tool surface: 8 active tools, 4 deferred scope stubs, remaining tools removed | Only 8 tools registered in active server; scope stubs exist but are not exposed |
| O8 | Per-source enrichment flag — sources.yaml `enrich: true/false` controls which sources get entity extraction | Ingesting a source with `enrich: false` stores chunks but skips enrichment queue |
| O9 | Content injection guard wired at ingest — `ContentInjectionGuard` scans all incoming content before storage | Attempt to ingest content with injection markers → guard rejects or sanitizes |

## 4. Design

### 4.1 Dependency Ordering

The work has hard prerequisites. Tasks must be sequenced:

```
Layer 0: Foundation
  ├── Fix MCP startup (remove copilot_auth)
  ├── Qdrant filesystem persistence (config change)
  ├── Source identity fix in ingest_document
  └── Content guard wiring to ingest pipeline

Layer 1: Schema + Wiring
  ├── New enrichment_state column (not reusing consolidated)
  ├── Worker claim table (enrichment_queue with claimed_at, lease expiry)
  ├── Provenance-aware edge uniqueness UNIQUE(src, tgt, rel, doc_id)
  ├── Wire browser fetcher into knowledge pipeline
  └── Fix RefreshOrchestrator wiring (content_fetcher, graph_store)

Layer 2: Enrichment Workers
  ├── get_next_batch tool (atomic claims, lease expiry)
  ├── store_enrichment tool (upsert semantics, WAL mode, both phases)
  ├── get_consolidation_candidates tool (deterministic SQL, review-state contract)
  └── get_stats enrichment progress (chunks processed / total)

Layer 3: Search + Agents
  ├── Search result provenance contract (machine-readable fields)
  ├── knowledge-ingestor agent + /kb-ingest prompt
  └── knowledge-enricher agent + /kb-enrich prompt

Layer 4: Tool Surface Cleanup
  ├── Remove inactive tools from MCP registration
  └── Register scope stubs (import/export/sync — not exposed to agents)
```

### 4.2 MCP Startup Fix

Remove `copilot_auth.py` from MCP server lifespan. The `IngestPipeline` already handles `extractor=None` — vector search works without LLM. Entity extraction is handled by VS Code agent workers, not the MCP server process.

Cleanup: delete cached token at `~/.owlbear/copilot_token.json` if present. Update/remove tests in `test_copilot_server_wiring_888.py` that depend on the auth flow.

### 4.3 Source Identity

`ingest_document` must register/resolve a source record before storing chunks. All downstream operations depend on `source_id`:
- `refresh_source` needs to know which chunks belong to a source
- `get_next_batch` filters by source enrichment state
- `get_consolidation_candidates` matches entities across sources
- `list_sources` reports per-source status

Source identity is resolved by URL (for web content) or file path (for local files). The source record stores: name, URL/path, `fetch_method` (http/browser/local), `enrich` flag (true/false), timestamps.

### 4.4 Enrichment Worker System

**New schema additions:**

| Table/Column | Purpose |
|-------------|---------|
| `enrichment_state` column on chunks | Track: pending → claimed → enriched. Replaces nothing — `consolidated` column retains its existing semantics. |
| `claimed_at` column on chunks | Lease timestamp for claimed chunks. Stale claims (>10 min) revert to pending. |
| `reviewed_pairs` table | Track consolidation outcomes: entity_name + source_a + source_b. Prevents resurfacing dismissed pairs. |

**Worker coordination:**
- `get_next_batch(limit=20)` — SELECT chunks WHERE enrichment_state='pending' with IMMEDIATE transaction, UPDATE to 'claimed' + set claimed_at. Returns chunk_id, text, doc_title, section_path, source_name.
- `store_enrichment(chunk_id, entities, edges)` — UPSERT entities (INSERT OR REPLACE), INSERT OR IGNORE edges with UNIQUE(source_entity, target_entity, relation, document_id). UPDATE chunk enrichment_state to 'enriched'. WAL mode required for concurrent writers.
- Lease expiry: a periodic check (or on-demand during `get_next_batch`) resets chunks WHERE enrichment_state='claimed' AND claimed_at < now() - 10 minutes back to 'pending'.

**Phase 2 consolidation:**
- `get_consolidation_candidates(limit=20)` — deterministic SQL: find entity names appearing in 2+ sources without existing cross-source edges or reviewed_pairs entries. Returns entity_name + relevant chunks from both sources inline.
- `store_enrichment(candidate_id, edges=[...])` — writes cross-source edges. Empty edges = reviewed, no match (marks pair in reviewed_pairs). Review unit is source-pair per entity name. New sources generate new candidate pairs; old dismissals are preserved.
- `get_stats` includes: total sources, total chunks, chunks enriched / total, consolidation candidates remaining.

### 4.5 Browser Detection Flow

Per D9 — HTTP-first with user validation:

1. Agent tries HTTP fetch (fast, no Playwright overhead)
2. Shows user preview (title + first ~200 chars of content)
3. User confirms content looks correct or rejects ("that's a login page")
4. If rejected → re-fetch via Browser module (Playwright + Edge SSO)
5. Save correct `fetch_method` to sources.yaml manifest entry
6. On re-ingest/refresh, use saved fetch_method (skip validation)

### 4.6 Content Injection Guard

Wire existing `ContentInjectionGuard` into the MCP `ingest_document` tool path. The guard exists in the library but is not connected to the live ingest flow. All web content must pass through the guard before being stored as chunks.

Guard runs at ingest time only (D20). Pre-guard legacy chunks are accepted as a one-time edge case.

### 4.7 RefreshOrchestrator Fix

`RefreshOrchestrator` is instantiated without `content_fetcher`, `graph_store`, or `inter_doc_builder`. Since `refresh_source` is in the active tool surface, the orchestrator must be wired correctly:
- Inject `ContentFetcher` (HTTP or browser, based on source manifest `fetch_method`)
- Inject `GraphStore` for entity/edge cleanup on re-ingest
- Skip `inter_doc_builder` (entity extraction handled by agent workers)

### 4.8 Search Result Provenance

`search_knowledge` response must include machine-readable provenance so agents and the operator can verify WHY a result was returned:

```
{
  "results": [
    {
      "chunk_text": "...",
      "score": 0.87,
      "source": {"name": "...", "url": "..."},
      "retrieval_path": "vector",  // or "graph" or "vector+graph"
      "entities": [
        {"name": "...", "type": "REQUIREMENT"}
      ],
      "related_sources": [
        {"name": "...", "relationship": "...", "entity": "..."}
      ]
    }
  ]
}
```

When enrichment hasn't been run, `entities` and `related_sources` are empty arrays. The response shape is deterministic regardless of enrichment state.

### 4.9 MCP Tool Surface

**8 active tools:**

| Tool | Consumer | Purpose |
|------|----------|---------|
| `search_knowledge` | Pipeline agents, user | Semantic search + graph-augmented results with provenance |
| `list_sources` | Pipeline agents, user, ingestor | What's indexed, with enrichment state |
| `get_stats` | Ingestor, enricher | Health check + enrichment/consolidation progress |
| `ingest_document` | Ingestor | Add content (local files, URLs, browser-fetched). Content guard at entry. |
| `refresh_source` | Ingestor | Re-ingest stale source using saved fetch_method |
| `get_next_batch` | Enricher | Pull unprocessed chunks for Phase 1 entity extraction |
| `get_consolidation_candidates` | Enricher | Pull unreviewed cross-source entity pairs for Phase 2 |
| `store_enrichment` | Enricher | Write entities + edges (Phase 1) or cross-source edges/dismissals (Phase 2) |

**4 deferred scope stubs:** `import_scope`, `export_scope`, `sync_from_global`, `sync_to_global` — registered as stubs, not exposed to agents. Implementation deferred until second consumer project (D12, D16).

**Removed from current 14-tool surface:** `list_entities`, `bookmark_source`, `list_bookmarks`, `update_bookmark_tags`, `consolidate_knowledge`, and any other tools not in the active 8.

### 4.10 Agent Model

| Agent | Role | Triggered by | Tools |
|-------|------|-------------|-------|
| `knowledge-ingestor` | Ingest, refresh, dispatch enrichment | User via `/kb-ingest` prompt | ingest_document, refresh_source, list_sources, get_stats |
| `knowledge-enricher` | Phase 1 entity extraction + Phase 2 consolidation | Ingestor dispatch or user via `/kb-enrich` prompt | get_next_batch, get_consolidation_candidates, store_enrichment, get_stats |

Both agents have `search_knowledge` access for verification.

**Enricher model:** gpt-5.4 mini (0.33x cost, 400K context). Fallback: gpt-5 mini → Haiku 4.5.

**Enricher worker loop:**
1. Call `get_next_batch(limit=20)` → chunks with metadata
2. For each chunk: extract entities + relations inline (LLM, no subagent)
3. Call `store_enrichment(chunk_id, entities, edges)` → persist
4. Repeat until `get_next_batch` returns empty
5. Phase 2: same loop with `get_consolidation_candidates` instead of `get_next_batch`

Parallelism: user chooses 1–6 workers at prompt time. Each pulls from same coordinated pool.

## 5. Entity Type Schema

Current types: FUNCTION, CLASS, FILE, CONCEPT, REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD.

This schema may need extension for the cross-source mapping use case (TICKET, COMPLIANCE_CONTROL, IMPLEMENTATION_EVIDENCE). Per D13, this is deferred to implementation-time research — the enricher agent's extraction prompt defines the type vocabulary, so it can be updated without schema migration.

## 6. Out of Scope

- **Batch rebuild/bootstrap** (`/kb-rebuild` prompt) — ingest is manual, one source at a time
- **`delete_source` tool** — manual lifecycle acceptable at current scale (D19)
- **Scope transfer implementation** — stubs only until second consumer project (D12, D16)
- **Per-source health in `get_stats`** — enrichment progress only, defer per-source breakdown (D18)
- **Content guard at enrichment time** — ingest-only scanning (D20)
- **BGE-M3 idle timeout configuration** — 600s default accepted
- **Entity type schema extension** — deferred to enricher prompt design (D13)
- **Hybrid sparse vector search activation** — existing Qdrant config supports it but not activated in this brief

## 7. Risks

| Risk | Mitigation |
|------|-----------|
| Enrichment model quality (gpt-5.4 mini untested at scale) | Fallback chain defined; entity extraction is narrow structured parsing |
| Worker coordination complexity (new code, not activation) | Atomic claims + lease expiry; simple timeout-based revert |
| BGE-M3 download (2.2 GB) on first use | One-time cost; lazy-loaded on first embed call |
| Re-ingest during active enrichment | Lease expiry handles stale chunk IDs; document the constraint |
| 14→8 tool surface reduction | No migration needed — server isn't in production use yet |

## 8. Key Decisions Reference

| Decision | Choice | Rationale |
|----------|--------|-----------|
| D1 Project type | Existing-feature/refactor | Code exists, DR #616 approved |
| D2 Tier | Shared | Multi-consumer, external integrations |
| D3 LLM access | Agent-driven in VS Code | No API keys (corporate policy) |
| D4 Graph enrichment | Core requirement | Cross-source relationship mapping |
| D5 LightRAG | Rejected | Custom engine's persistent SQLite graph is better |
| D6 Deliverable | One Brief | LightRAG eval was research, not a separate phase |
| D7 Worker pattern | Pull-based workers | 4-6 parallel, coordinated pool |
| D8 Model | gpt-5.4 mini (0.33x) | Cheap, good instruction-following |
| D9 Browser detection | HTTP-first + user validation | Prevents silent login page ingestion |
| D10 Ingest/enrich separation | Per-source enrich flag | sources.yaml enrich: true/false |
| D11 Tool surface | 8 active + 4 deferred | Cut premature features |
| D12 Scope machinery | Interfaces only, defer impl | Until second consumer project |
| D14 Consolidation | Phase 2 enrichment, pair-based | Empty edges = dismissed |
| D15 Agent model | 2 roles: ingestor + enricher | Distinct behavioral modes |
| D16 Scope tools | Defer all | D12 stands, narrow surface |
| D17 Edge uniqueness | Provenance-aware | UNIQUE(src, tgt, rel, doc_id) |
| D18 get_stats depth | Enrichment progress only | Defer per-source breakdown |
| D19 delete_source | Defer | Manual lifecycle acceptable |
| D20 Content guard timing | Ingest only | Pre-guard chunks are one-time legacy |
