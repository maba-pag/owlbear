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
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

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
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

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
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

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
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

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
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

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
        from owlbear_mcp_knowledge.server import knowledge_sources_list as list_sources

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
        from owlbear_mcp_knowledge.server import knowledge_sources_list as list_sources

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
        from owlbear_mcp_knowledge.server import knowledge_sources_list as list_sources

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
        from owlbear_mcp_knowledge.server import knowledge_sources_list as list_sources

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
        from owlbear_mcp_knowledge.server import knowledge_sources_list as list_sources

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
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

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
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

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
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

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
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

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
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

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
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

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
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

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


# ---------------------------------------------------------------------------
# AC2 retry — populated QueryFacade result serialization (field-level proof)
# ---------------------------------------------------------------------------

# --- helpers ----------------------------------------------------------------


def _make_populated_query_result_ctx() -> tuple[object, object]:
    """Return (mock QueryResult, mock ctx) for populated-result serialization tests.

    Layout:
    - graph_context: 2 entities (Entity0/concept, Entity1/concept), 1 edge
      → retrieval_path='vector+graph', graph_context text='graph expansion: 2 entities, 1 edges'
    - search_results: one hit (chunk-abc)
    - provenance: prov_main (chunk-abc, src-1, "Main Doc") +
                  prov_other (chunk-xyz, src-2, "Related Doc")
    - source_store_v2.get_source("src-1") returns a record with name/url
    """
    # graph context
    entity0 = MagicMock()
    entity0.name = "Entity0"
    entity0.entity_type = "concept"
    entity1 = MagicMock()
    entity1.name = "Entity1"
    entity1.entity_type = "concept"

    graph_ctx = MagicMock()
    graph_ctx.entities = (entity0, entity1)
    graph_ctx.edges = (MagicMock(),)

    # content hit
    chunk = MagicMock()
    chunk.id = "chunk-abc"
    chunk.text = "Relevant content"
    chunk.source_id = "src-1"

    search_hit = MagicMock()
    search_hit.chunk = chunk
    search_hit.score = 0.87

    # provenance
    prov_main = MagicMock()
    prov_main.chunk_id = "chunk-abc"
    prov_main.source_id = "src-1"
    prov_main.title = "Main Doc"
    prov_main.uri = "https://example.com/main"

    prov_other = MagicMock()
    prov_other.chunk_id = "chunk-xyz"
    prov_other.source_id = "src-2"
    prov_other.title = "Related Doc"
    prov_other.uri = "https://example.com/related"

    query_result = MagicMock()
    query_result.search_results = (search_hit,)
    query_result.graph_context = graph_ctx
    query_result.provenance = (prov_main, prov_other)

    # source store v2 returns a real-ish source record for src-1
    source_record = MagicMock()
    source_record.name = "Knowledge Store"
    source_record.url = "https://store.example.com"

    store_v2 = MagicMock()
    store_v2.get_source = MagicMock(return_value=source_record)

    facade = MagicMock(spec=QueryFacade)
    facade.search = AsyncMock(return_value=query_result)

    ctx = _make_ctx(query_facade=facade, source_store_v2=store_v2)
    return facade, ctx


def _make_vector_only_ctx() -> tuple[object, object]:
    """Return (mock QueryResult, mock ctx) with graph_context=None (vector path)."""
    chunk = MagicMock()
    chunk.id = "chunk-vec"
    chunk.text = "Vector only text"
    chunk.source_id = "src-v"

    search_hit = MagicMock()
    search_hit.chunk = chunk
    search_hit.score = 0.65

    prov = MagicMock()
    prov.chunk_id = "chunk-vec"
    prov.source_id = "src-v"
    prov.title = "Vector Doc"
    prov.uri = None

    query_result = MagicMock()
    query_result.search_results = (search_hit,)
    query_result.graph_context = None
    query_result.provenance = (prov,)

    facade = MagicMock(spec=QueryFacade)
    facade.search = AsyncMock(return_value=query_result)
    ctx = _make_ctx(query_facade=facade)
    return facade, ctx


