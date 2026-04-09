"""Tests for task #541: TypedDict return types for mcp-knowledge outputSchema.

TDD RED phase — tests written against the contract defined in AC, not any
implementation. All tests FAIL in RED (except AC9 guard) because:

- AC1-4: SearchResult/SourceInfo/EntityInfo/StatsResult are not yet defined in
  server.py; getattr returns None, assertion on None fails.
- AC5-8: Function return annotations still reference dict/Any, not TypedDicts;
  string checks for TypedDict names fail.
- AC9: ingest_document stays str — guard test PASSES in RED and GREEN.
- AC11: Tested via typing.is_typeddict() which requires the TypedDict to exist.

AC coverage (with mapping to #544 for schema/fn_metadata aspects):
  - AC1: SearchResult TypedDict at module scope with title:str, score:float, snippet:str
  - AC2: SourceInfo TypedDict at module scope with name:str, source_type:str, scope:str
  - AC3: EntityInfo TypedDict at module scope with name:str, entity_type:str, description:str
  - AC4: StatsResult TypedDict at module scope with documents:int, entities:int, edges:int
  - AC5: search_knowledge return annotation contains 'SearchResult'
  - AC6: list_sources return annotation contains 'SourceInfo'
  - AC7: list_entities return annotation contains 'EntityInfo'
  - AC8: get_stats return annotation contains 'StatsResult'
  - AC9: ingest_document return annotation is 'str' (guard — unchanged)
  - AC11: TypedDicts are genuine TypedDicts (typing.is_typeddict), not just dicts
  - AC12: Runtime outputSchema verification delegated to task #544
           (packages/mcp-knowledge/tests/test_outputschema_541.py).
"""

from __future__ import annotations

import typing

import pytest
from unittest.mock import MagicMock

from mcp.server.fastmcp.exceptions import ToolError

import owlbear_mcp_knowledge.server as server_mod
from owlbear_mcp_knowledge.server import get_stats, list_sources


# ---------------------------------------------------------------------------
# TestFromAC_TypedDictFieldAnnotations
# AC1-4 + AC11 — TypedDicts defined at module scope with correct field types
# ---------------------------------------------------------------------------


