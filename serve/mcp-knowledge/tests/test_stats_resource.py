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
        assert "knowledge://stats" in uris, f"Expected 'knowledge://stats' to be registered as a resource, got: {uris}"

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

    # ------------------------------------------------------------------
    # AC: registered knowledge_stats_resource handler queries the graph store
    # (not a hardcoded stub)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_stats_resource_handler_queries_graph_store(self) -> None:
        """knowledge_stats_resource() returns counts from graph_store, not hardcoded zeros."""
        from owlbear_mcp_knowledge.server import knowledge_stats_resource

        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=(7, 42, 99),
        ):
            result = await knowledge_stats_resource()

        assert isinstance(result, str)
        assert "7 documents" in result, (
            f"Expected '7 documents' in result but got: {result!r}. "
            "knowledge_stats_resource() must query the graph_store instead of "
            "returning hardcoded zeros."
        )
        assert "42 entities" in result
        assert "99 edges" in result


# ---------------------------------------------------------------------------
# Retry-cycle tests (added after reviewer FAIL: LAX mock, no compensating coverage)
# The existing tests above patch asyncio.to_thread entirely (new_callable=AsyncMock),
# which bypasses the hardcoded lambda: (0,0,0). These tests use side_effect to call
# the actual callable passed to asyncio.to_thread, so the bug is exposed.
# ---------------------------------------------------------------------------


