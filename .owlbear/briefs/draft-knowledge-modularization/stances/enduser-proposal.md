# End-User Proposal — Knowledge Module Decomposition

## Design Summary

The knowledge system exists to answer a consumer agent's question with **precise text, provenance, and cross-source relationships** — or to tell it cleanly that the data isn't available yet and accept a wish. Every design choice flows from that single interaction moment.

This proposal decomposes the system into **6 modules** along user-workflow boundaries, not pipeline-stage boundaries. The primary axis is: what does each actor need to interact with, and what contract do they see? The secondary axis is progressive capability — the system delivers value at each layer independently, with richer answers as more layers are populated.

The decomposition:

| Module | Primary Actor | Responsibility |
|--------|--------------|----------------|
| **Query** | Consumer agent | Search, rank, compose answer, attach provenance |
| **Content** | Ingest pipeline (writes), Query (reads) | Chunk storage, embeddings, full-text archive |
| **Graph** | Enrichment (writes), Query (reads) | Entities, relationships, cross-source edges |
| **Sources** | All actors | Source registry, health, freshness, wish list |
| **Ingest** | Ingestor agent + human | Fetch → chunk → embed → persist to Content + Sources |
| **Enrichment** | Enricher agent + human | Extract entities → resolve → build Graph edges |

## Key Structural Choices

### 1. Query is the consumer's ONLY interface

The consumer agent never touches Content, Graph, or Sources directly. It calls Query, which orchestrates retrieval internally. This means:
- The consumer sees ONE tool surface (search + wish)
- Answer quality improves transparently as Graph/Enrichment mature
- The internal decomposition is invisible to the consumer

**Why this matters for UX:** The agent should never need to know "did enrichment run?" to ask a good question. The system adapts its answer richness based on available data, not based on the consumer knowing which tools to call.

### 2. Sources is the universal registry — and the wish target

Sources owns metadata about what's ingested, when it was last refreshed, what health status it has, and critically — what's been WISHED for but not yet available. This gives every actor a single place to check "what do we have?" and "what's been requested?"

The wish flow: consumer agent calls a single fire-and-forget tool → Sources records the wish → human sees wishes in Cockpit → decides whether to ingest.

### 3. Content and Graph are separate stores with independent value

Content alone enables text retrieval + provenance (useful immediately after ingest). Graph adds entity-aware retrieval + cross-source answers (useful after enrichment). Separating them means:
- Ingest delivers value without waiting for enrichment
- Graph can be rebuilt/corrected without re-ingesting
- Each store has its own consistency contract

### 4. Enrichment is a separate module, not embedded in ingest

Enrichment is the least validated feature and the source of the worst boundary violations (F7, F8 from research). Making it a standalone module means:
- It can be absent entirely and the system still works (Content + Query alone)
- Its interfaces can evolve without touching the stable ingest path
- The "god module" problem in the MCP server is resolved by giving enrichment its own home

### 5. MCP tools map 1:1 to actor intents, not to modules

The MCP layer exposes tools named by what the actor wants to DO, not by which module serves it:

| MCP Tool | Actor | Maps to |
|----------|-------|---------|
| `knowledge_search` | Consumer | Query.search() |
| `knowledge_wish` | Consumer | Sources.register_wish() |
| `knowledge_ingest` | Ingestor | Ingest.run() |
| `knowledge_enrich` | Enricher | Enrichment.run() |
| `knowledge_sources` | Any agent | Sources.list() |
| `knowledge_source_health` | Any agent | Sources.health() |

This keeps the consumer's cognitive model simple: "I search, or I wish." The supply-side agents get their own clearly-named entry points.

## User Story Traces

### Trace 1: "ISMS control 2.4.5 — IAM standard procedure in AWS tools"

