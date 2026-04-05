"""Failing tests for task #617: Expose scope parameters in mcp-knowledge tool signatures.

TDD RED phase -- all tests must FAIL until the builder adds scope parameters to
search_knowledge, ingest_document, and list_entities in server.py.

AC1: search_knowledge accepts optional scopes: list[str] | None, forwarded to query()
AC2: ingest_document accepts optional scope: str = "global", forwarded to ingest_text()
AC3: list_entities accepts optional scopes: list[str] | None, forwarded to list_entities()
AC4: Default behavior preserved (scopes=None, scope="global")
AC5: New tests verify scope parameters are forwarded correctly (this file)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import ingest_document, list_entities, search_knowledge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(
    *,
    query_service: object = None,
    ingest_pipeline: object = None,
    graph_store: object = None,
) -> MagicMock:
    """Return a minimal FastMCP Context mock with app services in lifespan_context."""
    ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.query_service = query_service
    app_ctx.ingest_pipeline = ingest_pipeline
    app_ctx.graph_store = graph_store
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_ingest_result(
    *,
    document_id: str = "doc-abc",
    chunk_count: int = 3,
    entity_count: int = 1,
    edge_count: int = 0,
    status: str = "ok",
) -> MagicMock:
    result = MagicMock()
    result.document_id = document_id
    result.chunk_count = chunk_count
    result.entity_count = entity_count
    result.edge_count = edge_count
    result.status = status
    return result


def _make_entity(
    name: str = "E1",
    entity_type: str = "concept",
    description: str = "desc",
) -> MagicMock:
    ent = MagicMock()
    ent.name = name
    ent.entity_type = entity_type
    ent.description = description
    return ent


def _make_search_result(
    title: str = "T",
    score: float = 0.9,
    snippet: str = "s",
) -> MagicMock:
    r = MagicMock()
    r.title = title
    r.score = score
    r.snippet = snippet
    return r


# ---------------------------------------------------------------------------
# AC1 -- search_knowledge scopes parameter
# ---------------------------------------------------------------------------


class TestFromAC_SearchKnowledgeScopes:
    """Tests for AC1: search_knowledge scopes param forwarded to KnowledgeQueryService.query()."""

    # -- Happy: explicit single scope ----------------------------------------

    @pytest.mark.asyncio
    async def test_scopes_single_value_forwarded_to_query(self) -> None:
        """search_knowledge(scopes=['project-a']) passes scopes=['project-a'] to query()."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[_make_search_result()])
        ctx = _make_ctx(query_service=qs)

        await search_knowledge(ctx, query="test", scopes=["project-a"])

        call_kwargs = qs.query.call_args.kwargs
        assert call_kwargs.get("scopes") == ["project-a"]

    # -- Happy: multiple scopes ---------------------------------------------

    @pytest.mark.asyncio
    async def test_scopes_multiple_values_forwarded_to_query(self) -> None:
        """search_knowledge(scopes=['a', 'b']) forwards both scopes to query()."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(query_service=qs)

        await search_knowledge(ctx, query="q", scopes=["alpha", "beta"])

        call_kwargs = qs.query.call_args.kwargs
        assert call_kwargs.get("scopes") == ["alpha", "beta"]

    # -- AC4: default None preserved ----------------------------------------

    @pytest.mark.asyncio
    async def test_default_scopes_none_forwarded_to_query(self) -> None:
        """search_knowledge() with no scopes arg forwards scopes=None to query()."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(query_service=qs)

        await search_knowledge(ctx, query="q")

        call_kwargs = qs.query.call_args.kwargs
        # scopes=None must be explicitly forwarded, not merely absent
        assert "scopes" in call_kwargs
        assert call_kwargs["scopes"] is None

    # -- Explicit None round-trips ------------------------------------------

    @pytest.mark.asyncio
    async def test_explicit_none_scopes_forwarded_to_query(self) -> None:
        """search_knowledge(scopes=None) forwards None to query()."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(query_service=qs)

        await search_knowledge(ctx, query="q", scopes=None)

        call_kwargs = qs.query.call_args.kwargs
        assert call_kwargs.get("scopes") is None

    # -- Edge: empty list --------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_scopes_list_forwarded_to_query(self) -> None:
        """search_knowledge(scopes=[]) forwards empty list [] to query()."""
        qs = AsyncMock()
        qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(query_service=qs)

        await search_knowledge(ctx, query="q", scopes=[])

        call_kwargs = qs.query.call_args.kwargs
        assert call_kwargs.get("scopes") == []

    # -- AC5: result format unaffected by scope ----------------------------

    @pytest.mark.asyncio
    async def test_scoped_search_returns_correct_result_format(self) -> None:
        """search_knowledge with scopes returns list of SearchResult dicts."""
        qs = AsyncMock()
        qs.query = AsyncMock(
            return_value=[_make_search_result(title="Doc A", score=0.88, snippet="relevant")]
        )
        ctx = _make_ctx(query_service=qs)

        result = await search_knowledge(ctx, query="q", scopes=["work"])

        assert isinstance(result, list)
        assert result[0]["title"] == "Doc A"
        assert result[0]["score"] == 0.88


# ---------------------------------------------------------------------------
# AC2 -- ingest_document scope parameter
# ---------------------------------------------------------------------------


class TestFromAC_IngestDocumentScope:
    """Tests for AC2: ingest_document scope param forwarded to IngestPipeline.ingest_text()."""

    # -- Happy: explicit custom scope ----------------------------------------

    @pytest.mark.asyncio
    async def test_explicit_scope_forwarded_to_ingest_text(self) -> None:
        """ingest_document(scope='work') passes scope='work' to ingest_text()."""
        pipeline = AsyncMock()
        pipeline.ingest_text = AsyncMock(return_value=_make_ingest_result())
        ctx = _make_ctx(ingest_pipeline=pipeline)

        await ingest_document(ctx, text="content", scope="work")

        call_kwargs = pipeline.ingest_text.call_args.kwargs
        assert call_kwargs.get("scope") == "work"

    # -- Happy: project-specific scope string --------------------------------

    @pytest.mark.asyncio
    async def test_project_scope_forwarded_to_ingest_text(self) -> None:
        """ingest_document(scope='project-123') forwards that scope value."""
        pipeline = AsyncMock()
        pipeline.ingest_text = AsyncMock(return_value=_make_ingest_result())
        ctx = _make_ctx(ingest_pipeline=pipeline)

        await ingest_document(ctx, text="doc", scope="project-123")

        call_kwargs = pipeline.ingest_text.call_args.kwargs
        assert call_kwargs.get("scope") == "project-123"

    # -- AC4: default "global" when not provided ----------------------------

    @pytest.mark.asyncio
    async def test_default_scope_global_forwarded_to_ingest_text(self) -> None:
        """ingest_document() with no scope arg forwards scope='global' to ingest_text()."""
        pipeline = AsyncMock()
        pipeline.ingest_text = AsyncMock(return_value=_make_ingest_result())
        ctx = _make_ctx(ingest_pipeline=pipeline)

        await ingest_document(ctx, text="text")

        call_kwargs = pipeline.ingest_text.call_args.kwargs
        assert call_kwargs.get("scope") == "global"

    # -- AC4: explicit "global" round-trips ----------------------------------

    @pytest.mark.asyncio
    async def test_explicit_global_scope_forwarded_to_ingest_text(self) -> None:
        """ingest_document(scope='global') forwards 'global' to ingest_text()."""
        pipeline = AsyncMock()
        pipeline.ingest_text = AsyncMock(return_value=_make_ingest_result())
        ctx = _make_ctx(ingest_pipeline=pipeline)

        await ingest_document(ctx, text="text", scope="global")

        call_kwargs = pipeline.ingest_text.call_args.kwargs
        assert call_kwargs.get("scope") == "global"

    # -- AC5: output format unaffected by scope ----------------------------

    @pytest.mark.asyncio
    async def test_scope_does_not_affect_ingested_success_format(self) -> None:
        """Return value still starts with 'Ingested:' when scope is specified."""
        pipeline = AsyncMock()
        pipeline.ingest_text = AsyncMock(return_value=_make_ingest_result(document_id="doc-xyz"))
        ctx = _make_ctx(ingest_pipeline=pipeline)

        result = await ingest_document(ctx, text="text", scope="shared")

        assert isinstance(result, str)
        assert "Ingested" in result
        assert "doc-xyz" in result


# ---------------------------------------------------------------------------
# AC3 -- list_entities scopes parameter
# ---------------------------------------------------------------------------


class TestFromAC_ListEntitiesScopes:
    """Tests for AC3: list_entities scopes param forwarded to GraphStore.list_entities()."""

    # -- Happy: single scope forwarded via asyncio.to_thread ----------------

    @pytest.mark.asyncio
    async def test_scopes_single_value_forwarded_via_to_thread(self) -> None:
        """list_entities(scopes=['work']) includes scopes=['work'] in the to_thread call."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_ctx(), scopes=["work"])

        call_kwargs = mock_t.call_args.kwargs
        assert call_kwargs.get("scopes") == ["work"]

    # -- Happy: multiple scopes forwarded ------------------------------------

    @pytest.mark.asyncio
    async def test_scopes_multiple_values_forwarded_via_to_thread(self) -> None:
        """list_entities(scopes=['a', 'b']) forwards both scopes via asyncio.to_thread."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_ctx(), scopes=["scope-a", "scope-b"])

        call_kwargs = mock_t.call_args.kwargs
        assert call_kwargs.get("scopes") == ["scope-a", "scope-b"]

    # -- AC4: default None forwarded ----------------------------------------

    @pytest.mark.asyncio
    async def test_default_scopes_none_forwarded_via_to_thread(self) -> None:
        """list_entities() with no scopes arg forwards scopes=None via asyncio.to_thread."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_ctx())

        call_kwargs = mock_t.call_args.kwargs
        assert call_kwargs.get("scopes") is None

    # -- AC4: explicit None forwarded ----------------------------------------

    @pytest.mark.asyncio
    async def test_explicit_none_scopes_forwarded_via_to_thread(self) -> None:
        """list_entities(scopes=None) forwards None via asyncio.to_thread."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_ctx(), scopes=None)

        call_kwargs = mock_t.call_args.kwargs
        assert call_kwargs.get("scopes") is None

    # -- Edge: empty list distinct from None --------------------------------

    @pytest.mark.asyncio
    async def test_empty_scopes_list_forwarded_via_to_thread(self) -> None:
        """list_entities(scopes=[]) forwards [] (empty list is distinct from None)."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_ctx(), scopes=[])

        call_kwargs = mock_t.call_args.kwargs
        assert call_kwargs.get("scopes") == []

    # -- Scopes alongside entity_type filter --------------------------------

    @pytest.mark.asyncio
    async def test_scopes_and_entity_type_both_forwarded(self) -> None:
        """list_entities(entity_type='concept', scopes=['work']) forwards both filters."""
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = []
            await list_entities(_make_ctx(), entity_type="concept", scopes=["work"])

        call_kwargs = mock_t.call_args.kwargs
        assert call_kwargs.get("scopes") == ["work"]

    # -- AC5: result format unaffected by scope ----------------------------

    @pytest.mark.asyncio
    async def test_scoped_list_returns_entity_dicts(self) -> None:
        """list_entities with scopes still returns list of EntityInfo dicts."""
        entities = [_make_entity("ScopedEntity", "concept", "A scoped entity")]
        with patch("owlbear_mcp_knowledge.server.asyncio.to_thread", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = entities
            result = await list_entities(_make_ctx(), scopes=["project-x"])

        assert isinstance(result, list)
        assert result[0]["name"] == "ScopedEntity"
        assert result[0]["entity_type"] == "concept"
