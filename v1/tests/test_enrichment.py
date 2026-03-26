"""Tests for GraphEnricher — background graph enrichment scheduling."""

from __future__ import annotations

import asyncio
import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.memory.knowledge.document_store import DocumentStore
from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.schema import init_db

try:
    from owlbear.memory.knowledge.graph_builder import GraphBuildResult
except ImportError:
    from pydantic import BaseModel as _BaseModel

    from owlbear.memory.knowledge.models import Edge as _Edge

    class GraphBuildResult(_BaseModel):  # type: ignore[no-redef]
        edges_added: int = 0
        edges: list[_Edge] = []


# ---------------------------------------------------------------------------
# Import under test — will fail until enrichment.py exists
# ---------------------------------------------------------------------------

from owlbear.memory.knowledge.enrichment import GraphEnricher

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ENTITIES = [
    Entity(name="func_a", entity_type=EntityType.FUNCTION, description="A function"),
]
SAMPLE_EDGES = [
    Edge(source_id="s1", target_id="t1", relation=RelationType.DEFINES),
]
SAMPLE_EXTRACTION = ExtractionResult(entities=SAMPLE_ENTITIES, edges=SAMPLE_EDGES)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.Connection(":memory:")
    init_db(c)
    return c


@pytest.fixture
def graph_store(conn: sqlite3.Connection) -> GraphStore:
    return GraphStore(conn)


@pytest.fixture
def mock_graph_store() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_document_store(conn: sqlite3.Connection, mock_graph_store: MagicMock) -> MagicMock:
    """Mock DocumentStore with conn and set_status exposed."""
    store = MagicMock(spec=DocumentStore)
    store.conn = conn
    store.graph_store = mock_graph_store
    return store


@pytest.fixture
def mock_graph_builder() -> MagicMock:
    builder = MagicMock()
    builder.build = AsyncMock(return_value=GraphBuildResult())
    return builder


@pytest.fixture
def mock_inter_doc_builder() -> MagicMock:
    builder = MagicMock()
    builder.build = AsyncMock(return_value=GraphBuildResult())
    return builder


@pytest.fixture
def enricher(
    conn: sqlite3.Connection,
    mock_graph_store: MagicMock,
    mock_graph_builder: MagicMock,
    mock_document_store: MagicMock,
) -> GraphEnricher:
    """GraphEnricher with graph_builder wired in."""
    return GraphEnricher(
        conn=conn,
        graph_store=mock_graph_store,
        graph_builder=mock_graph_builder,
        inter_doc_builder=None,
        document_store=mock_document_store,
        pipeline_name="ingest",
        bg_concurrency=5,
    )


@pytest.fixture
def enricher_with_inter_doc(
    conn: sqlite3.Connection,
    mock_graph_store: MagicMock,
    mock_graph_builder: MagicMock,
    mock_inter_doc_builder: MagicMock,
    mock_document_store: MagicMock,
) -> GraphEnricher:
    """GraphEnricher with both builders wired in."""
    return GraphEnricher(
        conn=conn,
        graph_store=mock_graph_store,
        graph_builder=mock_graph_builder,
        inter_doc_builder=mock_inter_doc_builder,
        document_store=mock_document_store,
        pipeline_name="ingest",
        bg_concurrency=5,
    )


# ---------------------------------------------------------------------------
# AC-1: GraphEnricher class exists with expected methods
# ---------------------------------------------------------------------------


class TestGraphEnricherConstruction:
    """GraphEnricher class exists and has the expected interface."""

    def test_class_exists(self) -> None:
        assert GraphEnricher is not None

    def test_has_schedule_graph_enrichment(self, enricher: GraphEnricher) -> None:
        assert callable(getattr(enricher, "schedule_graph_enrichment", None))

    def test_has_schedule_inter_doc_enrichment(self, enricher: GraphEnricher) -> None:
        assert callable(getattr(enricher, "schedule_inter_doc_enrichment", None))

    def test_has_private_enrich_graph(self, enricher: GraphEnricher) -> None:
        assert callable(getattr(enricher, "_enrich_graph", None))

    def test_has_private_enrich_graph_inner(self, enricher: GraphEnricher) -> None:
        assert callable(getattr(enricher, "_enrich_graph_inner", None))

    def test_has_private_enrich_inter_doc_graph(self, enricher: GraphEnricher) -> None:
        assert callable(getattr(enricher, "_enrich_inter_doc_graph", None))


# ---------------------------------------------------------------------------
# AC-2: GraphEnricher owns _background_tasks and _bg_semaphore
# ---------------------------------------------------------------------------