```
Consumer agent
  → calls knowledge_search("ISMS control 2.4.5 IAM standard procedure AWS")
  → Query receives intent
    → searches Content (vector similarity across all sources)
    → hits: SharePoint ISMS chunk mentioning control 2.4.5
    → checks Graph: entity "ISMS-2.4.5" has edges to:
       - Confluence "AWS IAM Standard Procedure v3.2"
       - InfoSec approval record "IAM-APPROVE-2024-07"
    → retrieves Content chunks for those related entities
    → assembles response with provenance per chunk
  → Consumer agent receives:
    {
      answer_chunks: [
        { text: "Control 2.4.5 states...", source: "SharePoint/ISMS/Controls", updated: "2026-03-15" },
        { text: "Standard procedure: ...", source: "Confluence/AWS-Standards/IAM", updated: "2026-04-02" },
        { text: "Approved by InfoSec on...", source: "Confluence/InfoSec/Approvals", updated: "2026-04-10" }
      ],
      relationships: [
        { from: "ISMS-2.4.5", to: "AWS-IAM-Procedure-v3.2", type: "implements" },
        { from: "AWS-IAM-Procedure-v3.2", to: "IAM-APPROVE-2024-07", type: "approved_by" }
      ],
      confidence: 0.91,
      coverage: "full"  // all relevant sources ingested
    }
```

**UX quality bar:** The agent gets exact text (control numbers preserved), multi-source attribution (three different sources), and explicit relationships (which procedure implements which control, who approved it). The consumer can present this to the human user with full traceability.

### Trace 2: "Access right for service X" — partial data

```
Consumer agent
  → calls knowledge_search("access right tool service X")
  → Query receives intent
    → searches Content: finds service catalog entry for "Service X"
    → checks Graph: entity "Service-X" has edge to "Tool-Y" (type: "managed_in")
    → but: no edge to access management (enrichment hasn't linked this yet)
    → searches Content for "Service X" + "access": finds a chunk mentioning "Role-Admin-Y in Tool-Y"
    → assembles response with partial confidence
  → Consumer agent receives:
    {
      answer_chunks: [
        { text: "Service X is managed in Tool-Y...", source: "Confluence/ServiceCatalog", updated: "2026-02-20" },
        { text: "...requires Role-Admin-Y...", source: "Confluence/AccessManagement", updated: "2026-01-15" }
      ],
      relationships: [
        { from: "Service-X", to: "Tool-Y", type: "managed_in" }
      ],
      confidence: 0.62,
      coverage: "partial",  // access management source exists but enrichment incomplete
      gaps: ["Access management ↔ Service X relationship not explicitly confirmed by enrichment"]
    }
```

**UX quality bar:** The system gives its best answer even when enrichment is incomplete. It explicitly flags confidence and gaps. The consumer agent can decide whether to present this or caveat it.

### Trace 3: "PDS 4.1 PTag colors" — data not available

```
Consumer agent
  → calls knowledge_search("PDS 4.1 PTag color options corporate CI")
  → Query receives intent
    → searches Content: no PDS documentation ingested
    → checks Sources: PDS source registered but status = "wished" (never ingested)
  → Consumer agent receives:
    {
      answer_chunks: [],
      confidence: 0.0,
      coverage: "absent",
      reason: "PDS documentation has not been ingested yet. Source is registered as wished.",
      suggested_action: "Trigger ingest for source 'pds-docs' when PDS portal credentials are available."
    }

Consumer agent (if it wants to escalate):
  → calls knowledge_wish({ topic: "PDS 4.1 PTag color options", reason: "CI compliance check" })
  → Sources records wish (idempotent if already wished)
  → returns: { status: "recorded", existing_wish: true, source_hint: "pds-docs" }
```

**UX quality bar:** The consumer gets a CLEAR explanation of why data is absent, not just empty results. It gets actionable next steps. The wish registration is one tool call, zero friction, fire-and-forget.

## Workflow Decomposition

### Consumer Workflow (query path)

```
Agent prompt → MCP knowledge_search → Query module
                                         ├── Content.search(vector)
                                         ├── Graph.expand(entities found)
                                         ├── Content.retrieve(related chunks)
                                         ├── Sources.provenance(source_ids)
                                         └── compose response
```

**Human touchpoints:** None. This is fully autonomous.

### Consumer Workflow (wish path)