class TestFromAC_TypedDictFieldAnnotations:
    """Contract: four TypedDicts defined at module scope with exact field signatures.

    Each TypedDict is checked for:
    1. Existence at module scope (AC11 — not under TYPE_CHECKING)
    2. Is a genuine TypedDict (typing.is_typeddict)
    3. Each required field present with correct Python type
    """

    # -- AC1: SearchResult(title: str, score: float, snippet: str) -----------

    def test_search_result_is_typeddict(self) -> None:
        """SearchResult must be a TypedDict (not just a plain class or dict subclass)."""
        search_result_cls = getattr(server_mod, "SearchResult", None)
        assert search_result_cls is not None, (
            "SearchResult not found at module scope in owlbear_mcp_knowledge.server. "
            "Define it at module scope -- NOT inside 'if TYPE_CHECKING:' block."
        )
        assert typing.is_typeddict(search_result_cls), (
            f"SearchResult must be defined with TypedDict(), got type: {type(search_result_cls)}"
        )

    def test_search_result_title_is_str(self) -> None:
        """SearchResult.title field annotation must be str."""
        search_result_cls = getattr(server_mod, "SearchResult", None)
        assert search_result_cls is not None, "SearchResult not defined at module scope"
        hints = typing.get_type_hints(search_result_cls)
        assert "title" in hints, f"SearchResult missing 'title' field; fields: {list(hints)}"
        assert hints["title"] is str, f"SearchResult.title expected str, got {hints['title']!r}"

    def test_search_result_score_is_float(self) -> None:
        """SearchResult.score field annotation must be float."""
        search_result_cls = getattr(server_mod, "SearchResult", None)
        assert search_result_cls is not None, "SearchResult not defined at module scope"
        hints = typing.get_type_hints(search_result_cls)
        assert "score" in hints, f"SearchResult missing 'score' field; fields: {list(hints)}"
        assert hints["score"] is float, f"SearchResult.score expected float, got {hints['score']!r}"

    def test_search_result_snippet_is_str(self) -> None:
        """SearchResult.snippet field annotation must be str."""
        search_result_cls = getattr(server_mod, "SearchResult", None)
        assert search_result_cls is not None, "SearchResult not defined at module scope"
        hints = typing.get_type_hints(search_result_cls)
        assert "snippet" in hints, f"SearchResult missing 'snippet' field; fields: {list(hints)}"
        assert hints["snippet"] is str, f"SearchResult.snippet expected str, got {hints['snippet']!r}"

    def test_search_result_has_exactly_three_fields(self) -> None:
        """SearchResult must have exactly the fields: title, score, snippet (no extras)."""
        search_result_cls = getattr(server_mod, "SearchResult", None)
        assert search_result_cls is not None, "SearchResult not defined at module scope"
        hints = typing.get_type_hints(search_result_cls)
        assert set(hints) == {"title", "score", "snippet"}, (
            f"SearchResult fields must be exactly {{title, score, snippet}}, got: {set(hints)}"
        )

    # -- AC2: SourceInfo(name: str, source_type: str, scope: str) ------------

    def test_source_info_is_typeddict(self) -> None:
        """SourceInfo must be a TypedDict at module scope."""
        source_info_cls = getattr(server_mod, "SourceInfo", None)
        assert source_info_cls is not None, "SourceInfo not found at module scope in owlbear_mcp_knowledge.server."
        assert typing.is_typeddict(source_info_cls), (
            f"SourceInfo must be defined with TypedDict(), got type: {type(source_info_cls)}"
        )

    def test_source_info_name_is_str(self) -> None:
        """SourceInfo.name field annotation must be str."""
        source_info_cls = getattr(server_mod, "SourceInfo", None)
        assert source_info_cls is not None, "SourceInfo not defined at module scope"
        hints = typing.get_type_hints(source_info_cls)
        assert "name" in hints, f"SourceInfo missing 'name' field; fields: {list(hints)}"
        assert hints["name"] is str, f"SourceInfo.name expected str, got {hints['name']!r}"

    def test_source_info_source_type_is_str(self) -> None:
        """SourceInfo.source_type field annotation must be str."""
        source_info_cls = getattr(server_mod, "SourceInfo", None)
        assert source_info_cls is not None, "SourceInfo not defined at module scope"
        hints = typing.get_type_hints(source_info_cls)
        assert "source_type" in hints, f"SourceInfo missing 'source_type' field; fields: {list(hints)}"
        assert hints["source_type"] is str, f"SourceInfo.source_type expected str, got {hints['source_type']!r}"

    def test_source_info_scope_is_str(self) -> None:
        """SourceInfo.scope field annotation must be str."""
        source_info_cls = getattr(server_mod, "SourceInfo", None)
        assert source_info_cls is not None, "SourceInfo not defined at module scope"
        hints = typing.get_type_hints(source_info_cls)
        assert "scope" in hints, f"SourceInfo missing 'scope' field; fields: {list(hints)}"
        assert hints["scope"] is str, f"SourceInfo.scope expected str, got {hints['scope']!r}"

    # -- AC3: EntityInfo(name: str, entity_type: str, description: str) ------

    def test_entity_info_is_typeddict(self) -> None:
        """EntityInfo must be a TypedDict at module scope."""
        entity_info_cls = getattr(server_mod, "EntityInfo", None)
        assert entity_info_cls is not None, "EntityInfo not found at module scope in owlbear_mcp_knowledge.server."
        assert typing.is_typeddict(entity_info_cls), (
            f"EntityInfo must be defined with TypedDict(), got type: {type(entity_info_cls)}"
        )

    def test_entity_info_name_is_str(self) -> None:
        """EntityInfo.name field annotation must be str."""
        entity_info_cls = getattr(server_mod, "EntityInfo", None)
        assert entity_info_cls is not None, "EntityInfo not defined at module scope"
        hints = typing.get_type_hints(entity_info_cls)
        assert "name" in hints, f"EntityInfo missing 'name' field; fields: {list(hints)}"
        assert hints["name"] is str, f"EntityInfo.name expected str, got {hints['name']!r}"

    def test_entity_info_entity_type_is_str(self) -> None:
        """EntityInfo.entity_type field annotation must be str."""
        entity_info_cls = getattr(server_mod, "EntityInfo", None)
        assert entity_info_cls is not None, "EntityInfo not defined at module scope"
        hints = typing.get_type_hints(entity_info_cls)
        assert "entity_type" in hints, f"EntityInfo missing 'entity_type' field; fields: {list(hints)}"
        assert hints["entity_type"] is str, f"EntityInfo.entity_type expected str, got {hints['entity_type']!r}"

    def test_entity_info_description_is_str(self) -> None:
        """EntityInfo.description field annotation must be str."""
        entity_info_cls = getattr(server_mod, "EntityInfo", None)
        assert entity_info_cls is not None, "EntityInfo not defined at module scope"
        hints = typing.get_type_hints(entity_info_cls)
        assert "description" in hints, f"EntityInfo missing 'description' field; fields: {list(hints)}"
        assert hints["description"] is str, f"EntityInfo.description expected str, got {hints['description']!r}"

    # -- AC4: StatsResult(documents: int, entities: int, edges: int) ---------

    def test_stats_result_is_typeddict(self) -> None:
        """StatsResult must be a TypedDict at module scope."""
        stats_result_cls = getattr(server_mod, "StatsResult", None)
        assert stats_result_cls is not None, "StatsResult not found at module scope in owlbear_mcp_knowledge.server."
        assert typing.is_typeddict(stats_result_cls), (
            f"StatsResult must be defined with TypedDict(), got type: {type(stats_result_cls)}"
        )

    def test_stats_result_documents_is_int(self) -> None:
        """StatsResult.documents field annotation must be int."""
        stats_result_cls = getattr(server_mod, "StatsResult", None)
        assert stats_result_cls is not None, "StatsResult not defined at module scope"
        hints = typing.get_type_hints(stats_result_cls)
        assert "documents" in hints, f"StatsResult missing 'documents' field; fields: {list(hints)}"
        assert hints["documents"] is int, f"StatsResult.documents expected int, got {hints['documents']!r}"

    def test_stats_result_entities_is_int(self) -> None:
        """StatsResult.entities field annotation must be int."""
        stats_result_cls = getattr(server_mod, "StatsResult", None)
        assert stats_result_cls is not None, "StatsResult not defined at module scope"
        hints = typing.get_type_hints(stats_result_cls)
        assert "entities" in hints, f"StatsResult missing 'entities' field; fields: {list(hints)}"
        assert hints["entities"] is int, f"StatsResult.entities expected int, got {hints['entities']!r}"

    def test_stats_result_edges_is_int(self) -> None:
        """StatsResult.edges field annotation must be int."""
        stats_result_cls = getattr(server_mod, "StatsResult", None)
        assert stats_result_cls is not None, "StatsResult not defined at module scope"
        hints = typing.get_type_hints(stats_result_cls)
        assert "edges" in hints, f"StatsResult missing 'edges' field; fields: {list(hints)}"
        assert hints["edges"] is int, f"StatsResult.edges expected int, got {hints['edges']!r}"


