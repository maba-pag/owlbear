"""Shared TypedDicts and constants for owlbear-mcp-knowledge."""

from __future__ import annotations

from typing import TypedDict

_DEFAULT_KB_PATH = ".owlbear/knowledge/local.db"
_DEFAULT_QDRANT_PATH = ".owlbear/knowledge/vectors"
_MAX_ENRICHMENT_BATCH_SIZE = 100

_CANDIDATE_ID_BASE_PARTS = 3
_CANDIDATE_ID_EXTENDED_PARTS = 5
_CANDIDATE_SOURCE_COUNT = 2


class SearchResult(TypedDict):
    """A single knowledge-base search result."""

    title: str
    score: float
    snippet: str
    entity_type: str | None
    retrieval_path: str
    graph_context: str
    entities: list[SearchEntity]
    related_sources: list[RelatedSource]
    source: SearchSource


class SearchEntity(TypedDict):
    """A single entity mention attached to a search result."""

    name: str
    type: str


class RelatedSource(TypedDict):
    """A relationship edge from this result to another source."""

    name: str
    relationship: str
    entity: str


class SearchSource(TypedDict):
    """Source metadata attached to a search result."""

    name: str
    url: str


class SourceInfo(TypedDict):
    """A registered knowledge source entry."""

    id: str
    name: str
    source_type: str
    scope: str
    last_refreshed_at: str | None
    last_checked_at: str | None
    last_error: str | None
    enabled: bool
    fetch_method: str


class EntityInfo(TypedDict):
    """A knowledge-graph entity entry."""

    name: str
    entity_type: str
    description: str


class StatsResult(TypedDict):
    """Knowledge-base summary statistics."""

    documents: int
    entities: int
    edges: int
    total_sources: int
    total_chunks: int
    chunks_enriched_ratio: float
    consolidation_candidates_remaining: int


class EnrichmentChunk(TypedDict):
    """Chunk payload claimed by enrichment workers."""

    chunk_id: str
    text: str
    doc_title: str
    section_path: str | None
    source_name: str | None
    document_id: str
    source_id: str
    scope: str


class ConsolidationCandidate(TypedDict):
    """Cross-source entity pair eligible for phase-2 consolidation."""

    candidate_id: str
    entity_id_a: str
    entity_id_b: str
    entity_name: str
    source_a: str
    source_b: str
    source_a_name: str
    source_b_name: str
    source_a_chunk: str
    source_b_chunk: str


class _BrowserContentFetcher:
    """Protocol-compatible browser fetcher placeholder.

    The browser MCP server owns Playwright lifecycle. This placeholder preserves
    fetch-method routing behavior in mcp-knowledge without introducing a direct
    package dependency on owlbear_browser.
    """

    async def fetch(self, url: str) -> str:
        """Raise a clear error until a live browser fetcher is injected."""
        _ = url
        msg = "browser fetcher selected but no browser session is wired"
        raise RuntimeError(msg)
