"""Failing tests for task #1881 — MCP knowledge read tools wired to protocol implementations.

Source file under test:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py

AC coverage:
  AC1 — SqliteGraphStore + QueryFacade added to AppContext and instantiated in lifespan;
         SqliteGraphStore.ensure_tables() called at startup; legacy graph_store retained
  AC2 — search_knowledge delegates to QueryFacade.search(QueryRequest(text, top_k, scopes));
         response mapped to existing SearchResult TypedDict via serialization helpers
  AC3 — list_sources delegates to SqliteSourceStore.list_sources(scope=scope); mapped to
         SourceInfo TypedDict; state parameter NOT exposed as MCP param (deferred)
  AC4 — knowledge_entity_lookup tool registered; params: entity_id/entity_name/entity_type/
         expand_hops=1; delegates to QueryFacade.lookup_entity(EntityLookupRequest); returns
         serialized entity + neighbourhood
  AC5 — get_stats delegates to IngestCoordinator.stats() for base counts
         (sources_total, documents_total, chunks_total, graph_entities, graph_edges);
         enrichment detail fields from EnrichmentStore.stats(); consolidation_candidates_remaining
         from existing SQL; StatsResult TypedDict shape preserved
  AC6 — Error handling: ValueError → ToolError, LookupError → ToolError,
         ValidationError → ToolError; no raw exception strings in MCP responses
"""

from __future__ import annotations

import inspect
import os
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.protocols.enrichment import EnrichmentStats
from owlbear_knowledge.protocols.ingest import IngestStats
from owlbear_knowledge.protocols.query import EntityLookupRequest, QueryRequest
from owlbear_knowledge.query_facade import QueryFacade
from owlbear_knowledge.stores.graph import SqliteGraphStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(  # noqa: PLR0912, PLR0913, C901
    *,
    query_facade: object = "auto",
    query_service: object = None,
    source_store_v2: object = "auto",
    source_store: object = None,
    ingest_coordinator: object = "auto",
    enrichment_store: object = "auto",
    graph_store: object = "sentinel",
    conn: object = "auto",
) -> MagicMock:
    """Build a mock MCP request context with configurable AppContext fields."""
    app_ctx = MagicMock()
    app_ctx.query_service = query_service
    app_ctx.source_store = source_store

    if graph_store == "sentinel":
        gs = MagicMock()
        gs.get_counts.return_value = (0, 0, 0)
        app_ctx.graph_store = gs
    else:
        app_ctx.graph_store = graph_store

    if query_facade is None:
        app_ctx.query_facade = None
    elif query_facade == "auto":
        app_ctx.query_facade = MagicMock(spec=QueryFacade)
    else:
        app_ctx.query_facade = query_facade

    if source_store_v2 is None:
        app_ctx.source_store_v2 = None
    elif source_store_v2 == "auto":
        app_ctx.source_store_v2 = MagicMock()
    else:
        app_ctx.source_store_v2 = source_store_v2

    if ingest_coordinator is None:
        app_ctx.ingest_coordinator = None
    elif ingest_coordinator == "auto":
        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats()
        app_ctx.ingest_coordinator = coordinator
    else:
        app_ctx.ingest_coordinator = ingest_coordinator

    if enrichment_store is None:
        app_ctx.enrichment_store = None
    elif enrichment_store == "auto":
        es = MagicMock()
        es.stats.return_value = EnrichmentStats()
        app_ctx.enrichment_store = es
    else:
        app_ctx.enrichment_store = enrichment_store

    if conn == "auto":
        from owlbear_mcp_knowledge.server import init_db

        app_ctx.conn = init_db(":memory:")
    else:
        app_ctx.conn = conn

    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


