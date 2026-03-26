"""RED-phase tests for task #1006: Thread CancelSignal to enricher in _ingest_from_intake.

Verifies that _ingest_from_intake forwards its cancel kwarg to both
GraphEnricher schedule calls.

All tests MUST FAIL on current HEAD — _ingest_from_intake calls
schedule_graph_enrichment and schedule_inter_doc_enrichment without passing
the cancel kwarg (ingest.py lines 288-289).
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.memory.knowledge.chunker import Chunk
from owlbear.memory.knowledge.document_store import DocumentStore
from owlbear.memory.knowledge.enrichment import GraphEnricher
from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.ingest import IngestPipeline
from owlbear.memory.knowledge.intake import IntakeResult
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_SAMPLE_ENTITIES = [
    Entity(name="func_a", entity_type=EntityType.FUNCTION, description="A function"),
]
_SAMPLE_EDGES = [
    Edge(source_id="s1", target_id="t1", relation=RelationType.DEFINES),
]
_SAMPLE_EXTRACTION = ExtractionResult(entities=_SAMPLE_ENTITIES, edges=_SAMPLE_EDGES)
_SAMPLE_INTAKE = IntakeResult(
    content="hello world",
    source="test.txt",
    metadata={"source_type": "file"},
)
_SAMPLE_CHUNKS = [
    Chunk(text="chunk one", index=0, metadata={}),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pipeline(conn: sqlite3.Connection, mock_enricher: MagicMock) -> IngestPipeline:
    """Build an IngestPipeline with a mock enricher and stub sub-dependencies."""
    mock_graph_store = MagicMock()
    mock_vector_store = MagicMock()
    mock_embedder = MagicMock(spec=["embed"])
    mock_embedder.embed.return_value = [[0.1] * 384]

    store = DocumentStore(
        conn=conn,
        graph_store=mock_graph_store,
        vector_store=mock_vector_store,
        embedding_provider=mock_embedder,
    )

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(return_value=_SAMPLE_EXTRACTION)
    mock_chunker = MagicMock()
    mock_chunker.chunk.return_value = list(_SAMPLE_CHUNKS)

    return IngestPipeline(
        store=store,
        entity_extractor=mock_extractor,
        text_chunker=mock_chunker,
        workspace_root=Path(),
        enricher=mock_enricher,
        pipeline_name="test",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_IngestFromIntakeCancelThreading:
    """_ingest_from_intake must forward its cancel kwarg to both enricher schedule calls.

    All tests fail on current HEAD: cancel is not passed to
    schedule_graph_enrichment or schedule_inter_doc_enrichment (ingest.py:288-289).
    """

    @pytest.fixture
    def conn(self) -> sqlite3.Connection:
        """In-memory SQLite database with knowledge schema."""
        c = sqlite3.Connection(":memory:")
        init_db(c)
        return c

    @pytest.fixture
    def mock_enricher(self) -> MagicMock:
        """Mock GraphEnricher with all schedule methods as plain MagicMocks."""
        return MagicMock(spec=GraphEnricher)

    # -- AC-1: cancel threaded to schedule_graph_enrichment -----------------

    @pytest.mark.asyncio
    async def test_cancel_signal_forwarded_to_schedule_graph_enrichment(
        self,
        conn: sqlite3.Connection,
        mock_enricher: MagicMock,
    ) -> None:
        """_ingest_from_intake passes cancel=<signal> to schedule_graph_enrichment.

        Fails on current HEAD because cancel kwarg is not forwarded.
        """
        pipeline = _make_pipeline(conn, mock_enricher)
        cancel = asyncio.Event()

        with (
            patch.object(pipeline, "_run_embed", AsyncMock(return_value=[])),
            patch.object(
                pipeline,
                "_run_extract",
                AsyncMock(return_value=[_SAMPLE_EXTRACTION]),
            ),
            patch.object(
                pipeline,
                "_process_results",
                MagicMock(return_value=(1, 0, "complete")),
            ),
        ):
            await pipeline._ingest_from_intake(_SAMPLE_INTAKE, cancel=cancel)

        mock_enricher.schedule_graph_enrichment.assert_called_once()
        call_kwargs = mock_enricher.schedule_graph_enrichment.call_args.kwargs
        assert call_kwargs.get("cancel") is cancel  # FAILS on current HEAD

    # -- AC-2: cancel threaded to schedule_inter_doc_enrichment -------------

    @pytest.mark.asyncio
    async def test_cancel_signal_forwarded_to_schedule_inter_doc_enrichment(
        self,
        conn: sqlite3.Connection,
        mock_enricher: MagicMock,
    ) -> None:
        """_ingest_from_intake passes cancel=<signal> to schedule_inter_doc_enrichment.

        Fails on current HEAD because cancel kwarg is not forwarded.
        """
        pipeline = _make_pipeline(conn, mock_enricher)
        cancel = asyncio.Event()

        with (
            patch.object(pipeline, "_run_embed", AsyncMock(return_value=[])),
            patch.object(
                pipeline,
                "_run_extract",
                AsyncMock(return_value=[_SAMPLE_EXTRACTION]),
            ),
            patch.object(
                pipeline,
                "_process_results",
                MagicMock(return_value=(1, 0, "complete")),
            ),
        ):
            await pipeline._ingest_from_intake(_SAMPLE_INTAKE, cancel=cancel)

        mock_enricher.schedule_inter_doc_enrichment.assert_called_once()
        call_kwargs = mock_enricher.schedule_inter_doc_enrichment.call_args.kwargs
        assert call_kwargs.get("cancel") is cancel  # FAILS on current HEAD

    # -- AC-3: None cancel forwarded to schedule_graph_enrichment -----------

    @pytest.mark.asyncio
    async def test_cancel_none_forwarded_to_schedule_graph_enrichment(
        self,
        conn: sqlite3.Connection,
        mock_enricher: MagicMock,
    ) -> None:
        """When cancel is omitted, schedule_graph_enrichment still receives cancel=None.

        Fails on current HEAD: the kwarg is absent entirely from the call.
        """
        pipeline = _make_pipeline(conn, mock_enricher)

        with (
            patch.object(pipeline, "_run_embed", AsyncMock(return_value=[])),
            patch.object(
                pipeline,
                "_run_extract",
                AsyncMock(return_value=[_SAMPLE_EXTRACTION]),
            ),
            patch.object(
                pipeline,
                "_process_results",
                MagicMock(return_value=(1, 0, "complete")),
            ),
        ):
            await pipeline._ingest_from_intake(_SAMPLE_INTAKE)  # cancel defaults to None

        mock_enricher.schedule_graph_enrichment.assert_called_once()
        call_kwargs = mock_enricher.schedule_graph_enrichment.call_args.kwargs
        assert "cancel" in call_kwargs  # FAILS on current HEAD — kwarg absent
        assert call_kwargs["cancel"] is None

    # -- AC-3: None cancel forwarded to schedule_inter_doc_enrichment -------

    @pytest.mark.asyncio
    async def test_cancel_none_forwarded_to_schedule_inter_doc_enrichment(
        self,
        conn: sqlite3.Connection,
        mock_enricher: MagicMock,
    ) -> None:
        """When cancel is omitted, schedule_inter_doc_enrichment still receives cancel=None.

        Fails on current HEAD: the kwarg is absent entirely from the call.
        """
        pipeline = _make_pipeline(conn, mock_enricher)

        with (
            patch.object(pipeline, "_run_embed", AsyncMock(return_value=[])),
            patch.object(
                pipeline,
                "_run_extract",
                AsyncMock(return_value=[_SAMPLE_EXTRACTION]),
            ),
            patch.object(
                pipeline,
                "_process_results",
                MagicMock(return_value=(1, 0, "complete")),
            ),
        ):
            await pipeline._ingest_from_intake(_SAMPLE_INTAKE)  # cancel defaults to None

        mock_enricher.schedule_inter_doc_enrichment.assert_called_once()
        call_kwargs = mock_enricher.schedule_inter_doc_enrichment.call_args.kwargs
        assert "cancel" in call_kwargs  # FAILS on current HEAD — kwarg absent
        assert call_kwargs["cancel"] is None
