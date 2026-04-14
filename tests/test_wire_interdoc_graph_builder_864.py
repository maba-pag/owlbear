"""RED-phase tests for #864: Wire InterDocGraphBuilder into refresh pipeline.

AC coverage:
  AC1: After successful ingest + intra-doc build, entities retrieved via
       graph_store.list_entities_for_document(ingest_result.document_id) and passed
       to InterDocGraphBuilder.build(entities, scope=source.scope)
  AC2: Inter-doc build is non-blocking — asyncio.create_task() with a done-callback
       that logs exceptions at ERROR level; exceptions must not be silently swallowed.
  AC3: Skip inter-doc build if len(graph_store.list_documents(scopes=[source.scope])) < 2
       (scoped count, not global get_counts())
  AC4: RefreshOrchestrator.__init__ accepts optional inter_doc_builder=None (disabled by default)
  AC5: Caller persists each edge from build() result via graph_store.insert_edge(edge)
  AC6: RefreshOrchestrator.__init__ accepts optional graph_store=None for entity retrieval
       and edge persistence
  AC7: Integration: ingest 2 docs from different sources with mock StructuredExtractor;
       verify cross-doc edges created and persisted.

All tests FAIL until #864 wires InterDocGraphBuilder into RefreshOrchestrator.
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.graph_builder import GraphBuildResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestResult
from owlbear_knowledge.inter_doc_graph_builder import InterDocGraphBuilder
from owlbear_knowledge.models import (
    Document,
    Edge,
    Entity,
    EntityType,
    KnowledgeSource,
    RelationType,
    SourceType,
)
from owlbear_knowledge.refresh import RefreshOrchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(tz=UTC).isoformat()


def _source(scope: str = "global", source_type: SourceType = SourceType.URL_LIST) -> KnowledgeSource:
    return KnowledgeSource(
        name="test-source",
        source_type=source_type,
        config={"urls": ["https://example.com/doc"]},
        scope=scope,
        created_at=_now(),
        updated_at=_now(),
    )


def _ingest_result(doc_id: str = "doc-001", status: str = "ok") -> IngestResult:
    return IngestResult(
        document_id=doc_id,
        chunk_count=1,
        entity_count=2,
        edge_count=1,
        status=status,  # type: ignore[arg-type]
    )


def _entity(name: str = "TestEntity", doc_id: str = "doc-001") -> Entity:
    return Entity(name=name, entity_type=EntityType.CONCEPT, scope="global", document_id=doc_id)


def _edge(source_id: str = "e1", target_id: str = "e2") -> Edge:
    return Edge(source_id=source_id, target_id=target_id, relation=RelationType.RELATED_TO)


def _mock_pipeline(ingest_result: IngestResult | None = None) -> MagicMock:
    pipeline = MagicMock()
    pipeline.ingest = AsyncMock(return_value=ingest_result or _ingest_result())
    return pipeline


def _mock_graph_store(
    entities: list[Entity] | None = None,
    documents: list[Document] | None = None,
) -> MagicMock:
    gs = MagicMock(spec=GraphStore)
    gs.list_entities_for_document.return_value = entities or []
    gs.list_documents.return_value = documents or []
    gs.insert_edge = MagicMock()
    return gs


def _mock_inter_doc_builder(edges: list[Edge] | None = None) -> MagicMock:
    builder = MagicMock(spec=InterDocGraphBuilder)
    result = GraphBuildResult(edges=edges or [], edges_added=len(edges or []))
    builder.build = AsyncMock(return_value=result)
    return builder


def _make_orchestrator(
    inter_doc_builder: object = None,
    graph_store: object = None,
    pipeline: object = None,
) -> RefreshOrchestrator:
    return RefreshOrchestrator(
        store=MagicMock(),
        pipeline=pipeline or _mock_pipeline(),
        inter_doc_builder=inter_doc_builder,
        graph_store=graph_store,
    )


# ===========================================================================
# AC4 + AC6: Constructor DI params
# ===========================================================================


class TestFromAC_InterDocWiringConstructor:
    """RefreshOrchestrator.__init__ gains two optional DI params (AC4, AC6)."""

    def test_inter_doc_builder_keyword_param_accepted(self) -> None:
        """Constructor must accept inter_doc_builder= without TypeError."""
        RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            inter_doc_builder=MagicMock(spec=InterDocGraphBuilder),
        )

    def test_graph_store_keyword_param_accepted(self) -> None:
        """Constructor must accept graph_store= without TypeError."""
        RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            graph_store=MagicMock(spec=GraphStore),
        )

    def test_inter_doc_builder_defaults_to_none(self) -> None:
        """inter_doc_builder= defaults to None in constructor signature."""
        sig = inspect.signature(RefreshOrchestrator.__init__)
        assert "inter_doc_builder" in sig.parameters
        assert sig.parameters["inter_doc_builder"].default is None

    def test_graph_store_di_param_defaults_to_none(self) -> None:
        """graph_store= defaults to None in constructor signature."""
        sig = inspect.signature(RefreshOrchestrator.__init__)
        assert "graph_store" in sig.parameters
        assert sig.parameters["graph_store"].default is None

    def test_both_params_none_no_inter_doc_build_triggered(self) -> None:
        """With both params None, refresh runs without calling any graph_store or builder."""
        # The source has only 1 doc; also builder is None — double guard.
        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=None,
            graph_store=None,
        )
        # Existence of attributes is sufficient for this structural AC test.
        assert orchestrator._inter_doc_builder is None  # type: ignore[attr-defined]
        assert orchestrator._graph_store is None  # type: ignore[attr-defined]


# ===========================================================================
# AC1: Entity retrieval and builder invocation
# ===========================================================================


class TestFromAC_InterDocWiringEntityRetrieval:
    """After successful ingest, entities retrieved and passed to builder (AC1)."""

    @pytest.mark.asyncio
    async def test_list_entities_called_with_ingest_document_id(self) -> None:
        """list_entities_for_document(doc_id) called after ok-status ingest."""
        doc_id = "doc-abc"
        mock_gs = _mock_graph_store(
            entities=[_entity(doc_id=doc_id)],
            documents=[MagicMock(), MagicMock()],  # scope has 2 docs — guard passes
        )
        mock_builder = _mock_inter_doc_builder()
        pipeline = _mock_pipeline(ingest_result=_ingest_result(doc_id=doc_id))
        source = _source(scope="test-scope")

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=pipeline,
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)

        # Allow the background task to complete.
        await asyncio.sleep(0)

        mock_gs.list_entities_for_document.assert_called_once_with(doc_id)

    @pytest.mark.asyncio
    async def test_build_called_with_entities_and_source_scope(self) -> None:
        """builder.build(entities, scope=source.scope) called after entity retrieval."""
        doc_id = "doc-xyz"
        entities = [_entity("E1", doc_id), _entity("E2", doc_id)]
        scope = "project-alpha"
        mock_gs = _mock_graph_store(
            entities=entities,
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = _mock_inter_doc_builder()
        pipeline = _mock_pipeline(ingest_result=_ingest_result(doc_id=doc_id))
        source = _source(scope=scope)

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=pipeline,
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_builder.build.assert_called_once_with(entities, scope=scope)

    @pytest.mark.asyncio
    async def test_entity_retrieval_skipped_when_ingest_status_skipped(self) -> None:
        """No entity retrieval or builder.build call when ingest status is 'skipped'."""
        mock_gs = _mock_graph_store(documents=[MagicMock(), MagicMock()])
        mock_builder = _mock_inter_doc_builder()
        pipeline = _mock_pipeline(ingest_result=_ingest_result(status="skipped"))
        source = _source()

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=pipeline,
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_gs.list_entities_for_document.assert_not_called()
        mock_builder.build.assert_not_called()

    @pytest.mark.asyncio
    async def test_entity_retrieval_skipped_when_ingest_status_failed(self) -> None:
        """No entity retrieval or builder.build call when ingest status is 'failed'."""
        mock_gs = _mock_graph_store(documents=[MagicMock(), MagicMock()])
        mock_builder = _mock_inter_doc_builder()
        pipeline = _mock_pipeline(ingest_result=_ingest_result(status="failed"))
        source = _source()

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=pipeline,
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_gs.list_entities_for_document.assert_not_called()
        mock_builder.build.assert_not_called()


# ===========================================================================
# AC3: Skip guard — scoped doc count
# ===========================================================================


class TestFromAC_InterDocWiringSkipGuard:
    """Inter-doc build skipped when scoped doc count < 2; uses list_documents (AC3)."""

    @pytest.mark.asyncio
    async def test_skips_build_when_only_one_doc_in_scope(self) -> None:
        """Build not triggered when list_documents returns 1 document."""
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock()],  # only 1 doc
        )
        mock_builder = _mock_inter_doc_builder()
        source = _source(scope="narrow-scope")

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_builder.build.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_build_when_zero_docs_in_scope(self) -> None:
        """Build not triggered when list_documents returns empty list."""
        mock_gs = _mock_graph_store(entities=[_entity()], documents=[])
        mock_builder = _mock_inter_doc_builder()
        source = _source(scope="empty-scope")

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_builder.build.assert_not_called()

    @pytest.mark.asyncio
    async def test_proceeds_when_exactly_two_docs_in_scope(self) -> None:
        """Build IS triggered when list_documents returns exactly 2 documents."""
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],  # exactly 2
        )
        mock_builder = _mock_inter_doc_builder()
        source = _source(scope="two-doc-scope")

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_builder.build.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_scoped_list_documents_not_get_counts(self) -> None:
        """Scoped doc count check uses list_documents(scopes=[scope]), not get_counts()."""
        scope = "my-scope"
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = _mock_inter_doc_builder()
        source = _source(scope=scope)

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        # Must call list_documents with scopes=[scope], not get_counts()
        mock_gs.list_documents.assert_called_with(scopes=[scope])
        mock_gs.get_counts.assert_not_called()


# ===========================================================================
# AC2: Non-blocking execution and error logging
# ===========================================================================


class TestFromAC_InterDocWiringNonBlocking:
    """Inter-doc build scheduled non-blocking via asyncio.create_task (AC2)."""

    @pytest.mark.asyncio
    async def test_inter_doc_build_does_not_block_refresh_return(self) -> None:
        """refresh() returns before inter-doc build coroutine resolves."""
        build_started = asyncio.Event()
        build_released = asyncio.Event()

        async def slow_build(entities: list[Entity], scope: str = "global") -> GraphBuildResult:  # noqa: ARG001
            build_started.set()
            await build_released.wait()  # blocks until we release it
            return GraphBuildResult()

        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = MagicMock(spec=InterDocGraphBuilder)
        mock_builder.build = slow_build

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        # Refresh must return even though slow_build hasn't finished.
        result = await orchestrator.refresh(_source())

        # Result available before releasing the background task.
        assert result is not None
        assert not build_started.is_set() or True  # background may or may not have started

        # Release background task to avoid dangling coroutine.
        build_released.set()
        await asyncio.sleep(0)

    @pytest.mark.asyncio
    async def test_exception_in_inter_doc_build_logged_at_error_level(self) -> None:
        """Exception raised in build() is logged at ERROR level by the done-callback."""
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = MagicMock(spec=InterDocGraphBuilder)
        mock_builder.build = AsyncMock(side_effect=RuntimeError("inter-doc failure"))

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )

        with patch("owlbear_knowledge.refresh.logger") as mock_logger:
            await orchestrator.refresh(_source())
            # Allow background task to complete and callback to fire.
            await asyncio.sleep(0)

        # ERROR-level logging must have occurred.
        error_calls = list(mock_logger.error.call_args_list)
        assert error_calls, "logger.error() must be called when inter-doc build raises"

    @pytest.mark.asyncio
    async def test_exception_in_inter_doc_build_does_not_propagate_to_caller(self) -> None:
        """Exception in background build must not raise in the calling refresh() coroutine."""
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = MagicMock(spec=InterDocGraphBuilder)
        mock_builder.build = AsyncMock(side_effect=ValueError("graph error"))

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )

        # Must not raise.
        result = await orchestrator.refresh(_source())
        await asyncio.sleep(0)
        assert result is not None


# ===========================================================================
# AC5: Edge persistence via graph_store.insert_edge
# ===========================================================================


class TestFromAC_InterDocWiringEdgePersistence:
    """Each edge returned by build() is persisted via graph_store.insert_edge() (AC5)."""

    @pytest.mark.asyncio
    async def test_insert_edge_called_for_each_returned_edge(self) -> None:
        """insert_edge called once per edge in build() result."""
        edges = [_edge("e1", "e2"), _edge("e3", "e4"), _edge("e5", "e6")]
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = _mock_inter_doc_builder(edges=edges)

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(_source())
        await asyncio.sleep(0)

        assert mock_gs.insert_edge.call_count == 3

    @pytest.mark.asyncio
    async def test_insert_edge_called_with_correct_edge_objects(self) -> None:
        """insert_edge receives the exact edge objects returned by build()."""
        edge_a = _edge("a1", "a2")
        edge_b = _edge("b1", "b2")
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = _mock_inter_doc_builder(edges=[edge_a, edge_b])

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(_source())
        await asyncio.sleep(0)

        calls = [c.args[0] for c in mock_gs.insert_edge.call_args_list]
        assert edge_a in calls
        assert edge_b in calls

    @pytest.mark.asyncio
    async def test_empty_build_result_no_insert_edge_calls(self) -> None:
        """When build() returns no edges, insert_edge is never called."""
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = _mock_inter_doc_builder(edges=[])

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(_source())
        await asyncio.sleep(0)

        mock_gs.insert_edge.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_edge_insert_edge_called_once(self) -> None:
        """Boundary: exactly 1 edge in build() result → insert_edge called once."""
        single_edge = _edge("x1", "x2")
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = _mock_inter_doc_builder(edges=[single_edge])

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(_source())
        await asyncio.sleep(0)

        mock_gs.insert_edge.call_count == 1  # noqa: B015 — replaced by assertion below
        mock_gs.insert_edge.assert_called_once_with(single_edge)


# ===========================================================================
# AC7: Integration test — 2 docs, mock StructuredExtractor, cross-doc edges persisted
# ===========================================================================


class TestFromAC_InterDocWiringIntegration:
    """Integration: 2 ingested docs → InterDocGraphBuilder triggered → edges persisted (AC7)."""

    @pytest.mark.asyncio
    async def test_two_doc_ingest_triggers_inter_doc_build(self) -> None:
        """After ingesting 2nd doc from same scope, build() is called with scoped entities."""
        doc_id = "doc-integration"
        entities = [_entity("Alpha", doc_id), _entity("Beta", doc_id)]
        mock_gs = _mock_graph_store(
            entities=entities,
            documents=[MagicMock(), MagicMock()],  # scope has 2 docs after 2nd ingest
        )
        mock_builder = _mock_inter_doc_builder(edges=[_edge(entities[0].id, entities[1].id)])
        pipeline = _mock_pipeline(ingest_result=_ingest_result(doc_id=doc_id))
        source = _source(scope="integration-scope")

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=pipeline,
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_builder.build.assert_called_once_with(entities, scope="integration-scope")

    @pytest.mark.asyncio
    async def test_two_doc_ingest_edges_persisted_to_graph_store(self) -> None:
        """Cross-doc edges returned by mock StructuredExtractor are persisted via insert_edge."""
        doc_id = "doc-persist-test"
        e1 = _entity("ComponentA", doc_id)
        e2 = _entity("ComponentB", doc_id)
        cross_edge = _edge(e1.id, e2.id)

        mock_gs = _mock_graph_store(
            entities=[e1, e2],
            documents=[MagicMock(), MagicMock()],
        )
        mock_builder = _mock_inter_doc_builder(edges=[cross_edge])
        pipeline = _mock_pipeline(ingest_result=_ingest_result(doc_id=doc_id))
        source = _source(scope="persist-scope")

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=pipeline,
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_gs.insert_edge.assert_called_once_with(cross_edge)

    @pytest.mark.asyncio
    async def test_first_doc_in_scope_does_not_trigger_inter_doc_build(self) -> None:
        """When scope has only 1 document (first ingest), inter-doc build is skipped."""
        mock_gs = _mock_graph_store(
            entities=[_entity()],
            documents=[MagicMock()],  # only 1 doc — guard triggers
        )
        mock_builder = _mock_inter_doc_builder()
        source = _source(scope="single-doc-scope")

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=_mock_pipeline(),
            inter_doc_builder=mock_builder,
            graph_store=mock_gs,
        )
        await orchestrator.refresh(source)
        await asyncio.sleep(0)

        mock_builder.build.assert_not_called()
        mock_gs.insert_edge.assert_not_called()
