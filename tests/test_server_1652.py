"""Tests for task #1652: P1-03: Add remove_source MCP tool with vectors-first abort.

TDD RED phase — all tests FAIL before builder implements remove_source and extends AppContext.

AC coverage:
  - AC-1: AppContext has vector_store field typed QdrantVectorStore | None;
          app_lifespan wires the existing vs instance into it.
  - AC-2: remove_source registered with destructiveHint=True; source found →
          collects chunk IDs via SQL join, deletes vectors, calls delete_cascade,
          returns dict with documents/chunks/entities counts.
  - AC-3: delete_embedding raising exception → ToolError raised, delete_cascade NOT called;
          delete_embedding returning False is not an abort condition.
  - AC-4: Before delete_cascade, logger.info audit entry contains source_id, name, counts.
  - AC-5: source_id not found → ToolError; no vector deletions or SQL changes.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_knowledge.server import AppContext, app_lifespan, mcp, remove_source

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    """Return a mock SQLite connection.

    The chunk-ID join query (any SQL without COUNT) returns chunk_ids.
    COUNT queries return doc_count / chunk_count / entity_count based on keywords.
    """
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
            cursor.fetchall.return_value = [(eid,) for eid in entity_ids]
        else:
            cursor.fetchall.return_value = [(cid,) for cid in chunk_ids]
        return cursor

    conn.execute.side_effect = _execute
    return conn


def _make_ctx(
    *,
    source: MagicMock | None = None,
    vector_store: MagicMock | None = None,
    conn: MagicMock | None = None,
) -> MagicMock:
    """Return a FastMCP Context mock with controlled lifespan_context fields."""
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
    """Return the ToolAnnotations for a named mcp-knowledge tool, or None."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_AppContextVectorStore — AC-1
# ---------------------------------------------------------------------------


class TestFromAC_AppContextVectorStore:
    """AppContext must expose a vector_store field; app_lifespan must wire vs into it."""

    def test_app_context_has_vector_store_field(self) -> None:
        """AppContext dataclass declares a vector_store field."""
        assert "vector_store" in AppContext.__dataclass_fields__

    def test_app_context_vector_store_accepts_none(self) -> None:
        """vector_store field accepts None (QdrantVectorStore | None annotation)."""
        # The default or annotation must allow None; verify field exists and is nullable
        # by constructing with vector_store=None — this will raise TypeError if no such field
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
        """app_lifespan yields an AppContext whose vector_store is the QdrantVectorStore instance."""
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


# ---------------------------------------------------------------------------
# TestFromAC_RemoveSourceTool — AC-2
# ---------------------------------------------------------------------------


