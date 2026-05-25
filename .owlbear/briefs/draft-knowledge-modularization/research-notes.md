# Research Notes — Knowledge Module Modularization

## Verified Findings

### F1: Pipeline coupling is loose, not tight

Despite the audit finding issues, the runtime dependencies between pipeline stages are clean:
- Each stage (ingest, refresh, query, retrieval) is independently callable
- Data crosses between stages via frozen Pydantic models (5-6 field result objects)
- All dependencies are injected via protocol interfaces, not hard imports
- Zero circular dependencies confirmed

**Implication:** The cascade problem is NOT a code-coupling problem. It's a responsibility-boundary problem — modules exist but what they OWN is unclear.

### F2: Three natural narrow waists exist

| Boundary | Interface | Data Shape |
|----------|-----------|-----------|
| IngestPipeline ↔ Storage | `DocumentStore.store()`, `GraphStore.add_entities()` | `IngestResult` (5 fields) |
| RefreshOrchestrator ↔ IngestPipeline | `pipeline.ingest(intake_result, scope, source_id)` | `RefreshResult` (6 fields) |
| QueryService ↔ Vector/Graph | `VectorStoreProtocol.search_similar()`, `GraphStore.get_*()` | Chunk IDs, Entity objects, Edge objects |

### F3: Browser/fetcher boundary is already excellent

- Knowledge package never imports browser package
- Clean protocol: `ContentFetcher.fetch(url: str) -> str`
- Swappable: HTTP fallback vs. Playwright browser
- RefreshOrchestrator accepts optional ContentFetcher at runtime

### F4: MCP layer needs only 5 engine objects

Minimal set: `QueryService`, `IngestPipeline`, `RefreshOrchestrator`, `GraphStore`, `SourceStore`. Vector and embedding providers are internal to these. The MCP layer's surface is already narrow.

### F5: Kanban pattern comparison

| Aspect | Kanban | Knowledge (current) |
|--------|--------|-------------------|
| Config DI | Loads internally from filesystem | Everything injected |
| Public symbols | 8 | 23 |
| Topology | Opinionated (fixed board structure) | Infrastructure-neutral |
| Model | Engine → MCP → Cockpit (clean 3-layer) | Engine + MCP (blurred boundary in enrichment) |

Key lesson: Kanban works because its domain is simple and its public API is small (8 symbols). Knowledge has 3x the surface area — a sign of unclear boundaries.

### F6: Prior decomposition work (March 2026) recommended keeping flat

Proposed split at the time:
- `knowledge/storage/` — graph, qdrant, source_store
- `knowledge/pipeline/` — ingest, chunker, extractor, embeddings, intake, graph_builder
- `knowledge/retrieval/` — retrieval, query_service

Rejected because: no circular imports, below 30-file threshold. **But that analysis predated the cascade problem becoming severe.**

### F7: MCP server's "god module" problem is real

`server.py` (1100+ lines) contains:
- 15 tool handlers
- DI/lifespan init
- Direct SQL for enrichment claiming (CTEs)
- AppContext with 9 injected objects

This is the primary boundary violation — enrichment logic lives in the MCP layer instead of the engine.

### F8: Enrichment has the most uncertain interfaces

Entity extraction, consolidation, and the enrichment state machine are:
- Never validated by real consumer usage
- Involved in direct SQL in the MCP server (bypassing engine abstraction)
- The source of most boundary violations in the current architecture

## Candidate Implications (hypotheses for Phase 2)

### H1: The right decomposition might be responsibility-based, not stage-based

Instead of splitting by pipeline stage (ingest/retrieve/enrich), consider splitting by **what the module is responsible for**:
- "Content" (owns: chunks, full text, embeddings — the raw material)
- "Knowledge" (owns: entities, edges, relationships — the extracted understanding)
- "Sources" (owns: source registry, health, refresh scheduling — the data origin lifecycle)

This separates the "I store text and make it searchable" concern from "I understand what's in the text and how things relate."

### H2: Protocol contracts in code may be better than document specs

The system already uses Protocols extensively. The kanban module's boundary is defined by its `__init__.py` exports. The same pattern could define the knowledge decomposition — typed Protocol interfaces as the authoritative contract, not a separate document.

### H3: The enrichment boundary may need the most radical surgery

Enrichment logic currently lives partly in the engine and partly in the MCP server (direct SQL). This is the messiest boundary and likely the source of most cascade findings. Options:
- Move all enrichment into the engine behind a protocol
- Make enrichment a separate package entirely
- Treat enrichment as a feature flag that can be fully absent

### H4: Fewer, fatter modules might cascade less

32 modules at ~240 LOC each means many seams. If the system were 4-6 modules at ~1500 LOC each with well-defined interfaces, changes would cascade less because there are fewer boundaries to violate.

### H5: Source registration for "wished" data could be trivial

The consumer-agent's "I wish this was in the KB" registration is just a write to the source registry. If SourceStore has a clean protocol, this is a single MCP tool with no pipeline coupling.

## Open Research Questions for Phase 2

1. **What's the right number of modules?** 3 is too coarse (simplifier proposed this but user sees more natural cuts). 32 is too fine (current state). Where's the sweet spot?

2. **Should the spec be typed Protocol code or a document?** The simplifier argues for Protocol-first; the user's instinct is document-first. These aren't mutually exclusive — a document can DESCRIBE the protocols.

3. **How to handle enrichment's uncertain domain?** Enrichment is the least validated feature. Should it be spec'd aggressively (risk: spec is wrong), or deferred until search-without-enrichment proves value?

4. **What existing tests validate the narrow waists?** If tests already exercise IngestResult/RefreshResult/StructuredSearchResult, those interfaces are more stable than untested ones.

5. **Does the kanban "engine → MCP → cockpit" pattern scale?** Kanban has 8 public symbols. Knowledge might need 20+. Does the pattern still work at that surface area, or does it need an intermediate packaging strategy?

6. **What methodology produces the best module split?** Domain-Driven Design (bounded contexts)? Use-case-driven decomposition? Interface segregation from SOLID? The user asked for input on methodology — Phase 2 should evaluate approaches.
