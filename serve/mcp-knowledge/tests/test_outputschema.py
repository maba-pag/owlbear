"""Tests for task #544: TypedDict return types for mcp-knowledge outputSchema.

TDD RED phase -- all tests FAIL before builder implements TypedDicts in task #541.

AC coverage:
  - AC1: search_knowledge fn_metadata.output_schema has SearchResult in $defs
         with title(str), score(float), snippet(str)
  - AC2: list_sources fn_metadata.output_schema has SourceInfo in $defs
         with name(str), source_type(str), scope(str)
  - AC3: list_entities fn_metadata.output_schema has EntityInfo in $defs
         with name(str), entity_type(str), description(str)
  - AC4: get_stats fn_metadata.output_schema has top-level properties
         documents(int), entities(int), edges(int) -- unwrapped (no result wrapper)
  - AC5: ingest_document fn_metadata.output_schema unchanged (string type)
  - AC6: ingest_document ToolAnnotations includes destructiveHint=False
  - AC7: SearchResult, SourceInfo, EntityInfo, StatsResult importable from
         owlbear_mcp_knowledge.server at module scope (not wrapped in TYPE_CHECKING)

Note: FastMCP wraps all function outputs in {result: <actual_schema>} objects.
AC4/AC5 tests check schema["properties"]["result"] for the inner schema.

Tests FAIL in RED phase because:
  - AC1-3: list-returning tools have no $defs (return list[dict[str, Any]] | str,
    not TypedDict-based); no SearchResult/SourceInfo/EntityInfo in $defs.
  - AC4: get_stats returns dict[str, int] | str which produces anyOf in result with
    no inline 'properties' key; document/entities/edges not found.
  - AC5: Guard test -- passes in both RED and GREEN (ingest_document stays str).
  - AC6: ingest_document ToolAnnotations(readOnlyHint=False) has no explicit
    destructiveHint, so destructiveHint is None, not False.
  - AC7: SearchResult/SourceInfo/EntityInfo/StatsResult not yet defined in server.py.
"""

from __future__ import annotations

from owlbear_mcp_knowledge.server import mcp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_output_schema(tool_name: str) -> dict | None:
    """Return fn_metadata.output_schema for the named tool, or None if not found.

    Uses mcp._tool_manager._tools to access the FastMCP-internal Tool object
    (which carries fn_metadata), matching the access pattern in mcp-kanban.
    """
    if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):  # noqa: SLF001
        for t in mcp._tool_manager._tools.values():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(getattr(t, "fn_metadata", None), "output_schema", None)
    return None


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations for the named tool, or None if not found."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_ListToolOutputSchemas
# AC1, AC2, AC3 -- list-returning tools produce wrapped array schemas with $defs
# ---------------------------------------------------------------------------


