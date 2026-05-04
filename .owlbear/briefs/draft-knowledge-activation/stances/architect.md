# Architectural Stance — Knowledge Engine Activation

## Position

The converged approach is structurally sound. Separating ingest (store chunks + embeddings) from enrichment (agent-driven entity extraction + consolidation) correctly places the LLM boundary at the VS Code agent, not the engine. The pull-based worker pattern with `get_next_batch`/`store_enrichment` is the right coordination model for this environment.

However, the scope of new construction is larger than the problem summary implies. The enrichment worker infrastructure, consolidation model replacement, and several integration seams require significant new code, not just wiring fixes. Six structural issues need explicit resolution.

## Structural Reasoning

### 1. Source Identity Is the Primary Integration Seam

**Problem:** The "fetch → `ingest_document(text=...)`" flow does not preserve source identity. The current `ingest_text` path builds a `Document` without `source_id`, even though `Document.source_id` exists in the model. But refresh, source-scoped cleanup, and consolidation all depend on source identity.

**Position:** `ingest_document` must accept source metadata (URL, title, fetch_method) and either create or resolve a source record. Source registration currently only happens in the `loader.py` path (batch from `sources.yaml`). The MCP tool surface needs its own source registration path. Without this, the agent-driven ingest flow produces orphaned documents that cannot be refreshed, cleaned up by source, or matched in consolidation.

This is the highest-priority integration fix. Everything downstream — refresh, enrichment, consolidation — depends on documents having source identity.

### 2. Worker Infrastructure Is New Construction

`get_next_batch`, `store_enrichment`, `claimed_at`, `claimed_by`, `reviewed_pairs`, `candidate_id` — none of these exist. The current `consolidate_knowledge` tool does chunk-batch summarization via LLM (a fundamentally different model from entity-pair review). This is a replacement, not an extension.

**Position:** Frame the enrichment/consolidation worker surface as new development:

- New schema: `enrichment_claims` table (chunk_id, claimed_at, claimed_by, completed_at), `reviewed_pairs` table (entity_name, source_a, source_b, reviewed_at)
- New MCP tools: `get_next_batch`, `get_consolidation_candidates`, `store_enrichment` (replacing `consolidate_knowledge`)
- New graph store methods: upsert entities/edges (not bare INSERT)

The existing `consolidation.py` module can be retired. The `inter_doc_graph_builder.py` module's canonical-name matching logic should be studied for reusable patterns, but its LLM-dependent comparison path cannot be used in the no-API-key model.

### 3. Store Operations Must Be Idempotent

Entity and edge inserts in `graph_store.py` are direct `INSERT` without conflict handling. A timed-out claim re-processed by another worker produces duplicate graph data.

**Position:** All enrichment writes must use upsert semantics:

- `INSERT OR REPLACE` for entities (keyed on chunk_id + entity_name + entity_type)
- `INSERT OR IGNORE` or `INSERT OR REPLACE` for edges (keyed on source_entity + target_entity + relation_type)
- `INSERT OR IGNORE` for reviewed_pairs

This makes claim-timeout reprocessing safe. Double-processing wastes compute but doesn't corrupt data.

Additionally: enable WAL mode on SQLite connection. The current connection uses plain `connect()` without WAL — concurrent workers need WAL for reliable concurrent reads during writes.

### 4. Qdrant Must Use Filesystem Persistence

The server instantiates `QdrantVectorStore` with in-memory defaults (`location=None`). Every MCP server restart loses all vectors, requiring full re-embedding of all content. With 5,480+ chunks and a 2.2 GB embedding model, this makes the system operationally fragile.

**Position:** Qdrant must use filesystem persistence at `store/knowledge/qdrant/` (gitignored). This is a critical configuration fix. The `QdrantVectorStore` constructor already supports a `path` parameter for filesystem mode. The MCP server lifespan should pass a persistent path, not rely on in-memory default.

### 5. Refresh Is Structurally Incomplete

`RefreshOrchestrator` is instantiated in the MCP server without `content_fetcher`, `graph_store`, or `inter_doc_builder`. This isn't just "browser-authenticated refresh doesn't work" — refresh is incomplete regardless of fetch method. The type system models authenticated web sources as engine-managed, but the wiring doesn't deliver.

**Position:** `refresh_source` should be scoped to local-file and HTTP-refetchable sources for this activation. Browser-authenticated refresh is agent-level: the ingestor fetches via browser, then calls `ingest_document` with fresh content and the same source_id (triggering re-index). The `RefreshOrchestrator` wiring should be completed for the paths it can handle (local files, HTTP), and the agent should handle the rest.

Post-refresh enrichment (re-extracting entities from refreshed chunks) should be handled by the enrichment worker loop naturally — refreshed chunks appear as unenriched in `get_next_batch`.

### 6. `store_enrichment` Dual-Schema With Phase Discriminator

