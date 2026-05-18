"""Tests for search_knowledge provenance contract (#1331).

TDD RED phase — all tests must fail until search_knowledge serializes provenance
fields (retrieval_path, entities, related_sources, source) into response dicts.

Test layer: MCP tool level.  query_service.query() is mocked with MagicMock/
AsyncMock objects that carry provenance attributes; tests assert the MCP tool
serializes those attributes into the returned dict.

AC coverage:
- retrieval_path field with enum values: "vector", "graph", "vector+graph"
- entities array of {name, type} objects
- related_sources array of {name, relationship, entity} objects
- unenriched defaults: entities=[], related_sources=[], retrieval_path="vector",
  source always populated
- all provenance keys present in every result regardless of enrichment state
- source field is object with name (str) and url (str) keys
"""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_mcp_knowledge.server import search_knowledge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(query_service: object = None) -> MagicMock:
    """Return a minimal FastMCP Context mock whose lifespan_context has query_service."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = MagicMock(query_service=query_service)
    return ctx


def _make_source(name: str = "MySource", url: str = "https://example.com") -> MagicMock:
    """Return a mock source object with name and url attributes."""
    source = MagicMock()
    source.name = name
    source.url = url
    return source


def _make_enriched_result(  # noqa: PLR0913
    title: str = "doc",
    score: float = 0.85,
    snippet: str = "snippet text",
    retrieval_path: str = "vector+graph",
    graph_context: str = "Alpha --[related_to]--> Beta: graph detail",
    entities: list | None = None,
    related_sources: list | None = None,
    source: object | None = None,
) -> MagicMock:
    """Return a mock result with all provenance attributes set (enriched state)."""
    r = MagicMock()
    r.title = title
    r.score = score
    r.snippet = snippet
    r.entity_type = "concept"
    r.retrieval_path = retrieval_path
    r.graph_context = graph_context
    r.entities = entities if entities is not None else [{"name": "Python", "type": "technology"}]
    r.related_sources = (
        related_sources
        if related_sources is not None
        else [{"name": "related-doc", "relationship": "cites", "entity": "Python"}]
    )
    r.source = source if source is not None else _make_source()
    return r


def _make_unenriched_result(
    title: str = "doc",
    score: float = 0.85,
    snippet: str = "snippet text",
    source: object | None = None,
) -> MagicMock:
    """Return a mock result in unenriched state (empty provenance, vector path)."""
    r = MagicMock()
    r.title = title
    r.score = score
    r.snippet = snippet
    r.entity_type = "concept"
    r.retrieval_path = "vector"
    r.graph_context = ""
    r.entities = []
    r.related_sources = []
    r.source = source if source is not None else _make_source()
    return r


# ---------------------------------------------------------------------------
# Class 1: Field presence and enum values
# ---------------------------------------------------------------------------


class TestFromAC_SearchProvenanceFields:
    """Provenance field presence and valid enum values in search_knowledge response."""

    # ------------------------------------------------------------------
    # AC: retrieval_path field with valid enum values
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_retrieval_path_key_present_in_result(self) -> None:
        """search_knowledge result dict includes 'retrieval_path' key."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(retrieval_path="vector")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, list)
        assert "retrieval_path" in result[0]

    @pytest.mark.asyncio
    async def test_retrieval_path_value_is_vector(self) -> None:
        """retrieval_path serialized as 'vector' when mock result has retrieval_path='vector'."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(retrieval_path="vector")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["retrieval_path"] == "vector"

    @pytest.mark.asyncio
    async def test_retrieval_path_value_is_graph(self) -> None:
        """retrieval_path serialized as 'graph' when mock result has retrieval_path='graph'."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(retrieval_path="graph")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["retrieval_path"] == "graph"

    @pytest.mark.asyncio
    async def test_retrieval_path_value_is_vector_plus_graph(self) -> None:
        """retrieval_path serialized as 'vector+graph' when mock has retrieval_path='vector+graph'."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(retrieval_path="vector+graph")])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["retrieval_path"] == "vector+graph"

    @pytest.mark.asyncio
    async def test_graph_context_key_present_in_result(self) -> None:
        """search_knowledge result dict includes 'graph_context' key."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert "graph_context" in result[0]

    @pytest.mark.asyncio
    async def test_graph_context_value_serialized(self) -> None:
        """graph_context serialized from the query-service result."""
        graph_context = "Alpha --[depends_on]--> Beta: neighbor detail"
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(graph_context=graph_context)])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["graph_context"] == graph_context

    # ------------------------------------------------------------------
    # AC: entities array of {name, type} objects
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_entities_key_present_and_is_list(self) -> None:
        """search_knowledge result dict includes 'entities' key that is a list."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(entities=[{"name": "Python", "type": "technology"}])])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert "entities" in result[0]
        assert isinstance(result[0]["entities"], list)

    @pytest.mark.asyncio
    async def test_entities_items_have_name_and_type_keys(self) -> None:
        """Each item in 'entities' list has 'name' and 'type' keys."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[
                _make_enriched_result(
                    entities=[
                        {"name": "Python", "type": "technology"},
                        {"name": "FastAPI", "type": "framework"},
                    ]
                )
            ]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        entities = result[0]["entities"]
        assert len(entities) == 2
        for entity in entities:
            assert "name" in entity
            assert "type" in entity

    # ------------------------------------------------------------------
    # AC: related_sources array of {name, relationship, entity} objects
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_related_sources_key_present_and_is_list(self) -> None:
        """search_knowledge result dict includes 'related_sources' key that is a list."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[
                _make_enriched_result(
                    related_sources=[
                        {
                            "name": "other-doc",
                            "relationship": "cites",
                            "entity": "Python",
                        }
                    ]
                )
            ]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert "related_sources" in result[0]
        assert isinstance(result[0]["related_sources"], list)

    @pytest.mark.asyncio
    async def test_related_sources_items_have_required_keys(self) -> None:
        """Each item in 'related_sources' has 'name', 'relationship', and 'entity' keys."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[
                _make_enriched_result(
                    related_sources=[
                        {
                            "name": "doc-b",
                            "relationship": "references",
                            "entity": "API",
                        },
                        {"name": "doc-c", "relationship": "cites", "entity": "REST"},
                    ]
                )
            ]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        related = result[0]["related_sources"]
        assert len(related) == 2
        for rel in related:
            assert "name" in rel
            assert "relationship" in rel
            assert "entity" in rel


