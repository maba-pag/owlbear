"""Failing tests for task #104: FastMCP server wiring and lifespan in mcp-knowledge.

Covers (TDD RED phase — all tests must FAIL before builder implements #54 / server.py):
  - AC2: app_lifespan yields AppContext with non-None query_service
  - AC3: app_lifespan closes sqlite3 connection in finally block
  - AC4: app_lifespan reads OWLBEAR_KB_PATH env var for DB path
  - AC5: search_knowledge is registered as a tool on the FastMCP instance
  - AC6: __main__ module is importable

Tests mock all owlbear_knowledge imports — no real DB, Qdrant, or embeddings.
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import target — will raise ImportError until builder creates server.py (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_knowledge.server import app_lifespan, mcp  # type: ignore[import]


@pytest.fixture(autouse=True)
def _bypass_copilot_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a fake LLM API key so app_lifespan skips the Copilot device-auth flow."""
    monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "test-key")


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestFromAC_ServerLifespan:
    """Contract tests for the app_lifespan async context manager derived from AC."""

    # ------------------------------------------------------------------
    # AC2: app_lifespan yields AppContext with non-None query_service
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_app_lifespan_yields_app_context_with_query_service(self) -> None:
        """app_lifespan yields an AppContext whose query_service is not None."""
        mock_conn = MagicMock()
        mock_qs = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch(
                "owlbear_mcp_knowledge.server.KnowledgeQueryService",
                return_value=mock_qs,
            ),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server) as ctx:
                assert ctx is not None
                assert ctx.query_service is not None

    @pytest.mark.asyncio
    async def test_app_lifespan_query_service_is_knowledge_query_service(self) -> None:
        """The query_service stored in AppContext is the KnowledgeQueryService instance."""
        mock_conn = MagicMock()
        mock_qs = MagicMock(name="KnowledgeQueryServiceInstance")

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch(
                "owlbear_mcp_knowledge.server.KnowledgeQueryService",
                return_value=mock_qs,
            ),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server) as ctx:
                assert ctx.query_service is mock_qs

    # ------------------------------------------------------------------
    # AC3: app_lifespan closes sqlite3 connection in finally block
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_app_lifespan_closes_connection_on_clean_exit(self) -> None:
        """app_lifespan calls conn.close() in the finally block on clean exit."""
        mock_conn = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass  # exit normally

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_closes_connection_on_exception(self) -> None:
        """app_lifespan calls conn.close() in finally even when the body raises."""
        mock_conn = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        ):
            fake_server = MagicMock()

            async def _raise() -> None:
                msg = "body error"
                raise RuntimeError(msg)

            try:
                async with app_lifespan(fake_server):
                    await _raise()
            except RuntimeError:
                pass

            mock_conn.close.assert_called_once()

    # ------------------------------------------------------------------
    # AC4: app_lifespan reads OWLBEAR_KB_PATH env var for DB path
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_app_lifespan_reads_owlbear_kb_path_env_var(self) -> None:
        """app_lifespan passes the OWLBEAR_KB_PATH value to init_db."""
        mock_conn = MagicMock()
        expected_path = "/custom/kb/path/knowledge.db"

        with (
            patch(
                "owlbear_mcp_knowledge.server.init_db", return_value=mock_conn
            ) as mock_init,
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch.dict("os.environ", {"OWLBEAR_KB_PATH": expected_path}),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass

        # init_db must have been called with the env var value
        args, _ = mock_init.call_args
        assert expected_path in args

    @pytest.mark.asyncio
    async def test_app_lifespan_uses_default_path_when_env_var_absent(self) -> None:
        """app_lifespan calls init_db with some path even when OWLBEAR_KB_PATH is not set."""
        mock_conn = MagicMock()

        with (
            patch(
                "owlbear_mcp_knowledge.server.init_db", return_value=mock_conn
            ) as mock_init,
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch.dict("os.environ", {"OWLBEAR_LLM_API_KEY": "test-key"}, clear=True),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass

        # init_db must be called with exactly one positional arg (the path)
        mock_init.assert_called_once()
        args, _ = mock_init.call_args
        assert len(args) >= 1
        assert isinstance(args[0], str)


class TestFromAC_AppContextSourceStore:
    """Contract tests for AppContext.source_store field (AC: AppContext dataclass, #16)."""

    @pytest.mark.asyncio
    async def test_app_lifespan_yields_app_context_with_source_store(self) -> None:
        """app_lifespan yields an AppContext whose source_store is not None."""
        mock_conn = MagicMock()
        mock_source_store = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch(
                "owlbear_mcp_knowledge.server.KnowledgeSourceStore",
                return_value=mock_source_store,
            ),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server) as ctx:
                assert ctx.source_store is mock_source_store

    @pytest.mark.asyncio
    async def test_app_lifespan_constructs_source_store_with_conn(self) -> None:
        """app_lifespan passes the db connection to KnowledgeSourceStore."""
        mock_conn = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.KnowledgeSourceStore") as mock_kss_cls,
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass

        mock_kss_cls.assert_called_once_with(mock_conn)


class TestFromAC_ServerWiring:
    """Contract tests for FastMCP server registration and module structure."""

    # ------------------------------------------------------------------
    # AC5: search_knowledge is registered as a tool on the FastMCP instance
    # ------------------------------------------------------------------

    def test_search_knowledge_registered_as_tool(self) -> None:
        """The FastMCP instance 'mcp' exposes search_knowledge as a registered tool."""
        # Try _tool_manager first (FastMCP v1 internal); fall back to list_tools if needed
        if hasattr(mcp, "_tool_manager"):
            tool_names = list(mcp._tool_manager.list_tools())  # noqa: SLF001
            assert any(
                getattr(t, "name", t) == "search_knowledge" for t in tool_names
            ), f"Expected 'search_knowledge' in tools, got: {tool_names}"
        else:
            # FastMCP v2 / alternate API
            tools = mcp.list_tools()  # type: ignore[call-arg]
            assert any(
                getattr(t, "name", str(t)) == "search_knowledge" for t in tools
            ), f"Expected 'search_knowledge' in tools, got: {tools}"

    # ------------------------------------------------------------------
    # AC6: __main__ module is importable
    # ------------------------------------------------------------------

    def test_main_module_importable(self) -> None:
        """owlbear_mcp_knowledge.__main__ can be imported without errors."""
        importlib.import_module("owlbear_mcp_knowledge.__main__")
