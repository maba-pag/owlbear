"""RED-phase tests for task #739: update_bookmark_tags MCP tool in mcp-knowledge.

Tests the contract for:
- New `update_bookmark_tags` async MCP tool registered on `mcp` in server.py
- Tool signature: url: str, tags: list[str], scope: str = "global"
- Resolves bookmark via BookmarkStore.get_by_url(url, scope)
- Raises ToolError when bookmark_store is None or URL not found
- Calls BookmarkStore.update_tags(bookmark.id, tags) via asyncio.to_thread
- Returns BookmarkInfo dict (url, title, relevance_score, tags) with updated tags
- `update_bookmark_tags` present in server.py __all__
- Tool annotations: readOnlyHint=False, destructiveHint=False, idempotentHint=True

Pattern: mock AppContext per TestFromAC_MCPBookmarkTools in test_bookmark_pipeline_136.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bookmark(
    *,
    bookmark_id: str = "bm-001",
    url: str = "https://example.com",
    title: str = "Example",
    relevance_score: float = 0.8,
    tags: list[str] | None = None,
) -> MagicMock:
    """Return a MagicMock with Bookmark-like attributes."""
    bm = MagicMock()
    bm.id = bookmark_id
    bm.url = url
    bm.title = title
    bm.relevance_score = relevance_score
    bm.tags = tags if tags is not None else ["existing-tag"]
    return bm


def _make_ctx(*, bookmark_store: object = None) -> MagicMock:
    """Return a MagicMock FastMCP Context with the given bookmark_store."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = MagicMock(
        bookmark_store=bookmark_store,
    )
    return ctx


# ===========================================================================
# AC: update_bookmark_tags tool registered and in __all__
# ===========================================================================


class TestFromAC_UpdateBookmarkTagsRegistration:  # noqa: N801
    """update_bookmark_tags is registered on the mcp server and exported in __all__."""

    def test_update_bookmark_tags_function_registered(self) -> None:
        from owlbear_mcp_knowledge import server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "update_bookmark_tags"), (
            "update_bookmark_tags tool missing from server.py — must be defined and decorated with @mcp.tool()"
        )

    def test_update_bookmark_tags_in_all(self) -> None:
        from owlbear_mcp_knowledge import server as server_mod  # noqa: PLC0415

        assert "update_bookmark_tags" in server_mod.__all__, "update_bookmark_tags missing from server.py __all__"

    def test_update_bookmark_tags_is_callable(self) -> None:
        from owlbear_mcp_knowledge import server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "update_bookmark_tags", None)
        assert callable(fn), "update_bookmark_tags must be callable"