class TestFromAC_SearchResultSerialization:
    """AC2 retry: populated QueryFacade result serializes each field correctly.

    All tests exercise _serialize_query_facade_results via search_knowledge —
    none would pass if the helper regresses on any of the pinned fields.
    """

    @pytest.mark.asyncio
    async def test_populated_result_retrieval_path_vector_plus_graph(self) -> None:
        """retrieval_path is 'vector+graph' when graph_context is present.

        Pins: graph_context is not None → 'vector+graph' branch.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_populated_query_result_ctx()
        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["retrieval_path"] == "vector+graph"

    @pytest.mark.asyncio
    async def test_populated_result_graph_context_formatted_string(self) -> None:
        """graph_context is a formatted summary string with entity/edge counts.

        Pins: graph_context = 'graph expansion: 2 entities, 1 edges' (2 entities, 1 edge).
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_populated_query_result_ctx()
        result = await search_knowledge(ctx, query="test")

        assert result[0]["graph_context"] == "graph expansion: 2 entities, 1 edges"

    @pytest.mark.asyncio
    async def test_populated_result_entities_from_graph_traversal(self) -> None:
        """entities list contains {name, type} dicts from graph_context.entities.

        Pins: both Entity0/concept and Entity1/concept appear in entities.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_populated_query_result_ctx()
        result = await search_knowledge(ctx, query="test")

        entities = result[0]["entities"]
        assert isinstance(entities, list)
        assert {"name": "Entity0", "type": "concept"} in entities
        assert {"name": "Entity1", "type": "concept"} in entities

    @pytest.mark.asyncio
    async def test_populated_result_related_sources_excludes_self_chunk(self) -> None:
        """related_sources contains provenance from other chunks, not the self-chunk.

        Pins: prov_other (chunk-xyz) → related; prov_main (chunk-abc) excluded.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_populated_query_result_ctx()
        result = await search_knowledge(ctx, query="test")

        related = result[0]["related_sources"]
        assert isinstance(related, list)
        assert len(related) == 1
        assert related[0]["name"] == "Related Doc"
        assert related[0]["relationship"] == "related"

    @pytest.mark.asyncio
    async def test_populated_result_source_from_source_store_v2(self) -> None:
        """source field is populated from source_store_v2.get_source lookup.

        Pins: source_store_v2 provides name and url; not fallen back to SimpleNamespace.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_populated_query_result_ctx()
        result = await search_knowledge(ctx, query="test")

        source = result[0]["source"]
        assert isinstance(source, dict)
        assert source["name"] == "Knowledge Store"
        assert source["url"] == "https://store.example.com"

    @pytest.mark.asyncio
    async def test_vector_only_retrieval_path_and_empty_graph_context(self) -> None:
        """retrieval_path is 'vector' and graph_context is '' when graph_context=None.

        Pins: the 'vector' branch of retrieval_path logic.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_vector_only_ctx()
        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["retrieval_path"] == "vector"
        assert result[0]["graph_context"] == ""


# ---------------------------------------------------------------------------
# AC6 retry — exact sanitized ToolError message assertions
# ---------------------------------------------------------------------------