class TestFromAC_ListToolOutputSchemas:
    """Contract tests: list-returning tools must expose TypedDict shapes in $defs."""

    # -- AC1: search_knowledge / SearchResult ---------------------------------

    def test_search_knowledge_output_schema_has_defs_with_search_result(self) -> None:
        """search_knowledge output_schema must have SearchResult in $defs."""
        schema = _get_output_schema("search_knowledge")
        assert schema is not None, "search_knowledge tool or fn_metadata not found"
        assert "$defs" in schema, (
            "output_schema for search_knowledge missing '$defs'; expected TypedDict SearchResult to be defined there"
        )
        assert "SearchResult" in schema["$defs"], (
            f"'SearchResult' not found in $defs; available keys: {list(schema['$defs'])}"
        )

    def test_search_knowledge_search_result_has_title_field(self) -> None:
        """SearchResult in $defs must have a 'title' property of type string."""
        schema = _get_output_schema("search_knowledge")
        assert schema is not None
        props = schema.get("$defs", {}).get("SearchResult", {}).get("properties", {})
        assert "title" in props, "SearchResult missing 'title' property"
        assert props["title"].get("type") == "string", (
            f"SearchResult.title type expected 'string', got: {props['title'].get('type')!r}"
        )

    def test_search_knowledge_search_result_has_score_field(self) -> None:
        """SearchResult in $defs must have a 'score' property of type number."""
        schema = _get_output_schema("search_knowledge")
        assert schema is not None
        props = schema.get("$defs", {}).get("SearchResult", {}).get("properties", {})
        assert "score" in props, "SearchResult missing 'score' property"
        assert props["score"].get("type") == "number", (
            f"SearchResult.score type expected 'number', got: {props['score'].get('type')!r}"
        )

    def test_search_knowledge_search_result_has_snippet_field(self) -> None:
        """SearchResult in $defs must have a 'snippet' property of type string."""
        schema = _get_output_schema("search_knowledge")
        assert schema is not None
        props = schema.get("$defs", {}).get("SearchResult", {}).get("properties", {})
        assert "snippet" in props, "SearchResult missing 'snippet' property"
        assert props["snippet"].get("type") == "string", (
            f"SearchResult.snippet type expected 'string', got: {props['snippet'].get('type')!r}"
        )

    def test_search_knowledge_search_result_has_graph_context_field(self) -> None:
        """SearchResult in $defs must have a 'graph_context' property of type string."""
        schema = _get_output_schema("search_knowledge")
        assert schema is not None
        props = schema.get("$defs", {}).get("SearchResult", {}).get("properties", {})
        assert "graph_context" in props, "SearchResult missing 'graph_context' property"
        assert props["graph_context"].get("type") == "string", (
            f"SearchResult.graph_context type expected 'string', got: {props['graph_context'].get('type')!r}"
        )

    # -- AC2: list_sources / SourceInfo ---------------------------------------

    def test_list_sources_output_schema_has_defs_with_source_info(self) -> None:
        """list_sources output_schema must have SourceInfo in $defs."""
        schema = _get_output_schema("list_sources")
        assert schema is not None, "list_sources tool or fn_metadata not found"
        assert "$defs" in schema, (
            "output_schema for list_sources missing '$defs'; expected TypedDict SourceInfo to be defined there"
        )
        assert "SourceInfo" in schema["$defs"], (
            f"'SourceInfo' not found in $defs; available keys: {list(schema['$defs'])}"
        )

    def test_list_sources_source_info_has_name_field(self) -> None:
        """SourceInfo in $defs must have a 'name' property of type string."""
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "name" in props, "SourceInfo missing 'name' property"
        assert props["name"].get("type") == "string", (
            f"SourceInfo.name type expected 'string', got: {props['name'].get('type')!r}"
        )

    def test_list_sources_source_info_has_source_type_field(self) -> None:
        """SourceInfo in $defs must have a 'source_type' property of type string."""
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "source_type" in props, "SourceInfo missing 'source_type' property"
        assert props["source_type"].get("type") == "string", (
            f"SourceInfo.source_type type expected 'string', got: {props['source_type'].get('type')!r}"
        )

    def test_list_sources_source_info_has_scope_field(self) -> None:
        """SourceInfo in $defs must have a 'scope' property of type string."""
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "scope" in props, "SourceInfo missing 'scope' property"
        assert props["scope"].get("type") == "string", (
            f"SourceInfo.scope type expected 'string', got: {props['scope'].get('type')!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_StatsOutputSchema
# AC4 -- get_stats produces unwrapped TypedDict schema (top-level properties)
# ---------------------------------------------------------------------------


class TestFromAC_StatsOutputSchema:
    """Contract tests: get_stats exposes StatsResult as a top-level object schema."""

    def test_get_stats_result_schema_has_inline_properties(self) -> None:
        """get_stats schema must have top-level inline 'properties'."""
        schema = _get_output_schema("get_stats")
        assert schema is not None, "get_stats tool or fn_metadata not found"
        assert "properties" in schema, f"get_stats schema missing top-level 'properties'; Current schema: {schema}"

    def test_get_stats_result_has_documents_property(self) -> None:
        """get_stats schema must have a 'documents' property of type integer."""
        schema = _get_output_schema("get_stats")
        assert schema is not None
        props = schema.get("properties", {})
        assert "documents" in props, "get_stats schema missing 'documents' property"
        assert props["documents"].get("type") == "integer", (
            f"get_stats.documents type expected 'integer', got: {props['documents'].get('type')!r}"
        )

    def test_get_stats_result_has_entities_property(self) -> None:
        """get_stats schema must have an 'entities' property of type integer."""
        schema = _get_output_schema("get_stats")
        assert schema is not None
        props = schema.get("properties", {})
        assert "entities" in props, "get_stats schema missing 'entities' property"
        assert props["entities"].get("type") == "integer", (
            f"get_stats.entities type expected 'integer', got: {props['entities'].get('type')!r}"
        )

    def test_get_stats_result_has_edges_property(self) -> None:
        """get_stats schema must have an 'edges' property of type integer."""
        schema = _get_output_schema("get_stats")
        assert schema is not None
        props = schema.get("properties", {})
        assert "edges" in props, "get_stats schema missing 'edges' property"
        assert props["edges"].get("type") == "integer", (
            f"get_stats.edges type expected 'integer', got: {props['edges'].get('type')!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_IngestDocumentSchema
# AC5 -- ingest_document output_schema unchanged (guard test: must stay string type)
# ---------------------------------------------------------------------------


class TestFromAC_IngestDocumentSchema:
    """Guard test: ingest_document output_schema must remain a string type after #541.

    FastMCP wraps function output in {result: <actual_schema>}. The result schema
    for ingest_document (returns str) must remain type=string unchanged.
    """

    def test_ingest_document_result_schema_is_string_type(self) -> None:
        """ingest_document result schema must be type=string (unchanged by TypedDict refactor)."""
        schema = _get_output_schema("ingest_document")
        assert schema is not None, "ingest_document tool or fn_metadata not found"
        result_schema = schema.get("properties", {}).get("result", {})
        assert result_schema.get("type") == "string", (
            f"ingest_document result schema expected type=string, got: {result_schema.get('type')!r}. "
            "AC5 requires this schema to remain unchanged."
        )


# ---------------------------------------------------------------------------
# TestFromAC_IngestDocumentAnnotations
# AC6 -- ingest_document ToolAnnotations.destructiveHint must be False
# ---------------------------------------------------------------------------


class TestFromAC_IngestDocumentAnnotations:
    """Contract tests: ingest_document must declare destructiveHint=False explicitly."""

    def test_ingest_document_destructive_hint_is_false(self) -> None:
        """ingest_document ToolAnnotations must have destructiveHint=False (not None)."""
        annotations = _get_tool_annotations("ingest_document")
        assert annotations is not None, (
            "ingest_document has no ToolAnnotations object; readOnlyHint=False and destructiveHint=False must be set"
        )
        assert annotations.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for ingest_document, "
            f"got: {annotations.destructiveHint!r}. "  # type: ignore[union-attr]
            "Must be explicitly set to False, not left as None (the default)."
        )


# ---------------------------------------------------------------------------
# TestFromAC_TypeDictModuleScope
# AC7 -- TypedDict classes importable from owlbear_mcp_knowledge.server at runtime
# ---------------------------------------------------------------------------


class TestFromAC_TypeDictModuleScope:
    """Contract tests: TypedDict classes must be defined at module scope in server.py."""

    def test_search_result_importable_from_server(self) -> None:
        """SearchResult must be importable from owlbear_mcp_knowledge.server at module scope."""
        import owlbear_mcp_knowledge.server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "SearchResult"), (
            "SearchResult not found in owlbear_mcp_knowledge.server. "
            "Define it at module scope (not inside TYPE_CHECKING)."
        )

    def test_source_info_importable_from_server(self) -> None:
        """SourceInfo must be importable from owlbear_mcp_knowledge.server at module scope."""
        import owlbear_mcp_knowledge.server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "SourceInfo"), (
            "SourceInfo not found in owlbear_mcp_knowledge.server. "
            "Define it at module scope (not inside TYPE_CHECKING)."
        )

    def test_entity_info_importable_from_server(self) -> None:
        """EntityInfo must be importable from owlbear_mcp_knowledge.server at module scope."""
        import owlbear_mcp_knowledge.server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "EntityInfo"), (
            "EntityInfo not found in owlbear_mcp_knowledge.server. "
            "Define it at module scope (not inside TYPE_CHECKING)."
        )

    def test_stats_result_importable_from_server(self) -> None:
        """StatsResult must be importable from owlbear_mcp_knowledge.server at module scope."""
        import owlbear_mcp_knowledge.server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "StatsResult"), (
            "StatsResult not found in owlbear_mcp_knowledge.server. "
            "Define it at module scope (not inside TYPE_CHECKING)."
        )
