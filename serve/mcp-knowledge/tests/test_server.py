from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import app_lifespan, mcp


class TestFromAC_ServerLifespan:
    """Contract tests for the app_lifespan async context manager."""

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
        """The query_service stored in AppContext is the created service instance."""
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

    @pytest.mark.asyncio
    async def test_app_lifespan_closes_connection_on_clean_exit(self) -> None:
        """app_lifespan closes sqlite connection in the finally block."""
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
                pass

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_closes_connection_on_exception(self) -> None:
        """app_lifespan still closes connection when body raises."""
        mock_conn = MagicMock()

        async def _raise_inside_lifespan() -> None:
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                msg = "body error"
                raise RuntimeError(msg)

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            pytest.raises(RuntimeError, match="body error"),
        ):
            await _raise_inside_lifespan()

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_reads_owlbear_kb_path_env_var(self) -> None:
        """app_lifespan forwards OWLBEAR_KB_PATH to init_db."""
        mock_conn = MagicMock()
        expected_path = "/custom/kb/path/knowledge.db"

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn) as mock_init,
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch.dict("os.environ", {"OWLBEAR_KB_PATH": expected_path}),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass

        args, _ = mock_init.call_args
        assert expected_path in args

    @pytest.mark.asyncio
    async def test_app_lifespan_uses_default_path_when_env_var_absent(self) -> None:
        """app_lifespan still calls init_db with a default path when unset."""
        mock_conn = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn) as mock_init,
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch.dict("os.environ", {"OWLBEAR_LLM_API_KEY": "test-key"}, clear=True),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server):
                pass

        mock_init.assert_called_once()
        args, _ = mock_init.call_args
        assert len(args) >= 1
        assert isinstance(args[0], str)


class TestFromAC_AppContextSourceStore:
    """Contract tests for AppContext.source_store field."""

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
        """app_lifespan passes db connection to KnowledgeSourceStore."""
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

    def test_search_knowledge_registered_as_tool(self) -> None:
        """The FastMCP instance exposes search_knowledge as a registered tool."""
        if hasattr(mcp, "_tool_manager"):
            tools = list(mcp._tool_manager.list_tools())  # noqa: SLF001
        else:
            tools = mcp.list_tools()  # type: ignore[call-arg]
        assert any(getattr(t, "name", str(t)) == "search_knowledge" for t in tools), (
            f"Expected 'search_knowledge' in tools, got: {tools}"
        )

    def test_main_module_importable(self) -> None:
        """owlbear_mcp_knowledge.__main__ can be imported without errors."""
        importlib.import_module("owlbear_mcp_knowledge.__main__")
