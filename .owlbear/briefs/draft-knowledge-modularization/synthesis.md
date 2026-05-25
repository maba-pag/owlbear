# Synthesis — Knowledge Module Decomposition (compare mode)

## Divergence Matrix

| Decision Point | architect | data | enduser | security | Tension Level |
|---|---|---|---|---|---|
| **Enrichment placement** | Embedded in `graph` submodule (enrichment state + entity CRUD co-located) | Separate `enrichment-engine` module with own tables (`enrich_*`) | Separate `Enrichment` module with own interface | Quarantined `knowledge-graph` module (separate, blast-radius-contained) | **high** |
| **Module count** | 5 (content, graph, sources, ingest, query) | 6 (content-store, graph-store, source-registry, enrichment-engine, query-service, ingest-orchestrator) | 6 (Query, Content, Graph, Sources, Ingest, Enrichment) | 6 engine + 1 interface (source-registry, browser-auth, content-pipeline, knowledge-graph, persistence, query-service, mcp-knowledge) | **medium** |
| **Persistence as a module** | No — storage is internal to each data-owning submodule | No — each store module owns its tables directly | No — storage is behind each module's interface | Yes — separate `persistence` module (schema management, storage protocols, no business logic) | **medium** |
| **Content-pipeline scope** | `content` = storage + retrieval (chunking/embedding are internal); `ingest` coordinates the write path | `content-store` = storage + retrieval only; chunking/embedding are implementation details of store | `Content` = storage + retrieval; `Ingest` does the fetch→chunk→embed→store orchestration | `content-pipeline` = intake validation + chunking + embedding + sanitization (processing zone); separate from persistence | **medium** |
| **Primary decomposition axis** | Responsibility ownership (who is allowed to mutate this data?) | Data ownership (which module exclusively writes to which tables?) | User-workflow boundaries (what does each actor interact with?) | Trust boundaries (where does trust level change?) | **low** |
| **Schema/migration strategy** | Not prescriptive (implied: tables belong to submodules) | Table prefix convention (`content_*`, `graph_*`, etc.) + per-domain migration files + shared `_schema_versions` registry | Not prescriptive | Not prescriptive (notes parameterized SQL and schema conformance checks) | **medium** |
| **Wish system (consumer demand registration)** | Not addressed | Not addressed | Explicit: `knowledge_wish` MCP tool → Sources records wish → Cockpit shows wishes | Not addressed | **low** |
| **Browser-auth as separate package** | Not addressed (existing `serve/browser/` stays) | Not addressed (existing stays) | Not addressed (existing stays) | Explicitly preserved and reinforced as strongest boundary in system | **low** |
| **Transaction boundary ownership** | `ingest` coordinator holds write coordination (owns no tables, owns the flow) | `ingest-orchestrator` owns the transaction boundary explicitly (one multi-store write transaction) | Ingest coordinates writes across Content + Sources | `content-pipeline` validates; persistence accepts; no explicit coordinator named | **medium** |

---

## Common Ground

All four proposals agree on the following:

### Module identity and core cuts

- **Content, Graph, Sources, Query** appear as distinct modules in every proposal. The naming varies slightly but the responsibility mapping is identical: content owns chunks/embeddings/vector, graph owns entities/edges, sources owns source registry/status, query is a read-only orchestrator that composes across stores.
- **Query owns no data.** All proposals make query a pure coordination layer that reads from content + graph + sources and composes results. No proposal gives query write access or table ownership.
- **Ingest owns no data.** All proposals treat ingest/pipeline as an orchestrator that delegates writes to data-owning modules rather than writing directly.

### Structural bets

