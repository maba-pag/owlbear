"""owlbear_knowledge.protocols — Public boundary types and store protocols.

This package is the single import surface for all typed boundary models
used across the knowledge system. Internal modules import from here;
external consumers (MCP shell, tests) also import exclusively from here.

Re-exports are grouped by module and sorted alphabetically within groups.
"""

# --- common ---
from owlbear_knowledge.protocols.common import (
    BoundaryModel,
    EntityType,
    JsonValue,
    Metadata,
    RelationType,
    canonicalize_name,
)

# --- registry ---
from owlbear_knowledge.protocols.registry import (
    INFRASTRUCTURE_TABLES,
    MCP_TOOL_ROUTING,
    QDRANT_COLLECTIONS,
    TABLE_OWNERSHIP,
    KnowledgeModule,
)

# --- sources ---
from owlbear_knowledge.protocols.sources import (
    AuthenticatedWebConfig,
    ConfiguredSourceRecord,
    FetchTransport,
    FileGlobConfig,
    InlineConfig,
    SourceConfig,
    SourceDeletionInfo,
    SourceHealth,
    SourceHealthReport,
    SourceKind,
    SourceRecord,
    SourceRegistration,
    SourceState,
    SourceStats,
    SourceStore,
    SourceUpdate,
    SourceWish,
    UrlListConfig,
    WishedSourceRecord,
)

# --- content ---
from owlbear_knowledge.protocols.content import (
    ContentChunk,
    ContentDocument,
    ContentIngestRequest,
    ContentIngestResult,
    ContentIngestState,
    ContentPurgeResult,
    ContentSearchQuery,
    ContentSearchResult,
    ContentStats,
    ContentStore,
)

# --- graph ---
from owlbear_knowledge.protocols.graph import (
    AdjacencyQuery,
    ChunkClaims,
    EdgeInput,
    EdgeRecord,
    EntityAliasInput,
    EntityAliasRecord,
    EntityInput,
    EntityQuery,
    EntityRecord,
    EvidenceClaimType,
    EvidenceInvalidationResult,
    EvidenceInput,
    EvidenceRecord,
    GraphStats,
    GraphStore,
    TraversalDirection,
    TraversalQuery,
    TraversalResult,
)

# --- enrichment ---
from owlbear_knowledge.protocols.enrichment import (
    EnrichmentBatch,
    EnrichmentDiscardResult,
    EnrichmentParams,
    EnrichmentPurgeResult,
    EnrichmentQueueItem,
    EnrichmentState,
    EnrichmentStats,
    EnrichmentStore,
    ExtractionResult,
    ExtractedEntity,
    ExtractedRelation,
    SuggestedEdge,
)

# --- ingest ---
from owlbear_knowledge.protocols.ingest import (
    IngestCoordinator,
    IngestDocument,
    IngestRequest,
    IngestResult,
    IngestStats,
    PurgeResult,
    PurgeStatus,
    RefreshError,
    RefreshRequest,
    RefreshResult,
)

# --- query ---
from owlbear_knowledge.protocols.query import (
    ContextRenderRequest,
    EntityLookupRequest,
    EntityLookupResult,
    Provenance,
    QueryFacade,
    QueryRequest,
    QueryResult,
    RenderedContext,
)

__all__ = [
    # common
    "BoundaryModel",
    "EntityType",
    "JsonValue",
    "Metadata",
    "RelationType",
    "canonicalize_name",
    # registry
    "INFRASTRUCTURE_TABLES",
    "KnowledgeModule",
    "MCP_TOOL_ROUTING",
    "QDRANT_COLLECTIONS",
    "TABLE_OWNERSHIP",
    # sources
    "AuthenticatedWebConfig",
    "ConfiguredSourceRecord",
    "FetchTransport",
    "FileGlobConfig",
    "InlineConfig",
    "SourceConfig",
    "SourceDeletionInfo",
    "SourceHealth",
    "SourceHealthReport",
    "SourceKind",
    "SourceRecord",
    "SourceRegistration",
    "SourceState",
    "SourceStats",
    "SourceStore",
    "SourceUpdate",
    "SourceWish",
    "UrlListConfig",
    "WishedSourceRecord",
    # content
    "ContentChunk",
    "ContentDocument",
    "ContentIngestRequest",
    "ContentIngestResult",
    "ContentIngestState",
    "ContentPurgeResult",
    "ContentSearchQuery",
    "ContentSearchResult",
    "ContentStats",
    "ContentStore",
    # graph
    "AdjacencyQuery",
    "ChunkClaims",
    "EdgeInput",
    "EdgeRecord",
    "EntityAliasInput",
    "EntityAliasRecord",
    "EntityInput",
    "EntityQuery",
    "EntityRecord",
    "EvidenceClaimType",
    "EvidenceInvalidationResult",
    "EvidenceInput",
    "EvidenceRecord",
    "GraphStats",
    "GraphStore",
    "TraversalDirection",
    "TraversalQuery",
    "TraversalResult",
    # enrichment
    "EnrichmentBatch",
    "EnrichmentDiscardResult",
    "EnrichmentParams",
    "EnrichmentPurgeResult",
    "EnrichmentQueueItem",
    "EnrichmentState",
    "EnrichmentStats",
    "EnrichmentStore",
    "ExtractionResult",
    "ExtractedEntity",
    "ExtractedRelation",
    "SuggestedEdge",
    # ingest
    "IngestCoordinator",
    "IngestDocument",
    "IngestRequest",
    "IngestResult",
    "IngestStats",
    "PurgeResult",
    "PurgeStatus",
    "RefreshError",
    "RefreshRequest",
    "RefreshResult",
    # query
    "ContextRenderRequest",
    "EntityLookupRequest",
    "EntityLookupResult",
    "Provenance",
    "QueryFacade",
    "QueryRequest",
    "QueryResult",
    "RenderedContext",
]