@pytest.fixture
def _heavy_mocks(tmp_path: object) -> object:
    """Patch heavy lifespan deps (Qdrant, embeddings). Yields a mock server."""
    server_mock = MagicMock()
    env_overrides = {
        "OWLBEAR_LOCAL_KB_PATH": ":memory:",
        "OWLBEAR_QDRANT_PATH": str(tmp_path) + "/vectors",  # type: ignore[operator]
    }
    with (
        patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
        patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
        patch.dict(os.environ, env_overrides),
    ):
        yield server_mock


def _make_entity_lookup_result() -> MagicMock:
    """Return a minimal mock EntityLookupResult."""
    result = MagicMock()
    entity = MagicMock()
    entity.id = "ent-1"
    entity.name = "ConceptA"
    entity.entity_type = "concept"
    entity.description = "A test concept"
    result.entity = entity
    result.neighbourhood = None
    result.related_chunks = ()
    return result


def _make_query_result_empty() -> MagicMock:
    """Return a mock QueryResult with no search_results."""
    result = MagicMock()
    result.search_results = ()
    result.graph_context = None
    result.provenance = ()
    return result


# ---------------------------------------------------------------------------
# AC1 — AppContext gains query_facade + graph_store_v2 + lifespan wiring
# ---------------------------------------------------------------------------


class TestFromAC_AppContextFieldsV2:
    """AC1: AppContext gains query_facade and graph_store_v2 (SqliteGraphStore) fields.

    Also covers: SqliteGraphStore.ensure_tables() called in lifespan; legacy
    graph_store field retained.
    """

    def test_query_facade_field_defaults_to_none(self) -> None:
        """AppContext.query_facade field exists and defaults to None.

        Currently FAILS: query_facade is not declared on the slots=True dataclass —
        accessing it raises AttributeError.
        """
        from owlbear_mcp_knowledge.server import AppContext

        conn = sqlite3.connect(":memory:")
        ctx = AppContext(
            conn=conn,
            query_service=None,
            graph_store=None,
            ingest_pipeline=None,
            source_store=None,
        )
        assert ctx.query_facade is None  # noqa: SIM300

    def test_graph_store_v2_field_defaults_to_none(self) -> None:
        """AppContext.graph_store_v2 (SqliteGraphStore) field exists and defaults to None.

        Currently FAILS: graph_store_v2 is not declared on the dataclass.
        """
        from owlbear_mcp_knowledge.server import AppContext

        conn = sqlite3.connect(":memory:")
        ctx = AppContext(
            conn=conn,
            query_service=None,
            graph_store=None,
            ingest_pipeline=None,
            source_store=None,
        )
        assert ctx.graph_store_v2 is None  # noqa: SIM300

    def test_appcontext_accepts_query_facade_kwarg(self) -> None:
        """AppContext can be constructed with a real QueryFacade via keyword arg.

        Currently FAILS: query_facade is not a declared field; TypeError on construction.
        """
        from owlbear_mcp_knowledge.server import AppContext

        conn = sqlite3.connect(":memory:")
        facade_mock = MagicMock(spec=QueryFacade)
        ctx = AppContext(
            conn=conn,
            query_service=None,
            graph_store=None,
            ingest_pipeline=None,
            source_store=None,
            query_facade=facade_mock,
        )
        assert ctx.query_facade is facade_mock

    def test_legacy_graph_store_field_coexists_with_graph_store_v2(self) -> None:
        """Both graph_store (legacy) and graph_store_v2 are accessible on AppContext.

        graph_store_v2 default is None; legacy graph_store is set independently.
        Currently FAILS: graph_store_v2 field does not exist.
        """
        from owlbear_mcp_knowledge.server import AppContext

        conn = sqlite3.connect(":memory:")
        legacy_gs = MagicMock()
        ctx = AppContext(
            conn=conn,
            query_service=None,
            graph_store=legacy_gs,
            ingest_pipeline=None,
            source_store=None,
        )
        assert ctx.graph_store is legacy_gs  # legacy retained
        assert ctx.graph_store_v2 is None  # new field present with None default

    @pytest.mark.asyncio
    async def test_lifespan_populates_query_facade(self, _heavy_mocks: object) -> None:
        """app_lifespan instantiates QueryFacade and yields it in ctx.query_facade.

        Currently FAILS: app_lifespan does not import or instantiate QueryFacade.
        """
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert isinstance(ctx.query_facade, QueryFacade)

    @pytest.mark.asyncio
    async def test_lifespan_populates_graph_store_v2(self, _heavy_mocks: object) -> None:
        """app_lifespan instantiates SqliteGraphStore in ctx.graph_store_v2.

        Currently FAILS: app_lifespan does not import or instantiate SqliteGraphStore.
        """
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert isinstance(ctx.graph_store_v2, SqliteGraphStore)

    @pytest.mark.asyncio
    async def test_lifespan_calls_ensure_tables_on_sqlite_graph_store(
        self,
        _heavy_mocks: object,
    ) -> None:
        """SqliteGraphStore.ensure_tables() is called during lifespan startup.

        Currently FAILS: SqliteGraphStore is never instantiated in lifespan.
        """
        from owlbear_mcp_knowledge.server import app_lifespan

        with patch.object(SqliteGraphStore, "ensure_tables") as mock_ensure:
            async with app_lifespan(_heavy_mocks) as _ctx:
                pass
        mock_ensure.assert_called_once()


