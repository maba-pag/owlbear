# Research Notes — Knowledge Engine Activation

## Verified Findings

### F1: LightRAG Wrapping Assessment

LightRAG (28.7k stars, MIT) was thoroughly compared against the custom engine:

| Aspect | LightRAG | OwlBear Custom | Verdict |
|--------|----------|----------------|---------|
| Graph storage | In-memory NetworkX → export | SQLite + live query at retrieval time | **OwlBear better** for persistent cross-doc relationships |
| Scope isolation | Via query filters only | Column-based, schema v8 | **OwlBear better** for multi-scope use case |
| Entity extraction | LLM-based | LLM-based (`LLMExtractor`, OpenAI SDK) | Aligned |
| Vector DB | Multiple backends including Qdrant | Qdrant with dense + sparse | Compatible |
| Embedding model | Configurable (any HuggingFace) | BGE-M3 (1024-d dense + sparse + ColBERT) | Can align |
| Custom LLM endpoint | `llm_model_func` param | `base_url` + custom headers (for Copilot) | Both work |

**Key gap in LightRAG:** In-memory NetworkX graph with export. OwlBear needs persistent live graph for query-time traversal across documents. Wrapping LightRAG would require intercepting its graph construction and persisting to SQLite — a non-trivial adapter that buys nothing over the existing SQLite graph store.

**Verdict:** Wrapping LightRAG is **not justified**. The custom engine already has the pieces that match or exceed LightRAG for this use case. The recommendation is: adopt LightRAG's patterns (already done), keep custom engine, activate it.

### F2: The Blocking Bug (copilot_auth.py device-flow at startup)

The MCP server lifespan calls `get_copilot_token()` when no `OWLBEAR_LLM_API_KEY` or `OPENAI_API_KEY` is set. This triggers:
1. POST to github.com/login/device to get user_code + device_code
2. Prints "Open github.com/login/device and enter code: XXXX" to stdout
3. Polls github.com/login/oauth/access_token every 5 seconds for up to 900 seconds

In stdio MCP context, stdout is the JSON-RPC transport — the auth prompt is invisible. The poll loops until timeout (15 minutes).

**Fix:** The MCP server must NOT call copilot_auth at lifespan. Entity extraction (which needs LLM) should degrade gracefully — vector search works without LLM.

### F3: Engine Architecture (Confirmed Working Pieces)

| Component | Module | Status | Notes |
|-----------|--------|--------|-------|
| Vector store | `qdrant.py` | ✅ Complete | Dense + sparse vectors, scope filtering, filesystem or in-memory |
| Embeddings | `embeddings.py` | ✅ Complete | BGE-M3 via FlagEmbedding, lazy load, 600s idle unload, ~2.2 GB |
| Graph store | `graph_store.py` | ✅ Complete | SQLite with entities, edges, documents, chunks tables |
| LLM extractor | `llm_extractor.py` | ✅ Complete | OpenAI SDK, any endpoint, custom headers, rate limiting |
| Ingest pipeline | `ingest.py` | ✅ Complete | text → chunks → embed → extract entities → store |
| Query service | `query.py` | ✅ Complete | search → optional graph expansion → results |
| Content fetcher | `fetcher.py` | ✅ Complete | httpx for public URLs |
| Browser fetcher | `serve/browser/` | ✅ Complete | Playwright + Edge SSO. Implements `ContentFetcher` protocol. |
| Scope transfer | `scope_transfer.py` | ✅ Complete | import/export/sync between scopes |
| Bookmarks | `bookmark_pipeline.py` | ✅ Complete | URL evaluation + optional ingest |
| Consolidation | `consolidation.py` | ✅ Complete | Cross-doc insight synthesis (requires LLM) |
| Refresh | `refresh.py` | ✅ Complete | Re-ingest stale sources |

**Not yet wired:**
- Browser fetcher is NOT injected into knowledge pipeline (exported from `serve/browser/` but not used by `serve/knowledge/`)
- Hybrid vector search (sparse vectors) not yet active in Qdrant collection config

### F4: MCP Tool Surface — Revised (8 Active + 4 Deferred)

Original server had 14 tools. Cut to 8 active by eliminating: `list_entities` (vague browser — value flows through `search_knowledge` graph-augmented results), `bookmark_source`/`list_bookmarks`/`update_bookmark_tags` (premature), `consolidate_knowledge` (replaced by `get_consolidation_candidates` with deterministic pair-based matching).

