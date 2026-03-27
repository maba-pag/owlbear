"""Failing tests for task #72: real search_knowledge MCP tool.

Covers (TDD RED phase — all tests must FAIL before builder implements #54):
  - AC2: valid query returns str containing query-relevant text
  - AC3: calls query_for_context via asyncio.to_thread (non-blocking)
  - AC4: limit param maps to top_k kwarg
  - AC5: None return from query_for_context gives 'No relevant knowledge found'
  - AC6: AppContext.query_service is None gives 'Knowledge service not available'

Tests mock AppContext and KnowledgeQueryService — no real DB or embeddings.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import target — will raise ImportError until builder implements #54 (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_knowledge.tools import search_knowledge  # type: ignore[import]


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_app_context(query_service: Any = None) -> MagicMock:
    """Return a minimal AppContext mock with a configurable query_service."""
    ctx = MagicMock()
    ctx.query_service = query_service
    return ctx


def _make_query_service(return_value: str | None = "Relevant knowledge:\n\n- doc: snippet") -> MagicMock:
    """Return a KnowledgeQueryService mock whose query_for_context returns return_value."""
    svc = MagicMock()
    svc.query_for_context.return_value = return_value
    return svc


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestFromAC_SearchKnowledge:
    """Contract tests for the search_knowledge MCP tool derived from AC."""

    # ------------------------------------------------------------------
    # AC2: valid query returns str containing query-relevant text
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_valid_query_returns_string(self) -> None:
        """search_knowledge returns a non-empty string for a valid query."""
        svc = _make_query_service("Relevant knowledge:\n\n- myDoc: useful snippet")
        ctx = _make_app_context(query_service=svc)

        with patch("owlbear_mcp_knowledge.tools.AppContext", return_value=ctx):
            result = await search_knowledge(ctx, query="myDoc")

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_valid_query_result_contains_service_text(self) -> None:
        """Return value incorporates the text returned by query_for_context."""
        formatted = "Relevant knowledge:\n\n- alpha: the alpha snippet"
        svc = _make_query_service(formatted)
        ctx = _make_app_context(query_service=svc)

        with patch("owlbear_mcp_knowledge.tools.AppContext", return_value=ctx):
            result = await search_knowledge(ctx, query="alpha")

        assert "alpha" in result

    # ------------------------------------------------------------------
    # AC3: query_for_context called via asyncio.to_thread
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_uses_asyncio_to_thread(self) -> None:
        """search_knowledge wraps query_for_context in asyncio.to_thread."""
        svc = _make_query_service("some result")
        ctx = _make_app_context(query_service=svc)

        with patch("owlbear_mcp_knowledge.tools.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock(return_value="some result")
            await search_knowledge(ctx, query="test")

        mock_asyncio.to_thread.assert_called_once()
        # First positional arg to to_thread must be query_for_context
        call_args = mock_asyncio.to_thread.call_args
        assert call_args[0][0] is svc.query_for_context

    @pytest.mark.asyncio
    async def test_does_not_call_query_for_context_directly_in_thread(self) -> None:
        """query_for_context is not called directly (bypassing asyncio.to_thread)."""
        svc = _make_query_service("result")
        ctx = _make_app_context(query_service=svc)

        with patch("owlbear_mcp_knowledge.tools.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock(return_value="result")
            await search_knowledge(ctx, query="q")

        # query_for_context must not have been called directly (only via to_thread)
        svc.query_for_context.assert_not_called()

    # ------------------------------------------------------------------
    # AC4: limit param maps to top_k kwarg on query_for_context
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_limit_maps_to_top_k_kwarg(self) -> None:
        """The limit parameter is passed to query_for_context as top_k kwarg."""
        svc = _make_query_service("result")
        ctx = _make_app_context(query_service=svc)

        with patch("owlbear_mcp_knowledge.tools.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock(return_value="result")
            await search_knowledge(ctx, query="q", limit=10)

        call_args = mock_asyncio.to_thread.call_args
        # top_k=10 must be present as keyword arg
        assert call_args[1].get("top_k") == 10 or (
            len(call_args[0]) > 1 and call_args[0][1] == 10  # positional fallback
        )

    @pytest.mark.asyncio
    async def test_limit_default_is_forwarded(self) -> None:
        """The default limit value is still forwarded as top_k."""
        svc = _make_query_service("result")
        ctx = _make_app_context(query_service=svc)

        with patch("owlbear_mcp_knowledge.tools.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock(return_value="result")
            await search_knowledge(ctx, query="q")

        call_args = mock_asyncio.to_thread.call_args
        # top_k must be present (some default value, not absent)
        top_k_present = "top_k" in call_args[1] if call_args[1] else False
        assert top_k_present

    @pytest.mark.asyncio
    async def test_different_limit_values_passed_as_top_k(self) -> None:
        """Boundary: limit=1 and limit=20 are both forwarded correctly."""
        for limit_val in (1, 20):
            svc = _make_query_service("result")
            ctx = _make_app_context(query_service=svc)

            with patch("owlbear_mcp_knowledge.tools.asyncio") as mock_asyncio:
                mock_asyncio.to_thread = AsyncMock(return_value="result")
                await search_knowledge(ctx, query="q", limit=limit_val)

            call_args = mock_asyncio.to_thread.call_args
            assert call_args[1].get("top_k") == limit_val

    # ------------------------------------------------------------------
    # AC5: None from query_for_context → 'No relevant knowledge found'
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_none_result_returns_no_knowledge_message(self) -> None:
        """When query_for_context returns None, a friendly message is returned."""
        svc = _make_query_service(return_value=None)
        ctx = _make_app_context(query_service=svc)

        with patch("owlbear_mcp_knowledge.tools.AppContext", return_value=ctx):
            result = await search_knowledge(ctx, query="anything")

        assert "No relevant knowledge found" in result

    @pytest.mark.asyncio
    async def test_none_result_message_is_string(self) -> None:
        """The 'not found' response is a str, not None or another type."""
        svc = _make_query_service(return_value=None)
        ctx = _make_app_context(query_service=svc)

        with patch("owlbear_mcp_knowledge.tools.AppContext", return_value=ctx):
            result = await search_knowledge(ctx, query="x")

        assert isinstance(result, str)

    # ------------------------------------------------------------------
    # AC6: query_service is None → 'Knowledge service not available'
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_missing_query_service_returns_unavailable_message(self) -> None:
        """When AppContext.query_service is None, an availability message is returned."""
        ctx = _make_app_context(query_service=None)

        with patch("owlbear_mcp_knowledge.tools.AppContext", return_value=ctx):
            result = await search_knowledge(ctx, query="anything")

        assert "Knowledge service not available" in result

    @pytest.mark.asyncio
    async def test_missing_query_service_does_not_call_to_thread(self) -> None:
        """When service is None, asyncio.to_thread is never called."""
        ctx = _make_app_context(query_service=None)

        with (
            patch("owlbear_mcp_knowledge.tools.AppContext", return_value=ctx),
            patch("owlbear_mcp_knowledge.tools.asyncio") as mock_asyncio,
        ):
            mock_asyncio.to_thread = AsyncMock()
            await search_knowledge(ctx, query="anything")

        mock_asyncio.to_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_query_service_result_is_string(self) -> None:
        """The 'not available' response is a str, not None or an exception."""
        ctx = _make_app_context(query_service=None)

        with patch("owlbear_mcp_knowledge.tools.AppContext", return_value=ctx):
            result = await search_knowledge(ctx, query="q")

        assert isinstance(result, str)