class TestGraphEnricherOwnership:
    """GraphEnricher owns background task tracking and concurrency control."""

    def test_owns_background_tasks_set(self, enricher: GraphEnricher) -> None:
        assert isinstance(enricher._background_tasks, set)

    def test_owns_bg_semaphore(self, enricher: GraphEnricher) -> None:
        assert isinstance(enricher._bg_semaphore, asyncio.Semaphore)

    def test_default_semaphore_value(self, enricher: GraphEnricher) -> None:
        assert enricher._bg_semaphore._value == 5

    def test_custom_semaphore_value(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_graph_builder: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        e = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=mock_graph_builder,
            inter_doc_builder=None,
            document_store=mock_document_store,
            pipeline_name="test",
            bg_concurrency=3,
        )
        assert e._bg_semaphore._value == 3


# ---------------------------------------------------------------------------
# AC-3: Constructor signature
# ---------------------------------------------------------------------------


class TestGraphEnricherInit:
    """GraphEnricher.__init__ takes all required parameters."""

    def test_all_params(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_graph_builder: MagicMock,
        mock_inter_doc_builder: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        e = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=mock_graph_builder,
            inter_doc_builder=mock_inter_doc_builder,
            document_store=mock_document_store,
            pipeline_name="test",
            bg_concurrency=2,
        )
        assert e is not None

    def test_none_builders_accepted(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        e = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=None,
            inter_doc_builder=None,
            document_store=mock_document_store,
            pipeline_name="test",
            bg_concurrency=5,
        )
        assert e is not None


# ---------------------------------------------------------------------------
# Enrichment behavior — schedule_graph_enrichment
# ---------------------------------------------------------------------------


class TestScheduleGraphEnrichment:
    """schedule_graph_enrichment schedules background graph building."""

    @pytest.mark.anyio
    async def test_schedules_task(
        self, enricher: GraphEnricher, mock_graph_builder: MagicMock
    ) -> None:
        enricher.schedule_graph_enrichment("doc-1", [SAMPLE_EXTRACTION], "global")
        await asyncio.sleep(0.01)
        mock_graph_builder.build.assert_awaited_once()

    @pytest.mark.anyio
    async def test_no_op_when_no_graph_builder(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        e = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=None,
            inter_doc_builder=None,
            document_store=mock_document_store,
            pipeline_name="test",
            bg_concurrency=5,
        )
        # Should not raise
        e.schedule_graph_enrichment("doc-1", [SAMPLE_EXTRACTION], "global")
        await asyncio.sleep(0.01)

    @pytest.mark.anyio
    async def test_no_op_when_no_entities(
        self, enricher: GraphEnricher, mock_graph_builder: MagicMock
    ) -> None:
        empty_extraction = ExtractionResult(entities=[], edges=[])
        enricher.schedule_graph_enrichment("doc-1", [empty_extraction], "global")
        await asyncio.sleep(0.01)
        mock_graph_builder.build.assert_not_awaited()


# ---------------------------------------------------------------------------
# Enrichment behavior — _enrich_graph_inner
# ---------------------------------------------------------------------------


class TestEnrichGraphInner:
    """_enrich_graph_inner runs the graph builder and stores edges."""

    @pytest.mark.anyio
    async def test_builds_and_stores_edges(
        self,
        enricher: GraphEnricher,
        mock_graph_builder: MagicMock,
        mock_graph_store: MagicMock,
        conn: sqlite3.Connection,
    ) -> None:
        # Insert a document_status row so the idempotency check passes.
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-1", "indexed", "test.txt", "global", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        inferred_edge = Edge(
            source_id="e1", target_id="e2", relation=RelationType.DEFINES, weight=0.5
        )
        mock_graph_builder.build = AsyncMock(
            return_value=GraphBuildResult(edges_added=1, edges=[inferred_edge])
        )

        await enricher._enrich_graph_inner("doc-1", list(SAMPLE_ENTITIES), "global")

        mock_graph_store.insert_edge.assert_called()
        edge_calls = [c[0][0] for c in mock_graph_store.insert_edge.call_args_list]
        assert any(e.source_id == "e1" and e.target_id == "e2" for e in edge_calls)

    @pytest.mark.anyio
    async def test_skips_already_enriched(
        self,
        enricher: GraphEnricher,
        mock_graph_builder: MagicMock,
        conn: sqlite3.Connection,
    ) -> None:
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-1", "graph_enriched", "test.txt", "global", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        await enricher._enrich_graph_inner("doc-1", list(SAMPLE_ENTITIES), "global")
        mock_graph_builder.build.assert_not_awaited()

    @pytest.mark.anyio
    async def test_stamps_provenance(
        self,
        enricher: GraphEnricher,
        mock_graph_builder: MagicMock,
        mock_graph_store: MagicMock,
        conn: sqlite3.Connection,
    ) -> None:
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-1", "indexed", "test.txt", "global", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        inferred_edge = Edge(source_id="e1", target_id="e2", relation=RelationType.DEFINES)
        mock_graph_builder.build = AsyncMock(
            return_value=GraphBuildResult(edges_added=1, edges=[inferred_edge])
        )

        await enricher._enrich_graph_inner("doc-1", list(SAMPLE_ENTITIES), "global")

        edge_calls = [c[0][0] for c in mock_graph_store.insert_edge.call_args_list]
        assert any(
            e.metadata.get("source_task") == "graph_enrichment"
            and e.metadata.get("source_pipeline") == "ingest"
            for e in edge_calls
        )

    @pytest.mark.anyio
    async def test_sets_status_on_success(
        self,
        enricher: GraphEnricher,
        mock_document_store: MagicMock,
        conn: sqlite3.Connection,
    ) -> None:
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-1", "indexed", "test.txt", "global", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        await enricher._enrich_graph_inner("doc-1", list(SAMPLE_ENTITIES), "global")
        mock_document_store.set_status.assert_called_with("doc-1", "graph_enriched", scope="global")


