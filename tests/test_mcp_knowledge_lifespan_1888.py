"""Tests for MCP lifespan — new protocol store wiring (task #1888).

Tests the wiring contract defined in:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (AppContext, app_lifespan)

Target implementation:
  AppContext dataclass and app_lifespan asynccontextmanager in server.py

AC coverage:
  AC1 — AppContext gains fields content_store, enrichment_store, source_store_v2,
         ingest_coordinator — each typed T | None with default None (backwards compat)
  AC2 — Lifespan instantiates SqliteSourceStore(conn), ContentStore(db=conn, ...),
         EnrichmentStore(db=conn, graph=gs), IngestCoordinator(sources=..., ..., graph=gs)
  AC3 — ensure_tables() called on SqliteSourceStore, ContentStore, EnrichmentStore
         before yielding AppContext
  AC4 — Existing AppContext fields (source_store, ingest_pipeline, query_service, etc.)
         remain populated; existing MCP tools unaffected when new fields are None
"""

from __future__ import annotations

import os
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.stores.content import ContentStore
from owlbear_knowledge.stores.enrichment import EnrichmentStore
from owlbear_knowledge.stores.sources import SqliteSourceStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_minimal_app_ctx() -> object:
    """Return AppContext with only existing positional fields (new fields absent)."""
    from owlbear_mcp_knowledge.server import AppContext

    conn = sqlite3.connect(":memory:")
    return AppContext(
        conn=conn,
        query_service=None,
        graph_store=None,
        ingest_pipeline=None,
        source_store=None,
    )


@pytest.fixture
def _heavy_mocks(tmp_path: object) -> object:
    """Patch heavy lifespan deps (Qdrant, embeddings). Yields a server mock."""
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


# ---------------------------------------------------------------------------
# AC1 — AppContext field shape and None defaults
# ---------------------------------------------------------------------------


class TestFromAC_AppContextFields:
    """AC1: AppContext gains 4 new optional fields that default to None.

    Each new field must exist on the dataclass with a None default, preserving
    the ability to construct AppContext with only the existing positional args.
    """

    def test_content_store_field_defaults_to_none(self) -> None:
        """content_store field exists on AppContext and defaults to None."""
        ctx = _make_minimal_app_ctx()
        assert ctx.content_store is None  # noqa: SIM300

    def test_enrichment_store_field_defaults_to_none(self) -> None:
        """enrichment_store field exists on AppContext and defaults to None."""
        ctx = _make_minimal_app_ctx()
        assert ctx.enrichment_store is None

    def test_source_store_v2_field_defaults_to_none(self) -> None:
        """source_store_v2 field exists on AppContext and defaults to None."""
        ctx = _make_minimal_app_ctx()
        assert ctx.source_store_v2 is None

    def test_ingest_coordinator_field_defaults_to_none(self) -> None:
        """ingest_coordinator field exists on AppContext and defaults to None."""
        ctx = _make_minimal_app_ctx()
        assert ctx.ingest_coordinator is None

    def test_appcontext_accepts_all_four_new_fields_as_none_kwargs(self) -> None:
        """AppContext accepts explicit None for all 4 new fields without TypeError."""
        from owlbear_mcp_knowledge.server import AppContext

        conn = sqlite3.connect(":memory:")
        ctx = AppContext(
            conn=conn,
            query_service=None,
            graph_store=None,
            ingest_pipeline=None,
            source_store=None,
            content_store=None,
            enrichment_store=None,
            source_store_v2=None,
            ingest_coordinator=None,
        )
        assert ctx.content_store is None
        assert ctx.enrichment_store is None
        assert ctx.source_store_v2 is None
        assert ctx.ingest_coordinator is None

    def test_appcontext_accepts_real_store_instances_for_new_fields(self) -> None:
        """AppContext accepts real store instances for the new fields."""
        from owlbear_mcp_knowledge.server import AppContext

        conn = sqlite3.connect(":memory:")
        source_store_v2 = SqliteSourceStore(conn)
        ctx = AppContext(
            conn=conn,
            query_service=None,
            graph_store=None,
            ingest_pipeline=None,
            source_store=None,
            source_store_v2=source_store_v2,
        )
        assert ctx.source_store_v2 is source_store_v2

    def test_appcontext_positional_construction_preserves_new_field_defaults(self) -> None:
        """AppContext accepts original 5 positional args; new fields default to None.

        Reviewer gap AC1: keyword-only tests cannot prove positional compatibility.
        This test passes the original 5 args positionally (no kwargs for new fields)
        and asserts that all four new optional fields still default to None.
        """
        from owlbear_mcp_knowledge.server import AppContext

        conn = sqlite3.connect(":memory:")
        # Positional: conn, query_service, graph_store, ingest_pipeline, source_store
        ctx = AppContext(conn, None, None, None, None)
        assert ctx.conn is conn
        assert ctx.content_store is None
        assert ctx.enrichment_store is None
        assert ctx.source_store_v2 is None
        assert ctx.ingest_coordinator is None


