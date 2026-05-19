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
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.query_service import KnowledgeQueryError, StructuredSearchResult
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
    graph_context: str = "",
) -> StructuredSearchResult:
    return StructuredSearchResult(
        doc_id="d1",
        title=title,
        score=score,
        snippet=snippet,
        entity_type="concept",
        scope="global",
        graph_context=graph_context,
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
        """search_knowledge returns a list of result dicts when results are found."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(title="Alpha", score=0.9, snippet="alpha content")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="alpha")

        assert isinstance(result, list)
        assert len(result) >= 1

    # ------------------------------------------------------------------
    # AC: each bullet follows "- {title} ({score:.2f}): {snippet[:200]}" format
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_bullet_format_title_score_snippet(self) -> None:
        """Result dict contains title, score, and snippet fields with correct values."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(title="MyDoc", score=0.75, snippet="relevant text")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, list)
        assert result[0]["title"] == "MyDoc"
        assert result[0]["score"] == pytest.approx(0.75)
        assert result[0]["snippet"] == "relevant text"

    @pytest.mark.asyncio
    async def test_snippet_full_not_truncated(self) -> None:
        """Full snippet is returned in the dict (no truncation in structured output)."""
        long_snippet = "A" * 300
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(title="LongDoc", score=0.8, snippet=long_snippet)])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, list)
        assert result[0]["snippet"] == long_snippet

    # ------------------------------------------------------------------
    # AC: multiple results produce multiple bullet lines (edge case)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_multiple_results_produce_multiple_lines(self) -> None:
        """Each StructuredSearchResult maps to exactly one dict in the returned list."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[
                _make_result(title="Doc1", score=0.9, snippet="snippet1"),
                _make_result(title="Doc2", score=0.7, snippet="snippet2"),
            ]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="multi")

        assert isinstance(result, list)
        assert len(result) == 2

    # ------------------------------------------------------------------
    # AC: returns "No relevant knowledge found." when query() returns []
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self) -> None:
        """Returns [] when query() returns empty list."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result == []

    @pytest.mark.asyncio
    async def test_query_failure_returns_error_string(self) -> None:
        """search_knowledge returns an error string when query infrastructure fails."""
        qs = AsyncMock()
        qs.query = AsyncMock(side_effect=KnowledgeQueryError("knowledge query failed"))
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result == "error: knowledge query failed"

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

        qs.query.assert_awaited_once_with("bounded", top_k=7, scopes=None)

    @pytest.mark.asyncio
    async def test_scopes_normalized_before_query(self) -> None:
        """Scope filters are stripped and null-like entries are dropped before query execution."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(qs)

        await search_knowledge(ctx, query="scoped", scopes=[" global ", "", "null", "project"])

        qs.query.assert_awaited_once_with("scoped", top_k=5, scopes=["global", "project"])

    @pytest.mark.asyncio
    async def test_empty_scopes_normalize_to_no_scope_filter(self) -> None:
        """Blank/null-like scope lists behave like no scope filter."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(qs)

        await search_knowledge(ctx, query="scoped", scopes=["", "none"])

        qs.query.assert_awaited_once_with("scoped", top_k=5, scopes=None)

    @pytest.mark.asyncio
    async def test_invalid_limit_rejected_before_query(self) -> None:
        """Invalid limits should fail at the MCP boundary before query execution."""
        for limit in (0, -1, True):
            qs = AsyncMock()
            qs.query = AsyncMock(return_value=[])
            ctx = _make_ctx(qs)

            with pytest.raises(ToolError):
                await search_knowledge(ctx, query="bounded", limit=limit)

            qs.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_scopes_rejected_before_query(self) -> None:
        """Invalid scope shapes should fail at the MCP boundary before query execution."""
        for scopes in ("global", [None], [True]):
            qs = AsyncMock()
            qs.query = AsyncMock(return_value=[])
            ctx = _make_ctx(qs)

            with pytest.raises(ToolError):
                await search_knowledge(ctx, query="scoped", scopes=scopes)  # type: ignore[arg-type]

            qs.query.assert_not_called()

    # ------------------------------------------------------------------
    # AC: returns "Knowledge service not available." when query_service is None
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_qs_is_none_returns_service_unavailable(self) -> None:
        """search_knowledge returns 'Knowledge service not available.' when query_service is None."""
        ctx = _make_ctx(query_service=None)

        result = await search_knowledge(ctx, query="anything")

        assert result == "error: Knowledge service not available."


# ---------------------------------------------------------------------------
# TestFromAC_SearchKnowledgeStructuredReturn (#507)
# ---------------------------------------------------------------------------


class TestFromAC_SearchKnowledgeStructuredReturn:
    """Contract tests: search_knowledge returns list[dict] on success, [] on empty."""

    # ------------------------------------------------------------------
    # AC: success returns list not str
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_success_returns_list(self) -> None:
        """search_knowledge returns a list (not str) when results are found."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="hello")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_success_result_items_are_dicts(self) -> None:
        """Each item in the returned list is a dict."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(), _make_result(title="b")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="q")

        assert all(isinstance(item, dict) for item in result)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_each_dict_has_title_score_snippet_keys(self) -> None:
        """Each result dict contains 'title', 'score', and 'snippet' keys."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(title="T", score=0.9, snippet="S")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="keys")

        item = result[0]  # type: ignore[index]
        assert "title" in item
        assert "score" in item
        assert "snippet" in item

    @pytest.mark.asyncio
    async def test_title_value_is_str(self) -> None:
        """title field in the returned dict is a str."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(title="MyTitle")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="t")

        assert isinstance(result[0]["title"], str)  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_score_value_is_float(self) -> None:
        """score field in the returned dict is a float."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(score=0.77)])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="s")

        assert isinstance(result[0]["score"], float)  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_snippet_value_is_str(self) -> None:
        """snippet field in the returned dict is a str."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(snippet="abc")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="sn")

        assert isinstance(result[0]["snippet"], str)  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_graph_context_serialized_from_structured_result(self) -> None:
        """graph_context field carries graph expansion text through MCP serialization."""
        graph_context = "Alpha --[depends_on]--> Beta: neighbor detail"
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(graph_context=graph_context)])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="graph")

        assert result[0]["graph_context"] == graph_context  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_dict_values_match_source_result_fields(self) -> None:
        """title, score, snippet values come from the StructuredSearchResult fields."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_result(title="Alpha", score=0.95, snippet="alpha snip")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="values")

        item = result[0]  # type: ignore[index]
        assert item["title"] == "Alpha"
        assert item["score"] == pytest.approx(0.95)
        assert item["snippet"] == "alpha snip"

    @pytest.mark.asyncio
    async def test_multiple_results_list_length_matches(self) -> None:
        """List length equals the number of results returned by query()."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[
                _make_result(title="D1"),
                _make_result(title="D2"),
                _make_result(title="D3"),
            ]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="multi")

        assert len(result) == 3  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # AC: empty results return [] not a string message
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self) -> None:
        """search_knowledge returns [] (not a string) when query() yields no results."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="empty")

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_result_is_list_not_str(self) -> None:
        """Empty result is a list type, confirming no string sentinel is returned."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="empty")

        assert isinstance(result, list)
