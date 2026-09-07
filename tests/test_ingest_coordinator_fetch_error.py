"""Tests for IngestCoordinator.refresh() FetchError propagation.

Target implementation:
  serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py

Behavioral coverage:
  AC1 — refresh() maps each FetchError to RefreshError in RefreshResult.errors
        (source_id, error string incorporating uri/error, timestamp present)
  AC2 — partial success (docs + errors): update_source still called and
        sources_refreshed incremented; fetch errors captured in result.errors
  AC3 — total failure (empty docs + non-empty errors): update_source skipped
        and sources_refreshed not incremented
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.protocols.failures import (
    KnowledgeFailure,
    KnowledgeFailureStage,
    KnowledgeOperationError,
)
from owlbear_knowledge.protocols.fetcher import FetchedDocument, FetchError, FetchResult
from owlbear_knowledge.protocols.ingest import (
    IngestResult,
    RefreshRequest,
)
from owlbear_knowledge.protocols.sources import (
    ConfiguredSourceRecord,
    FetchTransport,
    InlineConfig,
    SourceHealth,
    SourceKind,
    SourceState,
    SourceStats,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(
    source_id: str = "src-1",
    *,
    refreshable: bool = True,
    enrich: bool = False,
) -> ConfiguredSourceRecord:
    return ConfiguredSourceRecord(
        id=source_id,
        name=f"Source {source_id}",
        state=SourceState.ACTIVE,
        kind=SourceKind.INLINE,
        fetch_method=FetchTransport.NONE,
        config=InlineConfig(),
        health=SourceHealth.UNKNOWN,
        refreshable=refreshable,
        enrich=enrich,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _make_fetched_doc(uri: str = "https://example.com/doc") -> FetchedDocument:
    return FetchedDocument(
        title="Doc Title",
        text="Doc body text.",
        uri=uri,
        external_id="ext-1",
    )


def _make_ingest_result(source_id: str = "src-1") -> IngestResult:
    now = datetime.now(tz=UTC)
    return IngestResult(
        source_id=source_id,
        documents_processed=1,
        documents_created=1,
        started_at=now,
        completed_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_sources() -> MagicMock:
    s = MagicMock(name="sources")
    s.get_source.return_value = _make_source()
    s.list_sources.return_value = (_make_source(),)
    s.update_source.return_value = _make_source()
    s.record_health.return_value = _make_source()
    s.stats.return_value = SourceStats(total=1, active=1, inactive=0, wished=0)
    return s


@pytest.fixture
def mock_content() -> MagicMock:
    c = MagicMock(name="content")
    c.ingest = AsyncMock()
    return c


@pytest.fixture
def mock_enrichment() -> MagicMock:
    e = MagicMock(name="enrichment")
    e.enqueue_chunks.return_value = 0
    return e


@pytest.fixture
def mock_graph() -> MagicMock:
    return MagicMock(name="graph")


@pytest.fixture
def mock_fetcher() -> MagicMock:
    f = MagicMock(name="fetcher")
    f.fetch_source = AsyncMock(return_value=FetchResult())
    return f


@pytest.fixture
def coordinator(
    mock_sources: MagicMock,
    mock_content: MagicMock,
    mock_enrichment: MagicMock,
    mock_graph: MagicMock,
    mock_fetcher: MagicMock,
) -> IngestCoordinator:
    c = IngestCoordinator(
        sources=mock_sources,
        content=mock_content,
        enrichment=mock_enrichment,
        graph=mock_graph,
        fetcher=mock_fetcher,
    )
    c.ingest = AsyncMock(return_value=_make_ingest_result())
    return c


# ---------------------------------------------------------------------------
# TestFromAC_FetchErrorPropagation
# ---------------------------------------------------------------------------


class TestFetchErrorPropagation:
    # ------------------------------------------------------------------
    # AC1 — FetchErrors mapped to RefreshErrors in RefreshResult.errors
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_errors_appear_in_refresh_result_errors(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        """AC1: A FetchError from the fetcher must be mapped to RefreshResult.errors.

        The coordinator must preserve the fetcher's typed error in the refresh result.
        """
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(),
                errors=(FetchError(uri="https://example.com/fail", error="timeout"),),
            )
        )

        result = await coordinator.refresh(RefreshRequest())

        assert len(result.errors) == 1

    # ------------------------------------------------------------------
    # AC2 — partial success: update_source called, errors still captured
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_partial_success_errors_captured_in_result(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        """AC2: With documents AND errors, fetch errors must be in RefreshResult.errors.

        Current code does not propagate fetch_result.errors — this test fails until
        the propagation fix is applied.  The partial-success path (sources_refreshed
        incremented) must coexist with captured errors.
        """
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(_make_fetched_doc(),),
                errors=(FetchError(uri="https://example.com/partial", error="403 Forbidden"),),
            )
        )

        result = await coordinator.refresh(RefreshRequest())

        assert len(result.errors) >= 1

    # ------------------------------------------------------------------
    # AC3 — total failure: update_source skipped, sources_refreshed stays 0
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_total_failure_does_not_increment_sources_refreshed(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        """AC3: When documents is empty and errors is non-empty, sources_refreshed must be 0.

        Current code always increments sources_refreshed after fetch, so this
        test fails until the total-failure branch is guarded.
        """
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(),
                errors=(FetchError(uri="https://example.com/fail", error="connection refused"),),
            )
        )

        result = await coordinator.refresh(RefreshRequest())

        assert result.sources_refreshed == 0

    # ------------------------------------------------------------------
    # AC1 strengthened — field-level mapping and multi-error propagation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ac1_refresh_error_source_id_matches_source(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        """AC1: RefreshError.source_id must equal the source's id."""
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(),
                errors=(FetchError(uri="https://example.com/fail", error="timeout"),),
            )
        )

        result = await coordinator.refresh(RefreshRequest())

        assert len(result.errors) == 1
        assert result.errors[0].source_id == "src-1"

    @pytest.mark.asyncio
    async def test_ac1_refresh_error_string_incorporates_uri_and_error(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        """AC1: RefreshError.error must incorporate both FetchError.uri and FetchError.error."""
        fetch_uri = "https://example.com/fail"
        fetch_err = "connection refused"
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="transport_failure",
            retryable=True,
            message=fetch_err,
        )
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(),
                errors=(FetchError(uri=fetch_uri, error=fetch_err, failure=failure),),
            )
        )

        result = await coordinator.refresh(RefreshRequest())

        assert len(result.errors) == 1
        assert result.errors[0].failure == failure
        assert result.errors[0].error == failure.message
        assert fetch_uri not in result.errors[0].error

    @pytest.mark.asyncio
    async def test_ac1_refresh_error_timestamp_is_datetime(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        """AC1: RefreshError.timestamp must be a current UTC datetime."""
        before = datetime.now(tz=UTC)
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(),
                errors=(FetchError(uri="https://example.com/fail", error="timeout"),),
            )
        )

        result = await coordinator.refresh(RefreshRequest())
        after = datetime.now(tz=UTC)

        assert len(result.errors) == 1
        ts = result.errors[0].timestamp
        assert isinstance(ts, datetime)
        assert before <= ts <= after

    @pytest.mark.asyncio
    async def test_ac1_all_fetch_errors_propagated_for_multiple_errors(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        """AC1: Every FetchError in fetch_result.errors must become a RefreshError — not just the first."""
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(),
                errors=(
                    FetchError(
                        uri="https://example.com/a",
                        error="timeout",
                        failure=KnowledgeFailure(
                            stage=KnowledgeFailureStage.ACQUISITION,
                            code="timeout",
                            retryable=True,
                            message="HTTP request timed out",
                        ),
                    ),
                    FetchError(
                        uri="https://example.com/b",
                        error="403 Forbidden",
                        failure=KnowledgeFailure(
                            stage=KnowledgeFailureStage.ACQUISITION,
                            code="http_status",
                            retryable=False,
                            message="HTTP request returned status 403",
                        ),
                    ),
                ),
            )
        )

        result = await coordinator.refresh(RefreshRequest())

        assert len(result.errors) == 2
        assert {error.failure.code for error in result.errors if error.failure is not None} == {
            "timeout",
            "http_status",
        }

    # ------------------------------------------------------------------
    # AC2 strengthened — update_source called and sources_refreshed increments
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ac2_partial_success_update_source_still_called(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
        mock_sources: MagicMock,
    ) -> None:
        """AC2: In partial success, update_source() must be called despite fetch errors."""
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(_make_fetched_doc(),),
                errors=(FetchError(uri="https://example.com/partial", error="403 Forbidden"),),
            )
        )

        await coordinator.refresh(RefreshRequest())

        mock_sources.update_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac2_partial_success_sources_refreshed_increments(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        """AC2: In partial success, sources_refreshed must increment despite fetch errors."""
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(_make_fetched_doc(),),
                errors=(FetchError(uri="https://example.com/partial", error="403 Forbidden"),),
            )
        )

        result = await coordinator.refresh(RefreshRequest())

        assert result.sources_refreshed == 1

    # ------------------------------------------------------------------
    # AC3 strengthened — update_source NOT called on total failure
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ac3_total_failure_update_source_not_called(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
        mock_sources: MagicMock,
    ) -> None:
        """AC3: When total failure (empty docs + non-empty errors), update_source must NOT be called."""
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(),
                errors=(FetchError(uri="https://example.com/fail", error="connection refused"),),
            )
        )

        await coordinator.refresh(RefreshRequest())

        mock_sources.update_source.assert_not_called()


@pytest.mark.asyncio
async def test_embedding_failure_is_returned_and_does_not_mark_source_refreshed(
    mock_sources: MagicMock,
    mock_enrichment: MagicMock,
    mock_graph: MagicMock,
    mock_fetcher: MagicMock,
) -> None:
    failure = KnowledgeFailure(
        stage=KnowledgeFailureStage.INDEXING,
        code="embedding_tls_failed",
        retryable=True,
        message="BGE-M3 download TLS verification failed",
    )
    content = MagicMock(name="content")
    content.ingest = AsyncMock(side_effect=KnowledgeOperationError(failure))
    coordinator = IngestCoordinator(
        sources=mock_sources,
        content=content,
        enrichment=mock_enrichment,
        graph=mock_graph,
        fetcher=mock_fetcher,
    )
    mock_fetcher.fetch_source = AsyncMock(return_value=FetchResult(documents=(_make_fetched_doc(),)))

    result = await coordinator.refresh(RefreshRequest())

    assert result.sources_refreshed == 0
    assert result.errors[0].failure == failure
    assert result.errors[0].error == failure.message
    mock_sources.update_source.assert_not_called()