```
Agent prompt → MCP knowledge_wish → Sources.register_wish()
                                      └── persist { topic, reason, timestamp }
```

**Human touchpoints:** None at registration time. Human reviews wishes in Cockpit later.

### Ingest Workflow (supply path)

```
Human triggers agent → Ingestor agent activates
  → MCP knowledge_ingest(source_id, auth_context)
  → Ingest module:
      ├── Browser/Fetcher.fetch(urls)        [may need auth — human provided]
      ├── Content.chunk(raw_text)
      ├── Content.embed(chunks)
      ├── Content.store(chunks + embeddings)
      └── Sources.update_status(source_id, "ingested", stats)
```

**Human touchpoints:** Trigger + auth provision. Human sees result in Cockpit (source status changes to "ingested", chunk count visible).

### Enrichment Workflow (understanding path)

```
Human triggers agent → Enricher agent activates
  → MCP knowledge_enrich(source_id | scope)
  → Enrichment module:
      ├── Content.read_chunks(scope)         [reads from Content store]
      ├── extract_entities(chunks)           [AI model call]
      ├── resolve_entities(new, existing)    [dedup against Graph]
      ├── Graph.add_entities(resolved)
      ├── Graph.add_edges(relationships)
      └── Sources.update_status(source_id, "enriched", entity_count)
```

**Human touchpoints:** Trigger only. Human sees entity/relationship counts in Cockpit after completion.

### Cockpit Workflow (observation path)

```
Human opens Cockpit → reads from:
  ├── Sources: list of all registered sources + status + freshness + wish count
  ├── Graph: entity count, relationship count, cross-source edge count
  └── Content: chunk count per source, storage size
```

**Human touchpoints:** Pure observation. No mutations from Cockpit.

## Error and Absence Handling

### The consumer NEVER gets silence

| Situation | Consumer Experience |
|-----------|-------------------|
| Full match | Precise answer + provenance + relationships + high confidence |
| Partial match (some sources ingested) | Best-effort answer + explicit gaps + medium confidence |
| Topic exists but not enriched | Text chunks without relationships + note about missing enrichment |
| Source registered but not ingested | Empty answer + "source exists but not yet ingested" + suggested action |
| Topic completely unknown | Empty answer + "no matching sources registered" + offer to register wish |
| System error (vector DB down) | Error with category ("storage unavailable") + retry guidance |

**Design principle:** The response ALWAYS contains a `coverage` field and a `confidence` score. The consumer agent can use these to decide how to present the answer to the human user.

### Wish Registration Flow

```
                    ┌─────────────────────────────────┐
                    │  Consumer calls knowledge_wish  │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │  Sources.register_wish()        │
                    │  - Idempotent (dedup by topic)  │
                    │  - Records: topic, reason, ts   │
                    │  - Returns: recorded/exists     │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │  Cockpit: "Wished Sources" tab  │
                    │  - Shows unfulfilled wishes     │
                    │  - Human decides: ingest or not │
                    └─────────────────────────────────┘
```

**Zero friction:** One tool call. No confirmation needed. No blocking. The consumer moves on immediately.

### Ingest Failure Handling

| Failure | Actor Experience |
|---------|-----------------|
| Auth expired | Ingestor agent gets clear error: "Authentication failed for source X. Human must re-authenticate." |
| URL unreachable | Source status → "fetch_failed" with timestamp. Cockpit shows red indicator. |
| Chunking/embedding failure | Source status → "processing_failed". Partial progress preserved (already-stored chunks remain). |
| Enrichment extraction failure | Source enrichment status → "enrichment_failed". Content remains searchable — only graph edges missing. |

**Design principle:** Failures are VISIBLE (Cockpit shows status), GRANULAR (which stage failed), and NON-DESTRUCTIVE (partial progress preserved).

## Information Requirements per Surface

### MCP Tool Response (what the consumer agent sees)

