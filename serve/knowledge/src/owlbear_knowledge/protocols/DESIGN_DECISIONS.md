# Knowledge Module — Design Decisions

> Per-decision rationale for each CP (Commitment Point) referenced in protocol files.

## CP1 — Canonical Identity

**Naive plan.** Per-document entity identity — each document creates its own entity nodes; a SAME_AS relation links duplicates across documents; a consolidation pipeline periodically merges confirmed duplicates. This is the standard approach in most knowledge graph systems.

**Intent.** Allow the same real-world entity to appear independently in different source documents without requiring global deduplication at ingest time.

**Why we know better now.** The pre-spec codebase implemented exactly this plan. Cost was paid on every cross-source query (Brief demand scenarios 1, 2, 3): traversal had to resolve SAME_AS chains before returning results; the `get_consolidation_candidates` MCP tool was never reliable; reviewed pairs accumulated faster than curators could process them. For a closed-corpus system with curator oversight, the complexity/benefit ratio was unacceptable.

**Final design.** Deterministic entity identity via `(canonicalize_name(name), entity_type)`. Two extractions that produce the same canonical name + type ARE the same entity row. No SAME_AS edges, no consolidation workflows. Graph entities are global (no scope in identity — D53). For names that cannot be canonicalized deterministically (German articles, abbreviations), `Graph.add_alias()` provides evidence-backed alternate names (CP18).

**Cost of reversal.** Re-introducing SAME_AS would require: a consolidation pipeline; `reviewed_pairs` table; `get_consolidation_candidates` MCP tool; SAME_AS-aware traversal in every Graph read path; a disambiguation UX for the curator; and a migration to split currently-merged entity rows.

## CP4 — Stats Composition

**Decision**: Each leaf module exposes `stats()`. `IngestCoordinator.stats()` aggregates them into a unified `IngestStats` view. No separate Query-level stats (D60).

**Rationale**: No single source of truth for aggregate counts — each module is authoritative for its own domain. Composition is cheap (4 function calls); denormalized aggregate tables would introduce stale-cache bugs. Ingest already imports all leaf stores for cascade coordination, so stats aggregation adds zero new coupling.

## CP6 — Typed Source Configuration (Discriminated Union)

**Decision**: `SourceConfig` is a discriminated union keyed on `kind` (FileGlobConfig | UrlListConfig | AuthenticatedWebConfig | InlineConfig).

**Rationale**: Type safety at the boundary eliminates runtime `isinstance` checks and provides IDE autocomplete. Each config shape is validated independently. Adding a new source kind is additive (new Literal + model) without changing existing code.

**Trade-off**: Slightly more boilerplate than a generic `dict[str, JsonValue]` config blob, but catches config errors at parse time rather than at fetch time.

## CP9 — Embedding Encapsulation

**Naive plan.** Expose embedding model name, vector dimensions, sparse/dense format, and ColBERT token-level vectors at the protocol boundary. Consumers construct their own query embeddings and pass vectors directly to search.

**Intent.** Give advanced consumers full control over similarity computation and allow mixed-model experimentation.

**Why we know better now.** Embedding models change frequently — the project has already switched models three times during development. Each switch required coordinating vector dimension changes across every consumer. The MCP shell had to know about sparse vs dense format. Test fixtures broke on every model change. The boundary surface became a coupling bottleneck for a decision that should be purely internal to Content.

**Final design.** No embedding types, dimensions, model names, or vector formats at the protocol boundary. Content owns the full embedding lifecycle: model selection, dimension, sparse/dense strategy, batch size, and query embedding. The boundary accepts text and returns scored results with normalised scores (0.0–1.0). Changing the embedding model requires zero boundary changes.

**Cost of reversal.** Re-exposing vectors would require: vector types on the boundary; query embedding as a consumer responsibility; model-version compatibility tracking; vector migration tooling when models change; sparse/dense format negotiation in the MCP shell.

## CP10 — Agent-External Enrichment

**Naive plan.** Enrichment module owns the LLM: it selects the model, constructs prompts, calls the inference API, parses responses, and retries on failure. The module is a self-contained extraction pipeline.

**Intent.** Provide a turnkey "ingest → enrich → graph" pipeline with no external orchestration.