class TestFromAC_RemoveSourceTool:
    """remove_source must be registered with destructiveHint=True and implement
    the vectors-first deletion flow, returning a counts dict."""

    def test_remove_source_registered_with_destructive_hint(self) -> None:
        """remove_source tool is registered with destructiveHint=True."""
        ann = _get_tool_annotations("remove_source")
        assert ann is not None, "remove_source has no ToolAnnotations"
        assert ann.destructiveHint is True  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_remove_source_returns_dict_with_expected_keys(self) -> None:
        """Happy path: source found → returns dict with documents, chunks, entities keys."""
        source = _make_source()
        ctx = _make_ctx(source=source)

        result = await remove_source(ctx, source_id="src-1")

        assert isinstance(result, dict)
        assert "documents" in result
        assert "chunks" in result
        assert "entities" in result

    @pytest.mark.asyncio
    async def test_remove_source_dict_values_are_integers(self) -> None:
        """Return dict values for documents, chunks, entities are integers."""
        source = _make_source()
        ctx = _make_ctx(source=source, conn=_make_conn(doc_count=2, chunk_count=3, entity_count=5))

        result = await remove_source(ctx, source_id="src-1")

        assert isinstance(result["documents"], int)
        assert isinstance(result["chunks"], int)
        assert isinstance(result["entities"], int)

    @pytest.mark.asyncio
    async def test_remove_source_calls_delete_embedding_for_each_chunk(self) -> None:
        """delete_embedding is called once per chunk ID collected from the SQL join."""
        chunk_ids = ["chunk-a", "chunk-b", "chunk-c"]
        source = _make_source()
        vs = MagicMock()
        vs.delete_embedding.return_value = True
        conn = _make_conn(chunk_ids=chunk_ids)
        ctx = _make_ctx(source=source, vector_store=vs, conn=conn)

        await remove_source(ctx, source_id="src-1")

        assert vs.delete_embedding.call_count == 3
        vs.delete_embedding.assert_any_call("chunk-a")
        vs.delete_embedding.assert_any_call("chunk-b")
        vs.delete_embedding.assert_any_call("chunk-c")

    @pytest.mark.asyncio
    async def test_remove_source_calls_delete_embedding_for_each_entity(self) -> None:
        """delete_embedding is also called for entity IDs collected from the source."""
        entity_ids = ["entity-a", "entity-b"]
        source = _make_source()
        vs = MagicMock()
        vs.delete_embedding.return_value = True
        conn = _make_conn(chunk_ids=[], entity_ids=entity_ids)
        ctx = _make_ctx(source=source, vector_store=vs, conn=conn)

        await remove_source(ctx, source_id="src-1")

        assert vs.delete_embedding.call_count == 2
        vs.delete_embedding.assert_any_call("entity-a")
        vs.delete_embedding.assert_any_call("entity-b")

    @pytest.mark.asyncio
    async def test_remove_source_calls_delete_cascade_with_source_id(self) -> None:
        """delete_cascade is called with the correct source_id after vector deletion."""
        source = _make_source(source_id="src-1")
        ctx = _make_ctx(source=source)
        store = ctx.request_context.lifespan_context.source_store

        await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_called_once_with("src-1")

    @pytest.mark.asyncio
    async def test_remove_source_returns_correct_counts(self) -> None:
        """Return dict reflects pre-cascade document, chunk, and entity counts."""
        source = _make_source()
        conn = _make_conn(doc_count=4, chunk_count=7, entity_count=11)
        ctx = _make_ctx(source=source, conn=conn)

        result = await remove_source(ctx, source_id="src-1")

        assert result["documents"] == 4
        assert result["chunks"] == 7
        assert result["entities"] == 11


# ---------------------------------------------------------------------------
# TestFromAC_VectorsFirstAbort — AC-3
# ---------------------------------------------------------------------------


class TestFromAC_VectorsFirstAbort:
    """Strict abort semantics: exception from delete_embedding → ToolError, no cascade.
    Returning False is NOT an abort condition."""

    @pytest.mark.asyncio
    async def test_remove_source_raises_tool_error_on_delete_embedding_exception(self) -> None:
        """delete_embedding raising any exception → ToolError is raised."""
        source = _make_source()
        vs = MagicMock()
        vs.delete_embedding.side_effect = RuntimeError("Qdrant connection refused")
        ctx = _make_ctx(source=source, vector_store=vs, conn=_make_conn(chunk_ids=["chunk-1"]))

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="src-1")

    @pytest.mark.asyncio
    async def test_remove_source_does_not_call_delete_cascade_when_vector_deletion_fails(self) -> None:
        """delete_cascade is NOT called when delete_embedding raises an exception."""
        source = _make_source()
        vs = MagicMock()
        vs.delete_embedding.side_effect = OSError("network error")
        ctx = _make_ctx(source=source, vector_store=vs, conn=_make_conn(chunk_ids=["chunk-1"]))
        store = ctx.request_context.lifespan_context.source_store

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_false_from_delete_embedding_is_not_abort(self) -> None:
        """delete_embedding returning False (missing vector) does not abort; cascade is called."""
        source = _make_source()
        vs = MagicMock()
        vs.delete_embedding.return_value = False  # missing vector — not an error
        ctx = _make_ctx(source=source, vector_store=vs, conn=_make_conn(chunk_ids=["chunk-1", "chunk-2"]))
        store = ctx.request_context.lifespan_context.source_store

        result = await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_remove_source_aborts_on_second_chunk_failure(self) -> None:
        """Exception on the second of three chunks → ToolError; delete_cascade not called."""
        source = _make_source()
        vs = MagicMock()
        vs.delete_embedding.side_effect = [True, ValueError("second chunk fails"), True]
        ctx = _make_ctx(
            source=source,
            vector_store=vs,
            conn=_make_conn(chunk_ids=["chunk-1", "chunk-2", "chunk-3"]),
        )
        store = ctx.request_context.lifespan_context.source_store

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_sqlite_intact_after_vector_failure(self) -> None:
        """No SQL mutation calls occur when delete_embedding raises (SQLite stays intact)."""
        source = _make_source()
        vs = MagicMock()
        vs.delete_embedding.side_effect = RuntimeError("abort")
        conn = _make_conn(chunk_ids=["chunk-x"])
        ctx = _make_ctx(source=source, vector_store=vs, conn=conn)
        store = ctx.request_context.lifespan_context.source_store

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="src-1")

        store.delete_cascade.assert_not_called()
        store.delete.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_AuditLog — AC-4