```
SearchResponse:
  answer_chunks: list[AnswerChunk]    # Exact text passages
    .text: str                         # Verbatim source text (never summarized)
    .source: str                       # Source identifier (human-readable)
    .section: str | None               # Section/page within source
    .updated: date                     # Last refresh date for this chunk
    .chunk_id: str                     # Stable reference ID
  relationships: list[Relationship]   # Cross-source connections
    .from_entity: str                  # Entity name
    .to_entity: str                    # Related entity name
    .type: str                         # Relationship type
    .source: str                       # Which source established this
  confidence: float                    # 0.0–1.0 answer quality estimate
  coverage: "full" | "partial" | "absent"
  gaps: list[str] | None              # What's missing, if partial
  reason: str | None                   # Why absent, if absent
  suggested_action: str | None         # What to do about absence
```

### Cockpit API (what the dashboard shows)

```
SourcesView:
  sources: list[SourceStatus]
    .id: str
    .name: str
    .type: "sharepoint" | "confluence" | "web" | "local"
    .ingest_status: "wished" | "ingesting" | "ingested" | "failed" | "stale"
    .enrich_status: "not_started" | "enriching" | "enriched" | "failed" | null
    .last_refresh: datetime | null
    .chunk_count: int
    .entity_count: int
    .staleness_days: int | null
  wishes: list[Wish]
    .topic: str
    .reason: str
    .requested_at: datetime
    .fulfilled: bool

GraphView:
  total_entities: int
  total_relationships: int
  cross_source_edges: int
  entity_types: dict[str, int]         # e.g. {"control": 45, "procedure": 23}
  source_connectivity: list[SourcePair] # which sources have cross-edges
```

### Source Registry (what all modules share)

```
SourceRecord:
  id: str
  name: str
  urls: list[str]
  auth_type: "none" | "oauth" | "api_key" | "browser_session"
  ingest_status: enum
  enrich_status: enum
  last_ingest: datetime | null
  last_enrich: datetime | null
  chunk_count: int
  entity_count: int
  config: dict                          # Source-specific settings
```

## Module Decomposition (User-Centric)

### Module 1: Query

**Owns:** Search orchestration, answer composition, confidence scoring, gap detection.
**Reads from:** Content (vector search, chunk retrieval), Graph (entity expansion, relationship traversal), Sources (provenance metadata, coverage assessment).
**Writes to:** Nothing. Pure read path.
**Public interface:**
- `search(intent: str, filters: SearchFilters | None) -> SearchResponse`
- `explain_coverage(topic: str) -> CoverageReport`

**Why separate:** The consumer's experience IS this module. Its quality (ranking, composition, confidence calibration) evolves independently of how data is stored or ingested.

### Module 2: Content

**Owns:** Chunk storage, embeddings, full-text archive, vector similarity search.
**Reads from:** Nothing external.
**Written by:** Ingest (stores chunks + embeddings), Enrichment (reads chunks for entity extraction).
**Public interface:**
- `store(chunks: list[Chunk], embeddings: list[Vector]) -> StoreResult`
- `search_similar(query_embedding: Vector, top_k: int, filters: ...) -> list[ChunkHit]`
- `retrieve(chunk_ids: list[str]) -> list[Chunk]`
- `read_by_source(source_id: str) -> list[Chunk]`

**Why separate:** This is the durable searchable material. It has value the moment ingest runs, before any enrichment. Its storage backend (Qdrant + SQLite) is an implementation detail hidden behind this interface.

### Module 3: Graph

**Owns:** Entities, relationships, cross-source edges, entity resolution state.
**Reads from:** Nothing external.
**Written by:** Enrichment.
**Public interface:**
- `add_entities(entities: list[Entity]) -> AddResult`
- `add_edges(edges: list[Edge]) -> AddResult`
- `get_related(entity_id: str, depth: int, edge_types: list[str] | None) -> SubGraph`
- `resolve(candidate: Entity, existing: list[Entity]) -> ResolvedEntity`
- `stats() -> GraphStats`

**Why separate:** The knowledge graph is the "understanding" layer. It can be empty (system still works via Content alone), rebuilt independently, or corrected without re-ingesting. Its correctness evolves separately from chunk quality.

### Module 4: Sources