**Why we know better now.** Agents need control over model selection (cost/quality tradeoffs vary per source), prompt engineering (domain-specific extraction instructions), temperature and sampling (deterministic for CI, creative for discovery), and batching strategy (bulk vs incremental). Embedding the LLM inside the module means: (a) testing requires LLM mocking — slow, flaky, and model-version-dependent; (b) changing extraction strategy requires module-internal changes; (c) cost control is impossible without module awareness of the agent's budget.

**Final design.** Enrichment is a state machine only (enqueue → claim → submit/fail). Agents: (1) call `claim_batch()` to claim chunks; (2) perform LLM extraction externally with their own model, prompt, and retry logic; (3) call `submit_extractions()` with results using `local_ref` for entity cross-referencing (CP20). The module is fully testable without LLM mocking. Agents own extraction strategy.

**Cost of reversal.** Re-internalising the LLM would require: model configuration surface; prompt template registry; inference API client inside the module; retry/backoff logic; cost tracking; and LLM mocking infrastructure for every enrichment test.

## CP12 — Typed Cascade Results

**Decision**: Every destructive cascade operation returns a typed result with affected IDs.

**Rationale**: Audit trail — the caller (Ingest coordinator) can log exactly what was purged. Testing — assertions verify the correct cascade depth. Debugging — if a stale entity survives, the result shows which step missed it.

## CP13 — Ingest as Pure Coordinator

**Naive plan.** Each module knows its upstream dependency and reacts to events: Content listens for source deletions and purges itself; Enrichment listens for content replacements and invalidates queue items; Graph listens for evidence invalidation requests from Enrichment. An event bus connects them.

**Intent.** Loose coupling via events; each module is autonomous and self-cleaning.

