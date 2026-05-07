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


@pytest.fixture(autouse=True)
def _bypass_copilot_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a fake LLM API key so app_lifespan skips the Copilot device-auth flow."""
    monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "test-key")


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
        output = await ingest_document(
            _make_mcp_ctx(_make_app_context(ingest_pipeline=pipeline)), text="hello"
        )

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

        assert "10" in output  # chunk_count
        assert "4" in output  # entity_count
        assert "2" in output  # edge_count
        assert "ok" in output  # status

    @pytest.mark.asyncio
    async def test_return_format_contains_chunks_entities_edges_status_keywords(
        self,
    ) -> None:
        """Return value contains 'chunks', 'entities', 'edges', and 'status:' keywords."""
        result = _make_ingest_result(
            chunk_count=1, entity_count=1, edge_count=1, status="ok"
        )
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
        assert (
            "my document content" in positional_args
            or keyword_args.get("text") == "my document content"
        )

    @pytest.mark.asyncio
    async def test_passes_metadata_as_keyword_argument(self) -> None:
        """metadata is passed to ingest_text as the metadata= keyword argument."""
        pipeline = AsyncMock()
        pipeline.ingest_text.return_value = _make_ingest_result()
        meta: dict[str, str] = {"url": "http://example.com", "type": "url_list"}

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
        """Response is a list of entity dicts when entities exist."""
        entities = [_make_entity("Alpha", "concept", "First")]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            output = await list_entities(_make_mcp_ctx())

        assert isinstance(output, list)
        assert len(output) == 1

    @pytest.mark.asyncio
    async def test_entity_lines_are_bullets(self) -> None:
        """Each entity in the response is a dict in the returned list."""
        entities = [_make_entity("Func1", "function", "A function")]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            output = await list_entities(_make_mcp_ctx())

        assert isinstance(output, list)
        assert all(isinstance(item, dict) for item in output)

    @pytest.mark.asyncio
    async def test_entity_line_format_name_type_description(self) -> None:
        """Entity dict contains name, entity_type, and description fields."""
        entities = [_make_entity("MyDecision", "decision", "A key decision")]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            output = await list_entities(_make_mcp_ctx())

        assert output[0]["name"] == "MyDecision"
        assert output[0]["entity_type"] == "decision"
        assert output[0]["description"] == "A key decision"

    @pytest.mark.asyncio
    async def test_calls_list_entities_via_asyncio_to_thread(self) -> None:
        """list_entities uses asyncio.to_thread to call the synchronous GraphStore.list_entities."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_mcp_ctx())

        mock_t.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_type_filter_passed_when_provided(self) -> None:
        """When entity_type is given, EntityType(entity_type) is passed to list_entities."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_mcp_ctx(), entity_type="concept")

        # to_thread was called once and receives entity_type info
        mock_t.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_entity_type_kwarg_when_none(self) -> None:
        """When entity_type is None, list_entities is called without an entity_type filter."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_mcp_ctx(), entity_type=None)

        call_args = mock_t.call_args
        # Verify entity_type is not forwarded as a kwarg to to_thread
        kwargs_passed = call_args.kwargs if call_args and call_args.kwargs else {}
        assert "entity_type" not in kwargs_passed

    @pytest.mark.asyncio
    async def test_pagination_slice_offset_and_limit(self) -> None:
        """Offset+limit slice is applied: result contains dicts for the correct entities."""
        all_entities = [
            _make_entity(f"E{i}", "concept", f"desc {i}") for i in range(10)
        ]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = all_entities
            output = await list_entities(_make_mcp_ctx(), offset=3, limit=2)

        # Page [3:5] -> E3, E4 only
        assert isinstance(output, list)
        assert len(output) == 2
        assert output[0]["name"] == "E3"
        assert output[1]["name"] == "E4"

    @pytest.mark.asyncio
    async def test_header_shows_total_count_not_just_page(self) -> None:
        """Pagination returns the correct page slice (offset/limit respected)."""
        all_entities = [_make_entity(f"X{i}", "concept", "d") for i in range(8)]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = all_entities
            output = await list_entities(_make_mcp_ctx(), offset=0, limit=3)

        # Page size=3, total=8; list must have exactly 3 items
        assert isinstance(output, list)
        assert len(output) == 3

    @pytest.mark.asyncio
    async def test_default_offset_0_limit_50(self) -> None:
        """Default parameters: offset=0, limit=50 return first 50 entities."""
        all_entities = [_make_entity(f"D{i}", "pattern", "x") for i in range(60)]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = all_entities
            output = await list_entities(_make_mcp_ctx())

        # With default limit=50, items 0..49 present; item 50+ absent
        assert isinstance(output, list)
        assert len(output) == 50
        assert output[0]["name"] == "D0"
        assert output[49]["name"] == "D49"

    # -- AC4: EntityType validation -----------------------------------------------

    @pytest.mark.asyncio
    async def test_invalid_entity_type_returns_error_not_exception(self) -> None:
        """An invalid entity_type value returns an error string, not an unhandled exception."""
        output = await list_entities(
            _make_mcp_ctx(), entity_type="completely_invalid_type_xyz"
        )

        assert isinstance(output, str)
        # Must not be a normal entity listing
        assert (
            "Entities" not in output
            or "valid" in output.lower()
            or "invalid" in output.lower()
        )

    @pytest.mark.asyncio
    async def test_error_for_invalid_type_lists_valid_entity_types(self) -> None:
        """Error string for invalid entity_type includes valid EntityType values."""
        from owlbear_knowledge.models import EntityType

        output = await list_entities(
            _make_mcp_ctx(), entity_type="not_a_valid_type_xyz"
        )

        valid_type_values = [e.value for e in EntityType]
        assert any(vt in output for vt in valid_type_values), (
            f"Expected at least one valid type from {valid_type_values!r} in: {output!r}"
        )

    # -- AC5: empty result --------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty_list(self) -> None:
        """Empty entity list returns []."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = []
            output = await list_entities(_make_mcp_ctx())

        assert output == []

    @pytest.mark.asyncio
    async def test_empty_after_type_filter_returns_empty_list(self) -> None:
        """Empty result after entity_type filter returns []."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = []
            output = await list_entities(_make_mcp_ctx(), entity_type="concept")

        assert output == []