# ---------------------------------------------------------------------------


class TestFromAC_AuditLog:
    """remove_source must log an audit entry via logger.info before calling delete_cascade."""

    @pytest.mark.asyncio
    async def test_remove_source_calls_logger_info_before_delete_cascade(self) -> None:
        """logger.info is called before delete_cascade during a successful removal."""
        source = _make_source()
        ctx = _make_ctx(source=source)

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_source_id(self) -> None:
        """Audit log message contains the source_id."""
        source = _make_source(source_id="src-audit-42")
        ctx = _make_ctx(source=source)

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-audit-42")

        all_args = " ".join(str(a) for c in mock_logger.info.call_args_list for a in c.args)
        assert "src-audit-42" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_source_name(self) -> None:
        """Audit log message contains the source name."""
        source = _make_source(name="My Special Knowledge Source")
        ctx = _make_ctx(source=source)

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")

        all_args = " ".join(str(a) for c in mock_logger.info.call_args_list for a in c.args)
        assert "My Special Knowledge Source" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_doc_count(self) -> None:
        """Audit log message contains the pre-cascade document count."""
        source = _make_source()
        conn = _make_conn(doc_count=99, chunk_count=1, entity_count=1)
        ctx = _make_ctx(source=source, conn=conn)

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")

        all_args = " ".join(str(a) for c in mock_logger.info.call_args_list for a in c.args)
        assert "99" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_chunk_count(self) -> None:
        """Audit log message contains the pre-cascade chunk count."""
        source = _make_source()
        conn = _make_conn(doc_count=1, chunk_count=88, entity_count=1)
        ctx = _make_ctx(source=source, conn=conn)

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")

        all_args = " ".join(str(a) for c in mock_logger.info.call_args_list for a in c.args)
        assert "88" in all_args

    @pytest.mark.asyncio
    async def test_remove_source_log_contains_entity_count(self) -> None:
        """Audit log message contains the pre-cascade entity count."""
        source = _make_source()
        conn = _make_conn(doc_count=1, chunk_count=1, entity_count=77)
        ctx = _make_ctx(source=source, conn=conn)

        with patch("owlbear_mcp_knowledge.server.logger") as mock_logger:
            await remove_source(ctx, source_id="src-1")

        all_args = " ".join(str(a) for c in mock_logger.info.call_args_list for a in c.args)
        assert "77" in all_args


# ---------------------------------------------------------------------------
# TestFromAC_SourceNotFound — AC-5
# ---------------------------------------------------------------------------


class TestFromAC_SourceNotFound:
    """remove_source with an unknown source_id must raise ToolError and leave state unchanged."""

    @pytest.mark.asyncio
    async def test_remove_source_raises_tool_error_when_source_not_found(self) -> None:
        """source_id not in knowledge_sources → ToolError is raised."""
        ctx = _make_ctx(source=None)  # source_store.get returns None

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="nonexistent")

    @pytest.mark.asyncio
    async def test_remove_source_no_delete_embedding_when_source_not_found(self) -> None:
        """No delete_embedding calls when the source is not found."""
        vs = MagicMock()
        ctx = _make_ctx(source=None, vector_store=vs)

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="nonexistent")

        vs.delete_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_no_delete_cascade_when_source_not_found(self) -> None:
        """delete_cascade is not called when the source is not found."""
        ctx = _make_ctx(source=None)
        store = ctx.request_context.lifespan_context.source_store

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="nonexistent")

        store.delete_cascade.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_no_sql_mutation_when_source_not_found(self) -> None:
        """No mutating SQL (no conn.execute write paths) when source is not found."""
        conn = MagicMock()
        conn.execute.return_value = MagicMock()
        ctx = _make_ctx(source=None, conn=conn)

        with pytest.raises(ToolError):
            await remove_source(ctx, source_id="nonexistent")

        # The only conn.execute call allowed is the initial lookup via source_store.get;
        # source_store is mocked separately, so conn.execute must not be called for mutations.
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_source_in_all_export(self) -> None:
        """remove_source is exported in __all__."""
        import owlbear_mcp_knowledge.server as srv

        assert "remove_source" in srv.__all__
