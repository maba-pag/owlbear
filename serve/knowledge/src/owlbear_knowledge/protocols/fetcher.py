"""Source fetcher protocol and boundary models for source refresh.

This module defines the transport-agnostic fetch boundary used by ingest
refresh flows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import Field

from owlbear_knowledge.protocols.common import BoundaryModel, Metadata
from owlbear_knowledge.protocols.failures import KnowledgeFailure

if TYPE_CHECKING:
    from owlbear_knowledge.cancellation import CancelSignal
    from owlbear_knowledge.protocols.sources import ConfiguredSourceRecord


class FetchedDocument(BoundaryModel):
    """One fetched document ready for ingest processing."""

    title: str
    text: str
    uri: str
    external_id: str | None = None
    metadata: Metadata = Field(default_factory=dict)


class FetchError(BoundaryModel):
    """One item-level fetch failure captured during source retrieval."""

    uri: str
    error: str = ""
    failure: KnowledgeFailure | None = None


class FetchResult(BoundaryModel):
    """Fetch output including successful documents and item-level failures."""

    documents: tuple[FetchedDocument, ...] = Field(default_factory=tuple)
    errors: tuple[FetchError, ...] = Field(default_factory=tuple)


@runtime_checkable
class SourceFetcher(Protocol):
    """Transport-specific source fetch contract for configured sources."""

    async def fetch_source(
        self,
        source: ConfiguredSourceRecord,
        *,
        cancel: CancelSignal | None = None,
    ) -> FetchResult:
        """Fetch one configured source.

        Guarantees:
          - Returns partial documents when cancellation is requested.
          - Captures per-item failures in the errors tuple and never raises
            item-level fetch failures.

        Non-guarantees:
          - Result ordering is not guaranteed.
          - Batch strategy and pagination behavior are implementation details.

        Side effects:
          - Performs transport I/O.

        Raises:
          - Never.
        """
        ...