# ---------------------------------------------------------------------------
# TestFromAC_GetStats
# ---------------------------------------------------------------------------


class TestFromAC_GetStats:
    """Contract tests for the get_stats MCP tool derived from AC6."""

    @pytest.mark.asyncio
    async def test_returns_knowledge_base_prefix(self) -> None:
        """get_stats returns a dict with 'documents', 'entities', 'edges' keys."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (3, 7, 5)
            output = await get_stats(_make_mcp_ctx())

        assert isinstance(output, dict)
        assert "documents" in output
        assert "entities" in output
        assert "edges" in output

    @pytest.mark.asyncio
    async def test_return_format_contains_all_three_counts(self) -> None:
        """Returned dict contains correct count values from get_counts()."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (5, 12, 7)
            output = await get_stats(_make_mcp_ctx())

        assert output["documents"] == 5
        assert output["entities"] == 12
        assert output["edges"] == 7

    @pytest.mark.asyncio
    async def test_return_format_contains_documents_entities_edges_keywords(
        self,
    ) -> None:
        """Returned dict has 'documents', 'entities', and 'edges' keys."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (0, 0, 0)
            output = await get_stats(_make_mcp_ctx())

        assert "documents" in output
        assert "entities" in output
        assert "edges" in output

    @pytest.mark.asyncio
    async def test_calls_get_counts_via_asyncio_to_thread(self) -> None:
        """get_stats uses asyncio.to_thread to call GraphStore.get_counts (synchronous)."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (0, 0, 0)
            await get_stats(_make_mcp_ctx())

        mock_t.assert_called_once()

    @pytest.mark.asyncio
    async def test_counts_order_is_documents_entities_edges(self) -> None:
        """Counts map correctly: documents=first, entities=second, edges=third."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (2, 300, 40)
            output = await get_stats(_make_mcp_ctx())

        assert output["documents"] == 2
        assert output["entities"] == 300
        assert output["edges"] == 40


# ---------------------------------------------------------------------------
# TestFromAC_ListEntitiesStructured (#507)
# ---------------------------------------------------------------------------


class TestFromAC_ListEntitiesStructured:
    """Contract tests: list_entities returns list[dict] on success, [] on empty."""

    # ------------------------------------------------------------------
    # AC: success returns list not str
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_success_returns_list(self) -> None:
        """list_entities returns a list (not str) when entities are found."""
        entities = [_make_entity("Alpha", "concept", "desc")]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            result = await list_entities(_make_mcp_ctx())

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_success_result_items_are_dicts(self) -> None:
        """Each item in the returned list is a dict."""
        entities = [
            _make_entity("A", "concept", "d1"),
            _make_entity("B", "pattern", "d2"),
        ]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            result = await list_entities(_make_mcp_ctx())

        assert all(isinstance(item, dict) for item in result)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_each_dict_has_name_entity_type_description_keys(self) -> None:
        """Each result dict has 'name', 'entity_type', and 'description' keys."""
        entities = [_make_entity("MyEnt", "decision", "A decision")]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            result = await list_entities(_make_mcp_ctx())

        item = result[0]  # type: ignore[index]
        assert "name" in item
        assert "entity_type" in item
        assert "description" in item

    @pytest.mark.asyncio
    async def test_dict_values_match_entity_fields(self) -> None:
        """name, entity_type, description values come from the entity object fields."""
        entities = [_make_entity("TestEnt", "function", "A function entity")]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            result = await list_entities(_make_mcp_ctx())

        item = result[0]  # type: ignore[index]
        assert item["name"] == "TestEnt"
        assert item["entity_type"] == "function"
        assert item["description"] == "A function entity"

    @pytest.mark.asyncio
    async def test_all_dict_fields_are_str(self) -> None:
        """name, entity_type, and description are all str values."""
        entities = [_make_entity("N", "concept", "D")]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            result = await list_entities(_make_mcp_ctx())

        item = result[0]  # type: ignore[index]
        assert isinstance(item["name"], str)
        assert isinstance(item["entity_type"], str)
        assert isinstance(item["description"], str)

    @pytest.mark.asyncio
    async def test_no_header_line_in_list_result(self) -> None:
        """Result is a plain list with no text header — no 'Entities (0-...' prefix item."""
        entities = [_make_entity("E1", "concept", "d")]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = entities
            result = await list_entities(_make_mcp_ctx())

        # Result must be a list of dicts; no dict should look like a header string
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_pagination_slice_returns_correct_dicts(self) -> None:
        """Pagination offset/limit produces the correct slice of dicts."""
        all_entities = [_make_entity(f"E{i}", "concept", f"desc{i}") for i in range(10)]
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = all_entities
            result = await list_entities(_make_mcp_ctx(), offset=2, limit=3)

        # Expect dicts for E2, E3, E4 only
        assert isinstance(result, list)
        assert len(result) == 3  # type: ignore[arg-type]
        names = [item["name"] for item in result]  # type: ignore[index]
        assert names == ["E2", "E3", "E4"]

    # ------------------------------------------------------------------
    # AC: empty results return [] not a string
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self) -> None:
        """list_entities returns [] (not 'No entities found.') when result set is empty."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = []
            result = await list_entities(_make_mcp_ctx())

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_result_is_list_not_str(self) -> None:
        """Empty result is a list type, confirming no string sentinel is returned."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = []
            result = await list_entities(_make_mcp_ctx())

        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# TestFromAC_GetStatsStructured (#507)
# ---------------------------------------------------------------------------


class TestFromAC_GetStatsStructured:
    """Contract tests: get_stats returns dict[str, int] with documents/entities/edges keys."""

    # ------------------------------------------------------------------
    # AC: returns dict not str
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_returns_dict(self) -> None:
        """get_stats returns a dict (not str)."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (3, 7, 5)
            result = await get_stats(_make_mcp_ctx())

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dict_has_documents_entities_edges_keys(self) -> None:
        """Returned dict has exactly 'documents', 'entities', 'edges' keys."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (1, 2, 3)
            result = await get_stats(_make_mcp_ctx())

        assert isinstance(result, dict)
        assert "documents" in result  # type: ignore[operator]
        assert "entities" in result  # type: ignore[operator]
        assert "edges" in result  # type: ignore[operator]

    @pytest.mark.asyncio
    async def test_dict_values_are_int(self) -> None:
        """All values in the returned dict are int."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (5, 10, 15)
            result = await get_stats(_make_mcp_ctx())

        for key in ("documents", "entities", "edges"):
            assert isinstance(result[key], int), f"{key!r} should be int"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_documents_matches_first_count(self) -> None:
        """'documents' maps to the first value from get_counts()."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (42, 0, 0)
            result = await get_stats(_make_mcp_ctx())

        assert result["documents"] == 42  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_entities_matches_second_count(self) -> None:
        """'entities' maps to the second value from get_counts()."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (0, 77, 0)
            result = await get_stats(_make_mcp_ctx())

        assert result["entities"] == 77  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_edges_matches_third_count(self) -> None:
        """'edges' maps to the third value from get_counts()."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (0, 0, 99)
            result = await get_stats(_make_mcp_ctx())

        assert result["edges"] == 99  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_all_three_values_correct_simultaneously(self) -> None:
        """All three count values are mapped correctly from get_counts() in a single call."""
        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = (11, 22, 33)
            result = await get_stats(_make_mcp_ctx())

        assert result["documents"] == 11  # type: ignore[index]
        assert result["entities"] == 22  # type: ignore[index]
        assert result["edges"] == 33  # type: ignore[index]


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
            patch(
                "owlbear_mcp_knowledge.server.IngestPipeline",
                return_value=mock_pipeline,
            ),
        ):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.ingest_pipeline is not None


# ---------------------------------------------------------------------------
# TestFromAC_ToolDescriptions
# ---------------------------------------------------------------------------

_VERB_FIRST_WORDS: frozenset[str] = frozenset(
    {
        "ingest",
        "list",
        "get",
        "search",
        "add",
        "create",
        "fetch",
        "retrieve",
        "return",
        "show",
        "find",
        "compute",
        "query",
    }
)


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
        first_word = (
            desc.strip().split()[0].lower().rstrip(".,") if desc.strip() else ""
        )
        assert first_word in _VERB_FIRST_WORDS, (
            f"'ingest_document' description should start with a verb, got: {desc!r}"
        )

    def test_get_stats_description_is_verb_first(self) -> None:
        """get_stats tool description opens with an action verb."""
        desc = _get_tool_description("get_stats")
        first_word = (
            desc.strip().split()[0].lower().rstrip(".,") if desc.strip() else ""
        )
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

        with patch(
            "owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_mcp_ctx(), entity_type="concept")

        call_kwargs = mock_t.call_args.kwargs
        assert "entity_type" in call_kwargs, (
            "entity_type kwarg must be forwarded to asyncio.to_thread when entity_type is given"
        )
        assert call_kwargs["entity_type"] == EntityType("concept"), (
            f"Expected EntityType('concept'), got: {call_kwargs['entity_type']!r}"
        )
