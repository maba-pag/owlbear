"""Tests for search_knowledge v2 API in owlbear_mcp_knowledge.server.

These tests target the v2 behavior where KnowledgeQueryService.query() (async)
is called directly instead of asyncio.to_thread(query_for_context, ...).

TDD RED phase — all tests must fail before builder updates search_knowledge in server.py.

Note: AC item 'returns Knowledge service not available when query_service is None' is
omitted — it tests unchanged behavior already present in current server.py; including
it would produce a GREEN test in the RED phase (violating TDD RED precondition).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.query_service import StructuredSearchResult
from owlbear_mcp_knowledge.server import search_knowledge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(query_service: object = None) -> MagicMock:
    """Return a minimal FastMCP Context mock whose lifespan_context has query_service."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = MagicMock(query_service=query_service)
    return ctx


def _make_result(
    title: str = "doc",
    score: float = 0.85,
    snippet: str = "snippet text",
) -> StructuredSearchResult:
    return StructuredSearchResult(
        doc_id="d1",
        title=title,
        score=score,
        snippet=snippet,
        entity_type="concept",
        scope="global",
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestFromAC_SearchKnowledgeV2:
    """Contract tests for search_knowledge v2 API (KnowledgeQueryService.query())."""

    # ------------------------------------------------------------------
    # AC: returns formatted bullet list for valid query
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_returns_bullet_list_for_valid_query(self) -> None:
        """search_knowledge returns bullet lines from list[StructuredSearchResult]."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[_make_result(title="Alpha", score=0.9, snippet="alpha content")]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="alpha")

        assert isinstance(result, str)
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert any(ln.startswith("- ") for ln in lines)

    # ------------------------------------------------------------------
    # AC: each bullet follows "- {title} ({score:.2f}): {snippet[:200]}" format
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_bullet_format_title_score_snippet(self) -> None:
        """Each bullet line matches '- {title} ({score:.2f}): {snippet[:200]}'."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[_make_result(title="MyDoc", score=0.75, snippet="relevant text")]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, str)
        assert "- MyDoc (0.75): relevant text" in result

    @pytest.mark.asyncio
    async def test_snippet_truncated_to_200_chars(self) -> None:
        """Snippet in bullet output is truncated to at most 200 characters."""
        long_snippet = "A" * 300
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[_make_result(title="LongDoc", score=0.8, snippet=long_snippet)]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, str)
        assert "A" * 300 not in result
        assert "A" * 200 in result

    # ------------------------------------------------------------------
    # AC: multiple results produce multiple bullet lines (edge case)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_multiple_results_produce_multiple_lines(self) -> None:
        """Each StructuredSearchResult maps to exactly one bullet line."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[
                _make_result(title="Doc1", score=0.9, snippet="snippet1"),
                _make_result(title="Doc2", score=0.7, snippet="snippet2"),
            ]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="multi")

        assert isinstance(result, str)
        bullet_lines = [ln for ln in result.splitlines() if ln.startswith("- ")]
        assert len(bullet_lines) == 2

    # ------------------------------------------------------------------
    # AC: returns "No relevant knowledge found." when query() returns []
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_results_returns_no_relevant_knowledge(self) -> None:
        """Returns 'No relevant knowledge found.' when query() returns empty list."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result == "No relevant knowledge found."

    # ------------------------------------------------------------------
    # AC: awaits query() directly (not via asyncio.to_thread)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_query_method_awaited_directly(self) -> None:
        """search_knowledge awaits qs.query() directly (observed via AsyncMock)."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(qs)

        await search_knowledge(ctx, query="direct")

        qs.query.assert_awaited_once()

    # ------------------------------------------------------------------
    # AC: limit param maps to top_k kwarg on query()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_limit_forwarded_as_top_k_to_query(self) -> None:
        """limit argument is forwarded to qs.query() as top_k kwarg."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(qs)

        await search_knowledge(ctx, query="bounded", limit=7)

        qs.query.assert_awaited_once_with("bounded", top_k=7)

    # ------------------------------------------------------------------
    # AC: returns "Knowledge service not available." when query_service is None
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_qs_is_none_returns_service_unavailable(self) -> None:
        """search_knowledge returns 'Knowledge service not available.' when query_service is None."""
        ctx = _make_ctx(query_service=None)

        result = await search_knowledge(ctx, query="anything")

        assert result == "Knowledge service not available."
