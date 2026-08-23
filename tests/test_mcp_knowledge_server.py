"""Knowledge MCP source-refresh behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_knowledge.protocols.failures import KnowledgeFailure, KnowledgeFailureStage, KnowledgeOperationError
from owlbear_knowledge.protocols.ingest import RefreshError, RefreshRequest, RefreshResult
from owlbear_knowledge.protocols.sources import SourceState
from owlbear_knowledge_mcp import server
from owlbear_knowledge_mcp.server import refresh_knowledge_source


class TestSourceFetcherWiring:
    @pytest.mark.asyncio
    async def test_lifespan_wires_composite_fetcher_to_coordinator(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        (tmp_path / ".owlbear").mkdir()
        monkeypatch.chdir(tmp_path)
        with (
            patch("owlbear_knowledge_mcp.server.sqlite3") as mock_sqlite,
            patch("owlbear_knowledge_mcp.server.QdrantVectorStore"),
            patch("owlbear_knowledge_mcp.server.SqliteSourceStore"),
            patch("owlbear_knowledge_mcp.server.SqliteGraphStore"),
            patch("owlbear_knowledge_mcp.server.ContentStore"),
            patch("owlbear_knowledge_mcp.server.QueryFacade"),
            patch("owlbear_knowledge_mcp.server.EnrichmentStore"),
            patch("owlbear_knowledge_mcp.server.CompositeSourceFetcher") as fetcher_class,
            patch("owlbear_knowledge_mcp.server.IngestCoordinator") as coordinator_class,
        ):
            mock_sqlite.connect.return_value = MagicMock()
            async with server.app_lifespan(MagicMock()):
                pass

        assert fetcher_class.call_args.kwargs["workspace_root"] == tmp_path
        assert coordinator_class.call_args.kwargs["fetcher"] is fetcher_class.return_value


class TestRefreshKnowledgeSource:
    @staticmethod
    def _context(source: object, refresh_result: RefreshResult) -> MagicMock:
        source_store = MagicMock()
        source_store.get_source.return_value = source
        coordinator = MagicMock()
        coordinator.refresh = AsyncMock(return_value=refresh_result)
        context = MagicMock()
        context.request_context.lifespan_context = SimpleNamespace(
            source_store_v2=source_store, ingest_coordinator=coordinator
        )
        return context

    @pytest.mark.asyncio
    async def test_refresh_maps_result_and_delegates_request(self) -> None:
        source = MagicMock(state=SourceState.ACTIVE)
        context = self._context(source, RefreshResult(sources_refreshed=5, errors=()))

        result = await refresh_knowledge_source(context, source_id="source-1")

        assert result == {
            "source_id": "source-1",
            "sources_refreshed": 5,
            "documents_created": 0,
            "documents_replaced": 0,
            "documents_unchanged": 0,
            "chunks_created": 0,
            "chunks_replaced": 0,
            "errors": [],
        }
        context.request_context.lifespan_context.ingest_coordinator.refresh.assert_awaited_once_with(
            RefreshRequest(source_ids=("source-1",))
        )

    @pytest.mark.asyncio
    async def test_refresh_projects_typed_failure_without_legacy_error_text(self) -> None:
        source = MagicMock(state=SourceState.ACTIVE)
        timestamp = datetime.now(tz=UTC)
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="transport_failure",
            retryable=True,
            message="HTTP transport failed",
        )
        result = RefreshResult(
            sources_refreshed=0,
            errors=(
                RefreshError(
                    source_id="source-1",
                    error="raw adapter secret",
                    timestamp=timestamp,
                    failure=failure,
                ),
            ),
        )
        context = self._context(source, result)

        response = await refresh_knowledge_source(context, source_id="source-1")

        assert response["errors"] == [
            {
                "source_id": "source-1",
                "stage": "acquisition",
                "code": "transport_failure",
                "retryable": True,
                "message": "HTTP transport failed",
                "timestamp": timestamp.isoformat(),
            }
        ]
        assert "error" not in response["errors"][0]
        assert "raw adapter secret" not in str(response)

    @pytest.mark.asyncio
    async def test_refresh_raises_for_missing_source(self) -> None:
        context = self._context(None, RefreshResult(sources_refreshed=0, errors=()))

        with pytest.raises(ToolError, match="not found"):
            await refresh_knowledge_source(context, source_id="missing")

    @pytest.mark.asyncio
    async def test_inactive_source_returns_serialized_error(self) -> None:
        source = MagicMock(state=SourceState.INACTIVE)
        context = self._context(source, RefreshResult(sources_refreshed=0, errors=()))

        with pytest.raises(ToolError, match=r"^source is not active$"):
            await refresh_knowledge_source(context, source_id="inactive")

        context.request_context.lifespan_context.ingest_coordinator.refresh.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_raises_when_coordinator_is_unavailable(self) -> None:
        source = MagicMock(state=SourceState.ACTIVE)
        context = self._context(source, RefreshResult(sources_refreshed=0, errors=()))
        context.request_context.lifespan_context.ingest_coordinator = None

        with pytest.raises(ToolError, match=r"^ingest coordinator not available$"):
            await refresh_knowledge_source(context, source_id="source-1")


@pytest.mark.asyncio
async def test_knowledge_search_projects_query_failure() -> None:
    failure = KnowledgeFailure(
        stage=KnowledgeFailureStage.QUERY,
        code="vector_query_failed",
        retryable=True,
        message="Vector search failed",
    )
    query_facade = MagicMock()
    query_facade.search = AsyncMock(side_effect=KnowledgeOperationError(failure))
    context = SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(query_facade=query_facade),
        ),
    )

    response = await server.knowledge_search(context, query="fixture query")

    assert response == {
        "stage": "query",
        "code": "vector_query_failed",
        "retryable": True,
        "message": "Vector search failed",
    }


@pytest.mark.asyncio
async def test_knowledge_search_raises_when_service_is_unavailable() -> None:
    context = SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(query_facade=None),
        ),
    )

    with pytest.raises(ToolError, match=r"^Knowledge service not available$"):
        await server.knowledge_search(context, query="fixture query")
