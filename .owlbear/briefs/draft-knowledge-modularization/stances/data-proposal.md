# Data Modeler Proposal — Knowledge Module Decomposition

## Design Summary

Decompose the knowledge subsystem along **data ownership boundaries**, not pipeline stages. Each module owns exactly one coherent data domain — its tables, its schema migrations, its validation logic, and its write path. Cross-module data access is read-only through typed Protocol interfaces returning frozen Pydantic models. This eliminates the cascade problem at its root: when a module owns its data exclusively, schema changes and validation logic cannot leak across boundaries.

The decomposition yields **5 data domains** mapped to 5 engine modules, plus an MCP facade and the existing browser package (unchanged). The critical insight: the current 32 modules have unclear ownership precisely because "what data does this module write?" was never the organizing question.

---

## Key Structural Choices

### 1. Data Ownership Map

| Data Domain | Owner Module | Tables/Collections Owned | Single Source of Truth For |
|---|---|---|---|
| **Content** | `content-store` | `documents`, `chunks`, `embeddings` (SQLite) + Qdrant collection | Raw text, chunk boundaries, vector representations |
| **Graph** | `graph-store` | `entities`, `edges` (SQLite) | Extracted knowledge structure, entity identity, relationships |
| **Sources** | `source-registry` | `sources`, `source_status`, `content_hashes` (SQLite) | Data origin lifecycle, refresh state, delta detection |
| **Enrichment** | `enrichment-engine` | `enrichment_claims`, `consolidation_log` (SQLite) | Cross-source entity resolution state, claim ownership |
| **Query** | (owns no tables) | — | Orchestrates reads across Content + Graph + Sources |

**Rule: A module that owns a table is the only writer to that table.** Other modules may read (via Protocol methods returning frozen models), but never write. This is the fundamental invariant that prevents cascading schema changes.

### 2. Schema Boundary Proposal

Split the current monolithic SQLite database into **domain-scoped schema namespaces** within a single SQLite file (SQLite has no schemas, so enforce via naming convention and migration ownership):

```
content_documents      -- owned by content-store
content_chunks         -- owned by content-store
graph_entities         -- owned by graph-store
graph_edges            -- owned by graph-store
source_sources         -- owned by source-registry
source_status          -- owned by source-registry
source_content_hashes  -- owned by source-registry
enrich_claims          -- owned by enrichment-engine
enrich_consolidation   -- owned by enrichment-engine
_schema_versions       -- shared migration registry
```

**Why single file, not separate databases:** SQLite transactions are per-connection. A single file allows the orchestration layer to wrap cross-domain reads in a single transaction for snapshot consistency. Separate files would require manual coordination for consistent reads.

**Why table prefixes:** Enforcement mechanism. A linter/test can verify that `content-store` only writes to `content_*` tables. This is checkable, not just documented.

### 3. Validation Boundaries

Validation happens at **three** points, never silently:

| Boundary | Validation Type | Mechanism | Failure Mode |
|---|---|---|---|
| **Write boundary** (data entering a store) | Full schema validation | Pydantic model with strict mode | Reject with structured error; never persist invalid data |
| **Cross-module read boundary** | Shape validation | Return type is frozen Pydantic model; construction validates | TypeError at call site; loud failure |
| **External input boundary** (MCP tool args, source content) | Input sanitization + type coercion | Pydantic with `BeforeValidator` for coercion, `AfterValidator` for domain rules | Structured error to caller with field-level detail |

**Critical rule: No raw dicts or untyped SQL results cross module boundaries.** Every boundary crossing materializes a frozen Pydantic model. This is where NaN/None/missing-field corruption gets caught — at the boundary, not downstream.

**Null handling policy:**
- `None` in a Pydantic field means "explicitly absent" — the field's type must be `Optional[T]` and the consumer must handle it.
- Missing fields in SQL results are a schema violation (bug), not a data condition. They raise, never default.
- Empty strings are NOT treated as None. They are valid data with distinct semantics.

