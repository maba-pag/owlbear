"""Tests for list_sources tool in owlbear_mcp_knowledge.server.

TDD RED phase — list_sources does not yet exist in server.py; all tests fail
immediately with ImportError until the builder implements the tool.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import list_sources  # type: ignore[import]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(source_store: object = None) -> MagicMock:
    """Return a minimal FastMCP Context mock with source_store in lifespan_context."""
    ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.source_store = source_store
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_source(
    name: str = "my-source",
    source_type: str = "url_list",
    scope: str = "global",
) -> MagicMock:
    src = MagicMock()
    src.name = name
    src.source_type = source_type
    src.scope = scope
    return src


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestFromAC_ListSources:
    """Contract tests for list_sources MCP tool."""

    # ------------------------------------------------------------------
    # AC: returns formatted bullet list "- {name} ({source_type}): scope={scope}"
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_returns_formatted_bullet_list(self) -> None:
        """list_sources returns '- {name} ({source_type}): scope={scope}' bullet lines."""
        source = _make_source(name="src-one", source_type="url_list", scope="work")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert isinstance(result, str)
        assert "- src-one (url_list): scope=work" in result

    # ------------------------------------------------------------------
    # AC: scope filter passes scope to list_all(scope=scope)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_with_scope_filter_passes_scope_to_list_all(self) -> None:
        """list_sources(scope='work') calls store.list_all(scope='work')."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        await list_sources(ctx, scope="work")

        store.list_all.assert_called_once_with(scope="work")

    # ------------------------------------------------------------------
    # AC: without scope passes None to list_all
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_without_scope_passes_none_to_list_all(self) -> None:
        """list_sources() without scope calls store.list_all with scope=None."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        await list_sources(ctx)

        store.list_all.assert_called_once_with(scope=None)

    # ------------------------------------------------------------------
    # AC: empty result returns "No sources found."
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_returns_no_sources_found(self) -> None:
        """list_sources returns 'No sources found.' when list_all returns []."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result == "No sources found."

    # ------------------------------------------------------------------
    # AC: calls list_all via asyncio.to_thread (sync method)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_calls_list_all_via_asyncio_to_thread(self) -> None:
        """list_sources uses asyncio.to_thread because list_all is a sync method."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_thread:
            await list_sources(ctx)

        mock_thread.assert_awaited_once()
        # First positional arg should be the store.list_all callable
        first_arg = mock_thread.call_args[0][0]
        assert first_arg is store.list_all