class TestFromAC_StatsResourceNotHardcoded:
    """Non-LAX tests: verify the registered handler uses gs.get_counts, not a hardcoded lambda."""

    @pytest.mark.asyncio
    async def test_stats_resource_with_ctx_reflects_graph_store_counts(self) -> None:
        """knowledge_stats_resource must accept ctx and return counts from gs.get_counts.

        Uses real_to_thread side_effect so the hardcoded lambda: (0,0,0) is exposed.
        Fails currently because knowledge_stats_resource() takes 0 params — builder
        must add ctx: Context and use gs.get_counts.
        """
        from owlbear_mcp_knowledge.server import knowledge_stats_resource

        mock_gs = MagicMock()
        mock_gs.get_counts.return_value = (3, 17, 55)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = MagicMock(graph_store=mock_gs)

        async def real_to_thread(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
            return fn(*args, **kwargs)

        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", side_effect=real_to_thread):
            result = await knowledge_stats_resource(ctx)

        assert "3 documents" in result, (
            f"Expected '3 documents' (from graph_store.get_counts) but got: {result!r}. "
            "knowledge_stats_resource must call gs.get_counts, not return hardcoded zeros."
        )
        assert "17 entities" in result
        assert "55 edges" in result

    @pytest.mark.asyncio
    async def test_stats_resource_asyncio_to_thread_called_with_get_counts(
        self,
    ) -> None:
        """asyncio.to_thread must be invoked with gs.get_counts, not a hardcoded lambda.

        Captures what asyncio.to_thread was called with and asserts that the
        callable is gs.get_counts. Hardcoded lambda: (0,0,0) would fail this check.
        Fails currently because knowledge_stats_resource() takes 0 params.
        """
        from owlbear_mcp_knowledge.server import knowledge_stats_resource

        mock_gs = MagicMock()
        mock_gs.get_counts.return_value = (1, 2, 3)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = MagicMock(graph_store=mock_gs)

        captured: list[object] = []

        async def capture_to_thread(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
            captured.append(fn)
            return fn(*args, **kwargs)

        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread",
            side_effect=capture_to_thread,
        ):
            await knowledge_stats_resource(ctx)

        assert len(captured) == 1, "Expected asyncio.to_thread to be called exactly once."
        assert captured[0] is mock_gs.get_counts, (
            f"asyncio.to_thread was called with {captured[0]!r}, expected gs.get_counts. "
            "The resource handler must not use a hardcoded lambda."
        )


# ---------------------------------------------------------------------------
# Retry-cycle 4 tests (reviewer cycle 3 FAIL: _knowledge_stats_bridge coverage 0%)
# Previous cycles tested knowledge_stats_resource(ctx) — NOT the registered handler.
# _knowledge_stats_bridge() is the actual function FastMCP invokes for knowledge://stats.
# Lines 184-185 of server.py were NEVER executed by any test.
# These tests target _knowledge_stats_bridge() directly with real_to_thread so the
# hardcoded lambda: (0,0,0) bug is exposed, and the builder must fix it.
# ---------------------------------------------------------------------------


class TestFromAC_StatsResourceRegisteredBridge:
    """Tests that directly invoke _knowledge_stats_bridge — the registered MCP resource.

    AC: knowledge://stats resource returns 'Knowledge base: N documents, N entities, N edges'
    with N values from graph_store.get_counts (same format as get_stats tool).
    """

    @pytest.mark.asyncio
    async def test_bridge_reflects_graph_store_counts_not_hardcoded_zeros(self) -> None:
        """_knowledge_stats_bridge() must return counts from graph_store, not lambda: (0,0,0).

        Uses real_to_thread so the actual fn passed to asyncio.to_thread is executed.
        Also patches module-level _app_context (create=True) so the builder can read
        graph_store from it — this is the standard FastMCP pattern for zero-arg resources.

        FAILS currently: _knowledge_stats_bridge calls asyncio.to_thread(lambda: (0,0,0)).
        With real_to_thread, the lambda executes and returns (0,0,0) → '0 documents'.
        Builder must: (1) set module-level _app_context in app_lifespan,
                      (2) read _app_context.graph_store.get_counts in _knowledge_stats_bridge.
        """
        mock_gs = MagicMock()
        mock_gs.get_counts.return_value = (5, 10, 15)
        mock_app_ctx = MagicMock(graph_store=mock_gs)

        async def real_to_thread(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
            return fn(*args, **kwargs)

        with (
            patch(
                "owlbear_mcp_knowledge.server.asyncio.to_thread",
                side_effect=real_to_thread,
            ),
            patch.object(server_module, "_app_context", mock_app_ctx, create=True),
        ):
            result = await server_module._knowledge_stats_bridge()

        assert "5 documents" in result, (
            f"Expected '5 documents' from graph_store.get_counts but got: {result!r}. "
            "_knowledge_stats_bridge must read _app_context.graph_store.get_counts, "
            "not call lambda: (0,0,0). Lines 184-185 of server.py are unreachable via "
            "graph_store — builder must redesign _knowledge_stats_bridge."
        )
        assert "10 entities" in result
        assert "15 edges" in result

    @pytest.mark.asyncio
    async def test_bridge_asyncio_to_thread_callable_is_not_constant_lambda(
        self,
    ) -> None:
        """asyncio.to_thread in _knowledge_stats_bridge must receive gs.get_counts, not a lambda.

        Captures the fn argument passed to asyncio.to_thread, then calls it to check
        whether it returns the hardcoded tuple (0,0,0). A constant lambda is the bug;
        a bound mock method (gs.get_counts) returns non-zero test data.

        FAILS currently: _knowledge_stats_bridge passes lambda: (0,0,0) to asyncio.to_thread.
        captured_fn() == (0,0,0) → assertion fails.
        Builder must pass _app_context.graph_store.get_counts instead.
        """
        mock_gs = MagicMock()
        mock_gs.get_counts.return_value = (3, 6, 9)
        mock_app_ctx = MagicMock(graph_store=mock_gs)

        captured_fns: list[object] = []

        async def capturing_to_thread(fn, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            captured_fns.append(fn)
            return (3, 6, 9)

        with (
            patch(
                "owlbear_mcp_knowledge.server.asyncio.to_thread",
                side_effect=capturing_to_thread,
            ),
            patch.object(server_module, "_app_context", mock_app_ctx, create=True),
        ):
            await server_module._knowledge_stats_bridge()

        assert captured_fns, "_knowledge_stats_bridge did not call asyncio.to_thread"
        actual_fn = captured_fns[0]
        # Call the captured callable; if it's the hardcoded lambda it returns (0,0,0).
        # If it's mock_gs.get_counts it returns (3,6,9) — not the constant.
        try:
            call_result = actual_fn()
        except (TypeError, AttributeError):
            # fn is a bound method that raised — not a constant lambda; PASS.
            return
        assert call_result != (0, 0, 0), (
            f"asyncio.to_thread was called with a callable that returns {call_result!r}. "
            "This matches the hardcoded lambda: (0,0,0) bug in _knowledge_stats_bridge. "
            "Builder must pass _app_context.graph_store.get_counts to asyncio.to_thread."
        )