### 4. Consistency Guarantees

| Scenario | Guarantee | Mechanism |
|---|---|---|
| Single-module write | ACID | SQLite transaction scoped to one store's write method |
| Multi-module write (ingest = content + graph + source) | Atomic via orchestrator | Orchestrator holds connection, calls stores in sequence within one transaction |
| Cross-module read | Snapshot consistency | Single connection, single transaction for all reads in one query |
| Enrichment claiming | Optimistic concurrency | CTE-based claim with `WHERE NOT EXISTS` (already implemented); retry on conflict |
| Source refresh vs. query | Eventual | Readers see committed state; in-progress refresh is invisible until commit |
| Qdrant vs. SQLite | Eventual | Qdrant write follows SQLite commit. On crash between the two, reconciliation re-embeds missing chunks |

**Where eventual consistency is acceptable:** Only between SQLite and Qdrant. These are separate storage systems with no shared transaction. The invariant: SQLite is always authoritative. Qdrant is a derived index that can be rebuilt from SQLite content.

**Where eventual consistency is NOT acceptable:** Between content, graph, and source tables during ingest. A document with chunks but no source record is corrupt. A source with status "ingested" but no chunks is corrupt. The orchestrator's transaction boundary prevents this.

### 5. Data Flow Through the System

```
Source Registration
  └─ source-registry.register(url, type, metadata)
       writes: source_sources, source_status (state=registered)

Content Acquisition (browser → ingest orchestrator)
  └─ browser.fetch(url) → raw_content: str
       (no DB writes — pure fetch)

Ingest (orchestrator transaction)
  └─ BEGIN TRANSACTION
     ├─ content-store.store_document(raw_content, source_id)
     │    writes: content_documents, content_chunks
     │    returns: DocumentResult (frozen: doc_id, chunk_ids, chunk_count)
     ├─ content-store.embed_chunks(chunk_ids)
     │    writes: Qdrant collection (eventual, post-commit)
     ├─ graph-store.store_entities(extracted_entities, source_id)
     │    writes: graph_entities, graph_edges
     │    returns: GraphResult (frozen: entity_ids, edge_count)
     ├─ source-registry.mark_ingested(source_id, content_hash)
     │    writes: source_status, source_content_hashes
     └─ COMMIT

Enrichment (separate transaction, separate trigger)
  └─ enrichment-engine.claim_batch(agent_id) → claimed entities
     enrichment-engine.submit_consolidation(entity_pairs, resolution)
       writes: enrich_claims, enrich_consolidation, graph_edges (via graph-store protocol)

Query (read-only, snapshot)
  └─ query-service.search(query, filters)
     ├─ content-store.search_similar(embedding) → chunks with scores
     ├─ graph-store.get_related(entity_ids) → entities + edges
     ├─ source-registry.get_provenance(source_ids) → source metadata
     └─ returns: SearchResult (frozen: chunks, entities, provenance)
```

### 6. Migration/Versioning Strategy

**Per-domain migration ownership with a shared registry:**

```sql
CREATE TABLE _schema_versions (
    domain TEXT NOT NULL,        -- 'content', 'graph', 'source', 'enrich'
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL,
    migration_hash TEXT NOT NULL,
    PRIMARY KEY (domain, version)
);
```

**Rules:**
- Each module owns a `migrations/` directory with numbered SQL files: `content/001_initial.sql`, `content/002_add_embedding_dim.sql`
- `init_db()` applies all pending migrations for all domains in dependency order
- A module may only contain migrations for its own prefixed tables
- Cross-domain migration (e.g., adding a FK from `graph_entities` to `content_documents`) requires coordination: the FK is owned by the referencing domain (graph), and the referenced domain (content) must be at the required version
- Migration dependency is declared in a header comment: `-- requires: content >= 2`
- **Test:** A CI check verifies no migration touches tables outside its domain prefix