| Tool | Consumer | Purpose |
|------|----------|---------|
| `search_knowledge` | Pipeline agents, user | Semantic search + graph-augmented results |
| `list_sources` | Pipeline agents, user, ingestor | What's indexed |
| `get_stats` | Ingestor, enricher | Health check + enrichment/consolidation progress |
| `ingest_document` | Ingestor | Add content |
| `refresh_source` | Ingestor | Re-ingest stale source |
| `get_next_batch` | Enricher | Pull unprocessed chunks (Phase 1) |
| `get_consolidation_candidates` | Enricher | Pull unreviewed cross-source entity pairs (Phase 2) |
| `store_enrichment` | Enricher | Write results for both phases; empty edges = dismissed pair |

Deferred: import_scope, export_scope, sync_from_global, sync_to_global (stubs until second consumer project).

**Agent model:** 2 functional roles — `knowledge-ingestor` (ingest, refresh, dispatch enrichment) and `knowledge-enricher` (Phase 1 extraction + Phase 2 consolidation). Enricher uses same worker loop for both phases, different pull source.

### F5: Protocol Interfaces (Extensibility)

The engine uses protocol classes (structural typing):
- `VectorStoreProtocol` — any vector DB can plug in
- `StructuredExtractor` — any LLM endpoint can plug in
- `ContentFetcher` — any fetcher can plug in (browser already satisfies this)
- `EmbeddingProvider` — any embedding model can plug in

This means the agent-as-LLM enrichment approach can work by implementing a new `StructuredExtractor` that routes through VS Code's agent/subagent mechanism rather than calling OpenAI SDK directly.

### F6: Test Coverage

- Unit tests exist for embedding provider, Qdrant store, graph store, SSRF, MCP tool contracts
- Tests are mock-based (no real DB or LLM required to run)
- No end-to-end integration test that validates the full pipeline (ingest → search → results)
- Missing: test that validates MCP server starts cleanly without LLM

## Candidate Implications

### I1: Agent-as-LLM Implementation Path

The `StructuredExtractor` protocol accepts `async extract(prompt: str) -> ExtractionResult`. A new implementation could:
1. Send the extraction prompt as a subagent call (the subagent receives the chunk + extraction instructions)
2. The subagent produces structured output (entity/relation tuples)
3. Parse into `ExtractionResult`

This is feasible because:
- VS Code supports parallel subagent calls (8+ observed)
- The extraction prompt is self-contained (chunk text + schema = ~800 tokens per call)
- Pydantic validation works regardless of how the output is generated

### I2: Browser Integration is Just Dependency Injection

The `ContentFetcher` protocol is already satisfied by `BrowserContentFetcher`. The gap is purely wiring:
- The ingest pipeline constructor accepts a `ContentFetcher`
- `BrowserContentFetcher` needs to be instantiated with a Playwright context
- The MCP server (or a curation prompt) needs to choose which fetcher to use based on URL

### I3: Startup Fix is Trivial

The MCP server lifespan just needs a conditional: if no LLM key, skip `LLMExtractor` initialization, set extractor to None, let the pipeline degrade gracefully (chunks + embeddings stored, entities not extracted). The `IngestPipeline` already handles `extractor=None`.

### I4: Scope Transfer May Be Premature

DR #616 approved scope machinery, but the user operates one project on one laptop. Import/export/sync tools add complexity without delivering value until the second consumer project exists. These could be hidden/disabled until needed.

## Open Research Questions

### Q1: How does the VS Code agent call the knowledge engine for enrichment?

The extraction happens inside the knowledge engine process (MCP server). But the LLM lives in VS Code (Copilot model). Two architectures:

- **A: MCP tool calls agent back** — Not possible. MCP is client→server only.
- **B: Agent orchestrates extraction** — Agent calls `ingest_document` (stores chunks + embeddings, skips entity extraction). Then agent calls a new `enrich_chunk` tool N times (each time providing the LLM output for one chunk). Engine stores the entities.
- **C: Agent does extraction locally, passes results to engine** — Agent gets chunk text via `list_unenriched_chunks` tool, runs extraction in its own context, calls `store_entities` tool to write results back.

Option C is cleanest: the MCP server is a dumb store, the agent is the LLM. Needs 2-3 new tools: `list_unenriched_chunks`, `store_entities`, `mark_enriched`.

### Q2: BGE-M3 Memory Footprint

2.2 GB model on CPU. On a laptop with 16-32 GB RAM this is manageable, but it stays loaded for 600s after each use. Should the idle timeout be configurable or shorter?

### Q3: DB Location and Lifecycle

