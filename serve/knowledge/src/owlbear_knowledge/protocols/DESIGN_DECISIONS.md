# Knowledge Module — Design Decisions

> Per-decision rationale for each CP (Commitment Point) referenced in protocol files.

## CP1 — Canonical Identity

**Decision**: Deterministic entity identity via `(canonicalize_name(name), entity_type)`. No SAME_AS edges, no consolidation workflows.

**Rationale**: Eliminates an entire class of ambiguity — if two extractions produce the same canonical name + type, they ARE the same entity. Consolidation introduces unbounded complexity (merge conflicts, lossy merges, user disambiguation UX) for marginal benefit in a closed-corpus system.

**Trade-off**: Homonyms (same name, same type, different real-world entity) are forcibly merged. Acceptable because scope + metadata disambiguate in practice, and the knowledge base is curator-supervised.

## CP4 — Stats Composition

**Decision**: Each leaf module exposes `stats()`. Coordinators (Ingest, Query) aggregate without owning counts.

**Rationale**: No single source of truth for aggregate counts — each module is authoritative for its own domain. Composition is cheap (4 function calls); denormalized aggregate tables would introduce stale-cache bugs.

## CP6 — Typed Source Configuration (Discriminated Union)

**Decision**: `SourceConfig` is a discriminated union keyed on `kind` (FileGlobConfig | UrlListConfig | AuthenticatedWebConfig | InlineConfig).

**Rationale**: Type safety at the boundary eliminates runtime `isinstance` checks and provides IDE autocomplete. Each config shape is validated independently. Adding a new source kind is additive (new Literal + model) without changing existing code.

**Trade-off**: Slightly more boilerplate than a generic `dict[str, JsonValue]` config blob, but catches config errors at parse time rather than at fetch time.

## CP9 — Embedding Encapsulation

**Decision**: No embedding types, dimensions, or model names at the protocol boundary.

**Rationale**: Embedding models change frequently (weekly in some cases). Exposing vector dimensions or model names would make every embedding upgrade a breaking API change. Content owns the full embedding lifecycle internally.

## CP10 — Agent-External Enrichment

**Decision**: Enrichment is a state machine (enqueue → claim → submit/fail). LLM calls happen outside.

**Rationale**: Testability — the enrichment module is fully testable without LLM mocking. Flexibility — agents choose their model, prompt, temperature, and retry strategy. Cost control — agents can batch, throttle, or skip enrichment without module awareness.

## CP12 — Typed Cascade Results

**Decision**: Every destructive cascade operation returns a typed result with affected IDs.

**Rationale**: Audit trail — the caller (Ingest coordinator) can log exactly what was purged. Testing — assertions verify the correct cascade depth. Debugging — if a stale entity survives, the result shows which step missed it.

## CP13 — Ingest as Pure Coordinator

**Decision**: Ingest owns no tables. Only Ingest calls cross-module cascades.

**Rationale**: Single Responsibility — leaf modules don't need to know about each other. Testing — leaf modules are tested in complete isolation. Ordering — cascade order is explicit in one place (Ingest), not scattered across event handlers.

## CP14 — Content-Trust Marking

**Decision**: `trusted: bool = False` on ContentChunk and ContentIngestRequest.

**Rationale**: Defense in depth for prompt injection. External content (web scrapes, user uploads) is untrusted by default. Only explicitly trusted content (internal docs, verified sources) gets the trusted flag. Downstream agents can filter on trust level.

## CP15 — Content-Hash Internal

**Decision**: Content computes `content_hash` internally. Callers never supply it.

**Rationale**: Single source of truth for deduplication. If callers could supply their own hash, hash mismatches would create phantom duplicates or missed updates. The hash algorithm is an implementation detail that can change without boundary impact.

## CP16 — No max_graph_depth at Query Boundary

**Decision**: Removed `max_graph_depth` from QueryRequest (R42). Traversal depth is controlled exclusively by `TraversalQuery.max_hops` on GraphStore.

**Rationale**: Layering violation — Query was duplicating a Graph-owned concern. The Query facade passes `graph_hops` to construct a `TraversalQuery`, but doesn't need its own depth concept. One knob (max_hops) in one place (Graph).

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