Phase 1 payload: `{chunk_id, entities: [...], edges: [...]}` — entities + intra-source edges per chunk.
Phase 2 payload: `{candidate_id, edges: [...]}` — cross-source edges or empty (= reviewed, no match).

**Position:** One tool, two phases. Add a `phase` parameter (1 or 2) to disambiguate. The empty-edges-means-dismissal convention for Phase 2 is clean — avoids a separate `dismiss_candidate` tool. The schema union must be validated server-side (Phase 1 requires chunk_id + entities; Phase 2 requires candidate_id).

## Key Trade-offs

| Trade-off | Chosen Side | Risk |
|-----------|------------|------|
| Agent-driven enrichment vs. direct API | Agent-driven (no API keys) | Lower throughput, rate-limited by Copilot |
| Pull-based workers vs. orchestrator | Pull-based (simpler) | Timeout tuning: too short = duplicates, too long = blocked progress. 10 min default. |
| Exact-string entity matching vs. fuzzy | Exact-string (no LLM needed) | Regression from `inter_doc_graph_builder`'s canonical-name + vector similarity matching. Justified by no-LLM constraint. Canonical normalization (lowercase, strip separators) could narrow the gap without LLM. |
| One `store_enrichment` tool vs. per-phase tools | One tool with phase discriminator | Dual-schema complexity, but avoids tool proliferation |
| `refresh_source` HTTP-only vs. full | HTTP-only + agent-level browser refresh | Asymmetric UX, but architecturally honest about what the engine can do without an agent |

## Warnings

1. **Qdrant in-memory default must be changed before any real use.** Without filesystem persistence, every MCP server restart requires full re-embedding. This is the single highest operational risk.

2. **Source identity gap in `ingest_document` blocks the entire downstream pipeline.** Refresh, consolidation, and source-scoped operations all depend on documents having source_id. This must be fixed before enrichment work begins.

3. **BGE-M3 first-use downloads 2.2 GB.** Blocks first search/ingest for minutes. The `/kb-rebuild` prompt and setup documentation must warn about this.

4. **Copilot auth deletion has a test suite.** `test_copilot_server_wiring_888.py` tests the auth path. Removing copilot_auth requires updating or removing these tests. Not just a code deletion — it's a contract change.

5. **Enrichment worker infrastructure is ~3 new schema tables + 3 new MCP tools + upsert graph store methods.** This is significant new development, not wiring.

6. **Exact-string consolidation is a capability regression** from the existing `inter_doc_graph_builder` which does canonical-name blocking + vector similarity. Justified by no-API-key constraint, but should be noted as a known limitation with a mitigation path (canonical normalization without LLM).

## MCP Tool Surface Assessment

**8 active tools — the cut is correct with one refinement:**

The 8 active tools (search_knowledge, list_sources, get_stats, ingest_document, refresh_source, get_next_batch, get_consolidation_candidates, store_enrichment) are well-scoped. Three are new construction (get_next_batch, get_consolidation_candidates, store_enrichment), replacing one existing tool (consolidate_knowledge).

**Tool exclusion refinement:** Don't blanket-exclude all scope tools. `import_scope` and `export_scope` are fully implemented in `scope_transfer.py` and useful for manual DB snapshots. Exclude only `sync_from_global` and `sync_to_global` (degraded — throw NotImplementedError) plus the bookmark tools (premature). Total excluded: 6 tools (list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, sync_from_global, sync_to_global).

## Agent Model

**Two agent files:**

- `knowledge-ingestor.agent.md` — interactive, user-facing. Tools: ingest_document, refresh_source, list_sources, get_stats. Handles source registration, browser detection flow, dispatches enrichment.
- `knowledge-enricher.agent.md` — batch worker, headless. Tools: get_next_batch, get_consolidation_candidates, store_enrichment, get_stats. Runs the pull-extract-store loop for both enrichment phases.

The behavioral modes are distinct: ingestor is conversational with user validation steps; enricher is a tight batch loop optimized for throughput on a cheap model. Combining them would muddy the prompt and waste context on instructions irrelevant to the current mode.

## Protocol Interface Assessment

`StructuredExtractor` and `LLMExtractor` become dormant library code. In the agent-driven model, the engine never calls an LLM directly — agents extract inline and push results via `store_enrichment`. The `EntityExtractor` wrapper already handles `extractor=None` (no-op path), so the ingest pipeline works without LLM. The protocols stay as library code for potential future API-key scenarios but are not wired in the active flow.

The `ContentFetcher` protocol is correctly satisfied by `BrowserContentFetcher` but is NOT injected anywhere in the active flow. Content fetching lives at the agent/prompt level: the agent fetches, then passes text to `ingest_document`. This is the right boundary.

## Confidence

**0.78**

The architecture is sound for the stated constraints. The main risk is underestimating the scope of new construction — the enrichment worker system, source identity fix, Qdrant persistence, and refresh completion are collectively a substantial development effort, not a "wiring activation" project.