- **MCP layer becomes a thin routing shell with zero domain logic.** All proposals eliminate the current god-module problem (F7) by removing SQL, enrichment logic, and business rules from the MCP server. Every proposal mandates that MCP calls engine Protocol methods only.
- **Typed Protocol interfaces at boundaries.** All proposals use Protocol classes (or equivalent typed contracts) as the enforcement mechanism between modules. No raw dicts or untyped results cross boundaries.
- **Frozen Pydantic models for boundary-crossing data.** All proposals agree that data leaving a module is immutable (frozen models). This prevents downstream mutation from cascading back.
- **Single workspace package, not separate packages.** Architect and data explicitly argue for subpackages within `serve/knowledge/`; enduser and security don't contradict this (they describe module responsibilities, not packaging). No proposal advocates splitting into multiple workspace packages at this domain maturity level.

### Shared rejections

- **Reject stage-based decomposition.** All proposals reject the prior proposal's `storage/pipeline/retrieval` split because it leaves table ownership ambiguous.
- **Reject the current 32-module flat structure.** All proposals reduce the public surface significantly (target 16–21 symbols from architect; similar reductions implied by others).
- **Reject MCP-layer business logic.** Universal agreement that the server.py god-module pattern must not recur.
- **Reject code as sacred.** All proposals accept rewriting or discarding existing implementations where boundaries require it.

### Consistency model

- **SQLite is authoritative; Qdrant is a derived index.** All proposals that discuss storage consistency agree: on crash, Qdrant can be rebuilt from SQLite.
- **Enrichment cannot block basic search.** All proposals agree the system must be fully functional (ingest + query + provenance) WITHOUT enrichment. Enrichment adds value but is not on the critical path.

---

## Expectation Fit

The user's stated expectations (from context.md):
- **Trying to get:** Top-down spec with independently testable modules that localize cascade failures.
- **Feel worth using:** Pick up any module, implement against contract, test independently.
- **First Useful Step:** Engine split into practical parts, each independently buildable.

### Direction A: Enrichment embedded in Graph (architect)

| Fit dimension | Assessment |
|---|---|
| Independent testability | Slightly weaker — graph tests must cover both entity CRUD and enrichment state transitions. Graph module is ~800–1000 LOC (acknowledged as "fatter"). |
| Cascade localization | Enrichment failures cascade within graph module, not across boundaries. But graph consumers (query) cannot avoid exposure to enrichment state. |
| Pick-up-and-implement | Graph module has a larger Protocol surface (14 methods) — more to implement, but one coherent domain if you accept that entities + enrichment are one concern. |
| First Useful Step | Simpler to deliver — 5 modules means fewer contracts to define upfront. Content + sources + ingest + query are buildable without touching graph/enrichment at all. |

### Direction B: Enrichment as separate module (data, enduser, security)

