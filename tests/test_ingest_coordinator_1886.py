"""Tests for IngestCoordinator.refresh() — fetcher integration (task #1886).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/ingest.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py

AC coverage:
  AC1 — __init__ accepts optional fetcher: SourceFetcher | None (backward-compatible)
  AC2 — refresh() with no fetcher returns empty RefreshResult (sources_checked=0, sources_refreshed=0)
  AC3 — refresh() lists ACTIVE sources, filters by source_ids, filters by refreshable unless force=True
  AC4 — refresh() calls fetch_source per source; maps FetchedDocument → IngestDocument (1:1 fields)
  AC5 — refresh() calls self.ingest only when fetch returns ≥1 document; enrich=source.enrich
  AC6 — refresh() updates last_refreshed_at after successful fetch (incl. zero-doc; NOT after errors)
  AC7 — per-source errors captured as RefreshError(source_id, str(exc), timestamp); batch continues
  AC8 — RefreshResult counters: sources_checked, sources_refreshed, ingest_results, errors
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.protocols.fetcher import FetchedDocument, FetchResult
from owlbear_knowledge.protocols.ingest import (
    IngestRequest,
    IngestResult,
    RefreshError,
    RefreshRequest,
    RefreshResult,
)
from owlbear_knowledge.protocols.sources import (
    ConfiguredSourceRecord,
    FetchTransport,
    InlineConfig,
    SourceHealth,
    SourceKind,
    SourceState,
    SourceStats,
    SourceUpdate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(
    source_id: str = "src-1",
    *,
    state: SourceState = SourceState.ACTIVE,
    refreshable: bool = True,
    enrich: bool = False,
) -> ConfiguredSourceRecord:
    return ConfiguredSourceRecord(
        id=source_id,
        name=f"Source {source_id}",
        state=state,
        kind=SourceKind.INLINE,
        fetch_method=FetchTransport.NONE,
        config=InlineConfig(),
        health=SourceHealth.UNKNOWN,
        refreshable=refreshable,
        enrich=enrich,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _make_fetched_doc(
    *,
    title: str = "Doc Title",
    text: str = "Doc body text.",
    uri: str = "https://example.com/doc",
    external_id: str | None = "ext-1",
    metadata: dict | None = None,
) -> FetchedDocument:
    return FetchedDocument(
        title=title,
        text=text,
        uri=uri,
        external_id=external_id,
        metadata=metadata or {},
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


@pytest.fixture()
def mock_sources() -> MagicMock:
    s = MagicMock(name="sources")
    s.get_source.return_value = _make_source()
    s.list_sources.return_value = (_make_source(),)
    s.update_source.return_value = _make_source()
    s.record_health.return_value = _make_source()
    s.stats.return_value = SourceStats(total=1, active=1, inactive=0, wished=0)
    return s


@pytest.fixture()
def mock_content() -> MagicMock:
    c = MagicMock(name="content")
    c.ingest = AsyncMock()
    return c


@pytest.fixture()
def mock_enrichment() -> MagicMock:
    e = MagicMock(name="enrichment")
    e.enqueue_chunks.return_value = 0
    return e


@pytest.fixture()
def mock_graph() -> MagicMock:
    return MagicMock(name="graph")


@pytest.fixture()
def mock_fetcher() -> MagicMock:
    f = MagicMock(name="fetcher")
    f.fetch_source = AsyncMock(
        return_value=FetchResult(documents=(_make_fetched_doc(),))
    )
    return f


@pytest.fixture()
def coordinator_no_fetcher(
    mock_sources: MagicMock,
    mock_content: MagicMock,
    mock_enrichment: MagicMock,
    mock_graph: MagicMock,
) -> IngestCoordinator:
    """Coordinator without a fetcher — tests AC1 backward-compat and AC2 no-op."""
    return IngestCoordinator(
        sources=mock_sources,
        content=mock_content,
        enrichment=mock_enrichment,
        graph=mock_graph,
    )


@pytest.fixture()
def coordinator(
    mock_sources: MagicMock,
    mock_content: MagicMock,
    mock_enrichment: MagicMock,
    mock_graph: MagicMock,
    mock_fetcher: MagicMock,
) -> IngestCoordinator:
    """Coordinator with fetcher; ingest patched to isolate refresh logic."""
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
# TestFromAC_RefreshImplementation
# ---------------------------------------------------------------------------


class TestFromAC_RefreshImplementation:
    # ------------------------------------------------------------------
    # AC1 — __init__ accepts optional fetcher parameter
    # ------------------------------------------------------------------

    def test_init_accepts_fetcher_keyword_argument(
        self,
        mock_sources: MagicMock,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """Constructor must accept fetcher= without raising TypeError."""
        coord = IngestCoordinator(
            sources=mock_sources,
            content=mock_content,
            enrichment=mock_enrichment,
            graph=mock_graph,
            fetcher=mock_fetcher,
        )
        assert coord is not None

    def test_init_accepts_explicit_fetcher_none(
        self,
        mock_sources: MagicMock,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """Explicit fetcher=None is accepted without raising TypeError."""
        coord = IngestCoordinator(
            sources=mock_sources,
            content=mock_content,
            enrichment=mock_enrichment,
            graph=mock_graph,
            fetcher=None,
        )
        assert coord is not None

    # ------------------------------------------------------------------
    # AC2 — refresh() with no fetcher returns empty RefreshResult
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_without_fetcher_returns_refresh_result_type(
        self, coordinator_no_fetcher: IngestCoordinator
    ) -> None:
        result = await coordinator_no_fetcher.refresh(RefreshRequest())
        assert isinstance(result, RefreshResult)

    @pytest.mark.asyncio
    async def test_refresh_without_fetcher_sources_checked_is_zero(
        self, coordinator_no_fetcher: IngestCoordinator
    ) -> None:
        result = await coordinator_no_fetcher.refresh(RefreshRequest())
        assert result.sources_checked == 0

    @pytest.mark.asyncio
    async def test_refresh_without_fetcher_sources_refreshed_is_zero(
        self, coordinator_no_fetcher: IngestCoordinator
    ) -> None:
        result = await coordinator_no_fetcher.refresh(RefreshRequest())
        assert result.sources_refreshed == 0

    @pytest.mark.asyncio
    async def test_refresh_without_fetcher_errors_is_empty(
        self, coordinator_no_fetcher: IngestCoordinator
    ) -> None:
        result = await coordinator_no_fetcher.refresh(RefreshRequest())
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_refresh_with_explicit_none_fetcher_returns_empty_result(
        self,
        mock_sources: MagicMock,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        coord = IngestCoordinator(
            sources=mock_sources,
            content=mock_content,
            enrichment=mock_enrichment,
            graph=mock_graph,
            fetcher=None,
        )
        result = await coord.refresh(RefreshRequest())
        assert result.sources_checked == 0
        assert result.sources_refreshed == 0

    # ------------------------------------------------------------------
    # AC3 — lists ACTIVE sources, filters source_ids, filters refreshable
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_calls_list_sources_with_state_active(
        self, coordinator: IngestCoordinator, mock_sources: MagicMock
    ) -> None:
        await coordinator.refresh(RefreshRequest())
        mock_sources.list_sources.assert_called_once_with(state=SourceState.ACTIVE)

    @pytest.mark.asyncio
    async def test_refresh_excludes_non_refreshable_sources_by_default(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """Sources with refreshable=False are skipped when force=False."""
        mock_sources.list_sources.return_value = (
            _make_source("src-nr", refreshable=False),
        )
        await coordinator.refresh(RefreshRequest(force=False))
        mock_fetcher.fetch_source.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_includes_non_refreshable_sources_when_force_true(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """force=True bypasses the refreshable=False filter."""
        mock_sources.list_sources.return_value = (
            _make_source("src-nr", refreshable=False),
        )
        await coordinator.refresh(RefreshRequest(force=True))
        mock_fetcher.fetch_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_filters_sources_by_source_ids_when_non_empty(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """Only sources matching request.source_ids are processed."""
        mock_sources.list_sources.return_value = (
            _make_source("src-a"),
            _make_source("src-b"),
        )
        await coordinator.refresh(RefreshRequest(source_ids=("src-a",)))
        assert mock_fetcher.fetch_source.call_count == 1
        fetched_source = mock_fetcher.fetch_source.call_args.args[0]
        assert fetched_source.id == "src-a"

    @pytest.mark.asyncio
    async def test_refresh_processes_all_sources_when_source_ids_empty(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """Empty source_ids tuple means no ID filter — all refreshable ACTIVE sources."""
        mock_sources.list_sources.return_value = (
            _make_source("src-a"),
            _make_source("src-b"),
        )
        coordinator.ingest.return_value = _make_ingest_result()
        await coordinator.refresh(RefreshRequest(source_ids=()))
        assert mock_fetcher.fetch_source.call_count == 2

    @pytest.mark.asyncio
    async def test_refresh_source_ids_filter_does_not_match_non_active(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """source_ids includes 'src-x' but only 'src-a' came back from list_sources — no fetch."""
        mock_sources.list_sources.return_value = (_make_source("src-a"),)
        await coordinator.refresh(RefreshRequest(source_ids=("src-x",)))
        mock_fetcher.fetch_source.assert_not_called()

    # ------------------------------------------------------------------
    # AC4 — calls fetch_source per source; maps FetchedDocument → IngestDocument 1:1
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_calls_fetch_source_with_the_source_record(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        source = _make_source("src-xyz")
        mock_sources.list_sources.return_value = (source,)
        await coordinator.refresh(RefreshRequest())
        mock_fetcher.fetch_source.assert_called_once()
        called_source = mock_fetcher.fetch_source.call_args.args[0]
        assert called_source.id == "src-xyz"

    @pytest.mark.asyncio
    async def test_refresh_maps_fetched_document_title(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(documents=(_make_fetched_doc(title="Article Alpha"),))
        )
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.documents[0].title == "Article Alpha"

    @pytest.mark.asyncio
    async def test_refresh_maps_fetched_document_text(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(documents=(_make_fetched_doc(text="Body of the article."),))
        )
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.documents[0].text == "Body of the article."

    @pytest.mark.asyncio
    async def test_refresh_maps_fetched_document_uri(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(_make_fetched_doc(uri="https://docs.example.com/page"),)
            )
        )
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.documents[0].uri == "https://docs.example.com/page"

    @pytest.mark.asyncio
    async def test_refresh_maps_fetched_document_external_id(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(_make_fetched_doc(external_id="ext-99"),)
            )
        )
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.documents[0].external_id == "ext-99"

    @pytest.mark.asyncio
    async def test_refresh_maps_fetched_document_external_id_none(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(_make_fetched_doc(external_id=None),)
            )
        )
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.documents[0].external_id is None

    @pytest.mark.asyncio
    async def test_refresh_maps_fetched_document_metadata(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(_make_fetched_doc(metadata={"lang": "en", "page": 3}),)
            )
        )
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.documents[0].metadata == {"lang": "en", "page": 3}

    @pytest.mark.asyncio
    async def test_refresh_maps_all_fetched_documents_to_ingest_request(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        docs = tuple(
            _make_fetched_doc(title=f"Doc {i}", external_id=f"ext-{i}")
            for i in range(3)
        )
        mock_fetcher.fetch_source = AsyncMock(return_value=FetchResult(documents=docs))
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert len(req.documents) == 3
        for i, mapped in enumerate(req.documents):
            assert mapped.title == f"Doc {i}"
            assert mapped.external_id == f"ext-{i}"

    # ------------------------------------------------------------------
    # AC5 — calls self.ingest only when fetch returns ≥1 document; enrich=source.enrich
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_calls_ingest_when_fetch_returns_one_document(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(documents=(_make_fetched_doc(),))
        )
        await coordinator.refresh(RefreshRequest())
        coordinator.ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_does_not_call_ingest_when_fetch_returns_zero_documents(
        self,
        coordinator: IngestCoordinator,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_fetcher.fetch_source = AsyncMock(return_value=FetchResult(documents=()))
        await coordinator.refresh(RefreshRequest())
        coordinator.ingest.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_passes_source_id_to_ingest_request(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-target"),)
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.source_id == "src-target"

    @pytest.mark.asyncio
    async def test_refresh_passes_source_enrich_true_to_ingest_request(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1", enrich=True),)
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.enrich is True

    @pytest.mark.asyncio
    async def test_refresh_passes_source_enrich_false_to_ingest_request(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1", enrich=False),)
        await coordinator.refresh(RefreshRequest())
        req: IngestRequest = coordinator.ingest.call_args.args[0]
        assert req.enrich is False

    # ------------------------------------------------------------------
    # AC6 — updates last_refreshed_at after successful fetch (incl. zero-doc; NOT after errors)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_calls_update_source_after_successful_fetch_with_documents(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(documents=(_make_fetched_doc(),))
        )
        await coordinator.refresh(RefreshRequest())
        mock_sources.update_source.assert_called_once()
        assert mock_sources.update_source.call_args.args[0] == "src-1"

    @pytest.mark.asyncio
    async def test_refresh_update_source_contains_last_refreshed_at_timestamp(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        before = datetime.now(tz=UTC)
        await coordinator.refresh(RefreshRequest())
        after = datetime.now(tz=UTC)
        update: SourceUpdate = mock_sources.update_source.call_args.args[1]
        assert isinstance(update, SourceUpdate)
        assert update.last_refreshed_at is not None
        assert before <= update.last_refreshed_at <= after

    @pytest.mark.asyncio
    async def test_refresh_calls_update_source_even_when_fetch_returns_zero_documents(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """Zero-document fetch is a successful fetch — watermark must still be updated."""
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        mock_fetcher.fetch_source = AsyncMock(return_value=FetchResult(documents=()))
        await coordinator.refresh(RefreshRequest())
        mock_sources.update_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_does_not_call_update_source_when_fetch_source_raises(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """Exception from fetch_source → watermark NOT updated."""
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        mock_fetcher.fetch_source = AsyncMock(side_effect=RuntimeError("transport error"))
        await coordinator.refresh(RefreshRequest())
        mock_sources.update_source.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_does_not_call_update_source_when_ingest_raises(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """Exception from self.ingest → watermark NOT updated."""
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        coordinator.ingest.side_effect = RuntimeError("ingest failure")
        await coordinator.refresh(RefreshRequest())
        mock_sources.update_source.assert_not_called()

    # ------------------------------------------------------------------
    # AC7 — per-source errors captured as RefreshError; batch continues
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_captures_refresh_error_when_fetch_source_raises(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        mock_fetcher.fetch_source = AsyncMock(side_effect=RuntimeError("connection refused"))
        result = await coordinator.refresh(RefreshRequest())
        assert len(result.errors) == 1
        assert result.errors[0].source_id == "src-1"
        assert "connection refused" in result.errors[0].error

    @pytest.mark.asyncio
    async def test_refresh_captures_refresh_error_when_ingest_raises(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        coordinator.ingest.side_effect = ValueError("ingest rejected")
        result = await coordinator.refresh(RefreshRequest())
        assert len(result.errors) == 1
        assert result.errors[0].source_id == "src-1"
        assert "ingest rejected" in result.errors[0].error

    @pytest.mark.asyncio
    async def test_refresh_error_message_equals_str_of_exception(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        exc = RuntimeError("exact error message text")
        mock_fetcher.fetch_source = AsyncMock(side_effect=exc)
        result = await coordinator.refresh(RefreshRequest())
        assert result.errors[0].error == str(exc)

    @pytest.mark.asyncio
    async def test_refresh_error_contains_timestamp(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        mock_fetcher.fetch_source = AsyncMock(side_effect=RuntimeError("err"))
        before = datetime.now(tz=UTC)
        result = await coordinator.refresh(RefreshRequest())
        after = datetime.now(tz=UTC)
        assert isinstance(result.errors[0], RefreshError)
        assert before <= result.errors[0].timestamp <= after

    @pytest.mark.asyncio
    async def test_refresh_continues_batch_after_fetch_source_error(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (
            _make_source("src-a"),
            _make_source("src-b"),
        )
        coordinator.ingest.return_value = _make_ingest_result("src-b")
        mock_fetcher.fetch_source = AsyncMock(
            side_effect=[
                RuntimeError("src-a transport failed"),
                FetchResult(documents=(_make_fetched_doc(),)),
            ]
        )
        result = await coordinator.refresh(RefreshRequest())
        assert len(result.errors) == 1
        assert result.errors[0].source_id == "src-a"
        assert result.sources_refreshed == 1

    @pytest.mark.asyncio
    async def test_refresh_continues_batch_after_ingest_error(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (
            _make_source("src-a"),
            _make_source("src-b"),
        )
        coordinator.ingest.side_effect = [
            RuntimeError("src-a ingest failed"),
            _make_ingest_result("src-b"),
        ]
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(documents=(_make_fetched_doc(),))
        )
        result = await coordinator.refresh(RefreshRequest())
        assert len(result.errors) == 1
        assert result.errors[0].source_id == "src-a"
        assert result.sources_refreshed == 1

    # ------------------------------------------------------------------
    # AC8 — RefreshResult counter semantics
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_sources_checked_equals_count_of_filtered_sources_attempted(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (
            _make_source("src-a"),
            _make_source("src-b"),
            _make_source("src-c"),
        )
        coordinator.ingest.return_value = _make_ingest_result()
        result = await coordinator.refresh(RefreshRequest())
        assert result.sources_checked == 3

    @pytest.mark.asyncio
    async def test_refresh_sources_checked_counts_only_post_filter_sources(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """sources_checked = filtered (after refreshable + source_ids filtering), not raw list_sources count."""
        mock_sources.list_sources.return_value = (
            _make_source("src-a", refreshable=True),
            _make_source("src-b", refreshable=False),
        )
        result = await coordinator.refresh(RefreshRequest(force=False))
        assert result.sources_checked == 1

    @pytest.mark.asyncio
    async def test_refresh_sources_refreshed_equals_completed_without_error(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (
            _make_source("src-a"),
            _make_source("src-b"),
            _make_source("src-c"),
        )
        coordinator.ingest.return_value = _make_ingest_result()
        mock_fetcher.fetch_source = AsyncMock(
            side_effect=[
                FetchResult(documents=(_make_fetched_doc(),)),
                RuntimeError("src-b transport failed"),
                FetchResult(documents=(_make_fetched_doc(),)),
            ]
        )
        result = await coordinator.refresh(RefreshRequest())
        assert result.sources_checked == 3
        assert result.sources_refreshed == 2

    @pytest.mark.asyncio
    async def test_refresh_ingest_results_contains_only_successful_ingest_results(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (
            _make_source("src-a"),
            _make_source("src-b"),
        )
        result_a = _make_ingest_result("src-a")
        coordinator.ingest.side_effect = [result_a, RuntimeError("src-b ingest failed")]
        mock_fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(documents=(_make_fetched_doc(),))
        )
        result = await coordinator.refresh(RefreshRequest())
        assert len(result.ingest_results) == 1
        assert result.ingest_results[0].source_id == "src-a"

    @pytest.mark.asyncio
    async def test_refresh_ingest_results_excludes_zero_document_sources(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """Zero-doc fetch → no ingest called → not in ingest_results; still counted as refreshed."""
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        mock_fetcher.fetch_source = AsyncMock(return_value=FetchResult(documents=()))
        result = await coordinator.refresh(RefreshRequest())
        assert len(result.ingest_results) == 0
        assert result.sources_refreshed == 1

    @pytest.mark.asyncio
    async def test_refresh_errors_tuple_contains_refresh_error_instances(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = (_make_source("src-1"),)
        mock_fetcher.fetch_source = AsyncMock(side_effect=RuntimeError("boom"))
        result = await coordinator.refresh(RefreshRequest())
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], RefreshError)

    @pytest.mark.asyncio
    async def test_refresh_with_no_sources_returns_all_zero_counts(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        mock_sources.list_sources.return_value = ()
        result = await coordinator.refresh(RefreshRequest())
        assert result.sources_checked == 0
        assert result.sources_refreshed == 0
        assert len(result.ingest_results) == 0
        assert len(result.errors) == 0