**Owns:** Source registry, health tracking, freshness, wish list.
**Reads from:** Nothing external.
**Written by:** Ingest (status updates), Enrichment (status updates), Consumer (wishes).
**Public interface:**
- `register(source: SourceConfig) -> SourceRecord`
- `update_status(source_id: str, status: StatusUpdate) -> SourceRecord`
- `list(filters: SourceFilters | None) -> list[SourceRecord]`
- `health(source_id: str) -> HealthReport`
- `register_wish(wish: WishRequest) -> WishResult`
- `list_wishes(fulfilled: bool | None) -> list[Wish]`

**Why separate:** Every actor needs to know "what data exists?" Sources is the single answer. It's also the simplest module — pure metadata, no AI, no heavy compute. Can be built and tested first.

### Module 5: Ingest

**Owns:** Fetch → chunk → embed → persist pipeline. Content transformation logic.
**Reads from:** Sources (source config, URLs, auth requirements).
**Writes to:** Content (chunks + embeddings), Sources (status updates).
**Public interface:**
- `run(source_id: str, fetcher: ContentFetcher) -> IngestResult`
- `run_incremental(source_id: str, fetcher: ContentFetcher, since: datetime) -> IngestResult`

**Why separate:** The supply pipeline. Its complexity (chunking strategies, embedding batching, incremental refresh) is invisible to consumers. It can fail without affecting existing searchable content.

### Module 6: Enrichment

**Owns:** Entity extraction, entity resolution, relationship inference, graph building.
**Reads from:** Content (chunks to analyze), Graph (existing entities for dedup).
**Writes to:** Graph (new entities + edges), Sources (enrichment status).
**Public interface:**
- `run(scope: EnrichScope) -> EnrichResult`
- `run_incremental(source_id: str, since: datetime) -> EnrichResult`

**Why separate:** The least validated feature. Making it a separate module means: (a) the system works without it, (b) it can be rewritten without touching stable paths, (c) its "god module" code in the MCP server gets a proper home.

## Interface Contracts

### Consumer → Query (via MCP)

| Aspect | Contract |
|--------|----------|
| Input | Natural language intent string + optional filters (source_ids, date range, entity types) |
| Output | `SearchResponse` (see above) — always includes confidence + coverage |
| Timing | Synchronous. Target: <3s for most queries (vector search + graph expansion) |
| Error shape | `{ error: str, category: "unavailable" \| "invalid_query" \| "internal", retry_after: int \| null }` |
| Guarantee | Never returns empty without explanation. Always provides coverage assessment. |

### Consumer → Sources (via MCP, wish path)

| Aspect | Contract |
|--------|----------|
| Input | `{ topic: str, reason: str }` |
| Output | `{ status: "recorded" \| "already_exists", wish_id: str }` |
| Timing | Synchronous, <100ms (pure metadata write) |
| Error shape | Same error envelope as above |
| Guarantee | Idempotent. Never blocks. Never fails unless storage is down. |

### Ingestor → Ingest (via MCP)

| Aspect | Contract |
|--------|----------|
| Input | `{ source_id: str, auth_context: AuthContext \| null }` |
| Output | `{ status: "completed" \| "partial", chunks_stored: int, errors: list[str] }` |
| Timing | Long-running (minutes for large sources). Returns summary when done. |
| Error shape | Per-URL error list (partial success is normal) |
| Guarantee | Partial progress persisted. Re-running is safe (idempotent at chunk level). |

### Enricher → Enrichment (via MCP)

| Aspect | Contract |
|--------|----------|
| Input | `{ scope: "source" \| "all", source_id: str \| null }` |
| Output | `{ entities_added: int, edges_added: int, conflicts_resolved: int }` |
| Timing | Long-running (depends on AI model speed + chunk count) |
| Error shape | `{ error: str, processed_chunks: int, total_chunks: int }` (progress indicator) |
| Guarantee | Partial progress persisted. Graph remains consistent even on failure. |

### Cockpit → Sources + Graph (via REST API)

