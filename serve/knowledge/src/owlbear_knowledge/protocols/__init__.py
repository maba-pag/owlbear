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
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    SuggestedEdge,
)

# --- fetcher ---
from owlbear_knowledge.protocols.fetcher import (
    FetchedDocument,
    FetchError,
    FetchResult,
    SourceFetcher,
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
    EvidenceInput,
    EvidenceInvalidationResult,
    EvidenceRecord,
    GraphStats,
    GraphStore,
    TraversalDirection,
    TraversalQuery,
    TraversalResult,
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

__all__ = [
    # registry
    "INFRASTRUCTURE_TABLES",
    "MCP_TOOL_ROUTING",
    "QDRANT_COLLECTIONS",
    "TABLE_OWNERSHIP",
    # graph
    "AdjacencyQuery",
    # sources
    "AuthenticatedWebConfig",
    # common
    "BoundaryModel",
    "ChunkClaims",
    "ConfiguredSourceRecord",
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
    # query
    "ContextRenderRequest",
    "EdgeInput",
    "EdgeRecord",
    # enrichment
    "EnrichmentBatch",
    "EnrichmentDiscardResult",
    "EnrichmentParams",
    "EnrichmentPurgeResult",
    "EnrichmentQueueItem",
    "EnrichmentState",
    "EnrichmentStats",
    "EnrichmentStore",
    "EntityAliasInput",
    "EntityAliasRecord",
    "EntityInput",
    "EntityLookupRequest",
    "EntityLookupResult",
    "EntityQuery",
    "EntityRecord",
    "EntityType",
    "EvidenceClaimType",
    "EvidenceInput",
    "EvidenceInvalidationResult",
    "EvidenceRecord",
    "ExtractedEntity",
    "ExtractedRelation",
    "ExtractionResult",
    "FetchError",
    "FetchResult",
    "FetchTransport",
    # fetcher
    "FetchedDocument",
    "FileGlobConfig",
    "GraphStats",
    "GraphStore",
    # ingest
    "IngestCoordinator",
    "IngestDocument",
    "IngestRequest",
    "IngestResult",
    "IngestStats",
    "InlineConfig",
    "JsonValue",
    "KnowledgeModule",
    "Metadata",
    "Provenance",
    "PurgeResult",
    "PurgeStatus",
    "QueryFacade",
    "QueryRequest",
    "QueryResult",
    "RefreshError",
    "RefreshRequest",
    "RefreshResult",
    "RelationType",
    "RenderedContext",
    "SourceConfig",
    "SourceDeletionInfo",
    "SourceFetcher",
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
    "SuggestedEdge",
    "TraversalDirection",
    "TraversalQuery",
    "TraversalResult",
    "UrlListConfig",
    "WishedSourceRecord",
    "canonicalize_name",
]
