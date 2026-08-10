# Brief — Knowledge Module Modularization

## 1. Problem & Deliverable

### Problem

The knowledge subsystem (~7700 LOC, 32 modules, zero end-to-end usage) has interfaces grown bottom-up through multiple architectural pivots (PydanticAI → GitHub CLI → VS Code Copilot agents). Every audit reveals cascading findings because no authoritative module contracts exist. After 5+ audit-fix cycles without convergence, the cost of continuing exceeds the cost of redesigning module boundaries top-down.

### Deliverable

A top-down design specification defining 6 engine modules + MCP shell. Each module has: responsibility boundary, Protocol interface, boundary types, lifecycle ownership, table ownership, and independently-executable acceptance criteria. The spec also includes 3 mandatory E2E scenario tests that cross module boundaries.

The spec is the authoritative reference. Code conforms to it. Interface changes require spec amendment (tracked in version control).

### Constraints (locked)

- Storage: SQLite (documents, chunks, entities, edges, sources) + Qdrant (vector embeddings)
- Embedding model: BGE-M3 (1024-dim dense + sparse)
- Execution model: VS Code Copilot agents, human-triggered, no cron/automation
- Existing browser boundary: `serve/browser/` stays unchanged (ContentFetcher protocol)
- Packaging: single workspace package (`serve/knowledge/`) with subpackages

---

## 2. Module Architecture

### The 6 Engine Modules

| Module | Responsibility | Owns (tables/collections) | Depends On | Public Surface |
|--------|---------------|---------------------------|------------|----------------|
| **Sources** | Source registry, health tracking, wish registration | `source_*` tables | — (no deps) | `SourceStore` Protocol (~5 methods incl. `register_wish`) |
| **Content** | Raw-to-searchable pipeline: accept text, chunk, embed, store, retrieve by vector similarity | `content_*` tables + Qdrant collections | — (no deps) | `ContentStore` Protocol (~4 methods) |
| **Graph** | Entity/edge CRUD, adjacency queries, traversal | `graph_*` tables | — (no deps) | `GraphStore` Protocol (~5 methods) |
| **Enrichment** | Entity extraction from chunks, cross-source consolidation, claim management | `enrich_*` tables (extraction state, claims) | Graph (writes via GraphStore), Content (reads chunks) | `EnrichmentEngine` Protocol (~3 methods) |
| **Ingest** | Orchestrates write path: fetch → Content.ingest → optional Enrichment. Updates Sources status. | None (coordinator) | Sources, Content, (optional) Enrichment | `IngestPipeline` Protocol (~3 methods) |
| **Query** | Orchestrates read path: hybrid search → graph augmentation → provenance assembly | None (coordinator) | Sources, Content, Graph | `QueryService` Protocol (~2 methods) |

### MCP Server

Zero-logic routing shell. Maps MCP tool calls 1:1 to engine Protocol methods. No SQL, no business logic, no state. All domain logic lives in engine modules.

### Dependency Graph (acyclic)

```
Sources ←── Ingest ──→ Content
                 └──→ Enrichment ──→ Graph
                                     ↑
                        Query ───────┘
                          └──→ Content
                          └──→ Sources
```

Leaf modules (Sources, Content, Graph) have zero dependencies on other knowledge modules. Coordinators (Ingest, Query) compose leaf modules. Enrichment bridges Content → Graph.

---

## 3. Interface Contracts & Lifecycle

### Contract Shape Per Module

Each module's spec defines:

1. **Protocol interface** — typed Python Protocol class with method signatures, return types, and semantic obligations
2. **Boundary types** — frozen Pydantic models that cross the boundary (e.g., `ContentResult`, `EntityRecord`, `SearchResult`)
3. **Lifecycle ownership** — what happens when upstream data changes
4. **Failure isolation** — what failure looks like and what downstream observes

### Lifecycle Ownership

| Module | Lifecycle Responsibility |
|--------|------------------------|
| Sources | Owns `active/inactive/wished` state transitions. Source deletion cascades a "purge" event. |
| Content | Owns chunk freshness via content-hash delta detection. On re-ingest: replaces stale chunks, updates Qdrant. |
| Graph | Owns entity/edge validity. When Content signals chunk replacement, affected entities marked for re-extraction. |
| Enrichment | Owns extraction state (`pending/claimed/done/stale`). When chunks replaced, extraction state resets to `pending`. |

### Semantic Obligations

Each Protocol method documents:
- **Guarantees** — what the caller may depend on (stable across versions)
- **Non-guarantees** — what may change between versions (caller must not assume)
- **Side effects** — what other state changes occur (e.g., "ingest_document MAY invalidate previously-extracted entities")

---

## 4. Delivery Sequence & Value Progression

