"""Failing tests for task #55: ingest and graph tools for mcp-knowledge server.

Covers (TDD RED phase — all tests must FAIL before builder implements #55):
  - AC1: ingest_document tool params, delegation to IngestPipeline, return format
  - AC2: ingest_document exception handling (unexpected raises + pipeline failures)
  - AC3: list_entities filtering, asyncio.to_thread delegation, pagination slice
  - AC4: list_entities EntityType validation — error string lists valid types
  - AC5: list_entities returns 'No entities found.' when result set is empty
  - AC6: get_stats asyncio.to_thread delegation, return format
  - AC8: AppContext extended with ingest_pipeline field; lifespan wires IngestPipeline
  - AC9: Tool descriptions are verb-first and LLM-friendly

All tests mock IngestPipeline, GraphStore, and MCP Context — no real DB, LLM, or
embeddings required. Tests fail with ImportError until builder creates server.py.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import targets — will raise ImportError until builder creates server.py (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_knowledge.server import (  # type: ignore[import]
    app_lifespan,
    get_stats,
    ingest_document,
    list_entities,
    mcp,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ingest_result(
    *,
    document_id: str = "doc-abc123",
    chunk_count: int = 5,
    entity_count: int = 3,
    edge_count: int = 2,
    status: str = "ok",
) -> MagicMock:
    """Return a MagicMock shaped like IngestResult."""
    result = MagicMock()
    result.document_id = document_id
    result.chunk_count = chunk_count
    result.entity_count = entity_count
    result.edge_count = edge_count
    result.status = status
    return result


def _make_entity(
    name: str = "MyEntity",
    entity_type: str = "concept",
    description: str = "A test entity",
) -> MagicMock:
    """Return a MagicMock shaped like Entity with string-compatible fields."""
    ent = MagicMock()
    ent.name = name
    ent.entity_type = entity_type
    ent.description = description
    return ent


def _make_app_context(
    *,
    ingest_pipeline: Any = None,
    graph_store: Any = None,
    query_service: Any = None,
) -> MagicMock:
    """Return a MagicMock shaped like the extended AppContext."""
    ctx = MagicMock()
    ctx.ingest_pipeline = ingest_pipeline or MagicMock()
    ctx.graph_store = graph_store or MagicMock()
    ctx.query_service = query_service
    return ctx


def _make_mcp_ctx(app_ctx: Any = None) -> MagicMock:
    """Return a MagicMock mimicking a FastMCP Context with a lifespan_context."""
    mcp_ctx = MagicMock()
    mcp_ctx.request_context.lifespan_context = app_ctx or _make_app_context()
    return mcp_ctx


# ---------------------------------------------------------------------------
# TestFromAC_IngestDocument
# ---------------------------------------------------------------------------


class TestFromAC_IngestDocument:
    """Contract tests for the ingest_document MCP tool derived from AC1-AC2."""

    # -- AC1: happy path — return format -----------------------------------------

    @pytest.mark.asyncio
    async def test_returns_ingested_prefix_with_doc_id(self) -> None:
        """ingest_document return value starts with 'Ingested:' and includes document_id."""
        result = _make_ingest_result(document_id="doc-xyz42", status="ok")
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = result
        output = await ingest_document(_make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)), text="hello")

        assert "Ingested" in output
        assert "doc-xyz42" in output

    @pytest.mark.asyncio
    async def test_return_format_includes_all_counts(self) -> None:
        """Return value includes chunk_count, entity_count, edge_count, and status."""
        result = _make_ingest_result(
            document_id="abc",
            chunk_count=10,
            entity_count=4,
            edge_count=2,
            status="ok",
        )
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = result
        output = await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
            text="sample",
        )

        assert "10" in output    # chunk_count
        assert "4" in output     # entity_count
        assert "2" in output     # edge_count
        assert "ok" in output    # status

    @pytest.mark.asyncio
    async def test_return_format_contains_chunks_entities_edges_status_keywords(self) -> None:
        """Return value contains 'chunks', 'entities', 'edges', and 'status:' keywords."""
        result = _make_ingest_result(chunk_count=1, entity_count=1, edge_count=1, status="ok")
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = result
        output = await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
            text="test",
        )

        assert "chunks" in output
        assert "entities" in output
        assert "edges" in output
        assert "status" in output

    @pytest.mark.asyncio
    async def test_delegates_text_to_ingest_text(self) -> None:
        """ingest_document passes the text argument as the first arg to IngestPipeline.ingest_text."""
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = _make_ingest_result()
        await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
            text="my document content",
        )

        pipeline.ingest_text.assert_called_once()
        call_args = pipeline.ingest_text.call_args
        positional_args = call_args.args or ()
        keyword_args = call_args.kwargs or {}
        assert "my document content" in positional_args or keyword_args.get("text") == "my document content"

    @pytest.mark.asyncio
    async def test_passes_metadata_as_keyword_argument(self) -> None:
        """metadata is passed to ingest_text as the metadata= keyword argument."""
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = _make_ingest_result()
        meta: dict[str, str] = {"url": "http://example.com", "type": "crawl"}

        await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
            text="content",
            metadata=meta,
        )

        call_kwargs = pipeline.ingest_text.call_args.kwargs
        assert call_kwargs.get("metadata") == meta

    @pytest.mark.asyncio
    async def test_metadata_defaults_to_none_when_omitted(self) -> None:
        """When metadata is not supplied, None is passed to ingest_text as metadata."""
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = _make_ingest_result()

        await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
            text="text only, no metadata",
        )

        call_kwargs = pipeline.ingest_text.call_args.kwargs
        assert call_kwargs.get("metadata") is None

    @pytest.mark.asyncio
    async def test_awaits_ingest_text_not_via_to_thread(self) -> None:
        """ingest_document awaits IngestPipeline.ingest_text directly, not via asyncio.to_thread."""
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = _make_ingest_result()

        with patch("owlbear_mcp_knowledge.server.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock()
            await ingest_document(
                _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
                text="test",
            )

        # ingest_text is async — tool must await it directly, NOT via asyncio.to_thread
        mock_asyncio.to_thread.assert_not_called()

    # -- AC2: exception handling -------------------------------------------------

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_string_not_raises(self) -> None:
        """An unexpected exception from IngestPipeline is caught; a string is returned."""
        pipeline = AsyncMock()
        pipeline.ingest_text.side_effect = RuntimeError("something went wrong")

        output = await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
            text="will fail",
        )

        assert isinstance(output, str)
        assert len(output) > 0

    @pytest.mark.asyncio
    async def test_error_string_contains_no_python_traceback(self) -> None:
        """Error response must not contain Python traceback markers ('Traceback', 'File ')."""
        pipeline = AsyncMock()
        pipeline.ingest_text.side_effect = ValueError("internal error")

        output = await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
            text="will raise",
        )

        assert "Traceback" not in output
        assert "File " not in output  # no file path lines from traceback

    @pytest.mark.asyncio
    async def test_failed_ingest_result_returned_as_string(self) -> None:
        """IngestResult with status='failed' is returned as a formatted string (no exception)."""
        failed_result = _make_ingest_result(
            document_id="doc-fail",
            chunk_count=0,
            entity_count=0,
            edge_count=0,
            status="failed",
        )
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = failed_result

        output = await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)),
            text="pipeline returns failure gracefully",
        )

        assert isinstance(output, str)
        assert "failed" in output


# ---------------------------------------------------------------------------
# TestFromAC_ListEntities
# ---------------------------------------------------------------------------


class TestFromAC_ListEntities:
    """Contract tests for the list_entities MCP tool derived from AC3-AC5."""

    # -- AC3: happy path — format and delegation ---------------------------------

    @pytest.mark.asyncio
    async def test_returns_entities_header_line(self) -> None:
        """Response includes 'Entities' header with total count."""
        entities = [_make_entity("Alpha", "concept", "First")]
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = entities
            output = await list_entities(_make_mcp_ctx())

        assert "Entities" in output
        assert "1" in output   # total shown in header

    @pytest.mark.asyncio
    async def test_entity_lines_are_bullets(self) -> None:
        """Each entity in the response renders as a bullet line starting with '-'."""
        entities = [_make_entity("Func1", "function", "A function")]
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = entities
            output = await list_entities(_make_mcp_ctx())

        lines = [ln.strip() for ln in output.split("\n") if ln.strip().startswith("-")]
        assert len(lines) >= 1

    @pytest.mark.asyncio
    async def test_entity_line_format_name_type_description(self) -> None:
        """Entity lines contain name, entity_type, and description."""
        entities = [_make_entity("MyDecision", "decision", "A key decision")]
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = entities
            output = await list_entities(_make_mcp_ctx())

        assert "MyDecision" in output
        assert "decision" in output
        assert "A key decision" in output

    @pytest.mark.asyncio
    async def test_calls_list_entities_via_asyncio_to_thread(self) -> None:
        """list_entities uses asyncio.to_thread to call the synchronous GraphStore.list_entities."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_mcp_ctx())

        mock_t.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_type_filter_passed_when_provided(self) -> None:
        """When entity_type is given, EntityType(entity_type) is passed to list_entities."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_mcp_ctx(), entity_type="concept")

        # to_thread was called once and receives entity_type info
        mock_t.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_entity_type_kwarg_when_none(self) -> None:
        """When entity_type is None, list_entities is called without an entity_type filter."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_mcp_ctx(), entity_type=None)

        call_args = mock_t.call_args
        # Verify entity_type is not forwarded as a kwarg to to_thread
        kwargs_passed = call_args.kwargs if call_args and call_args.kwargs else {}
        assert "entity_type" not in kwargs_passed

    @pytest.mark.asyncio
    async def test_pagination_slice_offset_and_limit(self) -> None:
        """Offset+limit slice is applied: result is all_entities[offset:offset+limit]."""
        all_entities = [_make_entity(f"E{i}", "concept", f"desc {i}") for i in range(10)]
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = all_entities
            output = await list_entities(_make_mcp_ctx(), offset=3, limit=2)

        # Page [3:5] → E3, E4 only
        assert "E3" in output
        assert "E4" in output
        assert "E0" not in output
        assert "E9" not in output

    @pytest.mark.asyncio
    async def test_header_shows_total_count_not_just_page(self) -> None:
        """Header reflects total entity count, not just the page size."""
        all_entities = [_make_entity(f"X{i}", "concept", "d") for i in range(8)]
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = all_entities
            output = await list_entities(_make_mcp_ctx(), offset=0, limit=3)

        # Header must show 8 (total), not 3 (page size)
        assert "8" in output.split("\n")[0]  # total on first line

    @pytest.mark.asyncio
    async def test_default_offset_0_limit_50(self) -> None:
        """Default parameters: offset=0, limit=50 are applied when not supplied."""
        all_entities = [_make_entity(f"D{i}", "pattern", "x") for i in range(60)]
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = all_entities
            output = await list_entities(_make_mcp_ctx())

        # With default limit=50, items 0..49 present; item 50+ absent
        assert "D0" in output
        assert "D49" in output
        assert "D50" not in output

    # -- AC4: EntityType validation -----------------------------------------------

    @pytest.mark.asyncio
    async def test_invalid_entity_type_returns_error_not_exception(self) -> None:
        """An invalid entity_type value returns an error string, not an unhandled exception."""
        output = await list_entities(_make_mcp_ctx(), entity_type="completely_invalid_type_xyz")

        assert isinstance(output, str)
        # Must not be a normal entity listing
        assert "Entities" not in output or "valid" in output.lower() or "invalid" in output.lower()

    @pytest.mark.asyncio
    async def test_error_for_invalid_type_lists_valid_entity_types(self) -> None:
        """Error string for invalid entity_type includes valid EntityType values."""
        from owlbear_knowledge.models import EntityType

        output = await list_entities(_make_mcp_ctx(), entity_type="not_a_valid_type_xyz")

        valid_type_values = [e.value for e in EntityType]
        assert any(vt in output for vt in valid_type_values), (
            f"Expected at least one valid type from {valid_type_values!r} in: {output!r}"
        )

    # -- AC5: empty result --------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_list_returns_no_entities_found(self) -> None:
        """Empty entity list (no filter) returns exactly 'No entities found.'"""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            output = await list_entities(_make_mcp_ctx())

        assert "No entities found." in output

    @pytest.mark.asyncio
    async def test_empty_after_type_filter_returns_no_entities_found(self) -> None:
        """Empty result after entity_type filter returns 'No entities found.'"""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            output = await list_entities(_make_mcp_ctx(), entity_type="concept")

        assert "No entities found." in output