| Aspect | Contract |
|--------|----------|
| Input | Standard REST GET with optional query params |
| Output | `SourcesView` / `GraphView` (see Information Requirements above) |
| Timing | <500ms (metadata reads only) |
| Caching | MtimeScanCache pattern (same as existing Cockpit) |

## Progressive Capability

### Level 0: Sources Only

**What works:** Source registration, wish list, Cockpit shows "what's planned."
**User value:** Human can see what knowledge sources exist, register intentions, plan ingest order.
**Agent value:** Consumer can check what's available, register wishes for missing data.

### Level 1: Sources + Content + Ingest + Query (no enrichment)

**What works:** Ingest sources → vector search → return chunks with provenance.
**User value:** Agent can answer questions using text similarity. Answers are precise (exact text) and attributed (source + date). Cross-source answers happen via keyword/semantic overlap, not explicit relationships.
**Agent value:** The THREE consumer scenarios work at ~60-70% quality. Text retrieval finds relevant passages. Missing: explicit entity relationships (e.g., "implements", "approved_by" links between sources).

**This is the First Useful Step.** It delivers real value for all three demand scenarios via semantic search alone.

### Level 2: Full system (+ Graph + Enrichment)

**What works:** Entity-aware retrieval, relationship traversal, cross-source edges.
**User value:** Answers include explicit relationships ("this control IS IMPLEMENTED BY that procedure"). Confidence increases. Cross-source queries get precise linking instead of keyword matching.
**Agent value:** All three scenarios work at full quality. The "ISMS → procedure → approval" trace becomes an explicit graph path, not a probabilistic text match.

### Level 3: Maturity (future, not in scope)

**What could work later:** Automated staleness detection, refresh suggestions, coverage gap analysis, entity trend tracking.

## Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| Query as sole consumer interface | Simple mental model, transparent improvement | Extra indirection; Query must be smart about composing from Content + Graph |
| Content and Graph as separate stores | Independent value at Level 1; Graph can be rebuilt | Two storage systems to maintain; consistency between them is eventually-consistent |
| Enrichment as separate module | Can be absent, rewritten, or deferred | Adds a module; enrichment needs read access to Content (cross-module dependency) |
| Sources as shared registry | Single source of truth for "what exists" | All modules depend on Sources; it becomes a coordination point |
| Wish registration as one-call fire-and-forget | Zero friction for consumer | Wishes may accumulate without action; needs Cockpit visibility to avoid black hole |
| Synchronous Query (target <3s) | Simple agent interaction model | Graph expansion on large graphs may exceed budget; needs depth limits |

## Domain Rationale

This decomposition is driven by **user-experience boundaries**, not implementation boundaries:

1. **The consumer agent sees exactly 2 tools** (search + wish). Everything else is supply-side infrastructure invisible to it. This is the lowest possible cognitive load for the primary actor.

2. **Absence is a first-class response, not an error.** The system always explains WHY data is missing and WHAT to do about it. This prevents the silent failure mode where agents get empty results and have no recourse.

3. **Progressive capability means early value.** Level 1 (no enrichment) already serves all three demand scenarios. The system doesn't require the full graph to be useful. This avoids the "big bang" risk where nothing works until everything works.

4. **Wishes close the feedback loop.** Without wish registration, gaps in knowledge are invisible. With it, the human user sees demand signal in the Cockpit and can prioritize ingest accordingly. This turns "missing data" from a dead end into a workflow step.

5. **Enrichment isolation protects the stable path.** The research confirms enrichment is the least validated and most boundary-violating feature. Isolating it means the stable path (ingest → search) cannot be broken by enrichment bugs.

6. **Source registry as shared ground truth.** Every actor's first question is "what data exists?" Having one authoritative answer prevents the confusion of inconsistent state across modules.

## Confidence

**0.82**

High confidence because: the decomposition follows validated user workflows, addresses the specific cascade failures identified in research (F7, F8), and aligns with the proven kanban pattern (engine → MCP → cockpit). The progressive capability model de-risks delivery.

Residual uncertainty: the Query module's internal complexity (composing from Content + Graph, confidence scoring, gap detection) may be underestimated. Its interface is clean but its implementation is the hardest part of the system.
