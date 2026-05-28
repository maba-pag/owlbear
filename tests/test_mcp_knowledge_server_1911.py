"""RED smoke tests for #1911 — Wire SourceFetcher in MCP server and replace refresh handler.

Tests verify:
- AC1: app_lifespan constructs CompositeSourceFetcher(workspace_root=Path.cwd(),
        content_fetcher_factory=select_content_fetcher) and passes fetcher= to IngestCoordinator
- AC2: knowledge_sources_refresh returns dict with source_id, sources_refreshed, errors keys
- AC3: AppContext has no refresh_orchestrator or source_store fields
- AC4: server.py has no imports of KnowledgeSourceStore, RefreshOrchestrator, or IngestPipeline
- AC5: knowledge_sources_refresh raises ToolError when source_store_v2.get_source returns None
- AC6: test_mcp_knowledge_legacy_removal_1900.py B2b-retention assertions updated to assert absence
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_knowledge.protocols.ingest import RefreshResult
from owlbear_knowledge.protocols.sources import SourceState
from owlbear_mcp_knowledge import server
from owlbear_mcp_knowledge.server import AppContext, knowledge_sources_refresh


class TestFromAC_SourceFetcherWiring:
    """Smoke tests for #1911 — source fetcher wiring and refresh handler replacement."""

    # -----------------------------------------------------------------------
    # AC1 — app_lifespan wires CompositeSourceFetcher into IngestCoordinator
    # -----------------------------------------------------------------------

    def test_app_lifespan_constructs_composite_fetcher_wired_to_coordinator(self) -> None:
        """app_lifespan must construct CompositeSourceFetcher and pass fetcher= to IngestCoordinator (AC1)."""
        src = inspect.getsource(server.app_lifespan)
        assert "CompositeSourceFetcher" in src, (
            "CompositeSourceFetcher not constructed in app_lifespan"
        )
        assert "fetcher=" in src, (
            "fetcher= argument not passed to IngestCoordinator in app_lifespan"
        )

    # -----------------------------------------------------------------------
    # AC2 — handler response shape
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_handler_returns_response_with_expected_keys(self) -> None:
        """knowledge_sources_refresh must return dict with source_id, sources_refreshed, errors (AC2)."""
        source = MagicMock()
        source.state = SourceState.ACTIVE

        mock_result = RefreshResult(sources_refreshed=1, errors=())

        ingest_coordinator = MagicMock()
        ingest_coordinator.refresh = AsyncMock(return_value=mock_result)

        source_store_v2 = MagicMock()
        source_store_v2.get_source = MagicMock(return_value=source)

        app_ctx = SimpleNamespace(
            source_store=None,
            source_store_v2=source_store_v2,
            ingest_coordinator=ingest_coordinator,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        result = await knowledge_sources_refresh(ctx, source_id="src-1")

        assert isinstance(result, dict), f"Expected dict, got {type(result)!r}"
        assert "source_id" in result, "response dict missing 'source_id' key"
        assert "sources_refreshed" in result, "response dict missing 'sources_refreshed' key"
        assert "errors" in result, "response dict missing 'errors' key"

    # -----------------------------------------------------------------------
    # AC3 — AppContext field removal
    # -----------------------------------------------------------------------

    def test_appcontext_has_no_source_store_or_refresh_orchestrator(self) -> None:
        """AppContext must not have source_store or refresh_orchestrator fields (AC3)."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "refresh_orchestrator" not in field_names, (
            "refresh_orchestrator still present in AppContext"
        )
        assert "source_store" not in field_names, (
            "source_store still present in AppContext"
        )

    # -----------------------------------------------------------------------
    # AC4 — No legacy imports in server.py
    # -----------------------------------------------------------------------

    def test_server_py_has_no_legacy_class_imports(self) -> None:
        """server.py must not import KnowledgeSourceStore, RefreshOrchestrator, or IngestPipeline (AC4)."""
        server_file = Path(inspect.getfile(server))
        server_source = server_file.read_text(encoding="utf-8")
        assert "KnowledgeSourceStore" not in server_source, (
            "KnowledgeSourceStore still imported in server.py"
        )
        assert "RefreshOrchestrator" not in server_source, (
            "RefreshOrchestrator still imported in server.py"
        )
        assert "IngestPipeline" not in server_source, (
            "IngestPipeline still imported in server.py"
        )

    # -----------------------------------------------------------------------
    # AC5 — ToolError when source not found
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_raises_toolerror_when_source_not_found(self) -> None:
        """knowledge_sources_refresh must raise ToolError when source_store_v2.get_source returns None (AC5)."""
        source_store_v2 = MagicMock()
        source_store_v2.get_source = MagicMock(return_value=None)

        app_ctx = SimpleNamespace(
            source_store=None,
            source_store_v2=source_store_v2,
            ingest_coordinator=MagicMock(),
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        with pytest.raises(ToolError, match=r"not found"):
            await knowledge_sources_refresh(ctx, source_id="nonexistent-src")

    # -----------------------------------------------------------------------
    # AC6 — Legacy 1900 test file retention assertions flipped to absence
    # -----------------------------------------------------------------------

    def test_legacy_removal_1900_b2b_tests_assert_absence_not_presence(self) -> None:
        """test_mcp_knowledge_legacy_removal_1900.py must assert source_store/refresh_orchestrator absent (AC6)."""
        test_file = Path(__file__).parent / "test_mcp_knowledge_legacy_removal_1900.py"
        content = test_file.read_text(encoding="utf-8")
        assert '"source_store" in field_names' not in content, (
            "Old B2b retention assertion 'source_store in field_names' still present in 1900 test file; "
            "must be updated to assert absence"
        )
        assert '"refresh_orchestrator" in field_names' not in content, (
            "Old B2b retention assertion 'refresh_orchestrator in field_names' still present in 1900 test file; "
            "must be updated to assert absence"
        )
