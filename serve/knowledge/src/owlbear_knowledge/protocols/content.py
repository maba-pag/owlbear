"""ContentStore Protocol — Content module public surface.

Module responsibility: raw-to-searchable content pipeline. Accepts text,
chunks it, embeds it, stores vectors, and provides hybrid search. Owns
tables ``content_*`` and Content-owned Qdrant collections.

Has zero dependencies on other knowledge modules.

Embedding model, chunking strategy, and vector storage layout are
internal implementation details NOT exposed at this boundary (CP9).

Table ownership: only Content writes ``content_*`` tables and
Content-owned Qdrant collections.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field

from owlbear_knowledge.protocols.common import BoundaryModel, Metadata


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ContentIngestState(StrEnum):
    """Outcome of a content ingest operation."""

    CREATED = "created"
    REPLACED = "replaced"
    UNCHANGED = "unchanged"


# ---------------------------------------------------------------------------
# Boundary types
# ---------------------------------------------------------------------------


class ContentIngestRequest(BoundaryModel):
    """Document write request accepted by Content."""

    source_id: str
    title: str
    text: str
    scope: str = "global"
    uri: str | None = None
    external_id: str | None = None
    content_hash: str | None = None
    metadata: Metadata = Field(default_factory=dict)


class ContentChunk(BoundaryModel):
    """Persisted chunk record returned by Content."""

    id: str
    document_id: str
    source_id: str
    index: int
    text: str
    content_hash: str
    scope: str = "global"
    uri: str | None = None
    section_path: tuple[str, ...] = Field(default_factory=tuple)
    metadata: Metadata = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ContentIngestResult(BoundaryModel):
    """Result of a content ingest operation.

    Downstream consumers use ``state`` for flow control and
    ``replaced_chunk_ids`` for Enrichment cascade (mark_stale).
    """

    document_id: str
    source_id: str
    state: ContentIngestState
    content_hash: str
    chunk_ids: tuple[str, ...] = Field(default_factory=tuple)
    replaced_chunk_ids: tuple[str, ...] = Field(default_factory=tuple)
    created_at: datetime


class ContentSearchQuery(BoundaryModel):
    """Semantic search request accepted by Content."""

    text: str
    top_k: int = Field(default=10, ge=1, le=100)
    scopes: tuple[str, ...] = Field(default_factory=tuple)
    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ContentSearchResult(BoundaryModel):
    """One search hit returned by Content."""

    chunk: ContentChunk
    score: float = Field(ge=0.0)
    matched_text: str = ""


class ContentPurgeResult(BoundaryModel):
    """Itemised result of content purge for audit and cascade."""

    source_id: str
    document_ids: tuple[str, ...] = Field(default_factory=tuple)
    chunk_ids: tuple[str, ...] = Field(default_factory=tuple)
    vector_ids: tuple[str, ...] = Field(default_factory=tuple)


class ContentStats(BoundaryModel):
    """Counts owned by the Content module."""

    documents: int = 0
    chunks: int = 0
    vectors: int = 0


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ContentStore(Protocol):
    """Public contract for the Content module.

    Storage ownership: only Content writes ``content_*`` tables and
    Content-owned Qdrant collections. Chunking and embedding are internal.
    Dependency rule: Content imports no other knowledge module internals.
    """

    async def ingest(self, request: ContentIngestRequest) -> ContentIngestResult:
        """Chunk, embed, store, and delta-check raw text.

        Guarantees:
          - Unchanged content (same content_hash) returns state=UNCHANGED
            and preserves current chunk IDs without re-writing.
          - Changed content returns state=REPLACED with replaced_chunk_ids
            listing the previous chunk IDs for downstream invalidation.
          - New content returns state=CREATED.
          - chunk_ids on the result always reflects the current set of
            chunks after the operation.

        Non-guarantees:
          - Chunk boundaries, embedding model, batch sizing, and vector
            payload shape are implementation details (CP9).

        Side effects:
          - Writes ``content_*`` tables and Content-owned Qdrant collections.

        Raises:
          - ``ValueError`` if text is empty or source_id is missing.
        """
        ...

    def get_chunk(self, chunk_id: str) -> ContentChunk | None:
        """Return one chunk by ID, or None if not found.

        Guarantees:
          - Returned ``text`` is exact source text (for provenance audit).

        Non-guarantees:
          - Callers must not assume chunk IDs are sortable or sequential.

        Side effects:
          - None.

        Raises:
          - Never raises for unknown IDs (returns None).
        """
        ...

    def list_chunks(self, document_id: str) -> tuple[ContentChunk, ...]:
        """Return current chunks for a document, ordered by index.

        Guarantees:
          - Only current chunks are returned (stale chunks replaced by
            re-ingest are excluded).
          - Ordered by chunk index ascending.

        Non-guarantees:
          - Chunk count and boundaries are implementation details.

        Side effects:
          - None.

        Raises:
          - Never raises for unknown document_id (returns empty tuple).
        """
        ...

    async def search(self, query: ContentSearchQuery) -> tuple[ContentSearchResult, ...]:
        """Hybrid semantic search across stored chunks.

        Guarantees:
          - Applies scope and source_id filters.
          - Preserves exact hit text in each result (no rewriting).
          - Result count <= query.top_k.
          - Results ordered by descending score.

        Non-guarantees:
          - Ranking internals (sparse vs dense weighting, re-ranking),
            tie-breaking, and query embedding strategy are implementation
            details (CP9).

        Side effects:
          - May compute a query embedding internally, but does not mutate
            stored content.

        Raises:
          - ``ValueError`` if query.text is empty.
        """
        ...

    def purge_source(self, source_id: str) -> ContentPurgeResult:
        """Remove all Content-owned data derived from a source.

        Guarantees:
          - Removes documents, chunks, and vectors owned by Content for
            the given source_id.
          - Idempotent: re-running on an already-purged source returns a
            result with empty ID tuples.

        Non-guarantees:
          - Does not remove Source, Graph, or Enrichment state.

        Side effects:
          - Writes ``content_*`` tables and Content-owned Qdrant collections
            (deletion).

        Raises:
          - Never raises for unknown source_id (returns empty result).
        """
        ...

    def stats(self) -> ContentStats:
        """Return counts owned by this module.

        Guarantees:
          - Reflects current content_* table and vector state.

        Non-guarantees:
          - Staleness tolerance is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises.
        """
        ...