# ---------------------------------------------------------------------------
# AC2 — search_knowledge → QueryFacade.search
# ---------------------------------------------------------------------------


class TestFromAC_SearchKnowledgeDelegate:
    """AC2: search_knowledge delegates to QueryFacade.search with QueryRequest."""

    @pytest.mark.asyncio
    async def test_search_calls_query_facade_search_not_legacy_service(self) -> None:
        """search_knowledge calls query_facade.search(), not query_service.query().

        Currently FAILS: code calls app_ctx.query_service.query() and returns
        'error: Knowledge service not available.' when query_service=None.
        With query_service=None but query_facade configured, result must be a list.
        """
        from owlbear_mcp_knowledge.server import search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(return_value=_make_query_result_empty())
        ctx = _make_ctx(query_facade=facade, query_service=None)

        outcome = await search_knowledge(ctx, query="what is TDD")
        assert isinstance(outcome, list), f"expected list, got: {outcome!r}"
        facade.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_passes_query_request_text_top_k_scopes(self) -> None:
        """QueryRequest(text=query, top_k=limit, scopes=...) passed to facade.search.

        Currently FAILS: code uses KnowledgeQueryService.query(prompt, top_k, scopes)
        positional-style, not QueryRequest.
        """
        from owlbear_mcp_knowledge.server import search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(return_value=_make_query_result_empty())
        ctx = _make_ctx(query_facade=facade, query_service=None)

        await search_knowledge(ctx, query="explain pytest", limit=8, scopes=["workspace"])

        assert facade.search.call_count == 1
        args, kwargs = facade.search.call_args
        req = args[0] if args else kwargs.get("request")
        assert isinstance(req, QueryRequest), f"expected QueryRequest, got: {type(req)}"
        assert req.text == "explain pytest"
        assert req.top_k == 8
        assert "workspace" in req.scopes

    @pytest.mark.asyncio
    async def test_search_returns_error_string_when_query_facade_is_none(self) -> None:
        """Returns error string when query_facade is None (not when query_service is None).

        Currently FAILS: code checks query_service, not query_facade.
        With query_service=MagicMock (non-None) and query_facade=None, old code
        calls query_service and returns results (list), not error string.
        New code checks query_facade first → returns error string.
        """
        from owlbear_mcp_knowledge.server import search_knowledge

        legacy_qs = MagicMock()
        legacy_qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(query_facade=None, query_service=legacy_qs)

        outcome = await search_knowledge(ctx, query="test")
        assert isinstance(outcome, str), f"expected str, got {type(outcome)}: {outcome!r}"
        assert "error" in outcome.lower(), f"expected error string, got: {outcome!r}"

    @pytest.mark.asyncio
    async def test_search_does_not_call_legacy_query_service(self) -> None:
        """search_knowledge must NOT call query_service.query() after rewiring.

        Currently FAILS: code exclusively calls query_service.query().
        """
        from owlbear_mcp_knowledge.server import search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(return_value=_make_query_result_empty())
        legacy_qs = MagicMock()
        legacy_qs.query = AsyncMock(return_value=[])
        ctx = _make_ctx(query_facade=facade, query_service=legacy_qs)

        await search_knowledge(ctx, query="test query")
        legacy_qs.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_maps_result_to_list_of_search_result_dicts(self) -> None:
        """Result is a list; when empty, returns []; shape preserved.

        Currently FAILS: code is not wired to QueryFacade, returns error string
        when query_service=None.
        """
        from owlbear_mcp_knowledge.server import search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(return_value=_make_query_result_empty())
        ctx = _make_ctx(query_facade=facade, query_service=None)

        result = await search_knowledge(ctx, query="hello")
        assert isinstance(result, list)
        # Empty search_results → empty list
        assert result == []