# ---------------------------------------------------------------------------
# AC2 — Lifespan instantiates the new stores
# ---------------------------------------------------------------------------


class TestFromAC_LifespanStoreInstantiation:
    """AC2: app_lifespan instantiates all 4 new stores with the correct constructor args."""

    @pytest.mark.asyncio
    async def test_lifespan_yields_sqlite_source_store_v2(self, _heavy_mocks: object) -> None:
        """ctx.source_store_v2 is a SqliteSourceStore instance after lifespan."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert isinstance(ctx.source_store_v2, SqliteSourceStore)

    @pytest.mark.asyncio
    async def test_lifespan_yields_content_store(self, _heavy_mocks: object) -> None:
        """ctx.content_store is a ContentStore instance after lifespan."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert isinstance(ctx.content_store, ContentStore)

    @pytest.mark.asyncio
    async def test_lifespan_yields_enrichment_store(self, _heavy_mocks: object) -> None:
        """ctx.enrichment_store is an EnrichmentStore instance after lifespan."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert isinstance(ctx.enrichment_store, EnrichmentStore)

    @pytest.mark.asyncio
    async def test_lifespan_yields_ingest_coordinator(self, _heavy_mocks: object) -> None:
        """ctx.ingest_coordinator is an IngestCoordinator instance after lifespan."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert isinstance(ctx.ingest_coordinator, IngestCoordinator)

    @pytest.mark.asyncio
    async def test_source_store_v2_shares_conn_with_appcontext(
        self, _heavy_mocks: object
    ) -> None:
        """SqliteSourceStore is constructed with the same conn as AppContext.conn."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            # SqliteSourceStore stores conn as _conn
            assert ctx.source_store_v2._conn is ctx.conn  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_content_store_shares_conn_with_appcontext(
        self, _heavy_mocks: object
    ) -> None:
        """ContentStore is constructed with the same conn as AppContext.conn."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            # ContentStore stores conn as _db
            assert ctx.content_store._db is ctx.conn  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_enrichment_store_shares_graph_with_appcontext(
        self, _heavy_mocks: object
    ) -> None:
        """EnrichmentStore is constructed with the same GraphStore as AppContext.graph_store."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            # EnrichmentStore stores graph as _graph
            assert ctx.enrichment_store._graph is ctx.graph_store  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_ingest_coordinator_uses_source_store_v2(
        self, _heavy_mocks: object
    ) -> None:
        """IngestCoordinator.sources is the SqliteSourceStore (source_store_v2)."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert ctx.ingest_coordinator._sources is ctx.source_store_v2  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_ingest_coordinator_uses_content_store(
        self, _heavy_mocks: object
    ) -> None:
        """IngestCoordinator.content is the ContentStore."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert ctx.ingest_coordinator._content is ctx.content_store  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_ingest_coordinator_uses_enrichment_store(
        self, _heavy_mocks: object
    ) -> None:
        """IngestCoordinator.enrichment is the EnrichmentStore."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert ctx.ingest_coordinator._enrichment is ctx.enrichment_store  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_ingest_coordinator_uses_graph_store(
        self, _heavy_mocks: object
    ) -> None:
        """IngestCoordinator.graph is the same GraphStore as AppContext.graph_store."""
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert ctx.ingest_coordinator._graph is ctx.graph_store  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_content_store_vector_store_identity(
        self, _heavy_mocks: object
    ) -> None:
        """ContentStore._vector_store is the same instance as AppContext.vector_store.

        Reviewer gap AC2: previous tests omitted this field. Both are assigned the
        same `vs` local in app_lifespan — this asserts that identity.
        """
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert ctx.content_store._vector_store is ctx.vector_store  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_content_store_embedding_provider_identity(
        self, tmp_path: object
    ) -> None:
        """ContentStore._embedding_provider is the same instance created in lifespan.

        Reviewer gap AC2: uses an inline patch to capture the BgeM3EmbeddingProvider
        mock and verifies ContentStore received the same instance.
        """
        from owlbear_mcp_knowledge.server import app_lifespan

        server_mock = MagicMock()
        env_overrides = {
            "OWLBEAR_LOCAL_KB_PATH": ":memory:",
            "OWLBEAR_QDRANT_PATH": str(tmp_path) + "/vectors",  # type: ignore[operator]
        }
        with (
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider") as mock_emb_cls,
            patch.dict(os.environ, env_overrides),
        ):
            async with app_lifespan(server_mock) as ctx:
                assert ctx.content_store._embedding_provider is mock_emb_cls.return_value  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_content_store_chunker_is_text_chunker_instance(
        self, _heavy_mocks: object
    ) -> None:
        """ContentStore._chunker is a TextChunker instance (from lifespan's TextChunker()).

        Reviewer gap AC2: chunker wiring was unverified.
        """
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert isinstance(ctx.content_store._chunker, TextChunker)  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_enrichment_store_db_identity_matches_appcontext_conn(
        self, _heavy_mocks: object
    ) -> None:
        """EnrichmentStore._db is the same connection as AppContext.conn.

        Reviewer gap AC2: _graph identity was tested but _db identity was not.
        """
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            assert ctx.enrichment_store._db is ctx.conn  # noqa: SLF001