# ---------------------------------------------------------------------------
# TestFromAC_FunctionReturnAnnotations
# AC5-9 — Tool function return annotations reference the new TypedDicts
# ---------------------------------------------------------------------------


class TestFromAC_FunctionReturnAnnotations:
    """Contract: tool function return annotations use TypedDicts, not generic dicts.

    With 'from __future__ import annotations' in server.py, annotations are stored
    as raw strings. These tests check the string annotation directly which:
    - FAILS in RED: annotation still says 'list[dict[str, Any]] | str' etc.
    - PASSES in GREEN: annotation says 'list[SearchResult] | str' etc.

    AC9 is a guard test: ingest_document stays str, passes in both RED and GREEN.
    """

    def test_search_knowledge_return_annotation_references_search_result(self) -> None:
        """search_knowledge return annotation must reference 'SearchResult' (AC5)."""
        ann = getattr(server_mod.search_knowledge, "__annotations__", {})
        ret = ann.get("return", "")
        assert "SearchResult" in ret, (
            f"Expected 'SearchResult' in search_knowledge return annotation, got: {ret!r}. "
            "AC5 requires return type list[SearchResult] | str."
        )

    def test_list_sources_return_annotation_references_source_info(self) -> None:
        """list_sources return annotation must reference 'SourceInfo' (AC6)."""
        ann = getattr(server_mod.list_sources, "__annotations__", {})
        ret = ann.get("return", "")
        assert "SourceInfo" in ret, (
            f"Expected 'SourceInfo' in list_sources return annotation, got: {ret!r}. "
            "AC6 requires return type list[SourceInfo]."
        )

    def test_list_entities_return_annotation_references_entity_info(self) -> None:
        """list_entities return annotation must reference 'EntityInfo' (AC7)."""
        ann = getattr(server_mod.list_entities, "__annotations__", {})
        ret = ann.get("return", "")
        assert "EntityInfo" in ret, (
            f"Expected 'EntityInfo' in list_entities return annotation, got: {ret!r}. "
            "AC7 requires return type list[EntityInfo] | str."
        )

    def test_get_stats_return_annotation_references_stats_result(self) -> None:
        """get_stats return annotation must reference 'StatsResult' (AC8)."""
        ann = getattr(server_mod.get_stats, "__annotations__", {})
        ret = ann.get("return", "")
        assert "StatsResult" in ret, (
            f"Expected 'StatsResult' in get_stats return annotation, got: {ret!r}. "
            "AC8 requires return type StatsResult (not dict[str, int] | str)."
        )

    def test_ingest_document_return_annotation_is_str_unchanged(self) -> None:
        """ingest_document return annotation must remain 'str' (AC9 guard test).

        This test PASSES in RED and GREEN — ingest_document is not changed by #541.
        """
        ann = getattr(server_mod.ingest_document, "__annotations__", {})
        ret = ann.get("return", "")
        assert ret == "str", (
            f"ingest_document return annotation expected 'str' (unchanged), got: {ret!r}. "
            "AC9 requires this function's return type to stay as str."
        )