# ---------------------------------------------------------------------------
# AC3 — list_sources → SqliteSourceStore.list_sources
# ---------------------------------------------------------------------------


class TestFromAC_ListSourcesDelegate:
    """AC3: list_sources delegates to SqliteSourceStore.list_sources(scope=scope)."""

    @pytest.mark.asyncio
    async def test_list_sources_calls_source_store_v2_not_legacy(self) -> None:
        """list_sources calls source_store_v2.list_sources(), not legacy store.list_all().

        Currently FAILS: code calls app_ctx.source_store.list_all(scope=scope).
        """
        from owlbear_mcp_knowledge.server import list_sources

        store_v2 = MagicMock()
        store_v2.list_sources = MagicMock(return_value=())
        legacy_store = MagicMock()
        legacy_store.list_all = MagicMock(return_value=[])

        ctx = _make_ctx(source_store_v2=store_v2, source_store=legacy_store)
        await list_sources(ctx, scope=None)
        store_v2.list_sources.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_sources_passes_scope_to_list_sources(self) -> None:
        """scope parameter forwarded to source_store_v2.list_sources(scope=scope).

        Currently FAILS: legacy code passes scope to list_all() with different semantics.
        """
        from owlbear_mcp_knowledge.server import list_sources

        store_v2 = MagicMock()
        store_v2.list_sources = MagicMock(return_value=())
        ctx = _make_ctx(source_store_v2=store_v2)

        await list_sources(ctx, scope="workspace")

        args, kwargs = store_v2.list_sources.call_args
        passed_scope = args[0] if args else kwargs.get("scope")
        assert passed_scope == "workspace"

    @pytest.mark.asyncio
    async def test_list_sources_maps_source_record_to_source_info_typed_dict(self) -> None:
        """SourceRecord from v2 store mapped to SourceInfo TypedDict with required keys.

        Currently FAILS: code maps from legacy KnowledgeSource (different field names/shape).
        """
        from owlbear_mcp_knowledge.server import list_sources

        record = MagicMock()
        record.id = "src-xyz"
        record.name = "My Source"
        record.kind = "file_glob"
        record.scope = "workspace"
        record.state = "active"
        record.last_refreshed_at = None
        record.last_error = None
        record.enrich = False
        record.refreshable = True
        record.fetch_method = "filesystem"

        store_v2 = MagicMock()
        store_v2.list_sources = MagicMock(return_value=(record,))
        ctx = _make_ctx(source_store_v2=store_v2)

        result = await list_sources(ctx, scope=None)
        assert isinstance(result, list)
        assert len(result) == 1
        item = result[0]
        assert item["id"] == "src-xyz"
        assert item["name"] == "My Source"
        assert "source_type" in item  # SourceInfo TypedDict key

    @pytest.mark.asyncio
    async def test_list_sources_raises_tool_error_when_store_v2_none(self) -> None:
        """Raises ToolError when source_store_v2 is None.

        Currently FAILS: code checks source_store (legacy), not source_store_v2.
        With source_store=non-None but source_store_v2=None, old code proceeds;
        new code raises ToolError from the v2 guard.
        """
        from owlbear_mcp_knowledge.server import list_sources

        legacy_store = MagicMock()
        legacy_store.list_all = MagicMock(return_value=[])
        ctx = _make_ctx(source_store_v2=None, source_store=legacy_store)

        with pytest.raises(ToolError):
            await list_sources(ctx, scope=None)

    @pytest.mark.asyncio
    async def test_list_sources_does_not_call_legacy_list_all(self) -> None:
        """list_sources must NOT call source_store.list_all() after rewiring.

        Currently FAILS: code calls source_store.list_all() exclusively.
        """
        from owlbear_mcp_knowledge.server import list_sources

        store_v2 = MagicMock()
        store_v2.list_sources = MagicMock(return_value=())
        legacy_store = MagicMock()
        legacy_store.list_all = MagicMock(return_value=[])
        ctx = _make_ctx(source_store_v2=store_v2, source_store=legacy_store)

        await list_sources(ctx, scope=None)
        legacy_store.list_all.assert_not_called()