| Slice | Modules | Delivers | Value vs. Demand Signal |
|-------|---------|----------|------------------------|
| **Slice 1** | Sources + Content + Ingest + Query | Semantic search with provenance. Find relevant text, know where it came from. | ~40-50% |
| **Slice 2** | + Graph + Enrichment | Full demand signal. Cross-source entity chains, relationship-aware retrieval. | ~90-95% |
| **Slice 3** | + MCP refinement + Cockpit API + agent definitions | Production surfaces: agents use it, Cockpit shows status, wish flow is end-to-end. | 100% |

### Honest framing

- **Slice 1** answers simpler queries ("what does the ISMS say about data at rest?") and validates core pipeline mechanics (ingest works, search returns good results, provenance correct).
- **Slice 2** is where the demand scenarios are fully met. Enrichment is "sequentially independent" (buildable after Slice 1), not "optional" (it IS core value for cross-source chains).
- **Slice 3** adds the surfaces that make it usable by agents and visible in Cockpit.

### Consumer Demand Signal (what full system must answer)

1. "For ISMS control 2.4.5 regarding IAM, what is the documented standard procedure in AWS standards tools approved by information security?" — requires SharePoint → Confluence → InfoSec relationship chain
2. "What access right in what tool do I need to apply for to use service X?" — requires service catalog → access management → tool registry chain
3. "In PDS 4.1 what color options does the PTag have that is in line with corporate CI?" — requires design system → corporate CI chain

---

## 5. Enforcement & Verification

### CI-Enforceable Rules

| Rule | What it prevents | How it's tested |
|------|-----------------|-----------------|
| Table ownership | Cross-module writes | Assert: module X only writes to `prefix_*` tables |
| Import direction | Internal coupling | Assert: module X only imports from declared dependencies' public Protocols |
| MCP is logic-free | God-module recurrence | Assert: zero SQL, zero business branching in MCP handlers |
| Boundary types | Untyped coupling | Assert: data leaving module is frozen Pydantic from declared boundary types |

### Two-Tier Testing

**Tier 1: Module ACs (independently executable)**

Each module has its own test suite testable without other knowledge modules:
- Sources: CRUD sources, register wishes, status transitions
- Content: ingest text → retrieve by similarity, delta detection
- Graph: store entities/edges → traverse adjacency
- Enrichment: given chunks → extract entities → write to GraphStore Protocol mock
- Ingest: given mocked Sources/Content/Enrichment → sequence correctly, handle partial failure
- Query: given mocked Content/Graph → compose hybrid result with provenance

**Tier 2: E2E Scenario Tests (cross-module)**

Three integration tests that exercise real module composition (no mocks):
1. ISMS → Standards → Approvals chain
2. Access rights → Tool identification chain
3. PDS component → CI alignment chain

Each asserts: correct entities found, relationship chain traversed, exact text preserved, provenance attributed to correct source.

---

## 6. Spec Format & Migration Path

### Spec Format

Delivered as BOTH document and code:
- **Document** (`serve/knowledge/ARCHITECTURE.md`): Human-readable overview — boundaries, dependencies, lifecycle, delivery sequence, enforcement. What to read to understand the system.
- **Code** (`serve/knowledge/src/owlbear_knowledge/protocols/`): Typed Protocol classes + frozen boundary models. The authoritative, testable contracts. When document and code disagree, code wins.

### Migration Path

1. **Spec phase** (this Brief): Write Protocol interfaces, boundary types, ARCHITECTURE.md. No code restructuring.
2. **Restructure phase**: Move existing modules into subpackage directories. Adjust imports. Mechanical refactoring guided by spec.
3. **Validation phase**: Implement CI rules. Write E2E scenario tests. Verify module ACs pass independently.
4. **Cleanup phase**: Remove dead code. Consolidate into coherent subpackages.

### Schema Migration Strategy

- Tables prefixed by owning module: `content_*`, `graph_*`, `source_*`, `enrich_*`
- Per-module migration directories
- Shared `init_db()` calls each module's migration in dependency order (Sources → Content → Graph → Enrichment)
- CI test enforces: no cross-module table writes

---

## 7. Success & Rejection Criteria

### Success (the Brief is met when)

1. Each module's Protocol can be implemented against its own AC without importing other knowledge module internals
2. CI rules mechanically prevent: cross-module table writes, unauthorized imports, business logic in MCP
3. E2E scenario tests prove the three demand scenarios work across module boundaries
4. When a module interface changes, the change is localized: spec amendment → module code → module tests. No untracked cascade.
5. A new contributor can read ARCHITECTURE.md + one module's Protocol and understand what to build without reading the whole system

### Rejection (the Brief has FAILED if)

- Module ACs all pass while demand scenarios still fail (modules compose incorrectly)
- The spec drifts from code (Protocols must BE the contracts, not describe them)
- Restructuring produces cascade patterns (spec must be revisable via tracked amendments)
- "Independent testability" requires mocking half the system (leaf modules need zero mocks of other knowledge modules)