class TestFromAC_ErrorMessageExact:
    """AC6 retry: ToolError messages are exact sanitized literals, not raw exc strings.

    Each test asserts the EXACT message — these would fail if the code
    regressed from sanitized literals back to ToolError(str(exc)).
    """

    @pytest.mark.asyncio
    async def test_search_value_error_message_is_exact_literal(self) -> None:
        """search_knowledge ValueError → ToolError('invalid search request') — exact match.

        Pins: message is the sanitized literal, not str(ValueError(...)).
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(
            side_effect=ValueError("request.text must not be empty — internal detail")
        )
        ctx = _make_ctx(query_facade=facade)

        with pytest.raises(ToolError) as exc_info:
            await search_knowledge(ctx, query="   ")

        assert str(exc_info.value) == "invalid search request"

    @pytest.mark.asyncio
    async def test_entity_lookup_value_error_message_is_exact_literal(self) -> None:
        """lookup_entity ValueError → ToolError('invalid entity lookup request') — exact match.

        Pins: message is the sanitized literal, not str(ValueError(...)).
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(
            side_effect=ValueError("some internal detail")
        )
        ctx = _make_ctx(query_facade=facade)

        with pytest.raises(ToolError) as exc_info:
            await knowledge_entity_lookup(ctx, entity_id="ent-1")

        assert str(exc_info.value) == "invalid entity lookup request"

    @pytest.mark.asyncio
    async def test_entity_lookup_validation_error_message_is_exact_literal(self) -> None:
        """ValidationError from EntityLookupRequest → ToolError('invalid entity lookup request').

        Pins: ValidationError branch uses the same sanitized literal as ValueError branch.
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        ctx = _make_ctx(query_facade=facade)

        # Both entity_id and entity_name None → ValidationError from model_validator
        with pytest.raises(ToolError) as exc_info:
            await knowledge_entity_lookup(ctx, entity_id=None, entity_name=None)

        assert str(exc_info.value) == "invalid entity lookup request"

    @pytest.mark.asyncio
    async def test_entity_lookup_error_message_is_exact_literal(self) -> None:
        """LookupError from lookup_entity → ToolError('entity not found') — exact match.

        Pins: message is the sanitized literal, not str(LookupError('entity_id not found: xyz')).
        """
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(
            side_effect=LookupError("entity_id not found: xyz — internal path detail")
        )
        ctx = _make_ctx(query_facade=facade)

        with pytest.raises(ToolError) as exc_info:
            await knowledge_entity_lookup(ctx, entity_id="xyz")

        assert str(exc_info.value) == "entity not found"


# ---------------------------------------------------------------------------
# AC2 (slot-correctness) — search_knowledge with a real slotted AppContext
# ---------------------------------------------------------------------------


def _make_slotted_ctx(
    *,
    query_facade: object = None,
    query_service: object = None,
    source_store_v2: object = None,
) -> object:
    """Wrap a *real* AppContext (@dataclass slots=True) in a mock MCP Context.

    Unlike _make_ctx(), this uses the production AppContext class so that
    getattr(app_ctx, '__dict__', {}) behaves as it does in production
    (returning {} because slots=True dataclasses have no __dict__).
    """
    from owlbear_mcp_knowledge.server import AppContext, init_db

    conn = init_db(":memory:")
    app_ctx = AppContext(
        conn=conn,
        query_service=query_service,
        graph_store=None,
        ingest_pipeline=None,
        source_store=None,
        query_facade=query_facade,
        source_store_v2=source_store_v2,
    )
    mcp_ctx = MagicMock()
    mcp_ctx.request_context.lifespan_context = app_ctx
    return mcp_ctx


class TestFromAC_SlottedContextSearch:
    """AC2 (slot-correctness): branch detection must work on slotted AppContext.

    AppContext is @dataclass(slots=True) — it has no __dict__. Tests here use
    the real AppContext so that getattr(app_ctx, '__dict__', {}).get('query_facade')
    returns None even when query_facade is populated, exposing the production bug.
    All tests currently FAIL because the __dict__-based detection always falls
    through to the legacy query_service path.
    """

    @pytest.mark.asyncio
    async def test_slotted_ctx_search_delegates_to_query_facade(self) -> None:
        """With real AppContext and query_facade populated, search_knowledge calls
        query_facade.search (not query_service).

        Currently FAILS: __dict__-based detection on a slotted dataclass returns {}
        → sees query_facade as absent → falls to legacy path → query_service=None
        → returns error string instead of calling facade.search.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(return_value=_make_query_result_empty())
        ctx = _make_slotted_ctx(query_facade=facade, query_service=None)

        result = await search_knowledge(ctx, query="explain pytest")

        facade.search.assert_called_once()
        assert isinstance(result, list), (
            f"expected list from QueryFacade path, got {type(result)}: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_slotted_ctx_search_does_not_call_legacy_service(self) -> None:
        """With real AppContext, legacy query_service.query is NOT called when
        query_facade is populated.

        Currently FAILS: __dict__-based detection always falls through to legacy
        path, so query_service.query is called even though query_facade is set.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(return_value=_make_query_result_empty())
        legacy_qs = MagicMock()
        legacy_qs.query = AsyncMock(return_value=[])
        ctx = _make_slotted_ctx(query_facade=facade, query_service=legacy_qs)

        await search_knowledge(ctx, query="test slotted")

        legacy_qs.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_slotted_ctx_search_error_when_query_facade_none(self) -> None:
        """With real AppContext and query_facade=None, search returns error string
        (legacy fallback expected when both query_facade and query_service are None).

        This test pins correct fallback behavior — it should PASS after the builder
        fixes the branch detection, confirming the None-facade guard still works.

        Currently FAILS (indirectly): the bug causes ALL contexts to fall to legacy,
        so the error-string outcome is reached for the wrong reason. After the fix,
        this test confirms the correct None-guard path.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        ctx = _make_slotted_ctx(query_facade=None, query_service=None)
        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, str)
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_slotted_ctx_search_passes_query_request_to_facade(self) -> None:
        """QueryRequest(text, top_k, scopes) is constructed and passed to facade.search
        when using a real slotted AppContext.

        Currently FAILS: slotted AppContext falls to legacy path; facade.search never called.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        facade = MagicMock(spec=QueryFacade)
        facade.search = AsyncMock(return_value=_make_query_result_empty())
        ctx = _make_slotted_ctx(query_facade=facade)

        await search_knowledge(ctx, query="domain concepts", limit=7, scopes=["docs"])

        assert facade.search.call_count == 1
        call_args = facade.search.call_args
        req = call_args[0][0] if call_args[0] else call_args[1].get("request")
        assert isinstance(req, QueryRequest)
        assert req.text == "domain concepts"
        assert req.top_k == 7
        assert "docs" in req.scopes


# ---------------------------------------------------------------------------
# AC7 (formerly AC5) — get_stats exact assertions for ALL 12 output fields
# ---------------------------------------------------------------------------


class TestFromAC_GetStatsAllFieldsExact:
    """AC7: get_stats proof must assert exact values for every one of the 12 output fields.

    The existing test_get_stats_preserves_stats_result_typed_dict_shape only checks
    key presence. These tests assert exact numeric values so that a miswiring of any
    field is caught. Tests that already had exact coverage in TestFromAC_GetStatsDelegation
    are extended here with complementary non-default values.
    """

    @pytest.mark.asyncio
    async def test_get_stats_all_12_fields_exact_values(self) -> None:
        """All 12 StatsResult fields match exact values from mocked coordinator and
        enrichment store; SQL-derived fields (claimable, consolidation) return 0
        from empty in-memory DB.

        Pins every field: documents, entities, edges, total_sources, total_chunks,
        chunks_pending, chunks_claimed, chunks_failed, chunks_enriched,
        chunks_claimable, chunks_enriched_ratio, consolidation_candidates_remaining.
        """
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats(
            sources_total=5,
            documents_total=20,
            chunks_total=100,
            graph_entities=50,
            graph_edges=30,
        )
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats(
            pending=10,
            in_progress=3,
            completed=15,
            failed=2,
        )
        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=None,
        )

        result = await get_stats(ctx)

        # Coordinator-sourced fields
        assert result["documents"] == 20
        assert result["entities"] == 50
        assert result["edges"] == 30
        assert result["total_sources"] == 5
        assert result["total_chunks"] == 100
        # EnrichmentStore-sourced fields
        assert result["chunks_pending"] == 10
        assert result["chunks_claimed"] == 3
        assert result["chunks_failed"] == 2
        assert result["chunks_enriched"] == 15
        # Computed field: ratio = completed / chunks_total = 15 / 100 = 0.15
        assert result["chunks_enriched_ratio"] == pytest.approx(0.15)
        # SQL-derived fields: empty DB → 0
        assert result["chunks_claimable"] == 0
        assert result["consolidation_candidates_remaining"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_enriched_ratio_zero_when_total_chunks_zero(self) -> None:
        """chunks_enriched_ratio is 0.0 when total_chunks is 0 (no division by zero).

        Pins: ratio computation guard branch — completed=5, chunks_total=0 → 0.0.
        """
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats(chunks_total=0)
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats(completed=5)
        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=None,
        )

        result = await get_stats(ctx)

        assert result["chunks_enriched_ratio"] == 0.0
        assert result["total_chunks"] == 0
        assert result["chunks_enriched"] == 5

    @pytest.mark.asyncio
    async def test_get_stats_edges_from_coordinator_not_legacy_graph_store(self) -> None:
        """StatsResult.edges comes from IngestCoordinator.stats().graph_edges,
        not from legacy GraphStore.get_counts().

        Pins: edges=88 from coordinator while legacy GraphStore returns (0, 0, 22).
        A miswiring that reads get_counts()[2] instead of graph_edges would fail.
        """
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats(graph_entities=77, graph_edges=88)
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats()
        # Legacy GraphStore returns different values
        gs_legacy = MagicMock()
        gs_legacy.get_counts.return_value = (0, 0, 22)
        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=gs_legacy,
        )

        result = await get_stats(ctx)

        assert result["edges"] == 88
        assert result["entities"] == 77

    @pytest.mark.asyncio
    async def test_get_stats_documents_from_coordinator_not_legacy_sql(self) -> None:
        """StatsResult.documents comes from IngestCoordinator.stats().documents_total.

        Pins: documents=42 from coordinator; legacy graph_store.get_counts()[0] = 0.
        A miswiring that reads get_counts() for documents would fail.
        """
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats(documents_total=42)
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats()
        gs_legacy = MagicMock()
        gs_legacy.get_counts.return_value = (0, 0, 0)
        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=gs_legacy,
        )

        result = await get_stats(ctx)

        assert result["documents"] == 42

    @pytest.mark.asyncio
    async def test_get_stats_chunks_claimed_from_enrichment_in_progress(self) -> None:
        """StatsResult.chunks_claimed maps to EnrichmentStats.in_progress (not a separate field).

        Pins: in_progress=7 → chunks_claimed=7. A miswiring that maps in_progress
        to chunks_pending or a SQL count would fail.
        """
        from owlbear_mcp_knowledge.server import knowledge_stats as get_stats

        coordinator = MagicMock()
        coordinator.stats.return_value = IngestStats()
        enrichment_store = MagicMock()
        enrichment_store.stats.return_value = EnrichmentStats(
            pending=2, in_progress=7, failed=1, completed=3
        )
        ctx = _make_ctx(
            ingest_coordinator=coordinator,
            enrichment_store=enrichment_store,
            graph_store=None,
        )

        result = await get_stats(ctx)

        assert result["chunks_claimed"] == 7
        assert result["chunks_pending"] == 2
        assert result["chunks_failed"] == 1
        assert result["chunks_enriched"] == 3


# ---------------------------------------------------------------------------
# Retry (cycle 4) helpers
# ---------------------------------------------------------------------------


def _make_slotted_populated_ctx(*, store_v2_hit: bool = True) -> tuple[object, object]:
    """Build a populated search context using a real slotted AppContext.

    Returns (facade, mcp_ctx) where facade.search returns a QueryResult with:
    - graph_context: 2 entities (Alpha/concept, Beta/tool), 1 edge
    - 1 search result (chunk 'c-aaa', source 'src-X')
    - 2 provenance entries: c-aaa (main) and c-bbb (other)

    store_v2_hit=True  → source_store_v2.get_source returns a SourceRecord
    store_v2_hit=False → source_store_v2.get_source returns None (fallback branch)
    """
    from owlbear_mcp_knowledge.server import AppContext, init_db

    entity0 = MagicMock()
    entity0.name = "Alpha"
    entity0.entity_type = "concept"

    entity1 = MagicMock()
    entity1.name = "Beta"
    entity1.entity_type = "tool"

    graph_ctx = MagicMock()
    graph_ctx.entities = (entity0, entity1)
    graph_ctx.edges = (MagicMock(),)  # 1 edge

    chunk = MagicMock()
    chunk.id = "c-aaa"
    chunk.text = "main text"
    chunk.source_id = "src-X"

    hit = MagicMock()
    hit.chunk = chunk
    hit.score = 0.9

    prov_main = MagicMock()
    prov_main.chunk_id = "c-aaa"
    prov_main.source_id = "src-X"
    prov_main.title = "Main"
    prov_main.uri = "https://main.example.com"

    prov_other = MagicMock()
    prov_other.chunk_id = "c-bbb"
    prov_other.source_id = "src-Y"
    prov_other.title = "Other"
    prov_other.uri = "https://other.example.com"

    qr = MagicMock()
    qr.search_results = (hit,)
    qr.graph_context = graph_ctx
    qr.provenance = (prov_main, prov_other)

    facade = MagicMock(spec=QueryFacade)
    facade.search = AsyncMock(return_value=qr)

    if store_v2_hit:
        source_rec = MagicMock()
        source_rec.name = "Primary Store"
        source_rec.url = "https://store.example.com"
        store_v2 = MagicMock()
        store_v2.get_source = MagicMock(return_value=source_rec)
    else:
        store_v2 = MagicMock()
        store_v2.get_source = MagicMock(return_value=None)

    conn = init_db(":memory:")
    app_ctx = AppContext(
        conn=conn,
        query_service=None,
        graph_store=None,
        ingest_pipeline=None,
        source_store=None,
        query_facade=facade,
        source_store_v2=store_v2,
    )

    mcp_ctx = MagicMock()
    mcp_ctx.request_context.lifespan_context = app_ctx
    return facade, mcp_ctx


def _make_rich_entity_lookup_result() -> MagicMock:
    """Return mock EntityLookupResult with all sub-keys populated."""
    result = MagicMock()

    entity = MagicMock()
    entity.id = "ent-42"
    entity.name = "PyTest"
    entity.entity_type = "tool"
    entity.description = "A testing framework"
    result.entity = entity

    nb_ent = MagicMock()
    nb_ent.id = "ent-99"
    nb_ent.name = "Python"
    nb_ent.entity_type = "language"

    nb_edge = MagicMock()
    nb_edge.id = "edge-11"
    nb_edge.source_entity_id = "ent-42"
    nb_edge.target_entity_id = "ent-99"
    nb_edge.relation_type = "uses"
    nb_edge.weight = 1.0

    neighborhood = MagicMock()
    neighborhood.entities = (nb_ent,)
    neighborhood.edges = (nb_edge,)
    result.neighbourhood = neighborhood

    chunk = MagicMock()
    chunk.id = "chunk-123"
    chunk.document_id = "doc-1"
    chunk.source_id = "src-A"
    chunk.text = "Chunk text here"
    chunk.scope = "workspace"
    chunk.uri = "https://docs.pytest.org"
    result.related_chunks = (chunk,)

    return result


# ---------------------------------------------------------------------------
# AC4 (retry cycle 4) — all populated-result field assertions on real slotted AppContext
# ---------------------------------------------------------------------------


class TestFromAC_SlottedPopulatedSearch:
    """AC4 (cycle 4): Populated QueryFacade result serialization proven on real slotted AppContext.

    All field assertions here use a real AppContext(@dataclass, slots=True) so that
    object.__getattribute__-based branch detection is exercised on the production path.
    Covers both the source_store_v2 HIT branch and the MISS (fallback) branch (AC3).
    """

    @pytest.mark.asyncio
    async def test_slotted_retrieval_path_vector_plus_graph(self) -> None:
        """retrieval_path is 'vector+graph' when graph_context is present on slotted ctx."""
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_slotted_populated_ctx()
        result = await search_knowledge(ctx, query="test")

        assert isinstance(result, list), f"expected list, got {type(result)}: {result!r}"
        assert len(result) == 1
        assert result[0]["retrieval_path"] == "vector+graph"

    @pytest.mark.asyncio
    async def test_slotted_graph_context_formatted_summary(self) -> None:
        """graph_context is 'graph expansion: 2 entities, 1 edges' on slotted ctx."""
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_slotted_populated_ctx()
        result = await search_knowledge(ctx, query="test")

        assert result[0]["graph_context"] == "graph expansion: 2 entities, 1 edges"

    @pytest.mark.asyncio
    async def test_slotted_entities_from_graph_traversal(self) -> None:
        """entities list contains {name, type} dicts from graph_context on slotted ctx."""
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_slotted_populated_ctx()
        result = await search_knowledge(ctx, query="test")

        entities = result[0]["entities"]
        assert isinstance(entities, list)
        assert {"name": "Alpha", "type": "concept"} in entities
        assert {"name": "Beta", "type": "tool"} in entities

    @pytest.mark.asyncio
    async def test_slotted_related_sources_excludes_self_chunk(self) -> None:
        """related_sources on slotted ctx: other-chunk provenance included, self excluded."""
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_slotted_populated_ctx()
        result = await search_knowledge(ctx, query="test")

        related = result[0]["related_sources"]
        assert isinstance(related, list)
        assert len(related) == 1
        assert related[0]["name"] == "Other"
        assert related[0]["relationship"] == "related"

    @pytest.mark.asyncio
    async def test_slotted_source_from_store_v2_hit(self) -> None:
        """Source populated from source_store_v2.get_source hit on slotted AppContext."""
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_slotted_populated_ctx(store_v2_hit=True)
        result = await search_knowledge(ctx, query="test")

        source = result[0]["source"]
        assert source["name"] == "Primary Store"
        assert source["url"] == "https://store.example.com"

    @pytest.mark.asyncio
    async def test_slotted_source_fallback_when_store_v2_miss(self) -> None:
        """When store_v2.get_source returns None: source={name: provenance.source_id, url: provenance.uri}.

        Exercises the AC3 source fallback branch on a real slotted AppContext.
        """
        from owlbear_mcp_knowledge.server import knowledge_search as search_knowledge

        _, ctx = _make_slotted_populated_ctx(store_v2_hit=False)
        result = await search_knowledge(ctx, query="test")

        source = result[0]["source"]
        assert source["name"] == "src-X"
        assert source["url"] == "https://main.example.com"


# ---------------------------------------------------------------------------
# AC5 (retry cycle 4) — list_sources: all 11 fields + state param absence
# ---------------------------------------------------------------------------


class TestFromAC_ListSourcesAllFields:
    """AC5 (cycle 4): list_sources proof asserts all 11 output fields exactly."""

    @pytest.mark.asyncio
    async def test_list_sources_all_11_fields_exact_values(self) -> None:
        """All 11 SourceInfo fields are mapped with exact controlled values.

        Pins: id, name, source_type (str of kind), scope, last_refreshed_at,
        last_checked_at, last_error (sanitized), enabled (state=='active'),
        refreshable, enrich, fetch_method.
        """
        from owlbear_mcp_knowledge.server import knowledge_sources_list as list_sources

        record = MagicMock()
        record.id = "src-full"
        record.name = "Full Source"
        record.kind = "rss"
        record.scope = "team"
        record.state = "active"
        record.last_refreshed_at = "2026-01-01T00:00:00Z"
        record.last_checked_at = "2026-01-02T00:00:00Z"
        record.last_error = None
        record.enrich = True
        record.refreshable = False
        record.fetch_method = "http"

        store_v2 = MagicMock()
        store_v2.list_sources = MagicMock(return_value=(record,))
        ctx = _make_ctx(source_store_v2=store_v2)

        result = await list_sources(ctx, scope=None)

        assert len(result) == 1
        item = result[0]
        assert item["id"] == "src-full"
        assert item["name"] == "Full Source"
        assert item["source_type"] == "rss"
        assert item["scope"] == "team"
        assert item["last_refreshed_at"] == "2026-01-01T00:00:00Z"
        assert item["last_checked_at"] == "2026-01-02T00:00:00Z"
        assert item["last_error"] is None
        assert item["enabled"] is True
        assert item["refreshable"] is False
        assert item["enrich"] is True
        assert item["fetch_method"] == "http"

    @pytest.mark.asyncio
    async def test_list_sources_enabled_false_when_state_not_active(self) -> None:
        """enabled is False when state is not 'active' (e.g. 'paused')."""
        from owlbear_mcp_knowledge.server import knowledge_sources_list as list_sources

        record = MagicMock()
        record.id = "src-paused"
        record.name = "Paused Source"
        record.kind = "file_glob"
        record.scope = "global"
        record.state = "paused"
        record.last_refreshed_at = None
        record.last_checked_at = None
        record.last_error = None
        record.enrich = False
        record.refreshable = True
        record.fetch_method = "filesystem"

        store_v2 = MagicMock()
        store_v2.list_sources = MagicMock(return_value=(record,))
        ctx = _make_ctx(source_store_v2=store_v2)

        result = await list_sources(ctx, scope=None)

        assert result[0]["enabled"] is False

    def test_list_sources_signature_has_no_state_param(self) -> None:
        """list_sources function signature must NOT include a 'state' parameter."""
        from owlbear_mcp_knowledge.server import knowledge_sources_list as list_sources

        sig = inspect.signature(list_sources)
        assert "state" not in sig.parameters


# ---------------------------------------------------------------------------
# AC6 (retry cycle 4) — knowledge_entity_lookup: full return dict structure
# ---------------------------------------------------------------------------


class TestFromAC_EntityLookupReturnStructure:
    """AC6 (cycle 4): knowledge_entity_lookup return dict asserted with exact field values."""

    @pytest.mark.asyncio
    async def test_entity_lookup_entity_fields_exact(self) -> None:
        """entity sub-dict contains id, name, entity_type (str), description with exact values."""
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(return_value=_make_rich_entity_lookup_result())
        ctx = _make_ctx(query_facade=facade)

        result = await knowledge_entity_lookup(ctx, entity_id="ent-42")

        assert result["entity"]["id"] == "ent-42"
        assert result["entity"]["name"] == "PyTest"
        assert result["entity"]["entity_type"] == "tool"
        assert result["entity"]["description"] == "A testing framework"

    @pytest.mark.asyncio
    async def test_entity_lookup_neighbourhood_exact_shape(self) -> None:
        """neighbourhood contains entities [{id, name, entity_type}] and edges [{id, src, tgt, rel, weight}]."""
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(return_value=_make_rich_entity_lookup_result())
        ctx = _make_ctx(query_facade=facade)

        result = await knowledge_entity_lookup(ctx, entity_id="ent-42")

        nb = result["neighbourhood"]
        assert len(nb["entities"]) == 1
        assert nb["entities"][0]["id"] == "ent-99"
        assert nb["entities"][0]["name"] == "Python"
        assert nb["entities"][0]["entity_type"] == "language"

        assert len(nb["edges"]) == 1
        assert nb["edges"][0]["id"] == "edge-11"
        assert nb["edges"][0]["source_entity_id"] == "ent-42"
        assert nb["edges"][0]["target_entity_id"] == "ent-99"
        assert nb["edges"][0]["relation_type"] == "uses"
        assert nb["edges"][0]["weight"] == 1.0

    @pytest.mark.asyncio
    async def test_entity_lookup_related_chunks_exact_shape(self) -> None:
        """related_chunks is a list of {id, document_id, source_id, text, scope, uri} dicts."""
        from owlbear_mcp_knowledge.server import knowledge_entity_lookup

        facade = MagicMock(spec=QueryFacade)
        facade.lookup_entity = MagicMock(return_value=_make_rich_entity_lookup_result())
        ctx = _make_ctx(query_facade=facade)

        result = await knowledge_entity_lookup(ctx, entity_id="ent-42")

        chunks = result["related_chunks"]
        assert len(chunks) == 1
        assert chunks[0]["id"] == "chunk-123"
        assert chunks[0]["document_id"] == "doc-1"
        assert chunks[0]["source_id"] == "src-A"
        assert chunks[0]["text"] == "Chunk text here"
        assert chunks[0]["scope"] == "workspace"
        assert chunks[0]["uri"] == "https://docs.pytest.org"
