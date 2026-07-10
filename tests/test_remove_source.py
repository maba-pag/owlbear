"""Tests for remove_source MCP tool delegation refactor (task #1889).

Tests the delegation contract defined in AC:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (remove_source tool)

Target implementation:
  remove_source delegates to IngestCoordinator.delete_source() instead of
  manual SQL/vector operations, and returns a structured PurgeResult dict.

AC coverage:
  AC1 — remove_source delegates to IngestCoordinator.delete_source(source_id)
  AC2 — COMPLETE status: response dict has status, completed_steps, source, content,
         enrichment, graph
  AC3 — PARTIAL status: response dict has status, completed_steps, failed_step, error;
         does NOT raise ToolError
  AC4 — source_store_v2.get_source returns None → ToolError raised before delegation
  AC5 — conn.execute and vector_store.delete_embedding not called (old code removed)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.protocols.content import ContentPurgeResult
from owlbear_knowledge.protocols.enrichment import EnrichmentPurgeResult
from owlbear_knowledge.protocols.graph import EvidenceInvalidationResult
from owlbear_knowledge.protocols.ingest import PurgeResult, PurgeStatus
from owlbear_knowledge.protocols.sources import SourceDeletionInfo
from owlbear_mcp_knowledge.server import delete_knowledge_source as remove_source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SOURCE_ID = "src-test-1889"


def _make_source_deletion_info(source_id: str = _SOURCE_ID) -> SourceDeletionInfo:
    return SourceDeletionInfo(
        source_id=source_id,
        source_name="Test Source",
        scope="global",
        deleted_at=datetime.now(tz=UTC),
        reason=None,
    )


def _make_content_purge(source_id: str = _SOURCE_ID) -> ContentPurgeResult:
    return ContentPurgeResult(
        source_id=source_id,
        document_ids=("doc-1",),
        chunk_ids=("chunk-1", "chunk-2"),
        vector_ids=("chunk-1", "chunk-2"),
    )


def _make_enrichment_purge(source_id: str = _SOURCE_ID) -> EnrichmentPurgeResult:
    return EnrichmentPurgeResult(
        source_id=source_id,
        queue_items_removed=2,
        extractions_removed=1,
    )


def _make_evidence_invalidation() -> EvidenceInvalidationResult:
    return EvidenceInvalidationResult(
        invalidated_evidence_ids=("ev-1",),
        orphaned_entity_ids=(),
        orphaned_edge_ids=(),
    )


def _make_complete_purge_result(source_id: str = _SOURCE_ID) -> PurgeResult:
    return PurgeResult(
        status=PurgeStatus.COMPLETE,
        completed_steps=(
            "sources.delete",
            "content.purge",
            "enrichment.discard",
            "enrichment.purge",
            "graph.invalidate",
        ),
        failed_step=None,
        error=None,
        source=_make_source_deletion_info(source_id),
        content=_make_content_purge(source_id),
        enrichment=_make_enrichment_purge(source_id),
        graph=_make_evidence_invalidation(),
    )


def _make_partial_purge_result(source_id: str = _SOURCE_ID) -> PurgeResult:
    return PurgeResult(
        status=PurgeStatus.PARTIAL,
        completed_steps=("sources.delete", "content.purge"),
        failed_step="enrichment.discard",
        error="EnrichmentStore connection lost",
        source=_make_source_deletion_info(source_id),
        content=_make_content_purge(source_id),
        enrichment=EnrichmentPurgeResult(source_id=source_id),
        graph=EvidenceInvalidationResult(),
    )


def _make_ctx(
    *,
    source_found: bool = True,
    purge_result: PurgeResult | None = None,
) -> MagicMock:
    """Return a mock FastMCP Context with AppContext lifespan context configured."""
    if purge_result is None:
        purge_result = _make_complete_purge_result()

    app_ctx = MagicMock()
    # New lookup API (AC4)
    if source_found:
        app_ctx.source_store_v2.get_source.return_value = MagicMock()
    else:
        app_ctx.source_store_v2.get_source.return_value = None
    # Coordinator delegation (AC1)
    app_ctx.ingest_coordinator.delete_source = AsyncMock(return_value=purge_result)
    # Configure the old SQL path to return real rows so the old code WOULD call
    # vector_store.delete_embedding — making AC5 regression tests fail correctly.
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (3,)
    conn.execute.return_value.fetchall.return_value = [("chunk-old-a",), ("chunk-old-b",)]
    app_ctx.conn = conn
    app_ctx.vector_store = MagicMock()

    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_RemoveSourceDelegation
# ---------------------------------------------------------------------------


class TestRemoveSourceDelegation:
    """AC coverage for remove_source delegation refactor (#1889).

    Verifies that remove_source delegates to IngestCoordinator.delete_source()
    and returns a structured PurgeResult dict instead of manual SQL/vector ops.
    """

    # ------------------------------------------------------------------
    # AC1 — Delegates to IngestCoordinator.delete_source
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_delegates_to_ingest_coordinator_delete_source(self) -> None:
        """remove_source calls ingest_coordinator.delete_source(source_id)."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context
        await remove_source(ctx, _SOURCE_ID)
        app_ctx.ingest_coordinator.delete_source.assert_called_once_with(_SOURCE_ID)

    @pytest.mark.asyncio
    async def test_passes_exact_source_id_to_coordinator(self) -> None:
        """remove_source forwards the exact source_id to ingest_coordinator.delete_source."""
        source_id = "specific-source-abc-1889"
        ctx = _make_ctx(purge_result=_make_complete_purge_result(source_id))
        app_ctx = ctx.request_context.lifespan_context
        await remove_source(ctx, source_id)
        args, kwargs = app_ctx.ingest_coordinator.delete_source.call_args
        assert args == (source_id,) or kwargs.get("source_id") == source_id

    # ------------------------------------------------------------------
    # AC2 — COMPLETE status response shape
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_complete_response_contains_status_complete(self) -> None:
        """Response dict on COMPLETE has status == 'complete'."""
        ctx = _make_ctx(purge_result=_make_complete_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert result["status"] == "complete"

    @pytest.mark.asyncio
    async def test_complete_response_contains_completed_steps(self) -> None:
        """Response dict on COMPLETE has 'completed_steps' key."""
        ctx = _make_ctx(purge_result=_make_complete_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert "completed_steps" in result

    @pytest.mark.asyncio
    async def test_complete_response_contains_source_sub_result(self) -> None:
        """Response dict on COMPLETE has 'source' summary field."""
        ctx = _make_ctx(purge_result=_make_complete_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert "source" in result

    @pytest.mark.asyncio
    async def test_complete_response_contains_content_sub_result(self) -> None:
        """Response dict on COMPLETE has 'content' summary field."""
        ctx = _make_ctx(purge_result=_make_complete_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert "content" in result

    @pytest.mark.asyncio
    async def test_complete_response_contains_enrichment_sub_result(self) -> None:
        """Response dict on COMPLETE has 'enrichment' summary field."""
        ctx = _make_ctx(purge_result=_make_complete_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert "enrichment" in result

    @pytest.mark.asyncio
    async def test_complete_response_contains_graph_sub_result(self) -> None:
        """Response dict on COMPLETE has 'graph' summary field."""
        ctx = _make_ctx(purge_result=_make_complete_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert "graph" in result

    # ------------------------------------------------------------------
    # AC3 — PARTIAL status response (does NOT raise ToolError)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_partial_returns_structured_dict_not_tool_error(self) -> None:
        """PARTIAL purge result is returned as a structured dict, not raised as ToolError."""
        ctx = _make_ctx(purge_result=_make_partial_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        # Old code raises ToolError on vector errors; new code returns structured dict.
        # 'status' key only present in the new response shape.
        assert "status" in result

    @pytest.mark.asyncio
    async def test_partial_response_status_equals_partial(self) -> None:
        """Response dict on PARTIAL has status == 'partial'."""
        ctx = _make_ctx(purge_result=_make_partial_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert result["status"] == "partial"

    @pytest.mark.asyncio
    async def test_partial_response_contains_failed_step(self) -> None:
        """Response dict on PARTIAL has 'failed_step' matching PurgeResult.failed_step."""
        ctx = _make_ctx(purge_result=_make_partial_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert result["failed_step"] == "enrichment.discard"

    @pytest.mark.asyncio
    async def test_partial_response_contains_error_field(self) -> None:
        """Response dict on PARTIAL has 'error' matching PurgeResult.error."""
        ctx = _make_ctx(purge_result=_make_partial_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert result["error"] == "EnrichmentStore connection lost"

    @pytest.mark.asyncio
    async def test_partial_response_contains_completed_steps(self) -> None:
        """Response dict on PARTIAL has 'completed_steps' key."""
        ctx = _make_ctx(purge_result=_make_partial_purge_result())
        result = await remove_source(ctx, _SOURCE_ID)
        assert "completed_steps" in result

    # ------------------------------------------------------------------
    # AC4 — Source not found raises ToolError before delegation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_source_not_found_raises_tool_error(self) -> None:
        """ToolError is raised when source_store_v2.get_source(source_id) returns None."""
        ctx = _make_ctx(source_found=False)
        with pytest.raises(ToolError):
            await remove_source(ctx, _SOURCE_ID)

    @pytest.mark.asyncio
    async def test_source_not_found_does_not_call_coordinator(self) -> None:
        """ingest_coordinator.delete_source is NOT called when source lookup returns None."""
        ctx = _make_ctx(source_found=False)
        app_ctx = ctx.request_context.lifespan_context
        with pytest.raises(ToolError):
            await remove_source(ctx, _SOURCE_ID)
        app_ctx.ingest_coordinator.delete_source.assert_not_called()

    @pytest.mark.asyncio
    async def test_source_store_v2_get_source_consulted_for_lookup(self) -> None:
        """source_store_v2.get_source(source_id) is used for not-found pre-validation."""
        ctx = _make_ctx(source_found=True)
        app_ctx = ctx.request_context.lifespan_context
        await remove_source(ctx, _SOURCE_ID)
        app_ctx.source_store_v2.get_source.assert_called_once_with(_SOURCE_ID)

    # ------------------------------------------------------------------
    # AC5 — Old SQL / vector deletion code removed (regression guards)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_conn_execute_not_called_on_successful_delete(self) -> None:
        """conn.execute (manual SQL) is NOT called — old queries must be removed."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context
        await remove_source(ctx, _SOURCE_ID)
        app_ctx.conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_vector_store_delete_embedding_not_called_on_successful_delete(self) -> None:
        """vector_store.delete_embedding is NOT called — old vector loop must be removed."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context
        await remove_source(ctx, _SOURCE_ID)
        app_ctx.vector_store.delete_embedding.assert_not_called()
