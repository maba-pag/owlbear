"""TDD RED tests for GraphEnricher AC 4 and AC 5 (drain branch) — #871.

Covers the gaps left by test_enrichment_cancellation.py (task #1000):
- AC 4: drain() must set _shutdown = True (not yet implemented)
- AC 5: schedule_* must be no-ops after drain() (not yet tested for drain branch)

Current HEAD: drain() does NOT set _shutdown = True, so both classes fail.
"""

from __future__ import annotations

import asyncio
import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.memory.knowledge.enrichment import GraphEnricher
from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.schema import init_db

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
    c = sqlite3.connect(":memory:")
    init_db(c)
    return c


@pytest.fixture
def mock_graph_store() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_document_store(conn: sqlite3.Connection, mock_graph_store: MagicMock) -> MagicMock:
    store = MagicMock()
    store.conn = conn
    store.graph_store = mock_graph_store
    return store


@pytest.fixture
def mock_graph_builder() -> MagicMock:
    builder = MagicMock()
    builder.build = AsyncMock(return_value=MagicMock(edges=[], edges_added=0))
    return builder


@pytest.fixture
def mock_inter_doc_builder() -> MagicMock:
    builder = MagicMock()
    builder.build = AsyncMock(return_value=MagicMock(edges=[], edges_added=0))
    return builder


@pytest.fixture
def enricher(
    conn: sqlite3.Connection,
    mock_graph_store: MagicMock,
    mock_graph_builder: MagicMock,
    mock_document_store: MagicMock,
) -> GraphEnricher:
    return GraphEnricher(
        conn=conn,
        graph_store=mock_graph_store,
        graph_builder=mock_graph_builder,
        inter_doc_builder=None,
        document_store=mock_document_store,
        pipeline_name="test",
        bg_concurrency=1,
    )


def _seed_document_count(conn: sqlite3.Connection, scope: str, count: int = 2) -> None:
    for i in range(count):
        conn.execute(
            "INSERT OR IGNORE INTO document_status (document_id, scope, status) VALUES (?, ?, ?)",
            (f"seed_doc_{i}", scope, "enriched"),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# AC 4: drain() must set _shutdown = True
# ---------------------------------------------------------------------------


class TestFromAC_DrainSetsShutdownFlag:
    """drain() must set _shutdown = True so subsequent schedule_* calls are blocked.

    AC 4: "Add async drain() that sets _shutdown = True, awaits all tracked tasks
    without cancelling, and leaves _background_tasks empty on return."

    Current HEAD: drain() does NOT set _shutdown = True — both tests fail with:
        assert enricher._shutdown is True
        AssertionError
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_drain_sets_shutdown_flag_when_no_tasks_pending(
        self,
        enricher: GraphEnricher,
    ) -> None:
        """drain() sets _shutdown = True even when there are no in-flight tasks."""
        assert enricher._shutdown is False, "precondition: starts False"

        await enricher.drain()

        assert enricher._shutdown is True, "drain() must set _shutdown = True"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_drain_sets_shutdown_flag_after_task_completes(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        """drain() sets _shutdown = True after awaiting an in-flight task to completion."""
        release = asyncio.Event()

        async def finishing_build(*_args: object, **_kwargs: object) -> MagicMock:
            await release.wait()
            return MagicMock(edges=[], edges_added=0)

        builder = MagicMock()
        builder.build = finishing_build
        enricher = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=builder,
            inter_doc_builder=None,
            document_store=mock_document_store,
            pipeline_name="test",
            bg_concurrency=1,
        )

        enricher.schedule_graph_enrichment("doc1", [SAMPLE_EXTRACTION], "global")
        await asyncio.sleep(0.05)  # let task start

        release.set()
        await enricher.drain()

        assert enricher._shutdown is True, "drain() must set _shutdown = True after task completes"


# ---------------------------------------------------------------------------
# AC 5 (drain branch): schedule_* are no-ops after drain() returns
# ---------------------------------------------------------------------------


class TestFromAC_ScheduleNoopAfterDrain:
    """schedule_graph_enrichment() and schedule_inter_doc_enrichment() are no-ops
    after drain() returns — no task is created, no coroutine executes.

    AC 5: "Subsequent schedule_* calls are no-ops after either shutdown() or
    drain() has been called."

    Current HEAD: drain() does NOT set _shutdown, so schedule_* proceeds normally
    after drain(). Both tests fail with:
        assert len(enricher._background_tasks) == size_before
        AssertionError (task WAS created)
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_graph_enrichment_is_noop_after_drain(
        self,
        enricher: GraphEnricher,
        mock_graph_builder: MagicMock,
    ) -> None:
        """schedule_graph_enrichment() creates no task and executes no work after drain()."""
        await enricher.drain()

        size_before = len(enricher._background_tasks)
        build_count_before = mock_graph_builder.build.call_count

        enricher.schedule_graph_enrichment("doc1", [SAMPLE_EXTRACTION], "global")

        # Immediate synchronous check — asyncio.create_task() adds synchronously.
        assert len(enricher._background_tasks) == size_before, (
            "schedule_graph_enrichment() must not create a task after drain() (pre-yield check)"
        )

        await asyncio.sleep(0.05)  # give event loop a tick to flush any leaked task

        assert len(enricher._background_tasks) == size_before, (
            "schedule_graph_enrichment() must not create any task after drain()"
        )
        assert mock_graph_builder.build.call_count == build_count_before, (
            "schedule_graph_enrichment() must not execute any work after drain()"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_inter_doc_enrichment_is_noop_after_drain(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
        mock_inter_doc_builder: MagicMock,
    ) -> None:
        """schedule_inter_doc_enrichment() creates no task and executes no work after drain()."""
        _seed_document_count(conn, "global")

        enricher = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=None,
            inter_doc_builder=mock_inter_doc_builder,
            document_store=mock_document_store,
            pipeline_name="test",
            bg_concurrency=1,
        )

        await enricher.drain()

        size_before = len(enricher._background_tasks)
        build_count_before = mock_inter_doc_builder.build.call_count

        enricher.schedule_inter_doc_enrichment("doc1", [SAMPLE_EXTRACTION], "global")

        # Immediate synchronous check — asyncio.create_task() adds synchronously.
        assert len(enricher._background_tasks) == size_before, (
            "schedule_inter_doc_enrichment() must not create a task after drain() (pre-yield check)"
        )

        await asyncio.sleep(0.05)  # give event loop a tick to flush any leaked task

        assert len(enricher._background_tasks) == size_before, (
            "schedule_inter_doc_enrichment() must not create any task after drain()"
        )
        assert mock_inter_doc_builder.build.call_count == build_count_before, (
            "schedule_inter_doc_enrichment() must not execute any work after drain()"
        )