# ---------------------------------------------------------------------------
# AC4 — knowledge_entity_lookup new tool
# ---------------------------------------------------------------------------


class TestFromAC_EntityLookupTool:
    """AC4: knowledge_entity_lookup tool registered; delegates to QueryFacade.lookup_entity."""

    def test_knowledge_entity_lookup_is_importable(self) -> None:
        """knowledge_entity_lookup function exists and is callable.

        Currently FAILS: the function does not exist in server.py — ImportError.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup  # noqa: F401

        assert callable(knowledge_entity_lookup)

    def test_knowledge_entity_lookup_has_required_params(self) -> None:
        """Function signature includes: ctx, entity_id, entity_name, entity_type, expand_hops.

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        sig = inspect.signature(knowledge_entity_lookup)
        params = sig.parameters
        assert "entity_id" in params
        assert "entity_name" in params
        assert "entity_type" in params
        assert "expand_hops" in params

    def test_knowledge_entity_lookup_expand_hops_default_is_1(self) -> None:
        """expand_hops defaults to 1 (matching EntityLookupRequest default).

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        sig = inspect.signature(knowledge_entity_lookup)
        assert sig.parameters["expand_hops"].default == 1

    def test_knowledge_entity_lookup_params_default_to_none_except_expand_hops(self) -> None:
        """entity_id, entity_name, entity_type all default to None.

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        sig = inspect.signature(knowledge_entity_lookup)
        assert sig.parameters["entity_id"].default is None
        assert sig.parameters["entity_name"].default is None
        assert sig.parameters["entity_type"].default is None

    @pytest.mark.asyncio
    async def test_entity_lookup_delegates_to_query_facade_lookup_entity(self) -> None:
        """Delegates to query_facade.lookup_entity with an EntityLookupRequest.

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(return_value=_make_entity_lookup_result())
        ctx = _make_ctx(query_facade=facade)

        await knowledge_entity_lookup(ctx, entity_id="ent-1")
        facade.lookup_entity.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_lookup_constructs_entity_lookup_request_with_entity_id(self) -> None:
        """EntityLookupRequest(entity_id=..., expand_hops=...) passed to lookup_entity.

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(return_value=_make_entity_lookup_result())
        ctx = _make_ctx(query_facade=facade)

        await knowledge_entity_lookup(ctx, entity_id="ent-42", expand_hops=2)

        args, kwargs = facade.lookup_entity.call_args
        req = args[0] if args else kwargs.get("request")
        assert isinstance(req, EntityLookupRequest)
        assert req.entity_id == "ent-42"
        assert req.expand_hops == 2

    @pytest.mark.asyncio
    async def test_entity_lookup_constructs_request_with_entity_name(self) -> None:
        """entity_name forwarded to EntityLookupRequest.entity_name when id is None.

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(return_value=_make_entity_lookup_result())
        ctx = _make_ctx(query_facade=facade)

        await knowledge_entity_lookup(ctx, entity_name="Python", entity_id=None)

        req = facade.lookup_entity.call_args[0][0]
        assert isinstance(req, EntityLookupRequest)
        assert req.entity_name == "Python"
        assert req.entity_id is None

    @pytest.mark.asyncio
    async def test_entity_lookup_returns_non_none_serializable_result(self) -> None:
        """Return value is non-None and serializable (dict, list, or str).

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(return_value=_make_entity_lookup_result())
        ctx = _make_ctx(query_facade=facade)

        result = await knowledge_entity_lookup(ctx, entity_id="ent-1")
        assert result is not None
        assert isinstance(result, (dict, list, str))


