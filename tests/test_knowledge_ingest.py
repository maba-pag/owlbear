"""Tests for knowledge ingest pipeline — async orchestration."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.chunker import Chunk
from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.ingest import DocumentStatus, IngestPipeline, IngestResult
from owlbear.memory.knowledge.intake import IntakeResult
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.protocol import HybridEmbedding, SparseVector
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

SAMPLE_ENTITIES = [
    Entity(name="func_a", entity_type=EntityType.FUNCTION, description="A function"),
]
SAMPLE_EDGES = [
    Edge(source_id="s1", target_id="t1", relation=RelationType.DEFINES),
]
SAMPLE_EXTRACTION = ExtractionResult(entities=SAMPLE_ENTITIES, edges=SAMPLE_EDGES)
SAMPLE_INTAKE = IntakeResult(
    content="hello world",
    source="test.txt",
    metadata={"source_type": "file"},
)
SAMPLE_CHUNKS = [
    Chunk(text="chunk one", index=0, metadata={}),
    Chunk(text="chunk two", index=1, metadata={}),
]
SAMPLE_EMBEDDINGS = [[0.1] * 384, [0.2] * 384]
SAMPLE_HYBRID_EMBEDDINGS = [
    HybridEmbedding(
        dense=[0.1] * 1024,
        sparse=SparseVector(indices=[1, 2], values=[0.5, 0.3]),
    ),
    HybridEmbedding(
        dense=[0.2] * 1024,
        sparse=SparseVector(indices=[3, 4], values=[0.4, 0.2]),
    ),
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
def mock_graph_store() -> MagicMock:
    """Mock GraphStore — insert_entity/insert_edge are MagicMocks."""
    return MagicMock()


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock VectorStore — store_embedding is a MagicMock."""
    return MagicMock()


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Mock dense-only EmbeddingProvider — no embed_hybrid method."""
    embedder = MagicMock(spec=["embed"])
    embedder.embed.return_value = list(SAMPLE_EMBEDDINGS)
    return embedder


@pytest.fixture
def mock_hybrid_embedder() -> MagicMock:
    """Mock hybrid EmbeddingProvider — has embed_hybrid method."""
    embedder = MagicMock(spec=["embed", "embed_hybrid"])
    embedder.embed_hybrid.return_value = list(SAMPLE_HYBRID_EMBEDDINGS)
    embedder.embed.return_value = list(SAMPLE_EMBEDDINGS)
    return embedder


@pytest.fixture
def mock_extractor() -> MagicMock:
    """Mock EntityExtractor — async extract returns sample entities/edges."""
    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value=SAMPLE_EXTRACTION)
    return extractor


@pytest.fixture
def mock_chunker() -> MagicMock:
    """Mock TextChunker — chunk returns two sample chunks."""
    chunker = MagicMock()
    chunker.chunk.return_value = list(SAMPLE_CHUNKS)
    return chunker


@pytest.fixture
def pipeline(  # noqa: PLR0913
    conn: sqlite3.Connection,
    mock_graph_store: MagicMock,
    mock_vector_store: MagicMock,
    mock_embedder: MagicMock,
    mock_extractor: MagicMock,
    mock_chunker: MagicMock,
) -> IngestPipeline:
    """Fully-wired IngestPipeline with mocked dependencies."""
    return IngestPipeline(
        conn=conn,
        graph_store=mock_graph_store,
        vector_store=mock_vector_store,
        embedding_provider=mock_embedder,
        entity_extractor=mock_extractor,
        text_chunker=mock_chunker,
    )


@pytest.fixture
def hybrid_pipeline(  # noqa: PLR0913
    conn: sqlite3.Connection,
    mock_graph_store: MagicMock,
    mock_vector_store: MagicMock,
    mock_hybrid_embedder: MagicMock,
    mock_extractor: MagicMock,
    mock_chunker: MagicMock,
) -> IngestPipeline:
    """IngestPipeline with hybrid embedding provider."""
    return IngestPipeline(
        conn=conn,
        graph_store=mock_graph_store,
        vector_store=mock_vector_store,
        embedding_provider=mock_hybrid_embedder,
        entity_extractor=mock_extractor,
        text_chunker=mock_chunker,
    )


# ---------------------------------------------------------------------------
# IngestResult model
# ---------------------------------------------------------------------------


class TestIngestResult:
    """IngestResult is a frozen Pydantic model with the expected fields."""

    def test_fields(self) -> None:
        r = IngestResult(
            document_id="abc123",
            chunk_count=2,
            entity_count=3,
            edge_count=1,
            status="indexed",
        )
        assert r.document_id == "abc123"
        assert r.chunk_count == 2
        assert r.entity_count == 3
        assert r.edge_count == 1
        assert r.status == "indexed"

    def test_frozen(self) -> None:
        r = IngestResult(
            document_id="abc123",
            chunk_count=2,
            entity_count=3,
            edge_count=1,
            status="indexed",
        )
        with pytest.raises(ValidationError):
            r.status = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IngestPipeline construction
# ---------------------------------------------------------------------------


class TestIngestPipelineConstruction:
    """IngestPipeline accepts all required dependencies."""

    def test_accepts_all_deps(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
    ) -> None:
        pipeline = IngestPipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        assert pipeline is not None


# ---------------------------------------------------------------------------
# Ingest orchestration — happy path
# ---------------------------------------------------------------------------


class TestIngestOrchestration:
    """ingest() orchestrates: intake -> chunk -> parallel(embed, extract) -> store."""

    @pytest.mark.anyio
    async def test_returns_ingest_result(self, pipeline: IngestPipeline) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        assert isinstance(result, IngestResult)
        assert result.status == "indexed"
        assert result.chunk_count == 2

    @pytest.mark.anyio
    async def test_intake_called_for_file_path(self, pipeline: IngestPipeline) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))
            mock_rf.assert_awaited_once()

    @pytest.mark.anyio
    async def test_intake_called_for_url(self, pipeline: IngestPipeline) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_url", new_callable=AsyncMock) as mock_ru:
            mock_ru.return_value = SAMPLE_INTAKE
            await pipeline.ingest("https://example.com/doc")
            mock_ru.assert_awaited_once()

    @pytest.mark.anyio
    async def test_chunker_receives_content(
        self, pipeline: IngestPipeline, mock_chunker: MagicMock
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        mock_chunker.chunk.assert_called_once()
        assert mock_chunker.chunk.call_args[0][0] == "hello world"

    @pytest.mark.anyio
    async def test_embedder_called_with_chunk_texts(
        self, pipeline: IngestPipeline, mock_embedder: MagicMock
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        mock_embedder.embed.assert_any_call(["chunk one", "chunk two"])

    @pytest.mark.anyio
    async def test_extractor_called_per_chunk(
        self, pipeline: IngestPipeline, mock_extractor: MagicMock
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        assert mock_extractor.extract.await_count == 2

    @pytest.mark.anyio
    async def test_entities_stored_in_graph(
        self, pipeline: IngestPipeline, mock_graph_store: MagicMock
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        mock_graph_store.insert_entity.assert_called()

    @pytest.mark.anyio
    async def test_edges_stored_in_graph(
        self, pipeline: IngestPipeline, mock_graph_store: MagicMock
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        mock_graph_store.insert_edge.assert_called()

    @pytest.mark.anyio
    async def test_embeddings_stored_in_vector_store(
        self, pipeline: IngestPipeline, mock_vector_store: MagicMock
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        mock_vector_store.store_embedding.assert_called()
        # 2 chunk embeddings + 2 entity embeddings = 4
        assert mock_vector_store.store_embedding.call_count == 4

    @pytest.mark.anyio
    async def test_chunks_stored_in_database(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        row = conn.execute("SELECT count(*) FROM chunks").fetchone()
        assert row[0] == 2

    @pytest.mark.anyio
    async def test_result_counts(self, pipeline: IngestPipeline) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        assert result.chunk_count == 2
        # Extractor returns 1 entity + 1 edge per chunk, 2 chunks total.
        assert result.entity_count == 2
        assert result.edge_count == 2


# ---------------------------------------------------------------------------
# Document status transitions
# ---------------------------------------------------------------------------


class TestDocumentStatusTransitions:
    """Document status transitions: pending -> processing -> indexed/failed."""

    @pytest.mark.anyio
    async def test_success_status_indexed(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        row = conn.execute(
            "SELECT status FROM document_status WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        assert row[0] == "indexed"

    @pytest.mark.anyio
    async def test_intake_error_status_failed(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.side_effect = FileNotFoundError("not found")
            result = await pipeline.ingest(Path("missing.txt"))

        assert result.status == "failed"
        row = conn.execute(
            "SELECT status FROM document_status WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        assert row[0] == "failed"

    @pytest.mark.anyio
    async def test_source_recorded_in_db(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        row = conn.execute(
            "SELECT source FROM document_status WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        assert row[0] is not None


# ---------------------------------------------------------------------------
# Partial failure — extract error
# ---------------------------------------------------------------------------


class TestExtractFailPartial:
    """Error in extract logs warning but embed+store still completes."""

    @pytest.mark.anyio
    async def test_extract_error_yields_partial_status(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
    ) -> None:
        failing_extractor = MagicMock()
        failing_extractor.extract = AsyncMock(side_effect=RuntimeError("LLM down"))

        pipeline = IngestPipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=failing_extractor,
            text_chunker=mock_chunker,
        )

        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        assert result.status == "partial"
        assert result.entity_count == 0
        assert result.edge_count == 0
        # Embeddings still stored despite extract failure.
        mock_vector_store.store_embedding.assert_called()

    @pytest.mark.anyio
    async def test_extract_error_logs_warning(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        failing_extractor = MagicMock()
        failing_extractor.extract = AsyncMock(side_effect=RuntimeError("LLM down"))

        pipeline = IngestPipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=failing_extractor,
            text_chunker=mock_chunker,
        )

        with (
            caplog.at_level(logging.WARNING),
            patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf,
        ):
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        assert any("extract" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Partial failure — embed error
# ---------------------------------------------------------------------------


class TestEmbedFailPartial:
    """Error in embed logs warning but extract+store still completes."""

    @pytest.mark.anyio
    async def test_embed_error_yields_partial_status(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
    ) -> None:
        failing_embedder = MagicMock(spec=["embed"])
        failing_embedder.embed.side_effect = RuntimeError("GPU OOM")

        pipeline = IngestPipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=failing_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )

        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        assert result.status == "partial"
        assert result.chunk_count == 2
        # Entities still stored despite embed failure.
        mock_graph_store.insert_entity.assert_called()
        mock_graph_store.insert_edge.assert_called()
        # No embeddings stored.
        mock_vector_store.store_embedding.assert_not_called()

    @pytest.mark.anyio
    async def test_embed_error_logs_warning(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        failing_embedder = MagicMock(spec=["embed"])
        failing_embedder.embed.side_effect = RuntimeError("GPU OOM")

        pipeline = IngestPipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=failing_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )

        with (
            caplog.at_level(logging.WARNING),
            patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf,
        ):
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        assert any("embed" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Scope passthrough (#223)
# ---------------------------------------------------------------------------


class TestIngestScopePassthrough:
    """ingest/ingest_text pass scope through the entire pipeline."""

    @pytest.mark.anyio
    async def test_ingest_passes_scope_to_graph_store(
        self, pipeline: IngestPipeline, mock_graph_store: MagicMock
    ) -> None:
        """ingest(source, scope='project:owlbear') passes scope to insert_entity/insert_edge."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"), scope="project:owlbear")

        # Every entity inserted should have scope='project:owlbear'.
        for call in mock_graph_store.insert_entity.call_args_list:
            entity = call[0][0]
            assert entity.scope == "project:owlbear"
        for call in mock_graph_store.insert_edge.call_args_list:
            edge = call[0][0]
            assert edge.scope == "project:owlbear"

    @pytest.mark.anyio
    async def test_ingest_passes_scope_to_vector_store(
        self, pipeline: IngestPipeline, mock_vector_store: MagicMock
    ) -> None:
        """ingest(source, scope='project:owlbear') passes scope to store_embedding."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"), scope="project:owlbear")

        for call in mock_vector_store.store_embedding.call_args_list:
            # store_embedding(embed_id, embedding, "document", scope=scope)
            assert call.kwargs.get("scope") == "project:owlbear" or (
                len(call[0]) >= 4 and call[0][3] == "project:owlbear"
            )

    @pytest.mark.anyio
    async def test_ingest_text_propagates_scope(
        self, pipeline: IngestPipeline, mock_graph_store: MagicMock
    ) -> None:
        """ingest_text(text, scope='agent:builder') propagates scope."""
        await pipeline.ingest_text("some text", scope="agent:builder")

        for call in mock_graph_store.insert_entity.call_args_list:
            entity = call[0][0]
            assert entity.scope == "agent:builder"
        for call in mock_graph_store.insert_edge.call_args_list:
            edge = call[0][0]
            assert edge.scope == "agent:builder"

    @pytest.mark.anyio
    async def test_ingest_default_scope_is_global(
        self, pipeline: IngestPipeline, mock_graph_store: MagicMock
    ) -> None:
        """ingest(source) without scope defaults to 'global'."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        for call in mock_graph_store.insert_entity.call_args_list:
            entity = call[0][0]
            assert entity.scope == "global"

    @pytest.mark.anyio
    async def test_ingest_result_unchanged_no_scope_field(self, pipeline: IngestPipeline) -> None:
        """IngestResult has no scope field — model is unchanged."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"), scope="project:owlbear")

        assert not hasattr(result, "scope") or "scope" not in result.model_fields

    @pytest.mark.anyio
    async def test_ingest_scope_written_to_documents_table(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """scope is written to the documents table."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"), scope="project:owlbear")

        row = conn.execute(
            "SELECT scope FROM documents WHERE id = ?", (result.document_id,)
        ).fetchone()
        assert row[0] == "project:owlbear"

    @pytest.mark.anyio
    async def test_ingest_scope_written_to_chunks_table(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """scope is written to the chunks table."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"), scope="project:owlbear")

        rows = conn.execute("SELECT scope FROM chunks").fetchall()
        assert len(rows) == 2
        assert all(r[0] == "project:owlbear" for r in rows)

    @pytest.mark.anyio
    async def test_ingest_scope_written_to_document_status_table(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """scope is written to the document_status table."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"), scope="project:owlbear")

        row = conn.execute(
            "SELECT scope FROM document_status WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        assert row[0] == "project:owlbear"


# ---------------------------------------------------------------------------
# Hybrid embedding support (#250)
# ---------------------------------------------------------------------------


class TestHybridEmbedding:
    """_run_embed prefers embed_hybrid; fallback wraps dense in HybridEmbedding."""

    @pytest.mark.anyio
    async def test_run_embed_calls_embed_hybrid_when_available(
        self, hybrid_pipeline: IngestPipeline, mock_hybrid_embedder: MagicMock
    ) -> None:
        """_run_embed calls embed_hybrid() when the provider has it."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await hybrid_pipeline.ingest(Path("test.txt"))

        mock_hybrid_embedder.embed_hybrid.assert_any_call(["chunk one", "chunk two"])
        mock_hybrid_embedder.embed.assert_not_called()

    @pytest.mark.anyio
    async def test_run_embed_fallback_wraps_dense_in_hybrid(
        self, pipeline: IngestPipeline, mock_embedder: MagicMock
    ) -> None:
        """_run_embed falls back to embed() and wraps each vector in HybridEmbedding."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        # embed() was called (no embed_hybrid on dense-only provider)
        mock_embedder.embed.assert_any_call(["chunk one", "chunk two"])

    @pytest.mark.anyio
    async def test_store_embeddings_passes_hybrid_to_vector_store(
        self, hybrid_pipeline: IngestPipeline, mock_vector_store: MagicMock
    ) -> None:
        """_store_embeddings passes HybridEmbedding objects to store_embedding."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await hybrid_pipeline.ingest(Path("test.txt"))

        # Check that chunk embeddings are HybridEmbedding instances
        doc_calls = [
            c for c in mock_vector_store.store_embedding.call_args_list if c[0][2] == "document"
        ]
        assert len(doc_calls) == 2
        for call_obj in doc_calls:
            assert isinstance(call_obj[0][1], HybridEmbedding)

    @pytest.mark.anyio
    async def test_entity_descriptions_embedded_and_stored(
        self, hybrid_pipeline: IngestPipeline, mock_vector_store: MagicMock
    ) -> None:
        """Entity descriptions are embedded and stored with embedding_type='entity'."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await hybrid_pipeline.ingest(Path("test.txt"))

        entity_calls = [
            c for c in mock_vector_store.store_embedding.call_args_list if c[0][2] == "entity"
        ]
        # 2 chunks x 1 entity each = 2 entity embeddings
        assert len(entity_calls) == 2
        for call_obj in entity_calls:
            assert isinstance(call_obj[0][1], HybridEmbedding)

    @pytest.mark.anyio
    async def test_e2e_ingest_with_hybrid_provider(self, hybrid_pipeline: IngestPipeline) -> None:
        """End-to-end ingest with hybrid provider produces correct result."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await hybrid_pipeline.ingest(Path("test.txt"))

        assert result.status == "indexed"
        assert result.chunk_count == 2
        assert result.entity_count == 2
        assert result.edge_count == 2


# ---------------------------------------------------------------------------
# find_status_by_source
# ---------------------------------------------------------------------------


class TestFindStatusBySource:
    """Tests for IngestPipeline.find_status_by_source()."""

    def test_source_found_returns_document_status(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """When a matching row exists, returns a DocumentStatus with correct fields."""
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, content_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("doc-1", "indexed", "test.txt", "global", "abc123hash", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        result = pipeline.find_status_by_source("test.txt")

        assert result is not None
        assert isinstance(result, DocumentStatus)
        assert result.document_id == "doc-1"
        assert result.content_hash == "abc123hash"
        assert result.status == "indexed"

    def test_source_not_found_returns_none(self, pipeline: IngestPipeline) -> None:
        """When no matching row exists, returns None."""
        result = pipeline.find_status_by_source("nonexistent.txt")
        assert result is None

    def test_scope_filtering(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """Only returns rows matching the requested scope."""
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, content_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("doc-a", "indexed", "shared.txt", "project-x", "hash-a", "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, content_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("doc-b", "indexed", "shared.txt", "global", "hash-b", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        # Default scope='global' should find doc-b, not doc-a.
        result = pipeline.find_status_by_source("shared.txt")
        assert result is not None
        assert result.document_id == "doc-b"
        assert result.content_hash == "hash-b"

        # Explicit scope='project-x' should find doc-a.
        result_scoped = pipeline.find_status_by_source("shared.txt", scope="project-x")
        assert result_scoped is not None
        assert result_scoped.document_id == "doc-a"
        assert result_scoped.content_hash == "hash-a"

        # Non-existent scope returns None.
        assert pipeline.find_status_by_source("shared.txt", scope="nope") is None
