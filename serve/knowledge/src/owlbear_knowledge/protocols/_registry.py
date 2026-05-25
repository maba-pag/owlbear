"""CI-enforceable registries — single source of truth for ownership mappings.

This module defines compile-time-checkable registries that CI can enforce
against the implementation. Adding a table, collection, or MCP tool
without updating these registries is a CI failure (R40).
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Table ownership: module → table name prefixes it may write
# ---------------------------------------------------------------------------

TABLE_OWNERSHIP: Final[dict[str, tuple[str, ...]]] = {
    "sources": ("source_",),
    "content": ("content_",),
    "graph": ("graph_",),
    "enrichment": ("enrich_",),
}
"""Maps module name → tuple of table-name prefixes it is allowed to write.

CI enforcement: any SQL CREATE TABLE or INSERT/UPDATE/DELETE that targets a
table not matching the module's prefix is a violation.
"""

# ---------------------------------------------------------------------------
# Qdrant collection ownership: module → collection names
# ---------------------------------------------------------------------------

QDRANT_COLLECTIONS: Final[dict[str, tuple[str, ...]]] = {
    "content": ("content_chunks",),
}
"""Maps module name → Qdrant collection names it owns.

Only Content writes vector collections. Graph, Enrichment, and Sources
have no vector storage.
"""

# ---------------------------------------------------------------------------
# MCP tool routing: tool name → module that handles it
# ---------------------------------------------------------------------------

MCP_TOOL_ROUTING: Final[dict[str, str]] = {
    "knowledge_search": "query",
    "knowledge_ingest": "ingest",
    "knowledge_sources_list": "sources",
    "knowledge_sources_register": "sources",
    "knowledge_sources_delete": "ingest",  # deletion cascade
    "knowledge_sources_refresh": "ingest",
    "knowledge_entity_lookup": "query",
    "knowledge_stats": "ingest",
}
"""Maps MCP tool name → module responsible for handling the call.

The MCP shell is zero-logic — it dispatches to the mapped module without
transformation. CI enforcement: any tool not in this registry is rejected
at startup.
"""