# ---------------------------------------------------------------------------
# Class 2: Unenriched state defaults
# ---------------------------------------------------------------------------


class TestFromAC_SearchProvenanceUnenrichedState:
    """Provenance field defaults when enrichment has not been run."""

    # ------------------------------------------------------------------
    # AC: entities=[] when unenriched
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_unenriched_entities_is_empty_list(self) -> None:
        """'entities' is an empty list (not absent) when enrichment has not been run."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_unenriched_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert "entities" in result[0]
        assert result[0]["entities"] == []

    # ------------------------------------------------------------------
    # AC: related_sources=[] when unenriched
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_unenriched_related_sources_is_empty_list(self) -> None:
        """'related_sources' is an empty list (not absent) when enrichment has not been run."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_unenriched_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert "related_sources" in result[0]
        assert result[0]["related_sources"] == []

    # ------------------------------------------------------------------
    # AC: retrieval_path defaults to "vector" when unenriched
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_unenriched_retrieval_path_defaults_to_vector(self) -> None:
        """'retrieval_path' is 'vector' in the response when enrichment has not been run."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_unenriched_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["retrieval_path"] == "vector"

    # ------------------------------------------------------------------
    # AC: source is always populated
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_source_always_present_in_unenriched_result(self) -> None:
        """'source' key is present in result dict even when entities/related_sources are empty."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_unenriched_result(source=_make_source("KB", "https://kb.local"))])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert "source" in result[0]
        assert result[0]["source"] is not None


# ---------------------------------------------------------------------------
# Class 3: Determinism — all keys present regardless of enrichment state
# ---------------------------------------------------------------------------