# ---------------------------------------------------------------------------
# Enrichment behavior — schedule_inter_doc_enrichment
# ---------------------------------------------------------------------------


class TestScheduleInterDocEnrichment:
    """schedule_inter_doc_enrichment schedules inter-doc graph building."""

    @pytest.mark.anyio
    async def test_schedules_task(
        self,
        enricher_with_inter_doc: GraphEnricher,
        mock_inter_doc_builder: MagicMock,
        conn: sqlite3.Connection,
    ) -> None:
        # Need at least 2 docs in scope for inter-doc enrichment.
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-1", "indexed", "a.txt", "global", "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-2", "indexed", "b.txt", "global", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        enricher_with_inter_doc.schedule_inter_doc_enrichment(
            "doc-1", [SAMPLE_EXTRACTION], "global"
        )
        await asyncio.sleep(0.01)
        mock_inter_doc_builder.build.assert_awaited_once()

    @pytest.mark.anyio
    async def test_no_op_when_no_inter_doc_builder(self, enricher: GraphEnricher) -> None:
        # enricher has inter_doc_builder=None
        enricher.schedule_inter_doc_enrichment("doc-1", [SAMPLE_EXTRACTION], "global")
        await asyncio.sleep(0.01)

    @pytest.mark.anyio
    async def test_skips_when_fewer_than_2_docs(
        self,
        enricher_with_inter_doc: GraphEnricher,
        mock_inter_doc_builder: MagicMock,
        conn: sqlite3.Connection,
    ) -> None:
        # Only 1 doc in scope.
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-1", "indexed", "a.txt", "global", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        enricher_with_inter_doc.schedule_inter_doc_enrichment(
            "doc-1", [SAMPLE_EXTRACTION], "global"
        )
        await asyncio.sleep(0.01)
        mock_inter_doc_builder.build.assert_not_awaited()


# ---------------------------------------------------------------------------
# Semaphore bounds
# ---------------------------------------------------------------------------


class TestEnricherSemaphoreBounds:
    """Enrichment tasks are bounded by the shared semaphore."""

    @pytest.mark.anyio
    async def test_enrich_graph_bounded(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        max_concurrent = 0
        current = 0
        lock = asyncio.Lock()

        async def slow_build(
            _entities: list,
            *,
            scope: str,  # noqa: ARG001
            document_id: str,  # noqa: ARG001
        ) -> GraphBuildResult:
            nonlocal max_concurrent, current
            async with lock:
                current += 1
                max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.05)
            async with lock:
                current -= 1
            return GraphBuildResult()

        mock_builder = MagicMock()
        mock_builder.build = slow_build

        e = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=mock_builder,
            inter_doc_builder=None,
            document_store=mock_document_store,
            pipeline_name="test",
            bg_concurrency=2,
        )

        tasks = [
            asyncio.create_task(e._enrich_graph(f"doc-{i}", SAMPLE_ENTITIES, "global"))
            for i in range(5)
        ]
        await asyncio.gather(*tasks)
        assert max_concurrent <= 2

    @pytest.mark.anyio
    async def test_enrich_inter_doc_bounded(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        max_concurrent = 0
        current = 0
        lock = asyncio.Lock()

        async def slow_build(
            _entities: list,
            *,
            scope: str,  # noqa: ARG001
            document_id: str,  # noqa: ARG001
        ) -> GraphBuildResult:
            nonlocal max_concurrent, current
            async with lock:
                current += 1
                max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.05)
            async with lock:
                current -= 1
            return GraphBuildResult()

        mock_inter = MagicMock()
        mock_inter.build = slow_build

        e = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=None,
            inter_doc_builder=mock_inter,
            document_store=mock_document_store,
            pipeline_name="test",
            bg_concurrency=2,
        )

        tasks = [
            asyncio.create_task(e._enrich_inter_doc_graph(f"doc-{i}", SAMPLE_ENTITIES, "global"))
            for i in range(5)
        ]
        await asyncio.gather(*tasks)
        assert max_concurrent <= 2
