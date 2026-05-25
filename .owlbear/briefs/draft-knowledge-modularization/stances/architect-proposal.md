# Architect Proposal — Knowledge Module Decomposition

## Design Summary

Decompose the knowledge engine into **5 responsibility-bounded submodules** within the existing `serve/knowledge/` package, plus a cleaned MCP layer with zero domain logic. The decomposition follows responsibility ownership (what data + logic each module exclusively controls), not pipeline stage.

The 5 submodules:

| # | Submodule | Owns | Public Symbols (target) |
|---|-----------|------|------------------------|
| 1 | `content` | Chunks, embeddings, vector storage, text splitting, document persistence | 4–5 |
| 2 | `graph` | Entities, edges, graph queries, graph traversal | 3–4 |
| 3 | `sources` | Source registry, refresh orchestration, intake, fetcher protocol | 4–5 |
| 4 | `ingest` | Pipeline coordination: content → storage + extraction → graph | 2–3 |
| 5 | `query` | Retrieval, graph-augmented search, structured results | 3–4 |

Total public surface: **16–21 symbols** (down from 23 today, but now with clear ownership).

The MCP layer (`serve/mcp-knowledge/`) becomes a thin tool-handler dispatcher: each tool maps to exactly one submodule call. All enrichment/consolidation SQL currently in `_enrichment.py` and `_consolidation.py` moves into the engine.

---

## Key Structural Choices

### Choice 1: Subpackages, not separate workspace packages

**What:** Each submodule is a Python subpackage (`owlbear_knowledge.content`, `owlbear_knowledge.graph`, etc.) within the single `serve/knowledge/` workspace package.

**Why:**
- Domain is immature — boundaries WILL move. Subpackage renames are trivial; workspace package splits require `pyproject.toml` changes, dependency rewiring, and CI updates.
- The kanban reference architecture works as a single package with 11 symbols because its domain is stable. Knowledge's domain is NOT stable. Internal modularity (subpackages) gives structure without premature commitment to hard boundaries.
- One package = one test suite, one coverage report, one import root. Simpler DX.