| Fit dimension | Assessment |
|---|---|
| Independent testability | Stronger — enrichment module has its own test suite, own tables, own failure modes. Graph module stays focused on entity/edge CRUD. |
| Cascade localization | Maximum isolation: enrichment bugs cannot corrupt chunk retrieval OR graph structure (enrichment writes through graph's Protocol). Blast radius is explicitly contained. |
| Pick-up-and-implement | Graph module has a smaller, cleaner interface (~5 methods). Enrichment is a separate contract (~3 methods). Each is independently implementable. |
| First Useful Step | Slightly more contracts to define upfront (6 vs 5), but the enrichment contract can be deferred entirely since the system works without it. |

### Direction C: Persistence as separate module (security only)

| Fit dimension | Assessment |
|---|---|
| Independent testability | Adds another boundary to test, but persistence tests are mechanical (schema + constraints). |
| Cascade localization | Separates schema migration concerns from business logic — migration failures localize to persistence, not to processing modules. |
| Pick-up-and-implement | Requires understanding an additional module before implementing any data-owning module. Adds indirection. |
| First Useful Step | Neutral — persistence would be built as infrastructure before any domain module. |

### What remains after any First Useful Step

All directions agree that the first buildable slice is **Sources + Content + Ingest + Query** (no enrichment, no graph). This delivers semantic search with provenance for all three demand scenarios at ~60–70% quality. The remaining question is only how enrichment/graph enters later — as one module or two.

---

## Open Questions

### Q1: Should enrichment be a submodule of graph or a separate peer module?

**Options:**

| Option | Pro | Con |
|---|---|---|
| **A: Embed in graph** (architect) | Fewer modules (5 total). Entity CRUD + enrichment state are tightly coupled in practice (enrichment writes entities). Simpler dependency graph. | Graph module becomes fatter (~1000 LOC). Harder to defer or replace enrichment independently. Graph Protocol surface grows to 14 methods. |
| **B: Separate module** (data, enduser, security) | Maximum blast-radius containment. Enrichment can be absent, deferred, or rewritten without touching graph. Each module stays focused. | Extra module boundary. Enrichment must call graph's Protocol to persist entities — adds indirection for what is fundamentally a write-to-graph operation. |

**Trade-off:** This is a confidence-vs-isolation trade-off. If enrichment will stabilize quickly, embedding saves boundary overhead. If enrichment will undergo multiple rewrites (likely given 0 real consumers), isolation pays for itself.

### Q2: Should a persistence module exist below the data-owning modules?

**Options:**

| Option | Pro | Con |
|---|---|---|
| **A: No persistence module** (architect, data, enduser) | Each data-owning module manages its own storage. Simpler hierarchy. One fewer abstraction layer. | Schema migrations are distributed across modules; coordinating cross-domain migrations requires convention (table prefixes, dependency headers). |
| **B: Separate persistence module** (security) | Centralizes schema management and migration logic. Separates "what tables exist" from "what business rules apply." | Adds indirection — data modules don't directly own their storage, reducing the "exclusive ownership" clarity. Could become a shared dependency that everything imports. |

**Trade-off:** The architect/data approach gives clearer "this module owns these tables" semantics but relies on convention enforcement. The security approach gives centralized schema governance but may dilute ownership clarity.

### Q3: What schema migration strategy to use?

**Options:**

| Option | Pro | Con |
|---|---|---|
| **A: Table prefix + per-domain migration dirs** (data) | Checkable by linter/test. Clear ownership. Each module evolves its schema independently. | Convention-based, not system-enforced. Cross-domain FK coordination is manual. |
| **B: Implicit via module ownership** (architect, enduser) | Simpler — no migration registry overhead. | Less explicit. "Who owns this table?" answered by documentation, not by schema structure. |
| **C: Defer** | Decide after module boundaries are confirmed. | Delays a foundational infrastructure decision. |

**Trade-off:** The data proposal's prefix convention is the most prescriptive and enforceable. It adds upfront structure cost but makes ownership violations mechanically detectable.

### Q4: Should the wish system be part of the module spec?

**Options:**

| Option | Pro | Con |
|---|---|---|
| **A: Include wish registration in Sources** (enduser) | Closes the "absent data" UX loop. Consumer always gets a clear next action. Simple implementation (metadata write + Cockpit display). | Slightly expands Sources responsibility. May be premature if the priority is getting ingest working first. |
| **B: Defer to later iteration** | Keeps initial scope focused on ingest → query path. | Consumer experience for "data not found" remains unspecified. |

**Trade-off:** Low implementation cost (one Protocol method + one table) vs. scope creep risk. The enduser proposal argues this is essential UX; the others simply don't address it.

### Q5: Where does content-pipeline processing logic live?

**Options:**

| Option | Pro | Con |
|---|---|---|
| **A: Processing is internal to content module** (architect, data, enduser) | Content module encapsulates chunking/embedding as implementation details. Simpler external interface. | Mixes "how to process" with "how to store" inside one module. |
| **B: Processing is a separate module from persistence** (security) | Explicit trust boundary between untrusted-content-handling and storage. Validation gate is a named module. | Adds a module. Content-store becomes passive persistence without processing intelligence. |

**Trade-off:** Security argues this is the most important validation boundary (TB2→TB3). Architect/data/enduser argue that since processing and storage are always called together by ingest, separating them adds indirection without practical benefit.
