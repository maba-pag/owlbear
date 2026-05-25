# Knowledge Module — Protocol Architecture

> **This spec is authoritative. Code conforms to it.**

## Overview

The knowledge module is structured as 6 engine modules with strict ownership boundaries. Communication happens exclusively via Protocol interfaces and frozen boundary types.

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Shell (zero logic)                │
├─────────────────────────────────────────────────────────┤
│  QueryService ←── read path (coordinator, no tables)    │
│  IngestPipeline ←── write path (coordinator, no tables) │
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
| **Graph** | `graph_entities`, `graph_edges`, `graph_evidence` | Entity/edge CRUD, evidence tracking, traversal |
| **Enrichment** | `enrich_chunk_state` | Extraction state machine, Phase 2 inference |
| **Ingest** | No tables | Write-path coordination, safety, cascade |
| **Query** | No tables | Read-path composition, provenance, stats |

## Dependency Graph (acyclic)

```
Sources ─────────────────────────────── (leaf, zero deps)
Content ─────────────────────────────── (leaf, zero deps)
Graph ───────────────────────────────── (leaf, zero deps)
Enrichment ──→ GraphStore, ContentStore
Ingest ──→ SourceStore, ContentStore, EnrichmentEngine, GraphStore
Query ──→ SourceStore, ContentStore, GraphStore, EnrichmentEngine (stats)
```

Leaf modules (Sources, Content, Graph) have zero knowledge-module dependencies. They import only from `common.py`.

## Shared Infrastructure (`common.py`)

Contains only types genuinely used by ≥2 modules:

- `BoundaryModel` — frozen + extra="forbid" base for all boundary types
- `JsonValue` — recursive JSON-safe type union
- `Metadata` — `dict[str, JsonValue]`
- `canonicalize_name()` — entity identity normalisation

Module-specific enums and models live in their respective module files.

## Design Decisions

### CP1 — Canonical Identity (no SAME_AS, no consolidation)

Entity identity is deterministic: `(canonicalize_name(name), kind, scope)`. Two entities with the same tuple are the same row. This eliminates:
- The SAME_AS relation (excluded from RelationKind)
- Consolidation workflows (no consolidation methods on any Protocol)
- Entity deduplication ambiguity

Evidence is tracked separately (graph_evidence table) enabling many-to-many provenance: one entity can be supported by evidence from N documents.

### CP4 — Stats Composition

Each leaf module exposes a `stats()` method. QueryService composes them into AggregateStats for the MCP `get_stats` tool.

### CP9 — Embedding Encapsulation

Embedding model, vector dimensions, sparse format, and ColBERT details are internal to Content. No vector types appear at the boundary. Changing the embedding model requires zero boundary changes.

### CP10 — Agent-External Enrichment

The Enrichment module is a state machine only. It does NOT call LLMs. Agents:
1. Call `next_pending_batch()` to claim chunks
2. Perform LLM extraction externally (with their own model/prompt)
3. Call `store_extraction()` with results

This keeps Enrichment testable without LLM mocking and lets agents own extraction strategy.

### CP12 — Typed Cascade Results

Cross-module invalidation uses imperative method calls (no event bus). Each purge/cascade method returns a typed result object for audit:
- `ContentPurgeResult` (document/chunk/vector IDs removed)
- `EnrichmentPurgeResult` (chunks purged)
- `PurgeEvidenceResult` (evidence/entity/edge counts removed)

### CP13 — Ingest as Pure Coordinator

Ingest owns no tables. Every write passes through a module protocol. The cascade sequence for source purge is:
1. `Content.purge_source(source_id)` → removes docs/chunks/vectors
2. `Enrichment.purge_source(source_id)` → removes enrich state
3. `Graph.purge_evidence_by_source(source_id)` → removes evidence + orphans

### CP14 — Content-Trust Safety Invariant

All ingested content is marked as externally-sourced before storage. This ensures downstream agents treat retrieved text as data, not as trusted system instructions.

## Boundary Conventions

- **Frozen types**: All boundary types inherit `BoundaryModel` (immutable, strict)
- **Tuple returns**: Protocol methods return `tuple[T, ...]` for collections (immutable snapshots)
- **Metadata**: `dict[str, JsonValue]` — JSON-serialisable, type-safe
- **Async**: Only on I/O-bound operations (Content.ingest, Content.search, Ingest.*, Query.search)
- **Doc depth**: Every Protocol method documents Guarantees, Non-guarantees, Side effects, Raises

## Table Ownership (CI-enforced)

| Prefix | Owner | Rule |
|--------|-------|------|
| `source_*` | Sources | Only SourceStore writes |
| `content_*` | Content | Only ContentStore writes |
| `graph_*` | Graph | Only GraphStore writes |
| `enrich_*` | Enrichment | Only EnrichmentEngine writes |

CI enforcement: static analysis verifies no module writes to another module's tables.

## Import Direction (CI-enforced)

- Leaf modules import only `common.py`
- Enrichment may import Graph and Content boundary types
- Ingest may import all module boundary types
- Query may import all module boundary types
- MCP shell imports only from `protocols/__init__.py`

## Testing Strategy

### Module acceptance tests (independent)
Each module is tested in isolation with mocked dependencies. Tests verify:
- Protocol method guarantees hold
- State machine transitions are correct
- Error conditions raise documented exceptions
- Table ownership is not violated

### End-to-end scenario tests (3 demand scenarios)
1. ISMS compliance chain (Standards → Controls → Approvals)
2. Access rights lookup (User → Tool → Required permissions)
3. Design system discovery (PDS component → CI pipeline → Docs)

## Spec Amendment Process

Interface changes require spec amendment tracked in version control. Enum values are additive (non-breaking). Method signature changes or semantic obligation changes require a new CP entry documenting rationale.