# ---------------------------------------------------------------------------
# AC5 — get_stats → IngestCoordinator.stats() + EnrichmentStore.stats()
# ---------------------------------------------------------------------------


class TestFromAC_GetStatsDelegation:
    """AC5: get_stats delegates to IngestCoordinator.stats() and EnrichmentStore.stats()."""

    @pytest.mark.asyncio
    async def test_get_stats_calls_ingest_coordinator_stats(self) -> None:
        """get_stats calls ingest_coordinator.stats() for base counts.

        Currently FAILS: code calls legacy GraphStore.get_counts() + raw SQL,
        never touches ingest_coordinator.stats().
        """
        from owlbear_mcp_knowledge.server import get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats()
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats()

        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=None,
        )
        await get_stats(ctx)
        coordinator.stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats_calls_enrichment_store_stats(self) -> None:
        """get_stats calls enrichment_store.stats() for chunk detail fields.

        Currently FAILS: code uses direct SQL GROUP BY enrichment_state query.
        """
        from owlbear_mcp_knowledge.server import get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats()
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats(pending=7)

        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=None,
        )
        await get_stats(ctx)
        enrichment_store.stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats_total_sources_from_coordinator_stats(self) -> None:
        """StatsResult.total_sources reflects IngestCoordinator.stats().sources_total.

        Currently FAILS: code counts via SQL on knowledge_sources (returns 0 for empty DB).
        Coordinator mock returns 99 → test asserts 99.
        """
        from owlbear_mcp_knowledge.server import get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats(sources_total=99)
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats()

        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=None,
        )
        result = await get_stats(ctx)
        assert result["total_sources"] == 99

    @pytest.mark.asyncio
    async def test_get_stats_entities_from_coordinator_stats(self) -> None:
        """StatsResult.entities reflects IngestCoordinator.stats().graph_entities.

        Currently FAILS: code calls legacy GraphStore.get_counts() which returns (0,0,0)
        from the mock → entities=0. Coordinator returns graph_entities=77 → asserts 77.
        """
        from owlbear_mcp_knowledge.server import get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats(graph_entities=77, graph_edges=88)
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats()

        # graph_store mock returns (0, 11, 22) — different from coordinator value
        gs_legacy = MagicMock()
        gs_legacy.get_counts.return_value = (0, 11, 22)

        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=gs_legacy,
        )
        result = await get_stats(ctx)
        # New code: entities=77 (from coordinator); old code: entities=11 (get_counts)
        assert result["entities"] == 77

    @pytest.mark.asyncio
    async def test_get_stats_chunks_pending_from_enrichment_store_stats(self) -> None:
        """StatsResult.chunks_pending reflects EnrichmentStore.stats().pending.

        Currently FAILS: code uses SQL state_counts (returns 0 for empty DB).
        EnrichmentStore mock returns pending=13 → asserts 13.
        """
        from owlbear_mcp_knowledge.server import get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats()
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats(pending=13)

        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=None,
        )
        result = await get_stats(ctx)
        # New code: from EnrichmentStats.pending=13; old code: SQL COUNT=0 (empty DB)
        assert result["chunks_pending"] == 13

    @pytest.mark.asyncio
    async def test_get_stats_preserves_stats_result_typed_dict_shape(self) -> None:
        """All StatsResult TypedDict keys are present in the returned dict.

        Currently FAILS: with graph_store=None, current code raises ToolError before
        returning. New code uses coordinator+enrichment store, handles None graph_store.
        """
        from owlbear_mcp_knowledge.server import get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats()
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats()

        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=None,
        )
        result = await get_stats(ctx)
        required_keys = {
            "documents",
            "entities",
            "edges",
            "total_sources",
            "total_chunks",
            "chunks_pending",
            "chunks_claimed",
            "chunks_failed",
            "chunks_enriched",
            "chunks_claimable",
            "chunks_enriched_ratio",
            "consolidation_candidates_remaining",
        }
        assert required_keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# AC6 — Error handling: ValueError/LookupError/ValidationError → ToolError
