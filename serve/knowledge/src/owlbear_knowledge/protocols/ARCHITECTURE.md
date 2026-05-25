# Knowledge Module — Protocol Architecture

> **This spec is authoritative. Code conforms to it.**

## Overview

The knowledge module is structured as 6 engine modules with strict ownership boundaries. Communication happens exclusively via Protocol interfaces and frozen boundary types.

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Shell (zero logic)                │
├─────────────────────────────────────────────────────────┤
│  QueryFacade ←── read path (coordinator, no tables)     │
│  IngestCoordinator ←── write path (coordinator, no tables) │
├─────────┬───────────┬───────────┬───────────────────────┤
│ Sources │  Content  │   Graph   │     Enrichment        │
│source_* │ content_* │  graph_*  │      enrich_*         │
│         │ + Qdrant  │           │                       │
└─────────┴───────────┴───────────┴───────────────────────┘
```

## Module Responsibilities

| Module | Owns | Role |
|--------|------|------|
| **Sources** | `source_*` tables | Registry, lifecycle state, health tracking, wish fulfilment |
| **Content** | `content_*` tables + Qdrant collections | Chunking, embedding, storage, hybrid search |
| **Graph** | `graph_*` tables | Entity/edge CRUD, evidence tracking, alias resolution, traversal |
| **Enrichment** | `enrich_*` tables | Extraction state machine, queue management, edge suggestion |
| **Ingest** | No tables | Write-path coordination, cascade orchestration |
| **Query** | No tables | Read-path composition, provenance assembly, context rendering |

## Dependency Graph (acyclic)

```
Sources ─────────────────────────────── (leaf, zero deps)
Content ─────────────────────────────── (leaf, zero deps)
Graph ───────────────────────────────── (leaf, zero deps)
Enrichment ──→ GraphStore, ContentStore
Ingest ──→ SourceStore, ContentStore, EnrichmentStore, GraphStore
Query ──→ ContentStore, GraphStore
```

Leaf modules (Sources, Content, Graph) have zero knowledge-module dependencies. They import only from `common.py`.

## Shared Infrastructure (`common.py`)

Contains only types genuinely used by ≥2 modules:

- `BoundaryModel` — frozen, strict, extra="forbid" base for all boundary types
- `JsonValue` — PEP 695 recursive JSON-safe type union
- `Metadata` — `dict[str, JsonValue]`
- `EntityType` / `RelationType` — shared vocabularies (12 entity + 13 relation)
- `canonicalize_name()` — entity identity normalisation (lowercase, strip, trailing punctuation removal)

Module-specific enums and models live in their respective module files.

## CI-Enforceable Registries (`_registry.py`) — R40

Three compile-time registries serve as single source of truth for ownership:

| Registry | Purpose |
|----------|---------|
| `TABLE_OWNERSHIP` | Module → table-name prefixes it may write |
| `QDRANT_COLLECTIONS` | Module → Qdrant collection names it owns |
| `MCP_TOOL_ROUTING` | Tool name → module responsible for handling |

Adding a table, collection, or MCP tool without updating `_registry.py` is a CI failure. The MCP shell uses `MCP_TOOL_ROUTING` for dispatch without transformation.

## Cascade Sequences (Ingest-Coordinated)

### Source Deletion Cascade

```
1. Sources.delete_source(id, reason) → SourceDeletionInfo
2. Content.purge_source(source_id) → ContentPurgeResult (has chunk_ids)
3. Enrichment.discard_chunks(chunk_ids) → remove pending queue items
4. Enrichment.purge_source(source_id) → remove extraction records
5. Graph.invalidate_evidence_by_chunks(chunk_ids) → evidence + orphans
```

### Content Replacement Cascade (re-ingest)

```
1. Content.ingest → ContentIngestResult (state=REPLACED, replaced_chunk_ids)
2. Enrichment.discard_chunks(replaced_chunk_ids) → clean stale queue items
3. Graph.invalidate_evidence_by_chunks(replaced_chunk_ids) → clean evidence
4. Enrichment.enqueue_chunks(new_chunk_ids) → queue for extraction
```

## Design Decisions

> Per-decision rationale with CP references is in `DESIGN_DECISIONS.md` (R46).

### CP1 — Canonical Identity (no SAME_AS, no consolidation)

Entity identity is deterministic: `(canonicalize_name(name), entity_type)`. Two entities with the same tuple are the same row. This eliminates:
- The SAME_AS relation (not in RelationType)
- Consolidation workflows
- Entity deduplication ambiguity

Identity aliases are managed through Graph's `add_alias` mechanism — evidence-backed alternate names that resolve transparently in `find_entities`.

### CP4 — Stats Composition

Each leaf module exposes a `stats()` method. QueryFacade and IngestCoordinator compose them for unified views.

### CP9 — Embedding Encapsulation

Embedding model, vector dimensions, sparse format, and ColBERT details are internal to Content. No vector types appear at the boundary. Changing the embedding model requires zero boundary changes.

### CP10 — Agent-External Enrichment

The Enrichment module is a state machine only. It does NOT call LLMs. Agents:
1. Call `claim_batch()` to claim chunks
2. Perform LLM extraction externally (with their own model/prompt)
3. Call `submit_extractions()` with results (using `local_ref` for entity cross-referencing)

This keeps Enrichment testable without LLM mocking and lets agents own extraction strategy.

### CP12 — Typed Cascade Results

Cross-module invalidation uses imperative method calls (no event bus). Each cascade method returns a typed result object for audit:
- `ContentPurgeResult` (document/chunk/vector IDs removed)
- `EnrichmentPurgeResult` (queue items + extractions removed)
- `EnrichmentDiscardResult` (chunks discarded from queue)
- `EvidenceInvalidationResult` (evidence + orphaned entities/edges)

### CP13 — Ingest as Pure Coordinator

Ingest owns no tables. Every write passes through a module protocol. Only Ingest orchestrates cross-module cascades — individual modules never call each other directly.

### CP14 — Content-Trust Safety Invariant

All ingested content carries `trusted: bool = False` by default. Callers must explicitly opt in to mark content as trusted. Downstream agents treat untrusted text as data, not as system instructions.

### CP15 — Content-Hash Single Source of Truth

Content always computes `content_hash` internally from the normalised text. Callers do not supply or influence the hash — it is purely internal for deduplication.

## max_chars Policy (R49)

The `ContextRenderRequest.max_chars` field controls the LLM context budget:
- Default: 8000 characters
- Range: 100–100,000
- Truncation: when output exceeds budget, `RenderedContext.truncated = True`
- Strategy: implementation-defined (may truncate lower-scored chunks first)

No `max_graph_depth` parameter exists at the Query boundary — traversal depth is controlled exclusively by `TraversalQuery.max_hops` on GraphStore (R42).

## Boundary Conventions

- **Frozen types**: All boundary types inherit `BoundaryModel` (frozen=True, strict=True, extra="forbid")
- **Tuple returns**: Protocol methods return `tuple[T, ...]` for collections (immutable snapshots)
- **Metadata**: `dict[str, JsonValue]` — JSON-serialisable, type-safe
- **Async**: Only on I/O-bound operations (Content.ingest, Content.search, Ingest.*, Query.search)
- **Doc depth**: Every Protocol method documents Guarantees, Non-guarantees, Side effects, Raises

## Table Ownership (CI-enforced via `_registry.py`)

| Prefix | Owner | Rule |
|--------|-------|------|
| `source_*` | Sources | Only SourceStore writes |
| `content_*` | Content | Only ContentStore writes |
| `graph_*` | Graph | Only GraphStore writes |
| `enrich_*` | Enrichment | Only EnrichmentStore writes |

## Import Direction (CI-enforced)

- Leaf modules import only `common.py`
- Enrichment may import Graph and Content boundary types
- Ingest may import all module boundary types
- Query may import Content and Graph boundary types
- MCP shell imports only from `protocols/__init__.py`

## Testing Strategy

### Module acceptance tests (independent)
Each module is tested in isolation with mocked dependencies. Tests verify:
- Protocol method guarantees hold
- State machine transitions are correct
- Error conditions raise documented exceptions
- Table ownership is not violated

### End-to-end scenario tests (Brief demand scenarios — R50)

Linked to Brief demand scenarios in `.owlbear/briefs/draft-knowledge-modularization/brief.md`:

1. **ISMS compliance chain** — Standards → Controls → Approvals (ingest + enrich + traverse)
2. **Access rights lookup** — User → Tool → Required permissions (search + entity lookup)
3. **Design system discovery** — PDS component → CI pipeline → Docs (multi-hop traversal)

## Spec Amendment Process

Interface changes require spec amendment tracked in version control. Enum values are additive (non-breaking). Method signature changes or semantic obligation changes require a new CP entry with rationale documented in `DESIGN_DECISIONS.md`.
