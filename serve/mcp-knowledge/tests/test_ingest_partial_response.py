"""MCP ingest/refresh responses should surface partial graph extraction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.ingest import IngestResult
from owlbear_knowledge.refresh import RefreshResult
from owlbear_mcp_knowledge.server import ingest_document, refresh_source


def _ctx_with_pipeline(pipeline: object) -> MagicMock:
    app_ctx = MagicMock()
    app_ctx.ingest_pipeline = pipeline
    context = MagicMock()
    context.request_context.lifespan_context = app_ctx
    return context


def _refresh_ctx(source: MagicMock) -> MagicMock:
    store = MagicMock()
    store.get.return_value = source
    app_ctx = MagicMock()
    app_ctx.source_store = store
    app_ctx.refresh_orchestrator = MagicMock()
    app_ctx.ingest_pipeline = MagicMock()
    app_ctx.graph_store = None
    context = MagicMock()
    context.request_context.lifespan_context = app_ctx
    return context


@pytest.mark.asyncio
async def test_ingest_document_response_includes_partial_warnings() -> None:
    pipeline = MagicMock()
    pipeline.ingest_text = AsyncMock(
        return_value=IngestResult(
            document_id="doc-1",
            chunk_count=2,
            entity_count=1,
            edge_count=0,
            status="partial",
            warnings=["chunk c1 extraction failed: RuntimeError: boom"],
        )
    )

    result = await ingest_document(_ctx_with_pipeline(pipeline), text="content")

    assert "status: partial" in result
    assert "warnings: chunk c1 extraction failed" in result


@pytest.mark.asyncio
async def test_refresh_source_response_includes_partial_and_warnings() -> None:
    source = MagicMock()
    source.id = "src-1"
    source.fetch_method = "http"
    refresh = MagicMock()
    refresh.refresh = AsyncMock(
        return_value=RefreshResult(
            source_id="src-1",
            refreshed=0,
            partial=1,
            skipped=0,
            failed=0,
            warnings=["chunk c1 extraction failed"],
        )
    )

    with patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", return_value=refresh):
        result = await refresh_source(_refresh_ctx(source), source_id="src-1")

    assert isinstance(result, dict)
    assert result["partial"] == 1
    assert result["warnings"] == ["chunk c1 extraction failed"]
