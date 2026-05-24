"""Response contract tests for refresh_source."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.refresh import RefreshResult
from owlbear_mcp_knowledge.server import refresh_source


def _ctx(source: MagicMock, *, inter_doc_builder: object | None = None) -> MagicMock:
    store = MagicMock()
    store.get.return_value = source
    app_ctx = MagicMock()
    app_ctx.source_store = store
    app_ctx.refresh_orchestrator = MagicMock()
    app_ctx.ingest_pipeline = MagicMock()
    app_ctx.graph_store = None
    app_ctx.inter_doc_builder = inter_doc_builder
    context = MagicMock()
    context.request_context.lifespan_context = app_ctx
    return context


def _source() -> MagicMock:
    source = MagicMock()
    source.id = "src-1"
    source.fetch_method = "http"
    return source


@pytest.mark.asyncio
async def test_refresh_source_response_includes_errors_from_result() -> None:
    source = _source()
    refresh = MagicMock()
    refresh.refresh = AsyncMock(
        return_value=RefreshResult(
            source_id="src-1",
            refreshed=0,
            skipped=0,
            failed=1,
            errors=["no files matched source path 'missing.md'"],
        )
    )

    with patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", return_value=refresh):
        result = await refresh_source(_ctx(source), source_id="src-1")

    assert isinstance(result, dict)
    assert result["partial"] == 0
    assert result["errors"] == ["no files matched source path 'missing.md'"]
    assert result["warnings"] == []


@pytest.mark.asyncio
async def test_refresh_source_success_response_includes_empty_errors() -> None:
    source = _source()
    refresh = MagicMock()
    refresh.refresh = AsyncMock(
        return_value=RefreshResult(
            source_id="src-1",
            refreshed=1,
            skipped=0,
            failed=0,
            errors=[],
        )
    )

    with patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", return_value=refresh):
        result = await refresh_source(_ctx(source), source_id="src-1")

    assert isinstance(result, dict)
    assert result["refreshed"] == 1
    assert result["partial"] == 0
    assert result["errors"] == []
    assert result["warnings"] == []


@pytest.mark.asyncio
async def test_refresh_source_passes_inter_doc_builder_to_orchestrator() -> None:
    source = _source()
    builder = object()
    refresh = MagicMock()
    refresh.refresh = AsyncMock(
        return_value=RefreshResult(
            source_id="src-1",
            refreshed=1,
            skipped=0,
            failed=0,
            errors=[],
        )
    )

    with patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", return_value=refresh) as orchestrator_cls:
        result = await refresh_source(_ctx(source, inter_doc_builder=builder), source_id="src-1")

    assert isinstance(result, dict)
    assert orchestrator_cls.call_args.kwargs["inter_doc_builder"] is builder


@pytest.mark.asyncio
async def test_refresh_source_raises_when_source_store_missing() -> None:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.source_store = None

    with pytest.raises(ToolError, match="source store not available"):
        await refresh_source(ctx, source_id="src-1")


@pytest.mark.asyncio
async def test_refresh_source_raises_when_source_not_found() -> None:
    with pytest.raises(ToolError, match="Source 'src-1' not found"):
        await refresh_source(_ctx(None), source_id="src-1")


@pytest.mark.asyncio
async def test_refresh_source_returns_error_when_orchestrator_missing() -> None:
    source = _source()
    ctx = _ctx(source)
    ctx.request_context.lifespan_context.refresh_orchestrator = None

    result = await refresh_source(ctx, source_id="src-1")

    assert result == "error: refresh orchestrator not available"


@pytest.mark.asyncio
async def test_refresh_source_returns_error_when_pipeline_missing() -> None:
    source = _source()
    ctx = _ctx(source)
    ctx.request_context.lifespan_context.ingest_pipeline = None

    result = await refresh_source(ctx, source_id="src-1")

    assert result == "error: ingest pipeline not available"


@pytest.mark.asyncio
async def test_refresh_source_value_error_returns_error_string() -> None:
    source = _source()
    refresh = MagicMock()
    refresh.refresh = AsyncMock(side_effect=ValueError("bad source config"))

    with patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", return_value=refresh):
        result = await refresh_source(_ctx(source), source_id="src-1")

    assert result == "error: bad source config"
