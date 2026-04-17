"""Failing tests for task #737: expose refresh_source as MCP tool in mcp-knowledge.

TDD RED phase — all tests FAIL because refresh_source does not yet exist in
server.py.  The builder reads this file as a specification.

AC coverage:
  - AC1 : refresh_source tool exists and is importable from server module
  - AC2 : AppContext dataclass has refresh_orchestrator field (RefreshOrchestrator | None)
  - AC3a: Tool annotations: readOnlyHint=False, destructiveHint=False
  - AC3b: refresh_source is present in server.__all__
  - AC4 : Tool accepts source_id: str (required parameter)
  - AC5 : Tool calls source_store.get(source_id) to resolve the source
  - AC6 : ToolError raised when source_store.get returns None (source not found)
  - AC7a: Disabled source (enabled=False) returns error string — ValueError not propagated
  - AC7b: Disabled source error string mentions the source_id (informative message)
  - AC8 : awaits refresh_orchestrator.refresh(source) directly — async, no asyncio.to_thread
  - AC9a: Successful result dict contains source_id key
  - AC9b: Successful result dict contains refreshed count
  - AC9c: Successful result dict contains skipped count
  - AC9d: Successful result dict contains failed count
  - AC10 : refresh_orchestrator is None → returns error string, no exception
  - AC11 : source_store is None → returns ToolError, consistent with existing store-null pattern
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import target — refresh_source does not yet exist in server.py (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_knowledge.server import (  # type: ignore[import]
    AppContext,
    refresh_source,
)
import owlbear_mcp_knowledge.server as server_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_refresh_result(
    source_id: str = "src-001",
    refreshed: int = 5,
    skipped: int = 1,
    failed: int = 0,
) -> MagicMock:
    """Return a MagicMock that mimics RefreshResult."""
    r = MagicMock()
    r.source_id = source_id
    r.refreshed = refreshed
    r.skipped = skipped
    r.failed = failed
    r.errors = []
    return r


def _make_source(
    source_id: str = "src-001",
    *,
    enabled: bool = True,
) -> MagicMock:
    """Return a MagicMock that mimics KnowledgeSource."""
    s = MagicMock()
    s.id = source_id
    s.enabled = enabled
    return s


def _make_ctx(
    *,
    source_store: object = None,
    refresh_orchestrator: object = None,
) -> MagicMock:
    """Return a minimal FastMCP Context mock with both stores in lifespan_context."""
    ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.source_store = source_store
    app_ctx.refresh_orchestrator = refresh_orchestrator
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_RefreshSourceMcpTool
# ---------------------------------------------------------------------------


class TestFromAC_RefreshSourceMcpTool:
    """Contract tests for refresh_source MCP tool derived from task #737 AC."""

    # -- AC1: tool is importable -----------------------------------------------

    def test_refresh_source_is_importable(self) -> None:
        """refresh_source must be importable from owlbear_mcp_knowledge.server."""
        assert callable(refresh_source), (
            "refresh_source not found in owlbear_mcp_knowledge.server. Builder must define and register it."
        )

    # -- AC2: AppContext has refresh_orchestrator field -------------------------

    def test_app_context_has_refresh_orchestrator_field(self) -> None:
        """AppContext dataclass must declare a refresh_orchestrator field."""
        fields = {f.name for f in AppContext.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        assert "refresh_orchestrator" in fields, (
            f"AppContext missing 'refresh_orchestrator' field; current fields: {fields}"
        )

    # -- AC3a: tool is an async function ----------------------------------------

    def test_refresh_source_is_async(self) -> None:
        """refresh_source must be an async function (await refresh_orchestrator.refresh)."""
        assert inspect.iscoroutinefunction(refresh_source), (
            "refresh_source must be defined as 'async def' to await the orchestrator"
        )

    # -- AC3b: refresh_source in __all__ ----------------------------------------

    def test_refresh_source_in_all(self) -> None:
        """refresh_source must be listed in server.__all__."""
        all_exports = getattr(server_mod, "__all__", [])
        assert "refresh_source" in all_exports, (
            f"'refresh_source' not found in server.__all__. Current __all__: {all_exports}"
        )

    # -- AC4: tool signature accepts source_id ---------------------------------

    def test_refresh_source_accepts_source_id_parameter(self) -> None:
        """refresh_source must accept a source_id parameter."""
        sig = inspect.signature(refresh_source)
        assert "source_id" in sig.parameters, f"refresh_source signature {sig} missing 'source_id' parameter"

    # -- AC5: calls store.get with source_id ------------------------------------

    @pytest.mark.asyncio
    async def test_calls_store_get_with_source_id(self) -> None:
        """Tool must call source_store.get(source_id) to look up the source."""
        mock_store = MagicMock()
        source = _make_source("abc-123")
        mock_store.get.return_value = source

        mock_orchestrator = AsyncMock()
        mock_orchestrator.refresh = AsyncMock(return_value=_make_refresh_result("abc-123"))

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        await refresh_source(ctx, source_id="abc-123")

        mock_store.get.assert_called_once_with("abc-123")

    # -- AC6: ToolError when source not found -----------------------------------

    @pytest.mark.asyncio
    async def test_raises_tool_error_when_source_not_found(self) -> None:
        """ToolError must be raised when source_store.get returns None."""
        from mcp.server.fastmcp.exceptions import ToolError

        mock_store = MagicMock()
        mock_store.get.return_value = None

        mock_orchestrator = AsyncMock()
        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        with pytest.raises(ToolError):
            await refresh_source(ctx, source_id="nonexistent-id")

    # -- AC7a: disabled source returns error string, not ValueError -------------

    @pytest.mark.asyncio
    async def test_disabled_source_returns_error_string_not_exception(self) -> None:
        """Disabled source must return an error string — ValueError must not propagate."""
        mock_store = MagicMock()
        disabled_source = _make_source("dis-001", enabled=False)
        mock_store.get.return_value = disabled_source

        mock_orchestrator = AsyncMock()
        mock_orchestrator.refresh.side_effect = ValueError("Source 'dis-001' is disabled")

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        result = await refresh_source(ctx, source_id="dis-001")

        assert isinstance(result, str), (
            f"Expected str error message for disabled source, got {type(result)}: {result!r}"
        )

    # -- AC7b: disabled source error string is informative ----------------------

    @pytest.mark.asyncio
    async def test_disabled_source_error_string_mentions_source(self) -> None:
        """Disabled source error string must mention the source_id."""
        mock_store = MagicMock()
        disabled_source = _make_source("dis-999", enabled=False)
        mock_store.get.return_value = disabled_source

        mock_orchestrator = AsyncMock()
        mock_orchestrator.refresh.side_effect = ValueError("Source 'dis-999' is disabled")

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        result = await refresh_source(ctx, source_id="dis-999")

        assert "dis-999" in result or "disabled" in result.lower(), (
            f"Error string should mention source_id or 'disabled'; got: {result!r}"
        )

    # -- AC8: awaits refresh_orchestrator.refresh(source) directly -------------

    @pytest.mark.asyncio
    async def test_calls_refresh_orchestrator_refresh_with_source(self) -> None:
        """Tool must call refresh_orchestrator.refresh(source) — not asyncio.to_thread."""
        mock_store = MagicMock()
        source = _make_source("src-007")
        mock_store.get.return_value = source

        mock_orchestrator = AsyncMock()
        mock_orchestrator.refresh = AsyncMock(return_value=_make_refresh_result("src-007"))

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        await refresh_source(ctx, source_id="src-007")

        mock_orchestrator.refresh.assert_called_once_with(source)

    # -- AC9a: result dict contains source_id -----------------------------------

    @pytest.mark.asyncio
    async def test_result_contains_source_id(self) -> None:
        """Return dict must contain 'source_id' key matching the source."""
        mock_store = MagicMock()
        source = _make_source("src-abc")
        mock_store.get.return_value = source

        refresh_result = _make_refresh_result(source_id="src-abc", refreshed=3, skipped=1, failed=0)
        mock_orchestrator = AsyncMock()
        mock_orchestrator.refresh = AsyncMock(return_value=refresh_result)

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        result = await refresh_source(ctx, source_id="src-abc")

        assert isinstance(result, dict), f"Expected dict result, got {type(result)}: {result!r}"
        assert "source_id" in result, f"Result dict missing 'source_id'; keys: {list(result)}"
        assert result["source_id"] == "src-abc"

    # -- AC9b: result dict contains refreshed count ----------------------------

    @pytest.mark.asyncio
    async def test_result_contains_refreshed_count(self) -> None:
        """Return dict must contain 'refreshed' key with correct count."""
        mock_store = MagicMock()
        source = _make_source("src-b1")
        mock_store.get.return_value = source

        refresh_result = _make_refresh_result(source_id="src-b1", refreshed=7, skipped=2, failed=1)
        mock_orchestrator = AsyncMock()
        mock_orchestrator.refresh = AsyncMock(return_value=refresh_result)

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        result = await refresh_source(ctx, source_id="src-b1")

        assert isinstance(result, dict)
        assert "refreshed" in result, f"Result dict missing 'refreshed'; keys: {list(result)}"
        assert result["refreshed"] == 7

    # -- AC9c: result dict contains skipped count ------------------------------

    @pytest.mark.asyncio
    async def test_result_contains_skipped_count(self) -> None:
        """Return dict must contain 'skipped' key with correct count."""
        mock_store = MagicMock()
        source = _make_source("src-c2")
        mock_store.get.return_value = source

        refresh_result = _make_refresh_result(source_id="src-c2", refreshed=2, skipped=4, failed=0)
        mock_orchestrator = AsyncMock()
        mock_orchestrator.refresh = AsyncMock(return_value=refresh_result)

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        result = await refresh_source(ctx, source_id="src-c2")

        assert isinstance(result, dict)
        assert "skipped" in result, f"Result dict missing 'skipped'; keys: {list(result)}"
        assert result["skipped"] == 4

    # -- AC9d: result dict contains failed count --------------------------------

    @pytest.mark.asyncio
    async def test_result_contains_failed_count(self) -> None:
        """Return dict must contain 'failed' key with correct count."""
        mock_store = MagicMock()
        source = _make_source("src-d3")
        mock_store.get.return_value = source

        refresh_result = _make_refresh_result(source_id="src-d3", refreshed=0, skipped=0, failed=3)
        mock_orchestrator = AsyncMock()
        mock_orchestrator.refresh = AsyncMock(return_value=refresh_result)

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=mock_orchestrator)

        result = await refresh_source(ctx, source_id="src-d3")

        assert isinstance(result, dict)
        assert "failed" in result, f"Result dict missing 'failed'; keys: {list(result)}"
        assert result["failed"] == 3

    # -- AC10: refresh_orchestrator is None → error string, no crash -----------

    @pytest.mark.asyncio
    async def test_refresh_orchestrator_none_returns_error_string(self) -> None:
        """When refresh_orchestrator is None, tool must return an error string (not crash)."""
        mock_store = MagicMock()
        source = _make_source("src-x")
        mock_store.get.return_value = source

        ctx = _make_ctx(source_store=mock_store, refresh_orchestrator=None)

        result = await refresh_source(ctx, source_id="src-x")

        assert isinstance(result, str), (
            f"Expected error string when orchestrator is None, got {type(result)}: {result!r}"
        )

    # -- AC11: source_store is None → consistent ToolError ---------------------

    @pytest.mark.asyncio
    async def test_source_store_none_raises_tool_error(self) -> None:
        """When source_store is None, tool must raise ToolError (follows list_sources pattern)."""
        from mcp.server.fastmcp.exceptions import ToolError

        mock_orchestrator = AsyncMock()
        ctx = _make_ctx(source_store=None, refresh_orchestrator=mock_orchestrator)

        with pytest.raises(ToolError):
            await refresh_source(ctx, source_id="any-id")