# ---------------------------------------------------------------------------


class TestFromAC_ErrorHandling:
    """AC6: ValueError/LookupError/ValidationError raised as ToolError; no raw tracebacks."""

    @pytest.mark.asyncio
    async def test_search_knowledge_value_error_from_facade_raises_tool_error(self) -> None:
        """QueryFacade.search raises ValueError → ToolError (not propagated raw).

        Currently FAILS: code catches KnowledgeQueryError (legacy), not ValueError.
        With query_service=None, returns error string not ToolError.
        New code: ValueError from QueryFacade → ToolError.
        """
        from owlbear_mcp_knowledge.server import search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(side_effect=ValueError("request.text must not be empty"))
        ctx = _make_ctx(query_facade=facade, query_service=None)

        with pytest.raises(ToolError):
            await search_knowledge(ctx, query="   ")

    @pytest.mark.asyncio
    async def test_entity_lookup_lookup_error_raises_tool_error(self) -> None:
        """LookupError from QueryFacade.lookup_entity → ToolError.

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(
            side_effect=LookupError("entity_id not found: nonexistent")
        )
        ctx = _make_ctx(query_facade=facade)

        with pytest.raises(ToolError):
            await knowledge_entity_lookup(ctx, entity_id="nonexistent")

    @pytest.mark.asyncio
    async def test_entity_lookup_validation_error_both_none_raises_tool_error(self) -> None:
        """ValidationError from EntityLookupRequest (entity_id and entity_name both None) → ToolError.

        Currently FAILS: function does not exist.
        AC: Pydantic ValidationError (from model_validator) raised as ToolError.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        ctx = _make_ctx(query_facade=facade)

        # entity_id=None and entity_name=None violates EntityLookupRequest model_validator
        with pytest.raises(ToolError):
            await knowledge_entity_lookup(ctx, entity_id=None, entity_name=None)

    @pytest.mark.asyncio
    async def test_entity_lookup_validation_error_both_set_raises_tool_error(self) -> None:
        """ValidationError from EntityLookupRequest (both id and name set) → ToolError.

        Currently FAILS: function does not exist.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        ctx = _make_ctx(query_facade=facade)

        with pytest.raises(ToolError):
            await knowledge_entity_lookup(
                ctx,
                entity_id="ent-1",
                entity_name="ConceptA",
            )

    @pytest.mark.asyncio
    async def test_entity_lookup_tool_error_message_contains_no_traceback(self) -> None:
        """ToolError message does not leak raw Python traceback text.

        Currently FAILS: function does not exist.
        AC6: no raw exception strings in MCP responses.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(
            side_effect=LookupError("entity_name not found: Unknown")
        )
        ctx = _make_ctx(query_facade=facade)

        try:
            await knowledge_entity_lookup(ctx, entity_id="x")
        except ToolError as exc:
            msg = str(exc)
            assert "Traceback" not in msg
            assert "File " not in msg
        else:
            pytest.fail("Expected ToolError was not raised")
