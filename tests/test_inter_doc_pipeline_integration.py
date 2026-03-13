"""Integration tests for InterDocGraphBuilder integration into IngestPipeline.

Tests the end-to-end flow: ingest 2 documents with related entities under
the same scope, then verify that inter-doc edges appear in GraphStore with
metadata ``source=inter_doc_inference``.
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.memory.knowledge.chunker import Chunk
from owlbear.memory.knowledge.document_store import DocumentStore
from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.graph_builder import GraphBuildResult
from owlbear.memory.knowledge.ingest import IngestPipeline
from owlbear.memory.knowledge.intake import IntakeResult
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.protocol import HybridEmbedding, SparseVector
from owlbear.memory.knowledge.schema import init_db


def _make_pipeline(  # noqa: PLR0913
    conn: sqlite3.Connection,
    graph_store: object,
    vector_store: object,
    embedding_provider: object,
    entity_extractor: object,
    text_chunker: object,
    workspace_root: Path,
    **kwargs: object,
) -> IngestPipeline:
    store = DocumentStore(
        conn=conn,
        graph_store=graph_store,
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )
    return IngestPipeline(
        store=store,
        entity_extractor=entity_extractor,
        text_chunker=text_chunker,
        workspace_root=workspace_root,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_HYBRID = HybridEmbedding(
    dense=[0.1] * 1024,
    sparse=SparseVector(indices=[1, 2], values=[0.5, 0.3]),
)


def _make_intake(source: str, content: str) -> IntakeResult:
    return IntakeResult(
        content=content,
        source=source,
        metadata={"source_type": "file"},
    )


def _make_entities(doc_id: str, names: list[str]) -> list[Entity]:
    return [
        Entity(
            name=name,
            entity_type=EntityType.CLASS_,
            description=f"{name} in {doc_id}",
            document_id=doc_id,
        )
        for name in names
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    """In-memory SQLite database with knowledge schema."""
    c = sqlite3.Connection(":memory:")
    init_db(c)
    return c


@pytest.fixture
def graph_store(conn: sqlite3.Connection) -> GraphStore:
    """Real GraphStore backed by in-memory SQLite."""
    return GraphStore(conn)


@pytest.fixture
def mock_vector_store() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_hybrid_embedder() -> MagicMock:
    embedder = MagicMock(spec=["embed", "embed_hybrid"])
    embedder.embed_hybrid.return_value = [SAMPLE_HYBRID, SAMPLE_HYBRID]
    embedder.embed.return_value = [[0.1] * 384, [0.2] * 384]
    return embedder


@pytest.fixture
def mock_chunker() -> MagicMock:
    chunker = MagicMock()
    chunker.chunk.return_value = [
        Chunk(text="chunk one", index=0, metadata={}),
        Chunk(text="chunk two", index=1, metadata={}),
    ]
    return chunker


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInterDocBuilderParam:
    """IngestPipeline accepts optional inter_doc_builder parameter."""

    def test_constructor_accepts_inter_doc_builder(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        mock_hybrid_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """inter_doc_builder param is stored on the pipeline."""
        mock_inter = MagicMock()
        extractor = MagicMock()
        extractor.extract = AsyncMock(return_value=ExtractionResult(entities=[], edges=[]))

        pipe = _make_pipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_hybrid_embedder,
            entity_extractor=extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            inter_doc_builder=mock_inter,
        )
        assert pipe._inter_doc_builder is mock_inter

    def test_constructor_defaults_inter_doc_builder_none(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        mock_hybrid_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """inter_doc_builder defaults to None when not provided."""
        extractor = MagicMock()
        extractor.extract = AsyncMock(return_value=ExtractionResult(entities=[], edges=[]))

        pipe = _make_pipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_hybrid_embedder,
            entity_extractor=extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
        )
        assert pipe._inter_doc_builder is None


class TestScheduleInterDocEnrichment:
    """_schedule_inter_doc_enrichment mirrors _schedule_graph_enrichment pattern."""

    @pytest.mark.anyio
    async def test_skips_when_builder_is_none(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        mock_hybrid_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """No inter-doc enrichment when inter_doc_builder is None."""
        extractor = MagicMock()
        extractor.extract = AsyncMock(
            return_value=ExtractionResult(
                entities=_make_entities("doc1", ["Alpha"]),
                edges=[],
            ),
        )

        pipe = _make_pipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_hybrid_embedder,
            entity_extractor=extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
        )

        with patch(
            "owlbear.memory.knowledge.ingest.read_file",
            new_callable=AsyncMock,
        ) as mock_rf:
            mock_rf.return_value = _make_intake("doc1.txt", "hello world")
            await pipe.ingest("doc1.txt")

        await asyncio.sleep(0.01)

        # No inter-doc edges should exist
        edges = graph_store.list_edges()
        inter_doc = [e for e in edges if e.metadata.get("source") == "inter_doc_inference"]
        assert inter_doc == []

    @pytest.mark.anyio
    async def test_skips_when_fewer_than_2_docs_in_scope(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        mock_hybrid_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Inter-doc enrichment skips when fewer than 2 documents exist in scope."""
        mock_inter = MagicMock()
        mock_inter.build = AsyncMock(return_value=GraphBuildResult())

        extractor = MagicMock()
        extractor.extract = AsyncMock(
            return_value=ExtractionResult(
                entities=_make_entities("doc1", ["Alpha"]),
                edges=[],
            ),
        )

        pipe = _make_pipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_hybrid_embedder,
            entity_extractor=extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            inter_doc_builder=mock_inter,
        )

        # Ingest only 1 document — should skip inter-doc
        with patch(
            "owlbear.memory.knowledge.ingest.read_file",
            new_callable=AsyncMock,
        ) as mock_rf:
            mock_rf.return_value = _make_intake("doc1.txt", "hello world")
            await pipe.ingest("doc1.txt")

        await asyncio.sleep(0.01)

        mock_inter.build.assert_not_awaited()

    @pytest.mark.anyio
    async def test_creates_background_task(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        mock_hybrid_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Inter-doc enrichment creates asyncio.Task added to _background_tasks."""
        mock_inter = MagicMock()
        mock_inter.build = AsyncMock(return_value=GraphBuildResult())

        call_count = 0

        async def counting_extract(_text: str, _metadata: dict) -> ExtractionResult:
            nonlocal call_count
            call_count += 1
            return ExtractionResult(
                entities=_make_entities(f"doc{call_count}", ["Alpha", "Beta"]),
                edges=[],
            )

        extractor = MagicMock()
        extractor.extract = AsyncMock(side_effect=counting_extract)

        pipe = _make_pipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_hybrid_embedder,
            entity_extractor=extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            inter_doc_builder=mock_inter,
        )

        # Ingest 2 documents so scope doc count >= 2
        with patch(
            "owlbear.memory.knowledge.ingest.read_file",
            new_callable=AsyncMock,
        ) as mock_rf:
            mock_rf.return_value = _make_intake("doc1.txt", "first doc content")
            await pipe.ingest("doc1.txt")

        with patch(
            "owlbear.memory.knowledge.ingest.read_file",
            new_callable=AsyncMock,
        ) as mock_rf:
            mock_rf.return_value = _make_intake("doc2.txt", "second doc content")
            await pipe.ingest("doc2.txt")

        await asyncio.sleep(0.05)

        # Should have been called at least once (for the 2nd doc)
        mock_inter.build.assert_awaited()


class TestInterDocIntegrationE2E:
    """End-to-end: ingest 2 docs, verify inter-doc edges in GraphStore."""

    @pytest.mark.anyio
    async def test_inter_doc_edges_appear_with_correct_metadata(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        mock_hybrid_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Ingest 2 docs with related entities; inter-doc edges have source=inter_doc_inference."""
        call_count = 0
        doc1_entity_ids: list[str] = []
        doc2_entity_ids: list[str] = []

        async def make_extraction(_text: str, _metadata: dict) -> ExtractionResult:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # first doc (2 chunks)
                entities = _make_entities("doc1", ["AuthService"])
                doc1_entity_ids.extend(e.id for e in entities)
                return ExtractionResult(entities=entities, edges=[])
            # Second doc chunks
            entities = _make_entities("doc2", ["UserController"])
            doc2_entity_ids.extend(e.id for e in entities)
            return ExtractionResult(entities=entities, edges=[])

        extractor = MagicMock()
        extractor.extract = AsyncMock(side_effect=make_extraction)

        # We'll create the mock_inter with a side_effect that returns edges
        # using the real entity IDs captured from extraction.
        mock_inter = MagicMock()

        async def build_side_effect(
            *_args: object,
            scope: str = "global",
            **_kwargs: object,
        ) -> GraphBuildResult:
            # Use actual entity IDs from the extraction to avoid FK violations
            if doc1_entity_ids and doc2_entity_ids:
                edge = Edge(
                    source_id=doc1_entity_ids[0],
                    target_id=doc2_entity_ids[0],
                    relation=RelationType.RELATED_TO,
                    weight=0.4,
                    metadata={
                        "source": "inter_doc_inference",
                        "doc_pair": ["doc1", "doc2"],
                    },
                    scope=scope,
                )
                return GraphBuildResult(edges_added=1, edges=[edge])
            return GraphBuildResult()

        mock_inter.build = AsyncMock(side_effect=build_side_effect)

        pipe = _make_pipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_hybrid_embedder,
            entity_extractor=extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            inter_doc_builder=mock_inter,
        )

        # Ingest doc 1
        with patch(
            "owlbear.memory.knowledge.ingest.read_file",
            new_callable=AsyncMock,
        ) as mock_rf:
            mock_rf.return_value = _make_intake("auth.py", "auth service code")
            result1 = await pipe.ingest("auth.py")

        assert result1.status in ("indexed", "partial")

        # Ingest doc 2
        with patch(
            "owlbear.memory.knowledge.ingest.read_file",
            new_callable=AsyncMock,
        ) as mock_rf:
            mock_rf.return_value = _make_intake("user.py", "user controller code")
            result2 = await pipe.ingest("user.py")

        assert result2.status in ("indexed", "partial")

        # Wait for background tasks to complete
        await asyncio.sleep(0.1)

        # Verify inter-doc edges in graph store
        all_edges = graph_store.list_edges()
        inter_doc_edges = [
            e for e in all_edges if e.metadata.get("source") == "inter_doc_inference"
        ]

        assert len(inter_doc_edges) >= 1
        edge = inter_doc_edges[0]
        assert edge.metadata["source"] == "inter_doc_inference"
        assert edge.scope == "global"

    @pytest.mark.anyio
    async def test_inter_doc_failure_does_not_crash_ingest(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        mock_hybrid_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """If inter-doc builder raises, ingest result is still returned successfully."""
        mock_inter = MagicMock()
        mock_inter.build = AsyncMock(side_effect=RuntimeError("LLM down"))

        call_count = 0

        async def make_extraction(_text: str, _metadata: dict) -> ExtractionResult:
            nonlocal call_count
            call_count += 1
            return ExtractionResult(
                entities=_make_entities(f"doc{call_count}", ["SomeClass"]),
                edges=[],
            )

        extractor = MagicMock()
        extractor.extract = AsyncMock(side_effect=make_extraction)

        pipe = _make_pipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_hybrid_embedder,
            entity_extractor=extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            inter_doc_builder=mock_inter,
        )

        # Ingest 2 docs
        with patch(
            "owlbear.memory.knowledge.ingest.read_file",
            new_callable=AsyncMock,
        ) as mock_rf:
            mock_rf.return_value = _make_intake("a.py", "doc one")
            result1 = await pipe.ingest("a.py")

        with patch(
            "owlbear.memory.knowledge.ingest.read_file",
            new_callable=AsyncMock,
        ) as mock_rf:
            mock_rf.return_value = _make_intake("b.py", "doc two")
            result2 = await pipe.ingest("b.py")

        await asyncio.sleep(0.05)

        # Ingest should succeed despite inter-doc builder failure
        assert result1.status in ("indexed", "partial")
        assert result2.status in ("indexed", "partial")

    @pytest.mark.anyio
    async def test_ingest_text_triggers_inter_doc_enrichment(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        mock_hybrid_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """ingest_text() also triggers inter-doc enrichment after 2nd doc."""
        mock_inter = MagicMock()
        mock_inter.build = AsyncMock(return_value=GraphBuildResult())

        call_count = 0

        async def make_extraction(_text: str, _metadata: dict) -> ExtractionResult:
            nonlocal call_count
            call_count += 1
            return ExtractionResult(
                entities=_make_entities(f"doc{call_count}", ["Foo"]),
                edges=[],
            )

        extractor = MagicMock()
        extractor.extract = AsyncMock(side_effect=make_extraction)

        pipe = _make_pipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_hybrid_embedder,
            entity_extractor=extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            inter_doc_builder=mock_inter,
        )

        await pipe.ingest_text("first text", metadata={"url": "doc1"})
        await pipe.ingest_text("second text", metadata={"url": "doc2"})

        await asyncio.sleep(0.05)

        # Should have been called at least once after 2nd doc
        mock_inter.build.assert_awaited()