# ---------------------------------------------------------------------------
# AC3 — ensure_tables() called before yield
# ---------------------------------------------------------------------------


class TestFromAC_EnsureTablesCalled:
    """AC3: ensure_tables() must be called on all 3 stores before the lifespan yields."""

    @pytest.mark.asyncio
    async def test_sqlite_source_store_ensure_tables_called(
        self, _heavy_mocks: object
    ) -> None:
        """SqliteSourceStore.ensure_tables() is called during lifespan startup."""
        from owlbear_mcp_knowledge.server import app_lifespan

        with patch.object(SqliteSourceStore, "ensure_tables") as mock_et:
            async with app_lifespan(_heavy_mocks):
                pass
            mock_et.assert_called_once()

    @pytest.mark.asyncio
    async def test_content_store_ensure_tables_called(
        self, _heavy_mocks: object
    ) -> None:
        """ContentStore.ensure_tables() is called during lifespan startup."""
        from owlbear_mcp_knowledge.server import app_lifespan

        with patch.object(ContentStore, "ensure_tables") as mock_et:
            async with app_lifespan(_heavy_mocks):
                pass
            mock_et.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrichment_store_ensure_tables_called(
        self, _heavy_mocks: object
    ) -> None:
        """EnrichmentStore.ensure_tables() is called during lifespan startup."""
        from owlbear_mcp_knowledge.server import app_lifespan

        with patch.object(EnrichmentStore, "ensure_tables") as mock_et:
            async with app_lifespan(_heavy_mocks):
                pass
            mock_et.assert_called_once()

    @pytest.mark.asyncio
    async def test_source_store_ensure_tables_called_before_yield(
        self, _heavy_mocks: object
    ) -> None:
        """SqliteSourceStore.ensure_tables() is called before the lifespan yields."""
        from owlbear_mcp_knowledge.server import app_lifespan

        call_log: list[str] = []

        original = SqliteSourceStore.ensure_tables

        def tracking_et(self: SqliteSourceStore) -> None:  # type: ignore[misc]
            call_log.append("ensure_tables:source_store_v2")
            return original(self)

        with patch.object(SqliteSourceStore, "ensure_tables", tracking_et):
            async with app_lifespan(_heavy_mocks):
                call_log.append("in_context")

        assert "ensure_tables:source_store_v2" in call_log, (
            "SqliteSourceStore.ensure_tables must be called before lifespan yields"
        )
        et_idx = call_log.index("ensure_tables:source_store_v2")
        ctx_idx = call_log.index("in_context")
        assert et_idx < ctx_idx, (
            "ensure_tables must be called BEFORE the lifespan yields AppContext"
        )

    @pytest.mark.asyncio
    async def test_content_store_ensure_tables_called_before_yield(
        self, _heavy_mocks: object
    ) -> None:
        """ContentStore.ensure_tables() is called before the lifespan yields."""
        from owlbear_mcp_knowledge.server import app_lifespan

        call_log: list[str] = []

        original = ContentStore.ensure_tables

        def tracking_et(self: ContentStore) -> None:  # type: ignore[misc]
            call_log.append("ensure_tables:content_store")
            return original(self)

        with patch.object(ContentStore, "ensure_tables", tracking_et):
            async with app_lifespan(_heavy_mocks):
                call_log.append("in_context")

        assert "ensure_tables:content_store" in call_log, (
            "ContentStore.ensure_tables must be called before lifespan yields"
        )
        et_idx = call_log.index("ensure_tables:content_store")
        ctx_idx = call_log.index("in_context")
        assert et_idx < ctx_idx, (
            "ContentStore.ensure_tables must be called BEFORE the lifespan yields AppContext"
        )

    @pytest.mark.asyncio
    async def test_enrichment_store_ensure_tables_called_before_yield(
        self, _heavy_mocks: object
    ) -> None:
        """EnrichmentStore.ensure_tables() is called before the lifespan yields."""
        from owlbear_mcp_knowledge.server import app_lifespan

        call_log: list[str] = []

        original = EnrichmentStore.ensure_tables

        def tracking_et(self: EnrichmentStore) -> None:  # type: ignore[misc]
            call_log.append("ensure_tables:enrichment_store")
            return original(self)

        with patch.object(EnrichmentStore, "ensure_tables", tracking_et):
            async with app_lifespan(_heavy_mocks):
                call_log.append("in_context")

        assert "ensure_tables:enrichment_store" in call_log, (
            "EnrichmentStore.ensure_tables must be called before lifespan yields"
        )
        et_idx = call_log.index("ensure_tables:enrichment_store")
        ctx_idx = call_log.index("in_context")
        assert et_idx < ctx_idx, (
            "EnrichmentStore.ensure_tables must be called BEFORE the lifespan yields AppContext"
        )


