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
        """list_sources returns a list of dicts with name, source_type, and scope."""
        source = _make_source(name="src-one", source_type="url_list", scope="work")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert isinstance(result, list)
        assert result[0]["name"] == "src-one"
        assert result[0]["source_type"] == "url_list"
        assert result[0]["scope"] == "work"

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
    async def test_empty_returns_empty_list(self) -> None:
        """list_sources returns [] when list_all returns []."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result == []

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


# ---------------------------------------------------------------------------
# TestFromAC_ListSourcesStructuredReturn (#507)
# ---------------------------------------------------------------------------


class TestFromAC_ListSourcesStructuredReturn:
    """Contract tests: list_sources returns list[dict] on success, [] on empty."""

    # ------------------------------------------------------------------
    # AC: success returns list not str
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_success_returns_list(self) -> None:
        """list_sources returns a list (not str) when sources exist."""
        source = _make_source(name="s1", source_type="url_list", scope="global")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_success_result_items_are_dicts(self) -> None:
        """Each item in the returned list is a dict."""
        store = MagicMock()
        store.list_all.return_value = [_make_source(), _make_source(name="s2")]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert all(isinstance(item, dict) for item in result)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_each_dict_has_name_source_type_scope_keys(self) -> None:
        """Each dict in the returned list has 'name', 'source_type', and 'scope' keys."""
        store = MagicMock()
        store.list_all.return_value = [_make_source(name="n", source_type="url_list", scope="work")]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        item = result[0]  # type: ignore[index]
        assert "name" in item
        assert "source_type" in item
        assert "scope" in item

    @pytest.mark.asyncio
    async def test_dict_values_match_source_fields(self) -> None:
        """name, source_type, scope values come from the source object fields."""
        store = MagicMock()
        store.list_all.return_value = [_make_source(name="my-src", source_type="file_glob", scope="work")]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        item = result[0]  # type: ignore[index]
        assert item["name"] == "my-src"
        assert item["source_type"] == "file_glob"
        assert item["scope"] == "work"

    @pytest.mark.asyncio
    async def test_all_fields_are_str(self) -> None:
        """name, source_type, and scope are all str values."""
        store = MagicMock()
        store.list_all.return_value = [_make_source()]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        item = result[0]  # type: ignore[index]
        assert isinstance(item["name"], str)
        assert isinstance(item["source_type"], str)
        assert isinstance(item["scope"], str)

    @pytest.mark.asyncio
    async def test_multiple_sources_list_length_matches(self) -> None:
        """List length equals the number of sources returned by list_all."""
        store = MagicMock()
        store.list_all.return_value = [
            _make_source(name="a"),
            _make_source(name="b"),
            _make_source(name="c"),
        ]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert len(result) == 3  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # AC: empty results return [] not a string message
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self) -> None:
        """list_sources returns [] (not 'No sources found.') when list_all returns []."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_result_is_list_not_str(self) -> None:
        """Empty result is a list type, confirming no string sentinel is returned."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert isinstance(result, list)