# ---------------------------------------------------------------------------
# Helpers for retry-cycle additions (AC10 + error path tests)
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations for a named tool registered in the mcp server, or None."""
    if hasattr(server_mod.mcp, "_tool_manager"):
        for t in server_mod.mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_ToolAnnotations (retry) — AC10: ingest_document destructiveHint=False
# The original RED phase omitted this test entirely (MISSING in reviewer's AC table).
# ---------------------------------------------------------------------------


class TestFromAC_ToolAnnotations:
    """Contract: ingest_document ToolAnnotations must include destructiveHint=False (AC10).

    NOTE: This test PASSES immediately — the builder already implemented destructiveHint=False.
    It was added in the retry cycle to fill the coverage gap flagged by the reviewer.
    """

    def test_ingest_document_destructive_hint_is_false(self) -> None:
        """ingest_document must be registered with destructiveHint=False (AC10).

        AC10 requires ToolAnnotations(readOnlyHint=False, destructiveHint=False) on
        ingest_document. This was the sole MISSING AC line in the original test suite.
        """
        annotations = _get_tool_annotations("ingest_document")
        assert annotations is not None, (
            "ingest_document has no ToolAnnotations attached; expected "
            "ToolAnnotations(readOnlyHint=False, destructiveHint=False)."
        )
        assert annotations.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for ingest_document, "
            f"got: {annotations.destructiveHint!r}. "
            "AC10: @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)) "
            "must be present."
        )


# ---------------------------------------------------------------------------
# TestFromAC_ErrorPathConventions (retry) — reviewer FAIL reason 2
# list_sources and get_stats return str literals on None-store error paths,
# but their return annotations carry no str union.  Per project convention
# (copilot-instructions.md): typed-return tools must raise ToolError, not
# return error strings.  Same fix was applied to mcp-project task #542.
# ---------------------------------------------------------------------------


class TestFromAC_ErrorPathConventions:
    """Contract: typed-return tools raise ToolError (not return str) on unavailable-service paths.

    - list_sources -> list[SourceInfo]  — no str union: must raise ToolError when store is None
    - get_stats    -> StatsResult       — no str union: must raise ToolError when gs is None

    Both tests FAIL in current state (functions return string literals instead of raising).
    Builder must change 'return "error: ..."' to 'raise ToolError(msg)' at those paths.
    """

    @pytest.mark.asyncio
    async def test_list_sources_raises_tool_error_when_source_store_none(self) -> None:
        """list_sources must raise ToolError when source_store is None.

        Return type is list[SourceInfo] with no str union — returning a string literal
        violates the annotation and suppresses the MCP isError flag.  Per convention,
        this unavailable-service path must raise ToolError.
        """
        ctx = MagicMock()
        ctx.request_context.lifespan_context.source_store = None

        with pytest.raises(ToolError):
            await list_sources(ctx)

    @pytest.mark.asyncio
    async def test_get_stats_raises_tool_error_when_graph_store_none(self) -> None:
        """get_stats must raise ToolError when graph_store is None.

        Return type is StatsResult with no str union — returning
        'error: graph store not available' violates the annotation.  Builder must
        raise ToolError per project convention (same fix as mcp-project #542).
        """
        ctx = MagicMock()
        ctx.request_context.lifespan_context.graph_store = None

        with pytest.raises(ToolError):
            await get_stats(ctx)
