"""CI-enforceable registries — single source of truth for ownership mappings.

This module defines compile-time-checkable registries that CI can enforce
against the implementation. Adding a table, collection, or MCP tool
without updating these registries is a CI failure (R40).
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

# ---------------------------------------------------------------------------
# Module vocabulary (D59)
# ---------------------------------------------------------------------------


class KnowledgeModule(StrEnum):
    """Closed set of knowledge engine modules."""

    SOURCES = "sources"
    CONTENT = "content"
    GRAPH = "graph"
    ENRICHMENT = "enrichment"
    INGEST = "ingest"
    QUERY = "query"


# ---------------------------------------------------------------------------
# Table ownership: module → table name prefixes it may write
# ---------------------------------------------------------------------------

TABLE_OWNERSHIP: Final[Mapping[KnowledgeModule, tuple[str, ...]]] = {
    KnowledgeModule.SOURCES: ("source_",),
    KnowledgeModule.CONTENT: ("content_",),
    KnowledgeModule.GRAPH: ("graph_",),
    KnowledgeModule.ENRICHMENT: ("enrich_",),
}
"""Maps module → tuple of table-name prefixes it is allowed to write.

CI enforcement: any SQL CREATE TABLE or INSERT/UPDATE/DELETE that targets a
table not matching the module's prefix is a violation.

Coordinators (Ingest, Query) own no tables — they delegate all writes.
"""

# ---------------------------------------------------------------------------
# Infrastructure tables (not module-owned)
# ---------------------------------------------------------------------------

INFRASTRUCTURE_TABLES: Final[frozenset[str]] = frozenset({"schema_version"})
"""Tables that exist outside module ownership (migrations, metadata).

CI enforcement: a table must match either a TABLE_OWNERSHIP prefix or
appear in INFRASTRUCTURE_TABLES. Unmatched tables are violations.
"""

# ---------------------------------------------------------------------------
# Qdrant collection ownership: module → collection names
# ---------------------------------------------------------------------------

QDRANT_COLLECTIONS: Final[Mapping[KnowledgeModule, tuple[str, ...]]] = {
    KnowledgeModule.CONTENT: ("content_chunks",),
}
"""Maps module → Qdrant collection names it owns.

Only Content writes vector collections. Graph, Enrichment, and Sources
have no vector storage.
"""

# ---------------------------------------------------------------------------
# MCP tool routing: tool name → Protocol.method that handles it (D58)
# ---------------------------------------------------------------------------

MCP_TOOL_ROUTING: Final[Mapping[str, str]] = {
    "knowledge_search": "QueryFacade.search",
    "knowledge_ingest": "IngestCoordinator.ingest",
    "knowledge_sources_list": "SourceStore.list_sources",
    "knowledge_sources_register": "SourceStore.register_source",
    "knowledge_sources_delete": "IngestCoordinator.delete_source",
    "knowledge_sources_refresh": "IngestCoordinator.refresh",
    "knowledge_entity_lookup": "QueryFacade.lookup_entity",
    "knowledge_stats": "IngestCoordinator.stats",
    "knowledge_enrichment_claim_batch": "EnrichmentStore.claim_batch",
    "knowledge_enrichment_store": "EnrichmentStore.submit_extractions",
    "knowledge_enrichment_retry": "EnrichmentStore.reset_failed",
}
"""Maps MCP tool name → Protocol.method responsible for handling the call.

The MCP shell is zero-logic — it dispatches to the mapped method without
transformation. CI enforcement: any tool not in this registry is rejected
at startup. The dotted value is resolvable via reflection on the Protocol
classes.
"""