# ===========================================================================
# AC: Tool annotations — readOnlyHint=False, destructiveHint=False, idempotentHint=True
# ===========================================================================


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named mcp-knowledge tool, or None."""
    from owlbear_mcp_knowledge.server import mcp  # noqa: PLC0415

    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


class TestFromAC_UpdateBookmarkTagsAnnotations:  # noqa: N801
    """update_bookmark_tags has correct ToolAnnotations — write, idempotent, non-destructive."""

    def test_not_read_only(self) -> None:
        ann = _get_tool_annotations("update_bookmark_tags")
        assert ann is not None, (
            "update_bookmark_tags has no ToolAnnotations; "
            "add annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)"
        )
        assert ann.readOnlyHint is False, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=False, got: {ann.readOnlyHint!r}"
        )

    def test_not_destructive(self) -> None:
        ann = _get_tool_annotations("update_bookmark_tags")
        assert ann is not None, "update_bookmark_tags has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False, got: {ann.destructiveHint!r}"
        )

    def test_idempotent_hint_true(self) -> None:
        ann = _get_tool_annotations("update_bookmark_tags")
        assert ann is not None, "update_bookmark_tags has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True, got: {ann.idempotentHint!r}"
        )


# ===========================================================================
# AC: Happy path — resolves bookmark, updates tags, returns BookmarkInfo
# ===========================================================================


class TestFromAC_UpdateBookmarkTagsHappyPath:  # noqa: N801
    """Happy path contract: get_by_url called, update_tags called, BookmarkInfo returned."""

    @pytest.mark.asyncio
    async def test_calls_get_by_url_with_url_and_scope(self) -> None:
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark()
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            await update_bookmark_tags(ctx, url="https://example.com", tags=["new"], scope="global")

        store.get_by_url.assert_called_once_with("https://example.com", "global")

    @pytest.mark.asyncio
    async def test_calls_update_tags_with_bookmark_id_and_new_tags(self) -> None:
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark(bookmark_id="bm-abc", tags=["old"])
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            await update_bookmark_tags(ctx, url="https://example.com", tags=["new-tag", "another"])

        store.update_tags.assert_called_once_with("bm-abc", ["new-tag", "another"])

    @pytest.mark.asyncio
    async def test_returns_bookmark_info_dict_with_url(self) -> None:
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark(url="https://example.com", title="My Page", relevance_score=0.9)
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            result = await update_bookmark_tags(ctx, url="https://example.com", tags=["python"])

        assert isinstance(result, dict)
        assert result["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_returned_tags_reflect_new_tags_not_old(self) -> None:
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark(tags=["old-tag"])
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            result = await update_bookmark_tags(ctx, url="https://example.com", tags=["fresh"])

        assert result["tags"] == ["fresh"], (
            f"Returned tags should be the NEW tags ['fresh'], not old ['old-tag']; got: {result['tags']!r}"
        )

    @pytest.mark.asyncio
    async def test_returns_title_and_relevance_score_from_bookmark(self) -> None:
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark(title="Test Title", relevance_score=0.75)
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            result = await update_bookmark_tags(ctx, url="https://example.com", tags=["t"])

        assert result["title"] == "Test Title"
        assert result["relevance_score"] == 0.75

    @pytest.mark.asyncio
    async def test_default_scope_is_global(self) -> None:
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark()
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            # Call WITHOUT scope parameter — default should be "global"
            await update_bookmark_tags(ctx, url="https://example.com", tags=["x"])

        store.get_by_url.assert_called_once_with("https://example.com", "global")


# ===========================================================================
# AC: Edge cases — empty tags, custom scope
# ===========================================================================


class TestFromAC_UpdateBookmarkTagsEdgeCases:  # noqa: N801
    """Edge cases: empty tag list clears tags; custom scope forwarded correctly."""

    @pytest.mark.asyncio
    async def test_empty_tags_list_accepted(self) -> None:
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark(tags=["existing"])
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            result = await update_bookmark_tags(ctx, url="https://example.com", tags=[])

        store.update_tags.assert_called_once_with(bookmark.id, [])
        assert result["tags"] == []

    @pytest.mark.asyncio
    async def test_custom_scope_passed_to_get_by_url(self) -> None:
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark()
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            await update_bookmark_tags(ctx, url="https://work.example.com", tags=["work"], scope="project:myapp")

        store.get_by_url.assert_called_once_with("https://work.example.com", "project:myapp")


# ===========================================================================
# AC: Error paths — ToolError on None store, ToolError on URL not found
# ===========================================================================


class TestFromAC_UpdateBookmarkTagsErrorPaths:  # noqa: N801
    """Error contract: ToolError raised when store is None or URL not found."""

    @pytest.mark.asyncio
    async def test_raises_tool_error_when_bookmark_store_none(self) -> None:
        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        ctx = _make_ctx(bookmark_store=None)

        with pytest.raises(ToolError):
            await update_bookmark_tags(ctx, url="https://example.com", tags=["x"])

    @pytest.mark.asyncio
    async def test_raises_tool_error_when_url_not_found(self) -> None:
        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url = MagicMock(return_value=None)
        ctx = _make_ctx(bookmark_store=store)

        with (
            patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))),
            pytest.raises(ToolError),
        ):
            await update_bookmark_tags(ctx, url="https://notfound.example.com", tags=["x"])

    @pytest.mark.asyncio
    async def test_update_tags_not_called_when_url_not_found(self) -> None:
        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url = MagicMock(return_value=None)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with (
            patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))),
            pytest.raises(ToolError),
        ):
            await update_bookmark_tags(ctx, url="https://notfound.example.com", tags=["x"])

        store.update_tags.assert_not_called()


# ===========================================================================
# AC: Boundary — no second DB read; update_tags offloaded via asyncio.to_thread
# ===========================================================================


class TestFromAC_UpdateBookmarkTagsBoundary:  # noqa: N801
    """Boundary: return dict built from fetched bookmark + new tags; no second DB read."""

    @pytest.mark.asyncio
    async def test_get_by_url_called_exactly_once(self) -> None:
        """AC: construct return from fetched bookmark + new tags — no second DB read."""
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark()
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            await update_bookmark_tags(ctx, url="https://example.com", tags=["a", "b"])

        assert store.get_by_url.call_count == 1, (
            f"get_by_url must be called exactly once (no second DB read); called {store.get_by_url.call_count} times"
        )

    @pytest.mark.asyncio
    async def test_result_has_all_bookmark_info_keys(self) -> None:
        """Return type must be a BookmarkInfo dict with url, title, relevance_score, tags."""
        from owlbear_mcp_knowledge.server import update_bookmark_tags  # noqa: PLC0415

        store = MagicMock()
        bookmark = _make_bookmark()
        store.get_by_url = MagicMock(return_value=bookmark)
        store.update_tags = MagicMock()
        ctx = _make_ctx(bookmark_store=store)

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            result = await update_bookmark_tags(ctx, url="https://example.com", tags=["z"])

        assert "url" in result
        assert "title" in result
        assert "relevance_score" in result
        assert "tags" in result
