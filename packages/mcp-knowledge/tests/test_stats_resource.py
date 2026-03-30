"""Tests for knowledge://stats resource in owlbear_mcp_knowledge.server.

TDD RED phase — the knowledge://stats resource does not yet exist in server.py;
all tests fail until the builder adds the resource registration.
"""

from __future__ import annotations

import owlbear_mcp_knowledge.server as server_module
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import mcp


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeStatsResource:
    """Contract tests for the knowledge://stats MCP resource."""

    # ------------------------------------------------------------------
    # AC: knowledge://stats resource is registered on the mcp instance
    # ------------------------------------------------------------------

    def test_stats_resource_registered_on_mcp(self) -> None:
        """knowledge://stats resource is registered on the FastMCP instance."""
        resource_manager = getattr(mcp, "_resource_manager", None)
        if resource_manager is None:
            pytest.fail(
                "mcp has no _resource_manager; cannot verify resource registration. "
                "Builder must register @mcp.resource('knowledge://stats')."
            )

        resources = list(resource_manager.list_resources())
        uris = {str(getattr(r, "uri", r)) for r in resources}
        assert "knowledge://stats" in uris, (
            f"Expected 'knowledge://stats' to be registered as a resource, got: {uris}"
        )

    # ------------------------------------------------------------------
    # AC: resource returns "Knowledge base: N documents, N entities, N edges"
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_stats_resource_returns_knowledge_base_format(self) -> None:
        """knowledge://stats handler returns 'Knowledge base: N documents, N entities, N edges'."""
        # The builder will register a function with @mcp.resource("knowledge://stats").
        # Common naming conventions are checked in order.
        handler = getattr(server_module, "knowledge_stats", None) or getattr(
            server_module, "knowledge_stats_resource", None
        )
        assert handler is not None, (
            "No stats resource handler found in server module. "
            "Expected a function named 'knowledge_stats' or 'knowledge_stats_resource' "
            "decorated with @mcp.resource('knowledge://stats')."
        )

        mock_gs = MagicMock()
        ctx = MagicMock()
        ctx.request_context.lifespan_context = MagicMock(graph_store=mock_gs)

        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=(5, 10, 15),
        ):
            result = await handler(ctx)

        assert isinstance(result, str)
        assert "Knowledge base:" in result
        assert "5 documents" in result
        assert "10 entities" in result
        assert "15 edges" in result