class TestFromAC_SearchProvenanceDeterminism:
    """All provenance keys present in every result dict regardless of enrichment state."""

    _PROVENANCE_KEYS: ClassVar[set[str]] = {
        "retrieval_path",
        "graph_context",
        "entities",
        "related_sources",
        "source",
    }

    # ------------------------------------------------------------------
    # AC: all provenance keys present when enriched
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_all_provenance_keys_present_in_enriched_result(self) -> None:
        """All four provenance keys are present in a result dict from an enriched document."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        for key in self._PROVENANCE_KEYS:
            assert key in result[0], f"missing provenance key '{key}' in enriched result"

    # ------------------------------------------------------------------
    # AC: all provenance keys present when unenriched
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_all_provenance_keys_present_in_unenriched_result(self) -> None:
        """All four provenance keys are present in a result dict from an unenriched document."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_unenriched_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        for key in self._PROVENANCE_KEYS:
            assert key in result[0], f"missing provenance key '{key}' in unenriched result"

    @pytest.mark.asyncio
    async def test_entities_empty_not_absent_in_unenriched_result(self) -> None:
        """'entities' key is present and equals [] — not missing — in unenriched result."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_unenriched_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0].get("entities") == []

    @pytest.mark.asyncio
    async def test_related_sources_empty_not_absent_in_unenriched_result(self) -> None:
        """'related_sources' key is present and equals [] — not missing — in unenriched result."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_unenriched_result()])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0].get("related_sources") == []

    # ------------------------------------------------------------------
    # AC: source field is object with name (str) and url (str) keys
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_source_field_is_dict_with_name_and_url(self) -> None:
        """'source' in result dict is a dict with 'name' and 'url' keys."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[_make_enriched_result(source=_make_source("KnowledgeBase", "https://kb.example.com"))]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        source = result[0]["source"]
        assert isinstance(source, dict)
        assert "name" in source
        assert "url" in source

    @pytest.mark.asyncio
    async def test_source_name_value_is_str(self) -> None:
        """source['name'] in result dict is a str."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(source=_make_source("MySource", "https://x.com"))])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert isinstance(result[0]["source"]["name"], str)

    @pytest.mark.asyncio
    async def test_source_url_value_is_str(self) -> None:
        """source['url'] in result dict is a str."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(source=_make_source("S", "https://s.com"))])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert isinstance(result[0]["source"]["url"], str)

    @pytest.mark.asyncio
    async def test_source_name_matches_mock_value(self) -> None:
        """source['name'] in result dict matches the name from the mock result object."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(source=_make_source("Exact-Name", "https://x.com"))])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["source"]["name"] == "Exact-Name"

    @pytest.mark.asyncio
    async def test_source_url_matches_mock_value(self) -> None:
        """source['url'] in result dict matches the url from the mock result object."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[_make_enriched_result(source=_make_source("S", "https://exact-url.example.com"))]
        )
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["source"]["url"] == "https://exact-url.example.com"


# ---------------------------------------------------------------------------
# Class 4: AC8 — MCP-boundary source URL proof with real KnowledgeSource
# ---------------------------------------------------------------------------


def _real_ks_source(
    name: str = "RealSource",
    url: str = "https://real.example.com/",
    source_id: str = "src-real",
) -> KnowledgeSource:
    """Return a real KnowledgeSource with config['url'] set (no bare .url attr)."""
    return KnowledgeSource(
        id=source_id,
        name=name,
        source_type=SourceType.URL_LIST,
        config={"url": url},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


class TestFromAC_MCPBoundarySourceProof:
    """AC8: MCP serializer resolves URL from real KnowledgeSource.config['url'], not bare .url."""

    @pytest.mark.asyncio
    async def test_source_url_serialized_from_config_dict_not_bare_attr(self) -> None:
        """search_knowledge serializes URL from config['url'] for a real KnowledgeSource."""
        real_ks = _real_ks_source(name="RealSource", url="https://config-dict.example.com/")

        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(source=real_ks)])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["source"]["url"] == "https://config-dict.example.com/"

    @pytest.mark.asyncio
    async def test_source_name_serialized_from_real_knowledge_source(self) -> None:
        """search_knowledge serializes name from real KnowledgeSource.name attribute."""
        real_ks = _real_ks_source(name="RealSourceName", url="https://example.com/")

        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_enriched_result(source=real_ks)])
        ctx = _make_ctx(qs)

        result = await search_knowledge(ctx, query="test")

        assert result[0]["source"]["name"] == "RealSourceName"