class TestInterDocConfig:
    """Config: inter_doc_graph_building setting exists and defaults to False."""

    def test_default_is_false(self) -> None:
        """inter_doc_graph_building defaults to False."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert settings.inter_doc_graph_building is False

    def test_can_enable(self) -> None:
        """inter_doc_graph_building can be set to True."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(inter_doc_graph_building=True)
        assert settings.inter_doc_graph_building is True


class TestBootstrapInterDocBuilder:
    """Bootstrap: _build_knowledge_toolset instantiates InterDocGraphBuilder when enabled."""

    def test_inter_doc_builder_passed_when_enabled(self, tmp_path: object) -> None:
        """When inter_doc_graph_building=True, IngestPipeline gets an inter_doc_builder."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

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
            patch(
                "owlbear.memory.knowledge.inter_doc_graph_builder.InterDocGraphBuilder.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.ingest.IngestPipeline.__init__",
                return_value=None,
            ) as mock_init,
        ):
            infra = _build_knowledge_infra(tmp_path)  # type: ignore[arg-type]
            assert infra is not None
            _build_knowledge_toolset(
                tmp_path,  # type: ignore[arg-type]
                infra,
                inter_doc_graph_building=True,
            )

        # Verify IngestPipeline was called with inter_doc_builder kwarg
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args[1]
        assert "inter_doc_builder" in call_kwargs
        assert call_kwargs["inter_doc_builder"] is not None

    def test_inter_doc_builder_not_passed_when_disabled(self, tmp_path: object) -> None:
        """When inter_doc_graph_building=False (default), no inter_doc_builder."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

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
            patch(
                "owlbear.memory.knowledge.ingest.IngestPipeline.__init__",
                return_value=None,
            ) as mock_init,
        ):
            infra = _build_knowledge_infra(tmp_path)  # type: ignore[arg-type]
            assert infra is not None
            _build_knowledge_toolset(tmp_path, infra)  # type: ignore[arg-type]

        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args[1]
        # inter_doc_builder should not be in kwargs, or should be None
        assert call_kwargs.get("inter_doc_builder") is None