# ---------------------------------------------------------------------------
# TestFromAC_GetStats
# ---------------------------------------------------------------------------


class TestFromAC_GetStats:
    """Contract tests for the get_stats MCP tool derived from AC6."""

    @pytest.mark.asyncio
    async def test_returns_knowledge_base_prefix(self) -> None:
        """get_stats return value starts with 'Knowledge base:'."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = (3, 7, 5)
            output = await get_stats(_make_mcp_ctx())

        assert "Knowledge base" in output

    @pytest.mark.asyncio
    async def test_return_format_contains_all_three_counts(self) -> None:
        """Return value includes all three counts from GraphStore.get_counts()."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = (5, 12, 7)
            output = await get_stats(_make_mcp_ctx())

        assert "5" in output    # doc_count
        assert "12" in output   # entity_count
        assert "7" in output    # edge_count

    @pytest.mark.asyncio
    async def test_return_format_contains_documents_entities_edges_keywords(self) -> None:
        """Return value contains the words 'documents', 'entities', and 'edges'."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = (0, 0, 0)
            output = await get_stats(_make_mcp_ctx())

        assert "documents" in output
        assert "entities" in output
        assert "edges" in output

    @pytest.mark.asyncio
    async def test_calls_get_counts_via_asyncio_to_thread(self) -> None:
        """get_stats uses asyncio.to_thread to call GraphStore.get_counts (synchronous)."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = (0, 0, 0)
            await get_stats(_make_mcp_ctx())

        mock_t.assert_called_once()

    @pytest.mark.asyncio
    async def test_counts_order_is_documents_entities_edges(self) -> None:
        """The format places doc count before entity count before edge count."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            # Use distinct values that are only unique to their position
            mock_t.return_value = (2, 300, 40)
            output = await get_stats(_make_mcp_ctx())

        # "2 documents" must appear before "300 entities" before "40 edges"
        doc_pos = output.find("2")
        entity_pos = output.find("300")
        edge_pos = output.find("40")
        assert doc_pos < entity_pos < edge_pos


# ---------------------------------------------------------------------------
# TestFromAC_AppContextExtension
# ---------------------------------------------------------------------------


class TestFromAC_AppContextExtension:
    """Contract tests for AppContext.ingest_pipeline field and lifespan wiring (AC8)."""

    @pytest.mark.asyncio
    async def test_app_context_has_ingest_pipeline_field(self) -> None:
        """AppContext yielded by app_lifespan has an 'ingest_pipeline' attribute."""
        with (
            patch("owlbear_mcp_knowledge.server.init_db"),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.DocumentStore"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor"),
            patch("owlbear_mcp_knowledge.server.TextChunker"),
            patch("owlbear_mcp_knowledge.server.IngestPipeline"),
        ):
            async with app_lifespan(MagicMock()) as ctx:
                assert hasattr(ctx, "ingest_pipeline")

    @pytest.mark.asyncio
    async def test_app_lifespan_ingest_pipeline_is_not_none(self) -> None:
        """AppContext.ingest_pipeline is not None after lifespan initialisation."""
        mock_pipeline = MagicMock()
        with (
            patch("owlbear_mcp_knowledge.server.init_db"),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.DocumentStore"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor"),
            patch("owlbear_mcp_knowledge.server.TextChunker"),
            patch("owlbear_mcp_knowledge.server.IngestPipeline", return_value=mock_pipeline),
        ):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.ingest_pipeline is not None

    @pytest.mark.asyncio
    async def test_entity_extractor_receives_owlbear_model_env_var(self) -> None:
        """EntityExtractor is instantiated with the OWLBEAR_MODEL env var value."""
        with (
            patch("owlbear_mcp_knowledge.server.init_db"),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.DocumentStore"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor") as mock_extractor_cls,
            patch("owlbear_mcp_knowledge.server.TextChunker"),
            patch("owlbear_mcp_knowledge.server.IngestPipeline"),
            patch.dict(os.environ, {"OWLBEAR_MODEL": "gpt-4o-mini"}),
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_extractor_cls.assert_called_once()
        all_args = list(mock_extractor_cls.call_args.args or ()) + list(
            (mock_extractor_cls.call_args.kwargs or {}).values()
        )
        assert "gpt-4o-mini" in all_args, (
            f"Expected 'gpt-4o-mini' among EntityExtractor args: {all_args}"
        )

    @pytest.mark.asyncio
    async def test_entity_extractor_receives_some_default_model_string(self) -> None:
        """When OWLBEAR_MODEL is absent, EntityExtractor receives a non-empty default string."""
        with (
            patch("owlbear_mcp_knowledge.server.init_db"),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.DocumentStore"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor") as mock_extractor_cls,
            patch("owlbear_mcp_knowledge.server.TextChunker"),
            patch("owlbear_mcp_knowledge.server.IngestPipeline"),
            patch.dict(os.environ, {}, clear=True),
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_extractor_cls.assert_called_once()
        all_args = list(mock_extractor_cls.call_args.args or ()) + list(
            (mock_extractor_cls.call_args.kwargs or {}).values()
        )
        str_args = [a for a in all_args if isinstance(a, str)]
        assert any(len(s) > 0 for s in str_args), (
            f"Expected a non-empty default model string in EntityExtractor args: {all_args}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ToolDescriptions
# ---------------------------------------------------------------------------

_VERB_FIRST_WORDS: frozenset[str] = frozenset({
    "ingest", "list", "get", "search", "add", "create", "fetch",
    "retrieve", "return", "show", "find", "compute", "query",
})


def _get_tool_description(tool_name: str) -> str:
    """Extract the description string for a named tool from the FastMCP instance."""
    if hasattr(mcp, "_tool_manager"):
        tools = list(mcp._tool_manager.list_tools())  # noqa: SLF001
        for t in tools:
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "description", "") or ""
    return ""


class TestFromAC_ToolDescriptions:
    """Contract tests for LLM-friendly, verb-first tool descriptions (AC9)."""

    def test_ingest_document_description_is_verb_first(self) -> None:
        """ingest_document tool description opens with an action verb."""
        desc = _get_tool_description("ingest_document")
        first_word = desc.strip().split()[0].lower().rstrip(".,") if desc.strip() else ""
        assert first_word in _VERB_FIRST_WORDS, (
            f"'ingest_document' description should start with a verb, got: {desc!r}"
        )

    def test_list_entities_description_is_verb_first(self) -> None:
        """list_entities tool description opens with an action verb."""
        desc = _get_tool_description("list_entities")
        first_word = desc.strip().split()[0].lower().rstrip(".,") if desc.strip() else ""
        assert first_word in _VERB_FIRST_WORDS, (
            f"'list_entities' description should start with a verb, got: {desc!r}"
        )

    def test_get_stats_description_is_verb_first(self) -> None:
        """get_stats tool description opens with an action verb."""
        desc = _get_tool_description("get_stats")
        first_word = desc.strip().split()[0].lower().rstrip(".,") if desc.strip() else ""
        assert first_word in _VERB_FIRST_WORDS, (
            f"'get_stats' description should start with a verb, got: {desc!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ToolReadOnlyHints  (retry: AC1, AC3, AC6 — readOnlyHint gaps)
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named tool, or None if not found."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


class TestFromAC_ToolReadOnlyHints:
    """Contract tests for @mcp.tool() readOnlyHint annotations (AC1, AC3, AC6 retry)."""

    def test_ingest_document_has_read_only_hint_false(self) -> None:
        """ingest_document must be registered with readOnlyHint=False (it writes to the KB)."""
        annotations = _get_tool_annotations("ingest_document")
        assert annotations is not None, (
            "ingest_document has no ToolAnnotations; readOnlyHint=False must be set"
        )
        assert annotations.readOnlyHint is False, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=False for ingest_document, got: {annotations.readOnlyHint!r}"
        )

    def test_list_entities_has_read_only_hint_true(self) -> None:
        """list_entities must be registered with readOnlyHint=True (it only reads the KB)."""
        annotations = _get_tool_annotations("list_entities")
        assert annotations is not None, (
            "list_entities has no ToolAnnotations; readOnlyHint=True must be set"
        )
        assert annotations.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for list_entities, got: {annotations.readOnlyHint!r}"
        )

    def test_get_stats_has_read_only_hint_true(self) -> None:
        """get_stats must be registered with readOnlyHint=True (it only reads counts)."""
        annotations = _get_tool_annotations("get_stats")
        assert annotations is not None, (
            "get_stats has no ToolAnnotations; readOnlyHint=True must be set"
        )
        assert annotations.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for get_stats, got: {annotations.readOnlyHint!r}"
        )


# ---------------------------------------------------------------------------
# TestBuilderDiscovered
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered edge cases not covered by TestFromAC_* classes.

    Tightens the LAX assertion in TestFromAC_ListEntities::
    test_entity_type_filter_passed_when_provided, which only checked
    to_thread call count without verifying the entity_type kwarg forwarding.
    """

    @pytest.mark.asyncio
    async def test_entity_type_kwarg_forwarded_as_enum_to_to_thread(self) -> None:
        """When entity_type='concept', EntityType enum value is forwarded as kwarg to to_thread."""
        from owlbear_knowledge.models import EntityType

        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_mcp_ctx(), entity_type="concept")

        call_kwargs = mock_t.call_args.kwargs
        assert "entity_type" in call_kwargs, (
            "entity_type kwarg must be forwarded to asyncio.to_thread when entity_type is given"
        )
        assert call_kwargs["entity_type"] == EntityType("concept"), (
            f"Expected EntityType('concept'), got: {call_kwargs['entity_type']!r}"
        )