**Trade-off:** Less enforcement than separate packages (Python doesn't prevent cross-subpackage imports by default). Mitigated by: import linting rules + the public API contract in `__init__.py`.

### Choice 2: Responsibility-bounded, not stage-bounded

**What:** Modules are cut by "what data they own and are exclusively allowed to mutate" rather than by pipeline temporal sequence.

**Why:**
- The cascade problem (F1 in research) is NOT code coupling — it's unclear responsibility. When two modules can both write to the same table or both interpret the same data shape, changes to one cascade to the other.
- Stage-based cuts (prior F6 proposal: `storage/`, `pipeline/`, `retrieval/`) still leave ownership ambiguous. Who owns the `entities` table — the ingest stage that writes entities, or the retrieval stage that reads them? Under responsibility-based cuts: `graph` owns it exclusively.

**The ownership rule:** Each SQLite table is owned by exactly one submodule. Other submodules access that data ONLY through the owning submodule's Protocol interface.

### Choice 3: Enrichment stays in the engine, not MCP

**What:** All enrichment logic (entity extraction during ingest, batch claiming, consolidation queries, phase-1/phase-2 persistence) moves from `serve/mcp-knowledge/` into `owlbear_knowledge.graph` (entity CRUD) and `owlbear_knowledge.ingest` (extraction coordination).

**Why:**
- F7 confirms the MCP server's "god module" problem. Direct SQL in the transport layer is an architecture violation — the MCP server should know nothing about table schemas.
- Enrichment is the least validated feature (F8). When it inevitably changes, changes should propagate within the engine (one package, one test suite), not across the engine-MCP boundary.

**Trade-off:** The `graph` submodule becomes fatter (~800–1000 LOC). Acceptable — that's still within single-responsibility if it exclusively owns entity/edge CRUD + enrichment state transitions.

### Choice 4: Two-tier Protocol contracts

**What:** Each submodule boundary is defined by a typed `Protocol` class (tier 1: inter-submodule) AND the package-level `__init__.py` re-exports (tier 2: engine→MCP boundary).

**Why:**
- Protocol classes ARE the living spec (aligns with simplifier). They're testable and enforceable.
- `__init__.py` re-exports define what the MCP layer (or Cockpit) is allowed to use. Anything not re-exported is internal.
- This makes "was this interface change intentional?" auditable: if a Protocol or `__init__.py` changed, the PR diff shows it explicitly.

### Choice 5: Query and Ingest are coordination modules, not data owners

**What:** `query` and `ingest` orchestrate operations across `content`, `graph`, and `sources` but own NO tables. They are pure logic — composing calls to data-owning modules.

**Why:**
- This is the critical insight that prevents the cascade problem. If `ingest` owned both chunk storage AND entity storage, changes to entity schema would cascade through ingest to all its callers. By making `ingest` a coordinator that calls `content.store_chunks()` and `graph.persist_extraction()`, each data concern changes independently.
- Coordinators have the thinnest interfaces (2–3 symbols each) because their job is assembly, not state.

---

## Proposed Module Decomposition

### Module 1: `owlbear_knowledge.content`

**Responsibility:** Text storage and vector retrieval — everything about "raw content as searchable material."

**Owns (exclusive mutation rights):**
- `documents` table
- `chunks` table (text, position, document_id)
- Vector collection in Qdrant (embeddings)
- `document_status` table

**Contains (current modules migrated):**
- `document_store.py` → core of this submodule
- `chunker.py` → internal
- `embeddings.py` → internal
- `protocol.py` (VectorStoreProtocol, HybridEmbedding, SparseVector) → public types
- `qdrant.py` → internal adapter
- `status_store.py` → internal
- `content_safety.py` → internal

**Public interface:**
```python
class ContentStore(Protocol):
    async def store_document(self, intake: IntakeResult, *, scope: str, source_id: str) -> str: ...
    async def store_chunks(self, doc_id: str, chunks: list[Chunk], embeddings: list[HybridEmbedding]) -> int: ...
    def get_document_status(self, doc_id: str) -> DocumentStatus | None: ...
    def search_similar(self, embedding: HybridEmbedding, *, limit: int, scope: str | None) -> list[tuple[str, float]]: ...
    def get_chunk_text(self, chunk_ids: list[str]) -> dict[str, str]: ...
```

**Called by:** `ingest` (store), `query` (search + retrieve text)

### Module 2: `owlbear_knowledge.graph`

**Responsibility:** Knowledge structure — entities, relationships, and graph traversal. The "understanding" layer.

**Owns (exclusive mutation rights):**
- `entities` table
- `edges` table
- Enrichment state (claim tokens, enrichment status per chunk)

**Contains (current modules migrated):**
- `graph_store.py` → core of this submodule
- `graph_builder.py` → internal (intra-doc graph construction)
- `models.py` (Entity, Edge, EntityType, RelationType) → public types
- `_enrichment.py` (from mcp-knowledge) → internal (phase-1 persistence)
- `_consolidation.py` (from mcp-knowledge) → internal (phase-2 cross-source)
- `extractor.py` → internal (LLM extraction interface)

**Public interface:**
```python
class KnowledgeGraph(Protocol):
    def add_entities(self, entities: list[Entity], *, doc_id: str, chunk_id: str) -> int: ...
    def add_edges(self, edges: list[Edge]) -> int: ...
    def get_entity(self, entity_id: str) -> Entity | None: ...
    def get_neighbors(self, entity_id: str, *, depth: int = 1) -> list[Entity]: ...
    def get_edges_for(self, entity_id: str) -> list[Edge]: ...
    def resolve_entities_for_chunks(self, chunk_ids: list[str]) -> list[Entity]: ...
    # Enrichment operations (moved from MCP)
    def claim_enrichment_batch(self, *, limit: int, scope: str | None) -> list[EnrichmentChunk]: ...
    def persist_enrichment(self, chunk_id: str, entities: list[Entity], edges: list[Edge]) -> None: ...
    def get_consolidation_candidates(self, *, limit: int | None) -> list[ConsolidationCandidate]: ...
    def persist_consolidation(self, candidate_id: str, edges: list[Edge]) -> None: ...
```

**Called by:** `ingest` (persist extraction), `query` (graph traversal), MCP (enrichment tools)

### Module 3: `owlbear_knowledge.sources`

**Responsibility:** Data origin lifecycle — where knowledge comes from, when it was last fetched, what its health is.

**Owns (exclusive mutation rights):**
- `knowledge_sources` table
- Source configuration and scheduling state

**Contains (current modules migrated):**
- `source_store.py` → core
- `intake.py` → internal (URL→content fetch coordination)
- `fetcher.py` → internal (ContentFetcher protocol + HTTP adapter)
- `_paths.py` → internal (sandbox path resolution)
- `_ssrf.py` → internal (URL validation)

**Public interface:**
```python
class SourceRegistry(Protocol):
    def list_sources(self, *, scope: str | None = None, enabled_only: bool = True) -> list[KnowledgeSource]: ...
    def get_source(self, source_id: str) -> KnowledgeSource | None: ...
    def register_source(self, name: str, source_type: SourceType, config: dict) -> str: ...
    def update_refresh_status(self, source_id: str, *, last_error: str | None = None) -> None: ...
    async def fetch_content(self, url: str, *, source: KnowledgeSource) -> IntakeResult: ...
```

**Called by:** `ingest` (resolve source, fetch content), MCP (source management tools), Cockpit (source status display)

### Module 4: `owlbear_knowledge.ingest`

**Responsibility:** Pipeline coordination — orchestrates the flow from "I have a URL" to "content is chunked, embedded, stored, and entities extracted."

**Owns:** No tables. Pure orchestration logic.

**Contains (current modules migrated):**
- `ingest.py` → core (IngestPipeline)
- `refresh.py` → internal (RefreshOrchestrator)
- `cancellation.py` → internal
- `integrity.py` → internal (content hash verification)
- `loader.py` → internal (source config loading)

**Public interface:**
```python
class IngestPipeline(Protocol):
    async def ingest(self, intake: IntakeResult, *, scope: str, source_id: str) -> IngestResult: ...

class RefreshOrchestrator(Protocol):
    async def refresh_source(self, source_id: str) -> RefreshResult: ...
    async def refresh_all(self, *, scope: str | None = None) -> RefreshResult: ...
```

**Called by:** MCP (ingest/refresh tools)

### Module 5: `owlbear_knowledge.query`

**Responsibility:** Read-path coordination — from a natural-language question to structured results with provenance and graph context.

**Owns:** No tables. Pure orchestration logic.

**Contains (current modules migrated):**
- `query_service.py` → core
- `retrieval.py` → internal (GraphAugmentedRetriever)

**Public interface:**
```python
class QueryService(Protocol):
    async def search(self, query: str, *, scope: str | None = None, limit: int = 10) -> list[StructuredSearchResult]: ...
    async def search_with_graph(self, query: str, *, scope: str | None = None) -> list[StructuredSearchResult]: ...
```

**Called by:** MCP (search tools), Cockpit (knowledge exploration)

---

## Dependency Graph

```
sources ─────────────┐
                     ▼
content ◄─────── ingest ──────► graph
                     ▲
                     │ (fetches from sources)
                     │
query ──► content
query ──► graph
```

**Acyclicity proof:**
- `content` depends on: nothing (leaf)
- `graph` depends on: nothing (leaf)
- `sources` depends on: nothing (leaf)
- `ingest` depends on: `content`, `graph`, `sources`
- `query` depends on: `content`, `graph`

No cycles. `content`, `graph`, and `sources` are independent leaves. `ingest` and `query` are coordination layers that compose leaves.

**MCP depends on:** all 5 submodules (but only through their Protocol interfaces)

---

## Package Strategy

### Single workspace package with subpackages

```
serve/knowledge/src/owlbear_knowledge/
├── __init__.py          # Package-level re-exports (engine→MCP boundary)
├── _types.py            # Shared frozen models (IngestResult, RefreshResult, etc.)
├── content/
│   ├── __init__.py      # Submodule public API
│   ├── _store.py
│   ├── _chunker.py
│   ├── _embeddings.py
│   ├── _vector.py       # Qdrant adapter
│   ├── _status.py
│   └── _safety.py
├── graph/
│   ├── __init__.py
│   ├── _store.py
│   ├── _builder.py
│   ├── _extractor.py
│   ├── _enrichment.py   # Moved from mcp-knowledge
│   ├── _consolidation.py  # Moved from mcp-knowledge
│   └── _models.py       # Entity, Edge, EntityType, RelationType
├── sources/
│   ├── __init__.py
│   ├── _store.py
│   ├── _intake.py
│   ├── _fetcher.py
│   ├── _ssrf.py
│   └── _paths.py
├── ingest/
│   ├── __init__.py
│   ├── _pipeline.py
│   ├── _refresh.py
│   ├── _cancellation.py
│   └── _loader.py
└── query/
    ├── __init__.py
    ├── _service.py
    └── _retrieval.py
```

### Why not separate workspace packages?

| Factor | Subpackages | Separate packages |
|--------|-------------|-------------------|
| Boundary rigidity | Soft (convention + lint) | Hard (import fails) |
| Cost to reorganize | Rename + move | New `pyproject.toml`, dep rewiring |
| Domain maturity needed | Low (boundaries can shift cheaply) | High (wrong boundary = expensive) |
| Test/coverage ergonomics | One suite | Multiple suites, cross-package mocking |
| Appropriate when | Domain still stabilizing | Domain is proven stable |

The domain is NOT proven stable. Subpackages give us the structure to reason about boundaries without the cost of being wrong about them.

---

## Public API Surface

The package-level `__init__.py` re-exports ONLY what the MCP layer and Cockpit need:

```python
# owlbear_knowledge/__init__.py — the engine→consumer boundary
__all__ = [
    # Query (consumer-facing)
    "QueryService", "StructuredSearchResult",
    # Ingest (agent-facing)
    "IngestPipeline", "IngestResult",
    "RefreshOrchestrator", "RefreshResult",
    # Sources (management)
    "SourceRegistry", "KnowledgeSource",
    # Graph (enrichment + exploration)
    "KnowledgeGraph", "Entity", "Edge",
    "EnrichmentChunk", "ConsolidationCandidate",
    # Content (types only, not the store itself)
    "DocumentStatus", "HybridEmbedding",
    # Infrastructure
    "init_db", "CancelSignal",
]
```

**Target: 18 symbols.** Down from 23 (current) and far fewer than the 32-module flat surface. Each symbol traces to exactly one submodule's public interface.

---

## Interface Contracts

### Boundary 1: Engine → MCP (transport boundary)

The MCP server imports ONLY from `owlbear_knowledge` top-level (never submodules directly). It constructs the engine objects during lifespan init and calls their protocol methods.

**Data crossing this boundary:** Frozen Pydantic models only (`IngestResult`, `RefreshResult`, `StructuredSearchResult`, `KnowledgeSource`, `Entity`, `Edge`, `EnrichmentChunk`, `ConsolidationCandidate`). No SQLite connections, no mutable state.

### Boundary 2: Ingest → Content (internal)

```python
# ingest calls content to store processed material
await content_store.store_document(intake, scope=scope, source_id=source_id)
await content_store.store_chunks(doc_id, chunks, embeddings)
```

Data shape: `IntakeResult` (frozen), `list[Chunk]` (frozen), `list[HybridEmbedding]` (frozen).

### Boundary 3: Ingest → Graph (internal)

```python
# ingest calls graph to persist extracted knowledge structure
graph.add_entities(entities, doc_id=doc_id, chunk_id=chunk_id)
graph.add_edges(edges)
```

Data shape: `list[Entity]` (frozen), `list[Edge]` (frozen).

### Boundary 4: Query → Content + Graph (internal)

```python
# query combines vector search with graph context
hits = content_store.search_similar(embedding, limit=limit, scope=scope)
chunk_text = content_store.get_chunk_text(chunk_ids)
entities = graph.resolve_entities_for_chunks(chunk_ids)
neighbors = graph.get_neighbors(entity_id, depth=1)
```

### Boundary 5: Ingest → Sources (internal)

```python
# ingest resolves source metadata and delegates fetching
source = source_registry.get_source(source_id)
intake = await source_registry.fetch_content(url, source=source)
source_registry.update_refresh_status(source_id, last_error=None)
```

---

## Methodology Justification

### Why responsibility-bounded decomposition?

The research findings (F1) prove the cascade problem is NOT code coupling — it's unclear ownership. When audits find "module A's test breaks because module B changed a table schema that A also reads directly," the fix is not more modules — it's exclusive ownership.

**Responsibility-bounded decomposition** answers the question "who is allowed to mutate this data?" for every table. That's the only question that prevents cascades.

### Why not stage-based (ingest/retrieve/store)?

Stage-based cuts leave table ownership ambiguous. The `entities` table is written by ingest and read by retrieval — under stage-based cuts, both stages "own" it, and changes cascade freely between them. Under responsibility-based cuts, `graph` owns it exclusively, and both `ingest` and `query` access it through `graph`'s Protocol.

### Why not 3 modules (as simplifier suggests)?

Three modules (retrieve/ingest/enrich) maps to actor-facing concerns but doesn't resolve the internal data-ownership question. "Ingest" would still own both chunks AND entities, coupling them. Five modules — with 3 data-owning leaves and 2 coordination layers — cleanly separates data ownership from orchestration.

### Why not the prior March 2026 proposal (storage/pipeline/retrieval)?

That proposal was a technical-layer split (where things live in the stack). It doesn't answer "who can mutate `entities`?" — the pipeline creates them, storage persists them, retrieval reads them. All three touch the same table. Under the proposed split, only `graph` touches entity data.

---

## Migration Path

### Phase 1: Create subpackage structure (mechanical, low-risk)

1. Create the 5 subdirectories with `__init__.py` files
2. Move existing modules into their subpackage (rename `graph_store.py` → `graph/_store.py`, etc.)
3. Update all internal imports
4. Preserve the top-level `__init__.py` re-exports (nothing changes for external consumers)
5. All existing tests continue passing without modification

**Validation:** `uv run pytest` passes. Import lint confirms no cross-subpackage private imports.

### Phase 2: Move enrichment into engine (boundary fix)

1. Move `_enrichment.py` and `_consolidation.py` from `serve/mcp-knowledge/` into `owlbear_knowledge/graph/`
2. Expose enrichment operations via `KnowledgeGraph` protocol methods
3. MCP server's enrichment tool handlers become thin calls to `graph.claim_enrichment_batch()`, `graph.persist_enrichment()`, etc.
4. Delete direct SQL from MCP server

**Validation:** MCP enrichment tools work identically. MCP server has zero `sqlite3` imports.

### Phase 3: Define Protocol interfaces (contract stabilization)

1. Write Protocol classes for each submodule boundary
2. Existing concrete classes implement these Protocols
3. Add protocol-conformance tests (assert `isinstance(concrete, Protocol)`)
4. Update `__init__.py` to export Protocols alongside concrete classes

**Validation:** Protocol conformance tests pass. Type checker confirms implementations satisfy protocols.

### Phase 4: Enforce ownership rules (cascade prevention)

1. Add import linting: no submodule imports another submodule's `_private` modules
2. Add table-ownership test: each submodule's tests verify it only accesses its owned tables
3. Document the ownership table in the package README

**Validation:** Lint rules pass. Ownership tests pass. Any future audit finding is attributable to a specific module boundary.

---

## Risk Assessment

### Risk 1: Domain shift invalidates boundaries (HIGH likelihood, MEDIUM impact)

**What:** Consumer usage reveals that "graph" and "content" aren't the right cuts — maybe entities should be co-located with their chunks for performance.

**Mitigation:** Subpackages are cheap to restructure. The Protocol interfaces shield consumers from internal reorganization. Impact is internal refactoring, not cascade.

### Risk 2: Enrichment complexity overwhelms `graph` module (MEDIUM likelihood, LOW impact)

**What:** If enrichment grows significantly, `graph` becomes a mini-monolith (entity CRUD + enrichment state machine + consolidation).

**Mitigation:** Enrichment can later split into its own submodule (`owlbear_knowledge.enrichment`) that calls into `graph` for persistence. The Protocol interface at the top level doesn't change.

### Risk 3: Performance cost of internal protocol boundaries (LOW likelihood, LOW impact)

**What:** Extra function calls between submodules add overhead vs. direct table access.

**Mitigation:** These are SQLite calls and Qdrant RPCs — the function-call overhead is negligible. Profile if observed.

### Risk 4: Over-engineering for a system with no consumers yet (MEDIUM likelihood, HIGH impact)

**What:** First-principles concern is valid — spending weeks on internal structure for a system nobody uses yet.

**Mitigation:** Phase 1 (mechanical move) is ~2 hours of work. Phase 2 (enrichment fix) resolves a known boundary violation regardless of future direction. Phases 3–4 can be deferred until first real consumer validates the read path. The proposal is designed for incremental adoption.

### Risk 5: Protocol proliferation creating its own maintenance burden (LOW likelihood, MEDIUM impact)

**What:** 5 Protocol classes + changes to any = 5 places to audit.

**Mitigation:** Protocols are narrow (3–5 methods each). They change less than implementations because they describe WHAT not HOW. When they do change, the change is visible in a single `__init__.py` diff.

---

## Domain Rationale

The three consumer scenarios from the demand signal inform this decomposition directly:

1. **Cross-source ISMS query** → exercises `query` (search) + `graph` (cross-source relationships) + `sources` (provenance attribution)
2. **Access rights + tool identification** → exercises `query` (search) + `graph` (entity relationships) + `content` (exact text)
3. **PDS component + CI alignment** → exercises `query` (search) + `content` (exact text) + `sources` (source identification)

All three scenarios use `query` as entry point, `content` for exact text, `graph` for relationships, and `sources` for provenance. None needs to know about `ingest` (that's agent-facing, not consumer-facing). This validates the read/write split: consumers touch `query` + read-side of `content`/`graph`/`sources`; agents touch `ingest` + `sources`.

---

## Confidence: 0.80

High confidence in the structural decomposition (5 modules, responsibility-bounded, acyclic). Moderate uncertainty about exact interface method signatures (these should emerge from first real consumer usage, not be specified speculatively). The migration path is low-risk because Phase 1 is purely mechanical and Phases 3–4 can be deferred.
