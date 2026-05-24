from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_knowledge.server import AppContext, app_lifespan, mcp, remove_source


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


# From task #1652: remove_source vectors-first abort and audit-log coverage.


def _make_source(source_id: str = "src-1", name: str = "Test Source") -> MagicMock:
    """Return a mock KnowledgeSource with id and name."""
    src = MagicMock()
    src.id = source_id
    src.name = name
    return src


def _make_conn(
    chunk_ids: list[str] | None = None,
    entity_ids: list[str] | None = None,
    doc_count: int = 2,
    chunk_count: int = 3,
    entity_count: int = 5,
) -> MagicMock:
    """Return a mock SQLite connection for remove_source count and join queries."""
    if chunk_ids is None:
        chunk_ids = ["chunk-1", "chunk-2", "chunk-3"]
    if entity_ids is None:
        entity_ids = []

    conn = MagicMock()

    def _execute(sql: str, params: object = ()) -> MagicMock:  # noqa: ARG001
        cursor = MagicMock()
        sql_lower = sql.lower()
        if "count" in sql_lower:
            if "entit" in sql_lower:
                cursor.fetchone.return_value = (entity_count,)
            elif "chunk" in sql_lower:
                cursor.fetchone.return_value = (chunk_count,)
            else:
                cursor.fetchone.return_value = (doc_count,)
        elif "from entities" in sql_lower:
            cursor.fetchall.return_value = [(entity_id,) for entity_id in entity_ids]
        else:
            cursor.fetchall.return_value = [(chunk_id,) for chunk_id in chunk_ids]
        return cursor

    conn.execute.side_effect = _execute
    return conn