# ---------------------------------------------------------------------------
# AC4 — Existing fields preserved; existing MCP tools unaffected
# ---------------------------------------------------------------------------


class TestFromAC_ExistingFieldsPreserved:
    """AC4: Existing AppContext fields remain populated; existing MCP tools unaffected.

    The new fields may be None while old fields (source_store, ingest_pipeline,
    query_service, graph_store) remain functional.
    """

    def test_existing_construction_still_gives_none_for_new_fields(self) -> None:
        """Old-style AppContext construction (without new fields) leaves new fields as None.

        Regression guard: existing code that constructs AppContext without the new kwargs
        must continue to work, and the new fields must default to None.
        """
        ctx = _make_minimal_app_ctx()
        # All four new fields must be accessible and default to None
        assert ctx.content_store is None
        assert ctx.enrichment_store is None
        assert ctx.source_store_v2 is None
        assert ctx.ingest_coordinator is None

    def test_list_sources_tool_works_with_new_appcontext_shape(self) -> None:
        """list_sources (existing tool) works when new fields are None.

        The existing list_sources tool must function correctly when AppContext
        carries the new fields set to None — i.e., the builder's changes must not
        break existing tool routing.
        """
        from owlbear_mcp_knowledge.server import AppContext, knowledge_sources_list as list_sources

        mock_source_store = MagicMock()
        mock_source_store.list_all.return_value = []

        conn = sqlite3.connect(":memory:")
        # Construct with all new fields = None (AC1 + AC4 contract)
        ctx = AppContext(
            conn=conn,
            query_service=None,
            graph_store=None,
            ingest_pipeline=None,
            source_store=mock_source_store,
            content_store=None,
            enrichment_store=None,
            source_store_v2=None,
            ingest_coordinator=None,
        )
        mcp_ctx = MagicMock()
        mcp_ctx.request_context.lifespan_context = ctx

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(list_sources(mcp_ctx, scope=None))
        assert result == []

    @pytest.mark.asyncio
    async def test_lifespan_populates_old_and_new_fields_simultaneously(
        self, _heavy_mocks: object
    ) -> None:
        """Old fields remain non-None AND new fields are also non-None after lifespan.

        Regression guard: the builder's additions must not displace existing field
        population. Both old (source_store, query_service, ingest_pipeline) and new
        (content_store, enrichment_store, source_store_v2, ingest_coordinator) must
        all be non-None after the lifespan yields.
        """
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.query_service import KnowledgeQueryService
        from owlbear_knowledge.source_store import KnowledgeSourceStore
        from owlbear_mcp_knowledge.server import app_lifespan

        async with app_lifespan(_heavy_mocks) as ctx:
            # Existing fields — must remain populated (regression guard)
            assert isinstance(ctx.source_store, KnowledgeSourceStore)
            assert isinstance(ctx.query_service, KnowledgeQueryService)
            assert isinstance(ctx.ingest_pipeline, IngestPipeline)
            # New fields — must also be populated (AC2); this line fails now
            assert ctx.content_store is not None
            assert ctx.enrichment_store is not None
            assert ctx.source_store_v2 is not None
            assert ctx.ingest_coordinator is not None
