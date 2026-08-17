"""Knowledge MCP source-refresh behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

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

        assert result == {"source_id": "source-1", "sources_refreshed": 5, "errors": []}
        context.request_context.lifespan_context.ingest_coordinator.refresh.assert_awaited_once_with(
            RefreshRequest(source_ids=("source-1",))
        )

    @pytest.mark.asyncio
    async def test_refresh_raises_for_missing_source(self) -> None:
        context = self._context(None, RefreshResult(sources_refreshed=0, errors=()))

        with pytest.raises(ToolError, match="not found"):
            await refresh_knowledge_source(context, source_id="missing")

    @pytest.mark.asyncio
    async def test_inactive_source_returns_serialized_error(self) -> None:
        source = MagicMock(state=SourceState.INACTIVE)
        timestamp = datetime.now(tz=UTC)
        result = RefreshResult(
            sources_refreshed=0,
            errors=(RefreshError(source_id="inactive", error="inactive", timestamp=timestamp),),
        )
        context = self._context(source, result)

        response = await refresh_knowledge_source(context, source_id="inactive")

        assert response["source_id"] == "inactive"
        assert response["sources_refreshed"] == 0
        assert response["errors"][0]["source_id"] == "inactive"
        assert isinstance(response["errors"][0]["timestamp"], str)