def _make_ctx(
    *,
    source: MagicMock | None = None,
    vector_store: MagicMock | None = None,
    conn: MagicMock | None = None,
) -> MagicMock:
    """Return a FastMCP Context mock with remove_source lifespan fields."""
    store = MagicMock()
    store.get.return_value = source

    vs = vector_store if vector_store is not None else MagicMock()
    vs.delete_embedding.return_value = True

    db_conn = conn if conn is not None else _make_conn()

    app_ctx = MagicMock()
    app_ctx.source_store = store
    app_ctx.vector_store = vs
    app_ctx.conn = db_conn

    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return ToolAnnotations for a named mcp-knowledge tool when present."""
    if hasattr(mcp, "_tool_manager"):
        for tool in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(tool, "name", None) == tool_name:
                return getattr(tool, "annotations", None)
    return None


class TestFromAC_AppContextVectorStore:
    """AppContext exposes vector_store and app_lifespan wires it."""

    def test_app_context_has_vector_store_field(self) -> None:
        assert "vector_store" in AppContext.__dataclass_fields__

    def test_app_context_vector_store_accepts_none(self) -> None:
        ctx = AppContext(  # type: ignore[call-arg]
            conn=MagicMock(),
            query_service=None,
            graph_store=None,
            ingest_pipeline=None,
            source_store=None,
            vector_store=None,
        )
        assert ctx.vector_store is None

    @pytest.mark.asyncio
    async def test_app_lifespan_wires_vector_store_to_app_context(self) -> None:
        mock_conn = MagicMock()
        mock_vs = MagicMock(name="QdrantVectorStoreInstance")

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=mock_conn),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore", return_value=mock_vs),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server) as ctx:
                assert ctx.vector_store is mock_vs


class TestFromAC_RemoveSourceTool:
    """remove_source is registered and performs vectors-first deletion."""

    def test_remove_source_registered_with_destructive_hint(self) -> None:
        ann = _get_tool_annotations("remove_source")
        assert ann is not None
        assert ann.destructiveHint is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_remove_source_returns_dict_with_expected_keys(self) -> None:
        ctx = _make_ctx(source=_make_source())

        result = await remove_source(ctx, source_id="src-1")

        assert isinstance(result, dict)
        assert "documents" in result
        assert "chunks" in result
        assert "entities" in result

    @pytest.mark.asyncio
    async def test_remove_source_dict_values_are_integers(self) -> None:
        ctx = _make_ctx(source=_make_source(), conn=_make_conn(doc_count=2, chunk_count=3, entity_count=5))

        result = await remove_source(ctx, source_id="src-1")

        assert isinstance(result["documents"], int)
        assert isinstance(result["chunks"], int)
        assert isinstance(result["entities"], int)

    @pytest.mark.asyncio
    async def test_remove_source_calls_delete_embedding_for_each_chunk(self) -> None:
        chunk_ids = ["chunk-a", "chunk-b", "chunk-c"]
        vs = MagicMock()
        vs.delete_embedding.return_value = True
        ctx = _make_ctx(source=_make_source(), vector_store=vs, conn=_make_conn(chunk_ids=chunk_ids))

        await remove_source(ctx, source_id="src-1")

        assert vs.delete_embedding.call_count == 3
        vs.delete_embedding.assert_any_call("chunk-a")
        vs.delete_embedding.assert_any_call("chunk-b")
        vs.delete_embedding.assert_any_call("chunk-c")

    @pytest.mark.asyncio
    async def test_remove_source_calls_delete_embedding_for_each_entity(self) -> None:
        entity_ids = ["entity-a", "entity-b"]
        vs = MagicMock()
        vs.delete_embedding.return_value = True
        ctx = _make_ctx(source=_make_source(), vector_store=vs, conn=_make_conn(chunk_ids=[], entity_ids=entity_ids))

        await remove_source(ctx, source_id="src-1")

        assert vs.delete_embedding.call_count == 2
        vs.delete_embedding.assert_any_call("entity-a")
        vs.delete_embedding.assert_any_call("entity-b")

    @pytest.mark.asyncio
    async def test_remove_source_calls_delete_cascade_with_source_id(self) -> None:
        ctx = _make_ctx(source=_make_source(source_id="src-1"))
        store = ctx.request_context.lifespan_context.source_store

        await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_called_once_with("src-1")

    @pytest.mark.asyncio
    async def test_remove_source_returns_correct_counts(self) -> None:
        ctx = _make_ctx(source=_make_source(), conn=_make_conn(doc_count=4, chunk_count=7, entity_count=11))

        result = await remove_source(ctx, source_id="src-1")

        assert result["documents"] == 4
        assert result["chunks"] == 7
        assert result["entities"] == 11


class TestFromAC_VectorsFirstAbort:
    """Vector deletion failures abort before SQL deletion, False does not."""

    @pytest.mark.asyncio
    async def test_remove_source_raises_tool_error_on_delete_embedding_exception(self) -> None:
        vs = MagicMock()
        vs.delete_embedding.side_effect = RuntimeError("Qdrant connection refused")
        ctx = _make_ctx(source=_make_source(), vector_store=vs, conn=_make_conn(chunk_ids=["chunk-1"]))

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="src-1")

    @pytest.mark.asyncio
    async def test_remove_source_does_not_call_delete_cascade_when_vector_deletion_fails(self) -> None:
        vs = MagicMock()
        vs.delete_embedding.side_effect = OSError("network error")
        ctx = _make_ctx(source=_make_source(), vector_store=vs, conn=_make_conn(chunk_ids=["chunk-1"]))
        store = ctx.request_context.lifespan_context.source_store

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_false_from_delete_embedding_is_not_abort(self) -> None:
        vs = MagicMock()
        vs.delete_embedding.return_value = False
        ctx = _make_ctx(source=_make_source(), vector_store=vs, conn=_make_conn(chunk_ids=["chunk-1", "chunk-2"]))
        store = ctx.request_context.lifespan_context.source_store

        result = await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_remove_source_aborts_on_second_chunk_failure(self) -> None:
        vs = MagicMock()
        vs.delete_embedding.side_effect = [True, ValueError("second chunk fails"), True]
        ctx = _make_ctx(
            source=_make_source(),
            vector_store=vs,
            conn=_make_conn(chunk_ids=["chunk-1", "chunk-2", "chunk-3"]),
        )
        store = ctx.request_context.lifespan_context.source_store

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_sqlite_intact_after_vector_failure(self) -> None:
        vs = MagicMock()
        vs.delete_embedding.side_effect = RuntimeError("abort")
        ctx = _make_ctx(source=_make_source(), vector_store=vs, conn=_make_conn(chunk_ids=["chunk-x"]))
        store = ctx.request_context.lifespan_context.source_store

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_not_called()
        store.delete.assert_not_called()


class TestFromAC_AuditLog:
    """remove_source logs an audit entry before delete_cascade."""

    @pytest.mark.asyncio
    async def test_remove_source_calls_logger_info_before_delete_cascade(self) -> None:
        ctx = _make_ctx(source=_make_source())

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_source_id(self) -> None:
        ctx = _make_ctx(source=_make_source(source_id="src-audit-42"))

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-audit-42")

        all_args = " ".join(str(arg) for call in mock_logger.info.call_args_list for arg in call.args)
        assert "src-audit-42" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_source_name(self) -> None:
        ctx = _make_ctx(source=_make_source(name="My Special Knowledge Source"))

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")

        all_args = " ".join(str(arg) for call in mock_logger.info.call_args_list for arg in call.args)
        assert "My Special Knowledge Source" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_doc_count(self) -> None:
        ctx = _make_ctx(source=_make_source(), conn=_make_conn(doc_count=99, chunk_count=1, entity_count=1))

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")

        all_args = " ".join(str(arg) for call in mock_logger.info.call_args_list for arg in call.args)
        assert "99" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_chunk_count(self) -> None:
        ctx = _make_ctx(source=_make_source(), conn=_make_conn(doc_count=1, chunk_count=88, entity_count=1))

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")

        all_args = " ".join(str(arg) for call in mock_logger.info.call_args_list for arg in call.args)
        assert "88" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_entity_count(self) -> None:
        ctx = _make_ctx(source=_make_source(), conn=_make_conn(doc_count=1, chunk_count=1, entity_count=77))

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")

        all_args = " ".join(str(arg) for call in mock_logger.info.call_args_list for arg in call.args)
        assert "77" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_logger_info_strictly_before_delete_cascade(self) -> None:
        ctx = _make_ctx(source=_make_source())
        store = ctx.request_context.lifespan_context.source_store

        call_order: list[str] = []

        def _record_cascade(*args: object, **kwargs: object) -> None:  # noqa: ARG001
            call_order.append("delete_cascade")

        store.delete_cascade.side_effect = _record_cascade

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:

            def _record_info(*args: object, **kwargs: object) -> None:  # noqa: ARG001
                call_order.append("logger.info")

            mock_logger.info.side_effect = _record_info
            await remove_source(ctx, source_id="src-1")

        assert "logger.info" in call_order
        assert "delete_cascade" in call_order
        assert call_order.index("logger.info") < call_order.index("delete_cascade")


class TestFromAC_SourceNotFound:
    """remove_source rejects unknown source IDs without side effects."""

    @pytest.mark.asyncio
    async def test_remove_source_raises_tool_error_when_source_not_found(self) -> None:
        ctx = _make_ctx(source=None)

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="nonexistent")

    @pytest.mark.asyncio
    async def test_remove_source_no_delete_embedding_when_source_not_found(self) -> None:
        vs = MagicMock()
        ctx = _make_ctx(source=None, vector_store=vs)

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="nonexistent")

        vs.delete_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_no_delete_cascade_when_source_not_found(self) -> None:
        ctx = _make_ctx(source=None)
        store = ctx.request_context.lifespan_context.source_store

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="nonexistent")

        store.delete_cascade.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_no_sql_mutation_when_source_not_found(self) -> None:
        conn = MagicMock()
        conn.execute.return_value = MagicMock()
        ctx = _make_ctx(source=None, conn=conn)

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="nonexistent")

        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_in_all_export(self) -> None:
        import owlbear_mcp_knowledge.server as server_module

        assert "remove_source" in server_module.__all__


class TestServerHelperFallbacks:
    """Small helper fallbacks keep the server resilient under optional failures."""

    def test_exclude_tools_ignores_empty_entries_and_remove_failures(self) -> None:
        from owlbear_mcp_knowledge.server import _apply_tool_exclusions

        server = MagicMock()

        def _remove_tool(tool_name: str) -> None:
            if tool_name == "broken":
                msg = "cannot remove"
                raise RuntimeError(msg)

        server.remove_tool.side_effect = _remove_tool

        with patch.dict("os.environ", {"KNOWLEDGE_TOOLS_EXCLUDE": "good, ,broken"}):
            excluded = _apply_tool_exclusions(server)

        assert excluded == {"good"}
        called = [call.args[0] for call in server.remove_tool.call_args_list]
        assert called == ["good", "broken"]

    @pytest.mark.asyncio
    async def test_web_read_returns_none_when_fetcher_raises(self) -> None:
        from owlbear_mcp_knowledge.server import _web_read

        with patch("owlbear_mcp_knowledge.server.HttpxContentFetcher") as fetcher_cls:
            fetcher_cls.return_value.fetch = AsyncMock(side_effect=RuntimeError("boom"))

            result = await _web_read("https://example.test")

        assert result is None


class TestRemoveSourceUnavailableDeps:
    """remove_source fails fast when required runtime dependencies are missing."""

    @pytest.mark.asyncio
    async def test_remove_source_raises_when_source_store_missing(self) -> None:
        ctx = MagicMock()
        ctx.request_context.lifespan_context.source_store = None

        with pytest.raises(ToolError, match="source store not available"):
            await remove_source(ctx, source_id="src-1")

    @pytest.mark.asyncio
    async def test_remove_source_raises_when_vector_store_missing(self) -> None:
        source = _make_source()
        store = MagicMock()
        store.get.return_value = source
        ctx = MagicMock()
        ctx.request_context.lifespan_context.source_store = store
        ctx.request_context.lifespan_context.conn = MagicMock()
        ctx.request_context.lifespan_context.vector_store = None

        with pytest.raises(ToolError, match="vector store not available"):
            await remove_source(ctx, source_id="src-1")
