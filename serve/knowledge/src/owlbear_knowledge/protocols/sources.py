"""SourceStore Protocol — Sources module public surface.

Module responsibility: source registry, lifecycle state, health tracking,
and wish fulfilment. Owns tables ``source_*``.

Has zero dependencies on other knowledge modules.

Table ownership: only Sources writes ``source_*`` tables.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from enum import StrEnum
from typing import Annotated, Literal, Protocol, runtime_checkable

from pydantic import Field

from owlbear_knowledge.protocols.common import BoundaryModel, Metadata

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SourceKind(StrEnum):
    """Classification of content source connectors."""

    AUTHENTICATED_WEB = "authenticated_web"
    FILE_GLOB = "file_glob"
    INLINE = "inline"
    URL_LIST = "url_list"


class FetchTransport(StrEnum):
    """Routing hint declaring how a source's content is fetched."""

    BROWSER = "browser"
    FILESYSTEM = "filesystem"
    HTTP = "http"
    NONE = "none"


class SourceState(StrEnum):
    """Lifecycle states for a registered source."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    WISHED = "wished"


class SourceHealth(StrEnum):
    """Operational health of a source's connector.

    Orthogonal to SourceState — a source can be ACTIVE + DEGRADED.
    """

    UNKNOWN = "unknown"
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Typed source configuration (discriminated union keyed on kind — CP6)
# ---------------------------------------------------------------------------


class FileGlobConfig(BoundaryModel):
    """Configuration for FILE_GLOB sources."""

    kind: Literal[SourceKind.FILE_GLOB] = SourceKind.FILE_GLOB
    patterns: tuple[str, ...]
    base_path: str = "."
    follow_symlinks: bool = False


class UrlListConfig(BoundaryModel):
    """Configuration for URL_LIST sources."""

    kind: Literal[SourceKind.URL_LIST] = SourceKind.URL_LIST
    urls: tuple[str, ...]


class AuthenticatedWebConfig(BoundaryModel):
    """Configuration for AUTHENTICATED_WEB sources."""

    kind: Literal[SourceKind.AUTHENTICATED_WEB] = SourceKind.AUTHENTICATED_WEB
    base_url: str
    auth_profile: str
    page_limit: int = Field(default=100, ge=1)


class InlineConfig(BoundaryModel):
    """Configuration for INLINE sources (text provided directly)."""

    kind: Literal[SourceKind.INLINE] = SourceKind.INLINE


SourceConfig = Annotated[
    FileGlobConfig | UrlListConfig | AuthenticatedWebConfig | InlineConfig,
    Field(discriminator="kind"),
]
"""Typed source configuration. Shape depends on SourceKind."""


# ---------------------------------------------------------------------------
# Boundary types
# ---------------------------------------------------------------------------


class SourceRegistration(BoundaryModel):
    """Request to register a fully-configured source."""

    name: str
    kind: SourceKind
    fetch_method: FetchTransport
    config: SourceConfig
    scope: str = "global"
    enrich: bool = False
    refreshable: bool = True
    priority: int = 0
    metadata: Metadata = Field(default_factory=dict)


class SourceWish(BoundaryModel):
    """Request to register demand for a source not yet ingestable.

    Unlike SourceRegistration, wishes may not know the connector type
    or configuration — they express demand only.
    """

    name: str
    expected_kind: SourceKind | None = None
    expected_fetch_method: FetchTransport | None = None
    scope: str = "global"
    reason: str = ""
    metadata: Metadata = Field(default_factory=dict)


class SourceUpdate(BoundaryModel):
    """Partial update request for a registered source.

    Only non-None fields are applied. Valid state transitions:
      - WISHED → ACTIVE (on first successful ingest)
      - ACTIVE → INACTIVE (admin deactivation)
      - INACTIVE → ACTIVE (re-activation)
      - WISHED → INACTIVE (admin rejection)
    Invalid transitions raise ValueError.
    """

    state: SourceState | None = None
    config: SourceConfig | None = None
    scope: str | None = None
    enrich: bool | None = None
    refreshable: bool | None = None
    last_refreshed_at: datetime | None = None
    priority: int | None = None
    reason: str | None = None
    metadata: Metadata | None = None


class SourceHealthReport(BoundaryModel):
    """Health observation to record against a source."""

    health: SourceHealth
    message: str | None = None
    checked_at: datetime


# ---------------------------------------------------------------------------
# Source records (discriminated union keyed on state — D51)
# ---------------------------------------------------------------------------


class _SourceRecordBase(BoundaryModel):
    """Shared fields for all source record variants."""

    id: str
    name: str
    scope: str = "global"
    priority: int = 0
    last_refreshed_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: Metadata = Field(default_factory=dict)


class ConfiguredSourceRecord(_SourceRecordBase):
    """A source with full connector configuration (ACTIVE or INACTIVE)."""

    state: Literal[SourceState.ACTIVE, SourceState.INACTIVE]
    kind: SourceKind
    fetch_method: FetchTransport
    health: SourceHealth = SourceHealth.UNKNOWN
    config: SourceConfig
    enrich: bool = False
    refreshable: bool = True


class WishedSourceRecord(_SourceRecordBase):
    """A demand-only source registration (WISHED state).

    Does not require connector kind, fetch method, or config — it
    expresses demand only (CP24).
    """

    state: Literal[SourceState.WISHED] = SourceState.WISHED
    expected_kind: SourceKind | None = None
    expected_fetch_method: FetchTransport | None = None
    reason: str = ""


SourceRecord = ConfiguredSourceRecord | WishedSourceRecord
"""Persisted source record. Shape depends on state (D51)."""


class SourceDeletionInfo(BoundaryModel):
    """Typed return from source deletion carrying context for downstream purge.

    Carries audit context (reason, timestamp) so downstream PurgeReport is
    fully traceable.
    """

    source_id: str
    source_name: str
    scope: str
    deleted_at: datetime
    reason: str | None = None


class SourceStats(BoundaryModel):
    """Counts owned by the Sources module."""

    total: int = 0
    active: int = 0
    inactive: int = 0
    wished: int = 0


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SourceStore(Protocol):
    """Public contract for the Sources module.

    Storage ownership: only Sources writes ``source_*`` tables.
    Dependency rule: Sources imports no other knowledge module internals.
    """

    def register_source(self, request: SourceRegistration) -> SourceRecord:
        """Create or replace a configured source.

        Guarantees:
          - Returns the persisted source in ACTIVE state with module-owned
            timestamps.
          - If a WISHED source with the same name+scope exists, it is
            promoted (superseded) rather than duplicated.
          - Config shape is validated at the boundary (discriminated union).

        Non-guarantees:
          - Source IDs, timestamp precision, and storage format are
            implementation details.

        Side effects:
          - Writes only ``source_*`` tables.

        Raises:
          - ``ValueError`` if required fields are missing or config shape
            does not match kind.
        """
        ...

    def register_wish(self, request: SourceWish) -> SourceRecord:
        """Register demand for a source that is not ingestable yet.

        Guarantees:
          - Returns a WISHED source record queryable through this protocol.
          - Does not require kind or config (demand signals only).

        Non-guarantees:
          - Wishes do not imply fetch credentials, URLs, or future
            ingestion priority.

        Side effects:
          - Writes only ``source_*`` tables.

        Raises:
          - ``ValueError`` if a source with the same name+scope already
            exists in ACTIVE state.
        """
        ...

    def get_source(self, source_id: str) -> SourceRecord | None:
        """Return one source by ID, or None if not found.

        Guarantees:
          - Returns None when the source is unknown or was deleted.

        Non-guarantees:
          - Callers must not infer table structure from the ID format.

        Side effects:
          - None.

        Raises:
          - Never raises for unknown IDs (returns None).
        """
        ...

    def list_sources(
        self,
        *,
        scope: str | None = None,
        state: SourceState | None = None,
    ) -> tuple[SourceRecord, ...]:
        """List sources filtered by stable registry attributes.

        Guarantees:
          - Results include configured and wished sources unless a filter
            excludes them.
          - Empty tuple if no sources match.

        Non-guarantees:
          - Ordering is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises (returns empty tuple for no matches).
        """
        ...

    def update_source(self, source_id: str, update: SourceUpdate) -> SourceRecord:
        """Apply a state or configuration update.

        Guarantees:
          - Only non-None fields in SourceUpdate are applied.
          - State transitions are validated per SourceUpdate documentation.
          - updated_at is refreshed on every successful call.

        Non-guarantees:
          - Metadata merge semantics are implementation-defined.

        Side effects:
          - Writes only ``source_*`` tables.

        Raises:
          - ``LookupError`` if source_id does not exist.
          - ``ValueError`` if the state transition is invalid or config
            shape does not match kind.
        """
        ...

    def record_health(self, source_id: str, report: SourceHealthReport) -> SourceRecord:
        """Persist the latest health observation for a source.

        Guarantees:
          - Health and last_checked_at are updated on the returned record.

        Non-guarantees:
          - Historical health retention and sampling are implementation
            details.

        Side effects:
          - Writes only ``source_*`` tables.

        Raises:
          - ``LookupError`` if source_id does not exist.
        """
        ...

    def delete_source(self, source_id: str, *, reason: str | None = None) -> SourceDeletionInfo:
        """Accept source deletion and return info for downstream purge.

        Guarantees:
          - The returned SourceDeletionInfo carries all context that
            downstream modules need for cascade cleanup without re-reading
            the deleted record.
          - The source record is removed from this module's storage.
          - deleted_at and reason are preserved in the return for audit.

        Non-guarantees:
          - Sources does not delete Content, Graph, or Enrichment records.
            That is Ingest's coordination responsibility.

        Side effects:
          - Writes only ``source_*`` tables (deletion).

        Raises:
          - ``LookupError`` if source_id does not exist.
        """
        ...

    def stats(self) -> SourceStats:
        """Return counts owned by this module.

        Guarantees:
          - Reflects current source_* table state.

        Non-guarantees:
          - Staleness tolerance is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises.
        """
        ...