**Why we know better now.** Event-driven cascades produce ordering bugs that are invisible in unit tests and only manifest under concurrent load. The 5-step deletion cascade has strict ordering requirements (Content must purge before Graph can invalidate evidence, because Graph needs chunk_ids from Content's purge result). An event bus cannot guarantee this ordering without reintroducing coordination. Additionally, scattered event handlers make the cascade unreadable — no single place shows the full deletion sequence.

**Final design.** Ingest owns no tables. Every write passes through a module protocol. Only Ingest orchestrates cross-module cascades — individual modules never call each other directly. The full cascade sequence is explicit in one place (Ingest), not scattered across event handlers. Each cascade step is idempotent (D63); partial failures are recoverable by re-running the coordination method.

**Cost of reversal.** Re-introducing an event bus would require: event type definitions; subscriber registration; ordering guarantees (saga pattern or sequenced topics); distributed transaction compensation; and scatter-gathering cascade logic across 4+ modules instead of one coordinator.

## CP14 — Content-Trust Marking

**Decision**: `trusted: bool = False` on ContentChunk and ContentIngestRequest.

**Rationale**: Defense in depth for prompt injection. External content (web scrapes, user uploads) is untrusted by default. Only explicitly trusted content (internal docs, verified sources) gets the trusted flag. Downstream agents can filter on trust level.

## CP15 — Content-Hash Internal

**Decision**: Content computes `content_hash` internally. Callers never supply it.

**Rationale**: Single source of truth for deduplication. If callers could supply their own hash, hash mismatches would create phantom duplicates or missed updates. The hash algorithm is an implementation detail that can change without boundary impact.

## CP16 — graph_hops as Facade Hint

**Decision**: `QueryRequest.graph_hops` is a facade-level hint. The Query facade translates it into `TraversalQuery.max_hops` when calling Graph. Query does not own a separate depth concept — one knob in one place (Graph).

**Rationale**: Layering — Graph owns traversal mechanics including depth limiting. The Query facade exposes `graph_hops` so callers can control traversal depth without constructing raw `TraversalQuery` objects. Internally, Query maps this value directly to `max_hops`. No duplication of depth semantics.

## CP17 — Provenance from Chunk Text (No matched_text)

**Decision**: `Provenance.exact_text` is derived from `ContentChunk.text` at query time (R44). No separate `matched_text` column.

**Rationale**: Single source of truth — the chunk text IS the matched text. A separate column would drift if chunks are reprocessed. Storage cost — no duplicate text storage. Simplicity — one less field to maintain consistency for.

## CP18 — Graph-Owned Aliases

**Decision**: Entity aliases are managed by Graph (`add_alias`, `EntityAliasInput/Record`). Not Sources, not Enrichment.

**Rationale**: Aliases are identity operations — they affect entity resolution in `find_entities`. Graph owns entity identity (CP1), so it naturally owns alias resolution. Placing aliases elsewhere would require cross-module writes that violate table ownership.

## CP19 — Evidence Claim Type Enum

**Decision**: `EvidenceClaimType(StrEnum)` with ENTITY/EDGE discriminator on evidence records.

**Rationale**: Enables targeted invalidation — when a chunk is replaced, we need to know whether its claims are about entities (potentially shared with other chunks) or edges (more likely chunk-specific). The discriminator avoids scanning both entity and edge tables to determine claim type.

## CP20 — Enrichment local_ref Mechanism

**Decision**: `ExtractedEntity.local_ref` + `ExtractedRelation.source_ref/target_ref` for within-batch entity references.

**Rationale**: During extraction, entities don't have persistent IDs yet. The LLM produces entity-relation pairs that reference each other. local_ref is a transient key valid only within a single `submit_extractions` call — it maps to persistent IDs after entity resolution. This avoids a two-phase commit where entities must be created before relations.

## CP21 — suggest_intra_doc_edges (Read-Only)

**Decision**: `suggest_intra_doc_edges` returns `SuggestedEdge` tuples but does NOT write to Graph (R37).

**Rationale**: Separation of suggestion from commitment. The agent/curator reviews suggestions and decides which to commit via `Graph.upsert_edge`. This prevents low-confidence intra-doc edges from polluting the graph without review.

## CP22 — claim_ttl as System Invariant

**Decision**: `claim_ttl` removed from `EnrichmentParams` (R41). It is an implementation-internal timeout.

**Rationale**: Callers should not tune claim expiry — it's a correctness invariant (preventing stuck claims from blocking the queue forever), not a performance knob. Exposing it invites misconfiguration (too short = premature reclaim, too long = stuck queue).

## CP23 — SourceDeletionInfo Audit Fields

**Decision**: `SourceDeletionInfo` carries `deleted_at: datetime` and `reason: str | None` (R43).

**Rationale**: Audit trail — the deletion cascade produces a `PurgeResult` that should be traceable to WHO deleted it, WHEN, and WHY. Without these fields, the audit log would require a separate lookup to the (now-deleted) source record.

## CP24 — Discriminated Union SourceWish.kind Optional

**Decision**: `SourceWish.expected_kind: SourceKind | None = None` (R39).

**Rationale**: Wishes express demand, not implementation. A wish like "I need ISMS compliance docs" may not know whether they'll come from a file glob or authenticated web source. Making kind optional on wishes (while required on registrations) separates demand from fulfilment.

## CP25 — Metadata Merge Semantics

**Decision**: Shallow merge (key-level replace). When `SourceUpdate.metadata` or similar partial-update types carry metadata, provided keys replace existing keys; absent keys are preserved. No deep merge.

**Rationale**: Predictable behaviour — callers know exactly which keys they're overwriting without reasoning about nested structures. Implementation simplicity — `{**existing, **update}` in Python. No recursive merge ambiguity (what does "merge" mean for lists? for nested dicts?). Callers who need to clear a key set it to `None` explicitly.

---

## Demand Scenario Vocabulary Mapping (D55)

Canonical encoding of real-world concepts from the Brief demand scenarios into protocol vocabulary. Ensures consistent graph structure across agents and extraction prompts.

| Domain concept | Protocol encoding |
|----------------|-------------------|
| ISMS control (e.g. A.8.1) | `EntityType.STANDARD` + `metadata.subtype = "control"` |
| Compliance approval | `RelationType.COMPLIES_WITH` + `metadata.approval_state = "approved"` |
| Access right / permission | `EntityType.PROCESS` + `metadata.subtype = "access_right"` |
| Service / Tool | `EntityType.TOOL` |
| PDS component (Porsche Design System) | `EntityType.PRODUCT` + `metadata.subtype = "component"` |
| Corporate identity alignment | `RelationType.COMPLIES_WITH` + `metadata.domain = "corporate_identity"` |

**Convention**: `metadata.subtype` differentiates specialisations within a base `EntityType`. `metadata.domain` scopes relations to a governance domain. Both are free-text strings validated by extraction prompt instructions, not by the protocol layer.