Current: `store/knowledge/knowledge.db` (doesn't exist yet). `.gitignore`d. `sources.yaml` is source of truth for rebuild.
Questions:
- How long does a full rebuild take for 548 sources? (Depends on embedding speed)
- Should there be a `uv run kb-rebuild` command?
- What about incremental updates vs. full rebuild?

### Q4: Entity Types Sufficient?

Current: FUNCTION, CLASS, FILE, CONCEPT, REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD.
For the cross-source mapping use case (SharePoint requirements ↔ Jira tickets ↔ Confluence standards), are REQUIREMENT, POLICY, STANDARD sufficient? May need: TICKET, EPIC, COMPLIANCE_CONTROL, IMPLEMENTATION_EVIDENCE.

## Draft Flows (for Phase 2 evaluation)

### Enrichment Flow (Pull-Based Worker)

```
Agent: kb-enrichment-worker
Model: gpt-5.4 mini (0.33x, 400K context)
Tools: get_next_batch, store_enrichment, get_enrichment_status

Loop:
  1. get_next_batch(limit=20) → [{chunk_id, text, doc_title, section_path, source_name}]
  2. For each chunk: extract entities + relations (LLM, inline, no subagent)
  3. store_enrichment(chunk_id, entities=[...], relations=[...])
  4. Repeat until get_next_batch returns empty
```

Parallelism: User chooses 1-6 workers at prompt time. Each pulls from same pool. `get_next_batch` marks chunks in-progress to prevent duplicates. Session-safe: if VS Code closes, unfinished chunks revert to unprocessed on timeout.

Volume: ~5,480 chunks (548 sources × ~10 chunks). At 20 chunks/batch, ~274 batches. One agent session.

### Consolidation Flow (Phase 2 Enrichment — Pull-Based Worker)

```
Agent: knowledge-enricher (Phase 2 mode)
Model: gpt-5.4 mini (0.33x, 400K context)
Tools: get_consolidation_candidates, store_enrichment, get_stats

Loop:
  1. get_consolidation_candidates(limit=20) → [{entity_name, source_a: {name, chunks}, source_b: {name, chunks}}]
  2. For each candidate pair:
     - Read chunks from both sources (returned inline)
     - Decide: same entity? → store_enrichment(candidate_id, edges=[{source, target, type}])
     - Not a match? → store_enrichment(candidate_id, edges=[]) — marks pair as reviewed
  3. Repeat until get_consolidation_candidates returns empty
```

Review unit: source-pair per entity name. Adding a new source generates new candidate pairs without resurface of old dismissed pairs. Deterministic SQL:

```sql
SELECT e1.name, e1.source_id, e2.source_id
FROM entities e1
JOIN entities e2 ON e1.name = e2.name AND e1.source_id < e2.source_id
LEFT JOIN reviewed_pairs rp
  ON rp.entity_name = e1.name
  AND rp.source_a = e1.source_id
  AND rp.source_b = e2.source_id
WHERE rp.id IS NULL
```

### Ingest Flow (/kb-ingest prompt)

```
User: /kb-ingest <url_or_path>

Agent:
  1. HTTP fetch → preview to user (title + 200 chars)
  2. User confirms content looks right
     → If login page/garbled: re-fetch via Browser (Playwright + Edge SSO)
  3. ingest_document(text, metadata) → chunks + embeddings stored
  4. Ask: "Should I enrich this source? [Yes/No]"
  5. If yes: "How many workers? [1-6]"
     → Launch enrichment worker(s) for just these chunks
  6. Offer to save source to sources.yaml manifest

fetch_method saved to manifest for future (skip validation on re-ingest).
```

### Bootstrap Flow (/kb-rebuild prompt)

```
User: /kb-rebuild

Agent:
  1. Read sources.yaml manifest
  2. For each source: fetch (HTTP or browser per manifest config) → ingest
  3. Report: "Ingested N sources, M chunks, X already existed (skipped)"
  4. Ask: "Run enrichment? How many workers?"
```

### Browser Detection

HTTP-first with user validation (confidence 0.90):
1. Try HTTP fetch (fast, no Playwright overhead)
2. Show user preview for validation
3. If wrong → re-fetch via Browser
4. Save correct fetch_method to manifest

Rejected: pure auto-detect (silent login page ingestion risk), domain allowlist (config drift), always-ask (UX fatigue).

### Model Selection

Default: gpt-5.4 mini (0.33x, 400K context).
Fallback: gpt-5 mini (0x) → gpt-5.4 mini → Haiku 4.5 (0.33x).
Rationale: extraction is structured parsing, not creative reasoning. Cheap models suffice.
