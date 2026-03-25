"""Failing TDD RED tests for GraphEnricher cancellation and draining (#1000).

All tests fail on current HEAD:
- AC 1-5: GraphEnricher has no shutdown(), drain(), _shutdown flag, or cancel
  parameter on schedule_*.
- AC 6: _build_knowledge_toolset() has no cleanup parameter (#998 implements this).
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.memory.knowledge.document_store import DocumentStore
from owlbear.memory.knowledge.enrichment import GraphEnricher
from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Sample data (mirrors test_enrichment.py)
# ---------------------------------------------------------------------------

SAMPLE_ENTITIES = [
    Entity(name="func_a", entity_type=EntityType.FUNCTION, description="A function"),
]
SAMPLE_EDGES = [
    Edge(source_id="s1", target_id="t1", relation=RelationType.DEFINES),
]
SAMPLE_EXTRACTION = ExtractionResult(entities=SAMPLE_ENTITIES, edges=SAMPLE_EDGES)


# ---------------------------------------------------------------------------
# Fixtures (reused from test_enrichment.py conventions)
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
def mock_document_store(conn: sqlite3.Connection, mock_graph_store: MagicMock) -> MagicMock:
    """Mock DocumentStore — matches test_enrichment.py canonical fixture."""
    store = MagicMock(spec=DocumentStore)
    store.conn = conn
    store.graph_store = mock_graph_store
    return store


@pytest.fixture
def enricher(
    conn: sqlite3.Connection,
    mock_graph_store: MagicMock,
    mock_graph_builder: MagicMock,
    mock_document_store: MagicMock,
) -> GraphEnricher:
    """GraphEnricher with graph_builder, bg_concurrency=1."""
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
    """Insert stub document_status rows to satisfy inter-doc min-doc threshold."""
    for i in range(count):
        conn.execute(
            "INSERT OR IGNORE INTO document_status (document_id, scope, status) VALUES (?, ?, ?)",
            (f"seed_doc_{i}", scope, "enriched"),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# AC-1: shutdown() cancels running tasks and empties _background_tasks
# ---------------------------------------------------------------------------


class TestFromAC_GraphEnricherShutdown:
    """shutdown() cancels all running tracked tasks and leaves _background_tasks empty.

    All tests fail on current HEAD: GraphEnricher has no shutdown() method.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_cancels_running_tracked_task(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        """Running task receives CancelledError during shutdown()."""
        hang_start = asyncio.Event()
        was_cancelled = asyncio.Event()

        async def hanging_build(*_args: object, **_kwargs: object) -> MagicMock:
            hang_start.set()
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                was_cancelled.set()
                raise
            return MagicMock(edges=[], edges_added=0)  # pragma: no cover

        builder = MagicMock()
        builder.build = hanging_build
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
        await asyncio.wait_for(hang_start.wait(), timeout=1.0)

        await enricher.shutdown()  # AttributeError on current HEAD

        assert was_cancelled.is_set(), "Task must receive CancelledError during shutdown"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_leaves_background_tasks_empty(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        """_background_tasks is empty after shutdown() returns."""
        hang_start = asyncio.Event()

        async def hanging_build(*_args: object, **_kwargs: object) -> MagicMock:
            hang_start.set()
            await asyncio.sleep(100)
            return MagicMock(edges=[], edges_added=0)  # pragma: no cover

        builder = MagicMock()
        builder.build = hanging_build
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
        await asyncio.wait_for(hang_start.wait(), timeout=1.0)

        await enricher.shutdown()  # AttributeError on current HEAD

        assert len(enricher._background_tasks) == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_with_no_tasks_returns_immediately(
        self,
        enricher: GraphEnricher,
    ) -> None:
        """shutdown() on empty enricher returns without hanging."""
        await asyncio.wait_for(
            enricher.shutdown(),
            timeout=1.0,  # AttributeError on current HEAD
        )
        assert len(enricher._background_tasks) == 0


# ---------------------------------------------------------------------------
# AC-2: drain() awaits normal completion — no CancelledError, empty set
# ---------------------------------------------------------------------------


class TestFromAC_GraphEnricherDrain:
    """drain() awaits running tasks to normal completion and leaves _background_tasks empty.

    All tests fail on current HEAD: GraphEnricher has no drain() method.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_drain_awaits_task_to_normal_completion(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        """drain() lets tasks complete normally; task is not cancelled."""
        completed = asyncio.Event()
        did_cancel = asyncio.Event()
        release = asyncio.Event()

        async def normal_build(*_args: object, **_kwargs: object) -> MagicMock:
            try:
                await release.wait()
                completed.set()
            except asyncio.CancelledError:
                did_cancel.set()
                raise
            return MagicMock(edges=[], edges_added=0)

        builder = MagicMock()
        builder.build = normal_build
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
        await asyncio.sleep(0.05)  # let task start and reach the await

        release.set()
        await enricher.drain()  # AttributeError on current HEAD

        assert completed.is_set(), "Task must complete normally during drain()"
        assert not did_cancel.is_set(), "drain() must not cancel tasks"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_drain_leaves_background_tasks_empty(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
    ) -> None:
        """_background_tasks is empty after drain() returns."""
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
        await asyncio.sleep(0.05)

        release.set()
        await enricher.drain()  # AttributeError on current HEAD

        assert len(enricher._background_tasks) == 0


# ---------------------------------------------------------------------------
# AC-3: schedule_* are no-ops after shutdown() returns
# ---------------------------------------------------------------------------


class TestFromAC_GraphEnricherScheduleAfterShutdown:
    """schedule_graph_enrichment() and schedule_inter_doc_enrichment() are no-ops
    after shutdown() returns — no task is created, no coroutine executes.

    All tests fail on current HEAD: GraphEnricher has no shutdown() method.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_graph_enrichment_is_noop_after_shutdown(
        self,
        enricher: GraphEnricher,
        mock_graph_builder: MagicMock,
    ) -> None:
        """schedule_graph_enrichment() does not create tasks or execute work after shutdown()."""
        await enricher.shutdown()  # AttributeError on current HEAD

        size_before = len(enricher._background_tasks)
        build_count_before = mock_graph_builder.build.call_count
        enricher.schedule_graph_enrichment("doc2", [SAMPLE_EXTRACTION], "global")
        await asyncio.sleep(0.05)  # give event loop a tick to dispatch any leaked task

        assert len(enricher._background_tasks) == size_before, (
            "schedule_graph_enrichment() must not create any task after shutdown"
        )
        assert mock_graph_builder.build.call_count == build_count_before, (
            "schedule_graph_enrichment() must not execute any work after shutdown"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_inter_doc_enrichment_is_noop_after_shutdown(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
        mock_inter_doc_builder: MagicMock,
    ) -> None:
        """schedule_inter_doc_enrichment() does not create tasks after shutdown()."""
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

        await enricher.shutdown()  # AttributeError on current HEAD

        size_before = len(enricher._background_tasks)
        build_count_before = mock_inter_doc_builder.build.call_count
        enricher.schedule_inter_doc_enrichment("doc1", [SAMPLE_EXTRACTION], "global")
        await asyncio.sleep(0.05)  # give event loop a tick to dispatch any leaked task

        assert len(enricher._background_tasks) == size_before, (
            "schedule_inter_doc_enrichment() must not create any task after shutdown"
        )
        assert mock_inter_doc_builder.build.call_count == build_count_before, (
            "schedule_inter_doc_enrichment() must not execute any work after shutdown"
        )


# ---------------------------------------------------------------------------
# AC-4: schedule_* are no-ops when cancel parameter is_set() returns True
# ---------------------------------------------------------------------------


class TestFromAC_GraphEnricherCancelSignal:
    """schedule_*() are no-ops when the cancel parameter's is_set() returns True.

    All tests fail on current HEAD: schedule_* do not accept a cancel parameter.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_graph_enrichment_is_noop_when_cancel_set(
        self,
        enricher: GraphEnricher,
        mock_graph_builder: MagicMock,
    ) -> None:
        """schedule_graph_enrichment() creates no task and executes no work when cancel.is_set()."""
        cancel = MagicMock()
        cancel.is_set.return_value = True

        size_before = len(enricher._background_tasks)
        build_count_before = mock_graph_builder.build.call_count
        # TypeError on current HEAD: schedule_graph_enrichment() has no cancel param
        enricher.schedule_graph_enrichment("doc1", [SAMPLE_EXTRACTION], "global", cancel=cancel)
        await asyncio.sleep(0.05)  # give event loop a tick to dispatch any leaked task

        assert len(enricher._background_tasks) == size_before, (
            "schedule_graph_enrichment() must not create any task when cancel.is_set() is True"
        )
        assert mock_graph_builder.build.call_count == build_count_before, (
            "schedule_graph_enrichment() must not execute any work when cancel.is_set() is True"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_inter_doc_enrichment_is_noop_when_cancel_set(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
        mock_inter_doc_builder: MagicMock,
    ) -> None:
        """schedule_inter_doc_enrichment() creates no task or work when cancel.is_set()."""
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

        cancel = MagicMock()
        cancel.is_set.return_value = True

        size_before = len(enricher._background_tasks)
        build_count_before = mock_inter_doc_builder.build.call_count
        # TypeError on current HEAD: schedule_inter_doc_enrichment() has no cancel param
        enricher.schedule_inter_doc_enrichment(
            "doc1", [SAMPLE_EXTRACTION], "global", cancel=cancel
        )
        await asyncio.sleep(0.05)  # give event loop a tick to dispatch any leaked task

        assert len(enricher._background_tasks) == size_before, (
            "schedule_inter_doc_enrichment() must not create any task when cancel.is_set() is True"
        )
        assert mock_inter_doc_builder.build.call_count == build_count_before, (
            "schedule_inter_doc_enrichment() must not execute any work when cancel.is_set() is True"
        )


# ---------------------------------------------------------------------------
# AC-5: direct _shutdown flag prevents task creation (distinct from AC-3)
# ---------------------------------------------------------------------------


class TestFromAC_GraphEnricherShutdownFlag:
    """Setting enricher._shutdown = True directly prevents schedule_* from creating tasks.

    Distinct from AC-3 (which tests the shutdown() method flow).
    Tests fail on current HEAD: GraphEnricher._shutdown is not consulted in schedule_*.
    """

    def test_enricher_has_shutdown_flag_initialized_false(
        self,
        enricher: GraphEnricher,
    ) -> None:
        """GraphEnricher must initialize _shutdown = False on construction.

        Fails on current HEAD: GraphEnricher has no _shutdown attribute.
        """
        assert hasattr(enricher, "_shutdown"), "GraphEnricher must have _shutdown attribute"
        assert enricher._shutdown is False, "_shutdown must initialize to False"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_flag_set_directly_prevents_schedule_graph_enrichment(
        self,
        enricher: GraphEnricher,
        mock_graph_builder: MagicMock,
    ) -> None:
        """_shutdown=True directly prevents schedule_graph_enrichment creating tasks or work."""
        enricher._shutdown = True  # set without calling shutdown()

        size_before = len(enricher._background_tasks)
        build_count_before = mock_graph_builder.build.call_count
        enricher.schedule_graph_enrichment("doc1", [SAMPLE_EXTRACTION], "global")
        await asyncio.sleep(0.05)  # give event loop a tick to dispatch any leaked task

        assert len(enricher._background_tasks) == size_before, (
            "_shutdown=True must block task creation in schedule_graph_enrichment"
        )
        assert mock_graph_builder.build.call_count == build_count_before, (
            "_shutdown=True must prevent work execution in schedule_graph_enrichment"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_flag_set_directly_prevents_schedule_inter_doc_enrichment(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_document_store: MagicMock,
        mock_inter_doc_builder: MagicMock,
    ) -> None:
        """_shutdown=True directly prevents schedule_inter_doc_enrichment creating tasks or work."""
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

        enricher._shutdown = True  # set without calling shutdown()

        size_before = len(enricher._background_tasks)
        build_count_before = mock_inter_doc_builder.build.call_count
        enricher.schedule_inter_doc_enrichment("doc1", [SAMPLE_EXTRACTION], "global")
        await asyncio.sleep(0.05)  # give event loop a tick to dispatch any leaked task

        assert len(enricher._background_tasks) == size_before, (
            "_shutdown=True must block task creation in schedule_inter_doc_enrichment"
        )
        assert mock_inter_doc_builder.build.call_count == build_count_before, (
            "_shutdown=True must prevent work execution in schedule_inter_doc_enrichment"
        )


# ---------------------------------------------------------------------------
# AC-6: bootstrap registers enricher.shutdown in BootstrapResult.cleanup
# NOTE: This class turns green with #998, not #871.
# ---------------------------------------------------------------------------


class TestFromAC_GraphEnricherBootstrapCleanup:
    """Bootstrap registers enricher.shutdown in BootstrapResult.cleanup when enricher is not None.

    NOTE: These tests turn green with #998, not #871. They remain red until
    #998 implements bootstrap enricher.shutdown cleanup registration.

    Fail on current HEAD: _build_knowledge_toolset() has no cleanup parameter
    (TypeError on the call site).
    """

    def test_build_knowledge_toolset_registers_enricher_shutdown_when_inter_doc_enabled(
        self,
        tmp_path: Path,
    ) -> None:
        """When inter_doc_graph_building=True, enricher.shutdown is appended to cleanup.

        Uses the same patching pattern as TestBuildKnowledgeToolset in test_bootstrap.py.
        Fails on current HEAD: _build_knowledge_toolset has no cleanup kwarg.
        """
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        cleanup: list = []

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None, "_build_knowledge_infra returned None unexpectedly"

            # TypeError on current HEAD — _build_knowledge_toolset has no cleanup kwarg
            result = _build_knowledge_toolset(
                tmp_path,
                infra,
                chat_model="test-model",
                inter_doc_graph_building=True,
                cleanup=cleanup,
            )

        assert result is not None, (
            "_build_knowledge_toolset returned None with inter_doc_graph_building=True"
        )
        assert any(
            callable(c)
            and getattr(c, "__name__", "") == "shutdown"
            and isinstance(getattr(c, "__self__", None), GraphEnricher)
            for c in cleanup
        ), (
            "enricher.shutdown not in cleanup. Got: "
            f"{[getattr(c, '__name__', str(c)) for c in cleanup]}"
        )

    def test_no_enricher_shutdown_when_inter_doc_disabled(
        self,
        tmp_path: Path,
    ) -> None:
        """When inter_doc_graph_building=False, no enricher.shutdown appears in cleanup.

        NOTE: Also turns green with #998.
        Fails on current HEAD: _build_knowledge_toolset has no cleanup kwarg (TypeError).
        """
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        cleanup: list = []

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None, "_build_knowledge_infra returned None unexpectedly"

            # TypeError on current HEAD — _build_knowledge_toolset has no cleanup kwarg
            result = _build_knowledge_toolset(
                tmp_path,
                infra,
                chat_model="test-model",
                inter_doc_graph_building=False,
                cleanup=cleanup,
            )

        assert result is not None
        assert not any(
            callable(c)
            and getattr(c, "__name__", "") == "shutdown"
            and isinstance(getattr(c, "__self__", None), GraphEnricher)
            for c in cleanup
        ), "enricher.shutdown must not be in cleanup when inter_doc_graph_building=False"