**Why not separate migration tools per domain:** Complexity. A single `init_db()` that processes all domains in order is simpler and matches SQLite's single-writer model. The domain prefix convention gives ownership clarity without tooling fragmentation.

### 7. Module Decomposition (Data-Centric)

| Module | Responsibility | Public Protocol | Owns Tables | Approximate LOC |
|---|---|---|---|---|
| `content-store` | Store documents, chunk them, manage embeddings, provide text search | `ContentStoreProtocol` | content_* + Qdrant | ~1200 |
| `graph-store` | Store entities and edges, provide graph traversal | `GraphStoreProtocol` | graph_* | ~800 |
| `source-registry` | Register sources, track status, detect deltas via hash | `SourceRegistryProtocol` | source_* | ~600 |
| `enrichment-engine` | Claim entities for consolidation, resolve cross-source duplicates | `EnrichmentProtocol` | enrich_* | ~900 |
| `query-service` | Orchestrate cross-domain reads into unified search results | `QueryProtocol` | (none — read-only) | ~700 |
| `ingest-orchestrator` | Drive the write path: fetch → chunk → extract → persist | `IngestProtocol` | (none — delegates) | ~500 |

**Note:** `ingest-orchestrator` owns no data. It owns the *transaction boundary*. It is the only code that opens a multi-store write transaction. This is intentional — the orchestrator's job is consistency, not storage.

**What about the MCP layer?** The MCP server becomes a thin tool registry that maps tool names to Protocol method calls. It owns zero business logic. The "god module" problem (F7) is resolved by moving enrichment claiming into `enrichment-engine` where it belongs.

### 8. Interface Contracts

**Cross-module data shapes (all frozen Pydantic):**

```python
# content-store → consumers
class ChunkResult(BaseModel, frozen=True):
    chunk_id: str
    document_id: str
    source_id: str
    text: str
    position: int
    score: float | None = None  # populated only in search results

# graph-store → consumers
class EntityResult(BaseModel, frozen=True):
    entity_id: str
    entity_type: str  # from EntityType enum
    name: str
    source_id: str
    properties: dict[str, str]  # frozen dict of domain-specific attributes

class EdgeResult(BaseModel, frozen=True):
    edge_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str  # from RelationType enum
    source_id: str

# source-registry → consumers
class SourceResult(BaseModel, frozen=True):
    source_id: str
    url: str
    source_type: str
    status: str  # from SourceStatus enum
    last_ingested: datetime | None
    content_hash: str | None

# query-service → MCP/agents
class SearchResult(BaseModel, frozen=True):
    chunks: list[ChunkResult]
    entities: list[EntityResult]
    edges: list[EdgeResult]
    provenance: list[SourceResult]
    query: str
    total_chunks: int
```

**Protocol interfaces (runtime contracts):**

```python
class ContentStoreProtocol(Protocol):
    def store_document(self, content: str, source_id: str, metadata: dict[str, str]) -> DocumentResult: ...
    def get_chunks(self, document_id: str) -> list[ChunkResult]: ...
    def search_similar(self, embedding: list[float], limit: int, filters: dict | None) -> list[ChunkResult]: ...
    def delete_by_source(self, source_id: str) -> int: ...

class GraphStoreProtocol(Protocol):
    def store_entities(self, entities: list[EntityInput], source_id: str) -> list[EntityResult]: ...
    def store_edges(self, edges: list[EdgeInput], source_id: str) -> list[EdgeResult]: ...
    def get_related(self, entity_ids: list[str], depth: int = 1) -> tuple[list[EntityResult], list[EdgeResult]]: ...
    def delete_by_source(self, source_id: str) -> int: ...

class SourceRegistryProtocol(Protocol):
    def register(self, url: str, source_type: str, metadata: dict[str, str]) -> SourceResult: ...
    def mark_ingested(self, source_id: str, content_hash: str) -> None: ...
    def get_status(self, source_id: str) -> SourceResult: ...
    def needs_refresh(self, source_id: str, new_hash: str) -> bool: ...
    def list_sources(self, filters: dict | None = None) -> list[SourceResult]: ...

class EnrichmentProtocol(Protocol):
    def claim_batch(self, agent_id: str, batch_size: int = 10) -> list[EntityResult]: ...
    def submit_resolution(self, entity_pairs: list[tuple[str, str]], canonical_id: str) -> None: ...
    def get_consolidation_status(self) -> dict[str, int]: ...
```

