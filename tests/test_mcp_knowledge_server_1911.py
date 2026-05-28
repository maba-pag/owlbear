"""Retry smoke tests for #1911 — Wire SourceFetcher in MCP server and replace refresh handler.

Tests verify:
- AC1: app_lifespan constructs CompositeSourceFetcher(workspace_root=Path.cwd(),
        content_fetcher_factory=select_content_fetcher) and passes its instance as fetcher=
        to IngestCoordinator — proven via mock.patch interception (not substring search)
- AC2: knowledge_sources_refresh returns exact mapped values (source_id echoed, sources_refreshed
        from RefreshResult, errors serialized via model_dump); refresh called with
        RefreshRequest(source_ids=(source_id,)); error dicts contain source_id, error, timestamp
- AC3: AppContext dataclass has no refresh_orchestrator or source_store fields
- AC4: server.py contains no imports of KnowledgeSourceStore, RefreshOrchestrator, or IngestPipeline
- AC5: raises ToolError when source not found; returns full envelope {source_id, sources_refreshed: 0,
        errors: [{source_id, error, timestamp}]} when source state is not ACTIVE
- AC6: test_mcp_knowledge_legacy_removal_1900.py B2b-retention assertions assert absence (not presence)
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_knowledge.protocols.ingest import RefreshError, RefreshRequest, RefreshResult
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
        assert "CompositeSourceFetcher" in src, "CompositeSourceFetcher not constructed in app_lifespan"
        assert "fetcher=" in src, "fetcher= argument not passed to IngestCoordinator in app_lifespan"

    @pytest.mark.asyncio
    async def test_app_lifespan_uses_exact_fetcher_kwargs_and_handoff_to_coordinator(self) -> None:
        """AC1: lifespan passes workspace_root=Path.cwd() and content_fetcher_factory=select_content_fetcher to
        CompositeSourceFetcher, then passes the returned instance as fetcher= to IngestCoordinator."""
        with (
            patch("owlbear_mcp_knowledge.server.sqlite3") as mock_sqlite,
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.SqliteSourceStore"),
            patch("owlbear_mcp_knowledge.server.SqliteGraphStore"),
            patch("owlbear_mcp_knowledge.server.ContentStore"),
            patch("owlbear_mcp_knowledge.server.QueryFacade"),
            patch("owlbear_mcp_knowledge.server.EnrichmentStore"),
            patch("owlbear_mcp_knowledge.server.CompositeSourceFetcher") as mock_csf,
            patch("owlbear_mcp_knowledge.server.IngestCoordinator") as mock_ic,
            patch("owlbear_mcp_knowledge.server._apply_tool_exclusions"),
        ):
            mock_sqlite.connect.return_value = MagicMock()
            async with server.app_lifespan(MagicMock()):
                pass

        # CompositeSourceFetcher must be constructed with exact required kwargs
        mock_csf.assert_called_once()
        csf_kwargs = mock_csf.call_args.kwargs
        assert csf_kwargs["workspace_root"] == Path.cwd(), (
            f"CompositeSourceFetcher workspace_root mismatch: {csf_kwargs.get('workspace_root')!r}"
        )
        assert csf_kwargs["content_fetcher_factory"] is server.select_content_fetcher, (
            "content_fetcher_factory must be select_content_fetcher"
        )

        # IngestCoordinator must receive the CompositeSourceFetcher instance as fetcher=
        mock_ic.assert_called_once()
        ic_kwargs = mock_ic.call_args.kwargs
        assert ic_kwargs.get("fetcher") is mock_csf.return_value, (
            "IngestCoordinator must receive the CompositeSourceFetcher instance as fetcher="
        )

    # -----------------------------------------------------------------------
    # AC2 — handler response: exact values, delegation, and error serialization
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

    @pytest.mark.asyncio
    async def test_refresh_handler_returns_exact_mapped_values_and_delegates_refresh_request(self) -> None:
        """AC2: source_id echoed, sources_refreshed from RefreshResult, errors list empty; refresh called with
        RefreshRequest(source_ids=(source_id,))."""
        source = MagicMock()
        source.state = SourceState.ACTIVE

        mock_result = RefreshResult(sources_refreshed=5, errors=())

        ingest_coordinator = MagicMock()
        ingest_coordinator.refresh = AsyncMock(return_value=mock_result)

        source_store_v2 = MagicMock()
        source_store_v2.get_source = MagicMock(return_value=source)

        app_ctx = SimpleNamespace(
            source_store_v2=source_store_v2,
            ingest_coordinator=ingest_coordinator,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        result = await knowledge_sources_refresh(ctx, source_id="my-src-42")

        assert result["source_id"] == "my-src-42", f"source_id not echoed: {result['source_id']!r}"
        assert result["sources_refreshed"] == 5, (
            f"sources_refreshed must equal RefreshResult.sources_refreshed=5, got {result['sources_refreshed']!r}"
        )
        assert result["errors"] == [], f"errors should be empty list, got {result['errors']!r}"
        ingest_coordinator.refresh.assert_called_once_with(RefreshRequest(source_ids=("my-src-42",)))

    @pytest.mark.asyncio
    async def test_refresh_handler_serializes_refresh_errors_with_all_fields(self) -> None:
        """AC2: each error entry is a dict with source_id, error, timestamp strings from RefreshError.model_dump(mode='json')."""
        source = MagicMock()
        source.state = SourceState.ACTIVE

        ts = datetime.now(tz=UTC)
        error_item = RefreshError(source_id="src-err", error="fetch failed", timestamp=ts)
        mock_result = RefreshResult(sources_refreshed=0, errors=(error_item,))

        ingest_coordinator = MagicMock()
        ingest_coordinator.refresh = AsyncMock(return_value=mock_result)

        source_store_v2 = MagicMock()
        source_store_v2.get_source = MagicMock(return_value=source)

        app_ctx = SimpleNamespace(
            source_store_v2=source_store_v2,
            ingest_coordinator=ingest_coordinator,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        result = await knowledge_sources_refresh(ctx, source_id="src-err")

        assert result["sources_refreshed"] == 0
        assert len(result["errors"]) == 1
        err = result["errors"][0]
        assert err["source_id"] == "src-err"
        assert err["error"] == "fetch failed"
        assert isinstance(err["timestamp"], str), "timestamp must be serialized to str via model_dump(mode='json')"

    # -----------------------------------------------------------------------
    # AC3 — AppContext field removal
    # -----------------------------------------------------------------------

    def test_appcontext_has_no_source_store_or_refresh_orchestrator(self) -> None:
        """AppContext must not have source_store or refresh_orchestrator fields (AC3)."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "refresh_orchestrator" not in field_names, "refresh_orchestrator still present in AppContext"
        assert "source_store" not in field_names, "source_store still present in AppContext"

    # -----------------------------------------------------------------------
    # AC4 — No legacy imports in server.py
    # -----------------------------------------------------------------------

    def test_server_py_has_no_legacy_class_imports(self) -> None:
        """server.py must not import KnowledgeSourceStore, RefreshOrchestrator, or IngestPipeline (AC4)."""
        server_file = Path(inspect.getfile(server))
        server_source = server_file.read_text(encoding="utf-8")
        assert "KnowledgeSourceStore" not in server_source, "KnowledgeSourceStore still imported in server.py"
        assert "RefreshOrchestrator" not in server_source, "RefreshOrchestrator still imported in server.py"
        assert "IngestPipeline" not in server_source, "IngestPipeline still imported in server.py"

    # -----------------------------------------------------------------------
    # AC5 — ToolError when source not found; full envelope when not ACTIVE
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

    @pytest.mark.asyncio
    async def test_refresh_returns_full_envelope_when_source_is_not_active(self) -> None:
        """AC5: returns {source_id, sources_refreshed: 0, errors: [{source_id, error, timestamp}]} when source is not ACTIVE."""
        source = MagicMock()
        source.state = SourceState.INACTIVE

        source_store_v2 = MagicMock()
        source_store_v2.get_source = MagicMock(return_value=source)

        app_ctx = SimpleNamespace(
            source_store_v2=source_store_v2,
            ingest_coordinator=MagicMock(),
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        result = await knowledge_sources_refresh(ctx, source_id="src-inactive")

        assert result["source_id"] == "src-inactive", f"source_id not echoed in envelope: {result.get('source_id')!r}"
        assert result["sources_refreshed"] == 0, (
            f"sources_refreshed must be 0 for non-ACTIVE source, got {result.get('sources_refreshed')!r}"
        )
        errors = result.get("errors", [])
        assert len(errors) == 1, f"expected 1 error entry in envelope, got {len(errors)}"
        err = errors[0]
        assert err["source_id"] == "src-inactive", f"error source_id not echoed: {err.get('source_id')!r}"
        assert isinstance(err["error"], str), "error field must be a string"
        assert len(err["error"]) > 0, "error field must be non-empty"
        assert isinstance(err["timestamp"], str), "timestamp must be an ISO datetime string"
        datetime.fromisoformat(err["timestamp"])  # must not raise

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