### 9. Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| **Qdrant/SQLite divergence after crash** | Medium | Reconciliation job that re-embeds chunks missing from Qdrant. SQLite is source of truth. |
| **Ingest transaction too large** (thousands of chunks in one commit) | Medium | Batch within transaction: commit per-document, not per-source. Source status updates only after all documents committed. |
| **Enrichment writes to graph tables it doesn't own** | High (current bug) | Enrichment calls `graph-store.store_edges()` via Protocol. Never touches `graph_*` tables directly. Test enforces: enrichment module imports no SQLite cursor. |
| **Schema drift between migration domains** | Low | CI test: run all migrations on empty DB, verify FK integrity, verify no table lacks its domain prefix. |
| **NaN/None propagation in search scores** | Medium | `ChunkResult.score` is `float | None`. Query service must handle None explicitly (sort with None-last, never arithmetic on optional scores). Pydantic strict mode prevents NaN assignment to float fields. |
| **Source deletion cascade** | High | `delete_by_source` is a Protocol method on BOTH content-store and graph-store. Orchestrator calls both in one transaction. Partial deletion = corruption. Enforce: delete is all-or-nothing per source. |
| **Enrichment on unvalidated domain** | Medium | Enrichment is architecturally optional. The system must be fully functional (ingest + query + provenance) WITHOUT enrichment. Enrichment adds cross-source edges; it doesn't gate basic retrieval. |

---

## Trade-offs

| Choice | Gain | Cost |
|---|---|---|
| Single SQLite file with prefix convention | Snapshot reads, simpler transactions | Domain isolation is convention-enforced, not system-enforced |
| Orchestrator owns transaction, not stores | Clear consistency boundary | Orchestrator must know store call order; coupling at orchestration level |
| Frozen Pydantic at every boundary | Corruption caught at source, not downstream | Allocation cost per boundary crossing; more model classes to maintain |
| Enrichment as separate optional domain | Can ship without it; isolates the most uncertain code | Must design graph-store Protocol to accept writes from enrichment without ownership confusion |
| Per-domain migrations in shared registry | Clear ownership; independent evolution | Dependency declaration is manual; cross-domain FKs need coordination |
| Query service owns no tables | Pure orchestration; easy to test with mocks | Cannot cache or materialize — every query hits underlying stores |

---

## Domain Rationale

This proposal follows data ownership as the primary decomposition axis because the research findings (F1, F7) show the cascade problem is not about code coupling — it's about unclear data responsibility. When `DocumentStore` owns both chunks AND delegates entity writes, when the MCP server runs direct SQL for enrichment, when `StatusStore` tracks hashes independently of the source registry — the system has no answer to "who is responsible for this data being correct?"

The consumer demand signal (D3) confirms: agents need **exact text with provenance and cross-source relationships**. That's three distinct data concerns (content, provenance, relationships) that should never be coupled in a single store. The schema split follows directly from what the consumers need to trust.

The enrichment isolation is the highest-conviction position: enrichment is the most uncertain domain (H3), has the most boundary violations (F7), and is the only feature that writes to another domain's tables. Making it optional AND giving it its own tables eliminates the largest source of cascade findings without blocking the core value path.

---

## Confidence

**0.82**

High confidence in: data ownership boundaries, validation strategy, transaction model, enrichment isolation.

Moderate uncertainty in: exact Protocol method signatures (will refine during implementation), migration dependency mechanism (may need tooling), whether 5 domains is optimal or whether content+graph should merge.
