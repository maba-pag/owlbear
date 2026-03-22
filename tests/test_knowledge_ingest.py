"""Tests for knowledge ingest pipeline — async orchestration."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.chunker import Chunk
from owlbear.memory.knowledge.extractor import ExtractionResult

try:
    from owlbear.memory.knowledge.graph_builder import GraphBuildResult
except ImportError:
    # graph_builder module not yet implemented (task #284).
    # Create a minimal stand-in so the rest of the tests can run.
    from pydantic import BaseModel as _BaseModel

    from owlbear.memory.knowledge.models import Edge as _Edge

    class GraphBuildResult(_BaseModel):  # type: ignore[no-redef]
        """Minimal stub for tests until graph_builder is built."""

        edges_added: int = 0
        edges: list[_Edge] = []


from owlbear.memory.knowledge.document_store import DocumentStore
from owlbear.memory.knowledge.enrichment import GraphEnricher
from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.ingest import (
    DocumentStatus,
    IngestPipeline,
    IngestResult,
    compute_content_hash,
)
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
# Helpers
# ---------------------------------------------------------------------------


def _make_pipeline(  # noqa: PLR0913
    conn: sqlite3.Connection,
    graph_store: MagicMock,
    vector_store: MagicMock,
    embedding_provider: MagicMock,
    entity_extractor: MagicMock,
    text_chunker: MagicMock,
    workspace_root: Path | None = None,
    *,
    graph_builder: object | None = None,
    inter_doc_builder: object | None = None,
    bg_concurrency: int = 5,
    pipeline_name: str = "ingest",
) -> IngestPipeline:
    """Build an IngestPipeline via DocumentStore (adapts old positional args)."""
    store = DocumentStore(
        conn=conn,
        graph_store=graph_store,
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )
    enricher: GraphEnricher | None = None
    if graph_builder is not None or inter_doc_builder is not None:
        enricher = GraphEnricher(
            conn=conn,
            graph_store=graph_store,
            graph_builder=graph_builder,
            inter_doc_builder=inter_doc_builder,
            document_store=store,
            pipeline_name=pipeline_name,
            bg_concurrency=bg_concurrency,
        )
    return IngestPipeline(
        store=store,
        entity_extractor=entity_extractor,
        text_chunker=text_chunker,
        workspace_root=workspace_root,
        enricher=enricher,
        pipeline_name=pipeline_name,
    )


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
    tmp_path: Path,
) -> IngestPipeline:
    """Fully-wired IngestPipeline with mocked dependencies."""
    store = DocumentStore(
        conn=conn,
        graph_store=mock_graph_store,
        vector_store=mock_vector_store,
        embedding_provider=mock_embedder,
    )
    return IngestPipeline(
        store=store,
        entity_extractor=mock_extractor,
        text_chunker=mock_chunker,
        workspace_root=tmp_path,
    )


@pytest.fixture
def hybrid_pipeline(  # noqa: PLR0913
    conn: sqlite3.Connection,
    mock_graph_store: MagicMock,
    mock_vector_store: MagicMock,
    mock_hybrid_embedder: MagicMock,
    mock_extractor: MagicMock,
    mock_chunker: MagicMock,
    tmp_path: Path,
) -> IngestPipeline:
    """IngestPipeline with hybrid embedding provider."""
    store = DocumentStore(
        conn=conn,
        graph_store=mock_graph_store,
        vector_store=mock_vector_store,
        embedding_provider=mock_hybrid_embedder,
    )
    return IngestPipeline(
        store=store,
        entity_extractor=mock_extractor,
        text_chunker=mock_chunker,
        workspace_root=tmp_path,
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
        tmp_path: Path,
    ) -> None:
        pipeline = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
        )
        assert pipeline is not None

    def test_workspace_root_is_required(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
    ) -> None:
        """workspace_root is mandatory — omitting it raises TypeError."""
        store = DocumentStore(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
        )
        with pytest.raises(TypeError):
            IngestPipeline(
                store=store,
                entity_extractor=mock_extractor,
                text_chunker=mock_chunker,
            )


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
    async def test_extract_error_yields_partial_status(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        failing_extractor = MagicMock()
        failing_extractor.extract = AsyncMock(side_effect=RuntimeError("LLM down"))

        pipeline = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=failing_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
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
        tmp_path: Path,
    ) -> None:
        failing_extractor = MagicMock()
        failing_extractor.extract = AsyncMock(side_effect=RuntimeError("LLM down"))

        pipeline = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=failing_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
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
    async def test_embed_error_yields_partial_status(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        failing_embedder = MagicMock(spec=["embed"])
        failing_embedder.embed.side_effect = RuntimeError("GPU OOM")

        pipeline = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=failing_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
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
        tmp_path: Path,
    ) -> None:
        failing_embedder = MagicMock(spec=["embed"])
        failing_embedder.embed.side_effect = RuntimeError("GPU OOM")

        pipeline = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=failing_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
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

    def test_scope_filtering(self, pipeline: IngestPipeline, conn: sqlite3.Connection) -> None:
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


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


class TestComputeContentHash:
    """Tests for the compute_content_hash() free function."""

    def test_sha256_hex_digest(self) -> None:
        """Returns SHA-256 hex digest of content.strip()."""
        import hashlib

        content = "hello world"
        expected = hashlib.sha256(content.encode()).hexdigest()
        assert compute_content_hash(content) == expected

    def test_strips_whitespace_before_hashing(self) -> None:
        """Leading/trailing whitespace is stripped before hashing."""
        assert compute_content_hash("  hello  ") == compute_content_hash("hello")

    def test_identical_content_same_hash(self) -> None:
        """Identical content produces identical hashes."""
        assert compute_content_hash("abc") == compute_content_hash("abc")

    def test_different_content_different_hash(self) -> None:
        """Different content produces different hashes."""
        assert compute_content_hash("abc") != compute_content_hash("xyz")

    def test_empty_string(self) -> None:
        """Empty string (after strip) is hashable."""
        import hashlib

        expected = hashlib.sha256(b"").hexdigest()
        assert compute_content_hash("") == expected
        assert compute_content_hash("   ") == expected


# ---------------------------------------------------------------------------
# check_content_changed
# ---------------------------------------------------------------------------


class TestCheckContentChanged:
    """Tests for IngestPipeline.check_content_changed()."""

    def test_new_content_returns_true_none(self, pipeline: IngestPipeline) -> None:
        """Source not previously ingested -> (True, None)."""
        changed, doc_id = pipeline.check_content_changed("new-file.txt", "some content", "global")
        assert changed is True
        assert doc_id is None

    def test_identical_content_returns_false_and_id(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """Content hash matches stored -> (False, existing_document_id)."""
        content = "hello world"
        content_hash = compute_content_hash(content)
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, content_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "doc-existing",
                "indexed",
                "test.txt",
                "global",
                content_hash,
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.commit()

        changed, doc_id = pipeline.check_content_changed("test.txt", content, "global")
        assert changed is False
        assert doc_id == "doc-existing"

    def test_changed_content_returns_true_and_id(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """Content hash differs from stored -> (True, existing_document_id)."""
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, content_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "doc-old",
                "indexed",
                "test.txt",
                "global",
                "old-hash-value",
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.commit()

        changed, doc_id = pipeline.check_content_changed("test.txt", "updated content", "global")
        assert changed is True
        assert doc_id == "doc-old"

    def test_respects_scope(self, pipeline: IngestPipeline, conn: sqlite3.Connection) -> None:
        """check_content_changed respects scope parameter."""
        content = "scoped content"
        content_hash = compute_content_hash(content)
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, content_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "doc-scoped",
                "indexed",
                "test.txt",
                "project-x",
                content_hash,
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.commit()

        # Global scope has no record -> new content.
        changed, doc_id = pipeline.check_content_changed("test.txt", content, "global")
        assert changed is True
        assert doc_id is None

        # project-x scope has matching hash -> unchanged.
        changed, doc_id = pipeline.check_content_changed("test.txt", content, "project-x")
        assert changed is False
        assert doc_id == "doc-scoped"

    def test_whitespace_only_change_no_diff(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """Trailing whitespace difference is not detected as a change."""
        content = "hello world"
        content_hash = compute_content_hash(content)
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, content_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("doc-ws", "indexed", "test.txt", "global", content_hash, "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        # Extra whitespace should NOT be detected as a change.
        changed, doc_id = pipeline.check_content_changed("test.txt", "  hello world  \n", "global")
        assert changed is False
        assert doc_id == "doc-ws"


# ---------------------------------------------------------------------------
# IngestResult.skipped field
# ---------------------------------------------------------------------------


class TestIngestResultSkipped:
    """IngestResult gains skipped: bool = False field."""

    def test_skipped_defaults_false(self) -> None:
        r = IngestResult(
            document_id="abc",
            chunk_count=1,
            entity_count=0,
            edge_count=0,
            status="indexed",
        )
        assert r.skipped is False

    def test_skipped_explicit_true(self) -> None:
        r = IngestResult(
            document_id="abc",
            chunk_count=0,
            entity_count=0,
            edge_count=0,
            status="skipped",
            skipped=True,
        )
        assert r.skipped is True


# ---------------------------------------------------------------------------
# Delta re-ingest integration tests (#282)
# ---------------------------------------------------------------------------


class TestDeltaReIngest:
    """Wire delta re-ingest check into ingest() and ingest_text()."""

    @pytest.mark.anyio
    async def test_first_ingest_normal_path(self, pipeline: IngestPipeline) -> None:
        """First ingest of a source runs the full pipeline (no skip)."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        assert result.status == "indexed"
        assert result.skipped is False
        assert result.chunk_count == 2

    @pytest.mark.anyio
    async def test_first_ingest_stores_content_hash(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """After first ingest, document_status.content_hash is populated."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        row = conn.execute(
            "SELECT content_hash FROM document_status WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        expected_hash = compute_content_hash(SAMPLE_INTAKE.content)
        assert row[0] == expected_hash

    @pytest.mark.anyio
    async def test_reingest_unchanged_content_skips(self, pipeline: IngestPipeline) -> None:
        """Re-ingesting identical content returns skipped=True, no new doc."""
        # First ingest.
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            first = await pipeline.ingest("test.txt")

        assert first.status == "indexed"

        # Second ingest — same content.
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            second = await pipeline.ingest("test.txt")

        assert second.skipped is True
        assert second.status == "skipped"
        assert second.document_id == first.document_id

    @pytest.mark.anyio
    async def test_reingest_unchanged_logs_skip(
        self,
        pipeline: IngestPipeline,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Skipping unchanged source logs INFO message."""
        # First ingest.
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest("test.txt")

        # Second ingest — same content, should log skip.
        with (
            caplog.at_level(logging.INFO),
            patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf,
        ):
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest("test.txt")

        assert any("skipping unchanged source" in r.message.lower() for r in caplog.records)

    @pytest.mark.anyio
    async def test_reingest_changed_content_deletes_old_and_reingests(
        self,
        pipeline: IngestPipeline,
        conn: sqlite3.Connection,
    ) -> None:
        """Re-ingesting changed content deletes old data and creates new doc."""
        # First ingest.
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            first = await pipeline.ingest("test.txt")

        assert first.status == "indexed"
        old_doc_id = first.document_id

        # Second ingest — changed content.
        changed_intake = IntakeResult(
            content="updated content here",
            source="test.txt",
            metadata={"source_type": "file"},
        )
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = changed_intake
            second = await pipeline.ingest("test.txt")

        assert second.skipped is False
        assert second.status == "indexed"
        assert second.document_id != old_doc_id

        # Old document should be deleted.
        old_row = conn.execute(
            "SELECT count(*) FROM documents WHERE id = ?", (old_doc_id,)
        ).fetchone()
        assert old_row[0] == 0

        # New document should exist.
        new_row = conn.execute(
            "SELECT count(*) FROM documents WHERE id = ?", (second.document_id,)
        ).fetchone()
        assert new_row[0] == 1

        # Content hash updated to new content.
        hash_row = conn.execute(
            "SELECT content_hash FROM document_status WHERE document_id = ?",
            (second.document_id,),
        ).fetchone()
        assert hash_row[0] == compute_content_hash("updated content here")

    @pytest.mark.anyio
    async def test_reingest_changed_logs_reingest(
        self,
        pipeline: IngestPipeline,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Re-ingesting changed source logs INFO message with old doc id."""
        # First ingest.
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            first = await pipeline.ingest("test.txt")

        # Second ingest — different content.
        changed_intake = IntakeResult(
            content="different content",
            source="test.txt",
            metadata={"source_type": "file"},
        )
        with (
            caplog.at_level(logging.INFO),
            patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf,
        ):
            mock_rf.return_value = changed_intake
            await pipeline.ingest("test.txt")

        assert any(
            "re-ingesting changed source" in r.message.lower() and first.document_id in r.message
            for r in caplog.records
        )

    @pytest.mark.anyio
    async def test_ingest_text_unchanged_skips(self, pipeline: IngestPipeline) -> None:
        """ingest_text() with unchanged content skips re-ingest."""
        first = await pipeline.ingest_text(
            "hello world", metadata={"url": "https://example.com/page"}
        )
        assert first.status == "indexed"
        assert first.skipped is False

        second = await pipeline.ingest_text(
            "hello world", metadata={"url": "https://example.com/page"}
        )
        assert second.skipped is True
        assert second.status == "skipped"
        assert second.document_id == first.document_id

    @pytest.mark.anyio
    async def test_ingest_text_changed_reingests(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """ingest_text() with changed content deletes old and creates new doc."""
        first = await pipeline.ingest_text(
            "original text", metadata={"url": "https://example.com/page"}
        )
        assert first.status == "indexed"

        second = await pipeline.ingest_text(
            "updated text", metadata={"url": "https://example.com/page"}
        )
        assert second.skipped is False
        assert second.status == "indexed"
        assert second.document_id != first.document_id

        # Old doc gone.
        old = conn.execute(
            "SELECT count(*) FROM documents WHERE id = ?", (first.document_id,)
        ).fetchone()
        assert old[0] == 0

    @pytest.mark.anyio
    async def test_ingest_text_stores_content_hash(
        self, pipeline: IngestPipeline, conn: sqlite3.Connection
    ) -> None:
        """After ingest_text(), document_status.content_hash is populated."""
        result = await pipeline.ingest_text("hash me", metadata={"url": "test-url"})

        row = conn.execute(
            "SELECT content_hash FROM document_status WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        assert row[0] == compute_content_hash("hash me")


# ---------------------------------------------------------------------------
# Graph builder integration (#286)
# ---------------------------------------------------------------------------


class TestGraphBuilderIntegration:
    """IngestPipeline triggers IntraDocGraphBuilder after successful ingestion."""

    @pytest.fixture
    def mock_intra_doc_builder(self) -> MagicMock:
        """Mock IntraDocGraphBuilder — async build returns empty result."""
        builder = MagicMock()
        builder.build = AsyncMock(return_value=GraphBuildResult())
        return builder

    @pytest.fixture
    def pipeline_with_builder(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
        mock_intra_doc_builder: MagicMock,
        tmp_path: Path,
    ) -> IngestPipeline:
        """IngestPipeline with a mocked IntraDocGraphBuilder wired in."""
        return _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            graph_builder=mock_intra_doc_builder,
        )

    @pytest.mark.anyio
    async def test_constructor_accepts_graph_builder(
        self, pipeline_with_builder: IngestPipeline
    ) -> None:
        """IngestPipeline accepts optional enricher parameter."""
        assert pipeline_with_builder._enricher is not None

    def test_constructor_defaults_graph_builder_none(self, pipeline: IngestPipeline) -> None:
        """enricher defaults to None when not provided."""
        assert pipeline._enricher is None

    @pytest.mark.anyio
    async def test_build_called_after_successful_ingest(
        self,
        pipeline_with_builder: IngestPipeline,
        mock_intra_doc_builder: MagicMock,
    ) -> None:
        """After successful ingest, graph builder build() is called."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline_with_builder.ingest(Path("test.txt"))

        await asyncio.sleep(0.01)

        mock_intra_doc_builder.build.assert_awaited_once()

    @pytest.mark.anyio
    async def test_enrichment_runs_non_blocking(
        self,
        pipeline_with_builder: IngestPipeline,
        conn: sqlite3.Connection,
    ) -> None:
        """ingest() returns 'indexed' immediately; enrichment updates DB later."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline_with_builder.ingest(Path("test.txt"))

        # Ingest returns "indexed" — enrichment hasn't run yet.
        assert result.status == "indexed"

        await asyncio.sleep(0.01)

        # After yielding, background task updated status.
        row = conn.execute(
            "SELECT status FROM document_status WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        assert row[0] == "graph_enriched"

    @pytest.mark.anyio
    async def test_skips_already_enriched_document(
        self,
        pipeline_with_builder: IngestPipeline,
        conn: sqlite3.Connection,
        mock_intra_doc_builder: MagicMock,
    ) -> None:
        """If document status is already graph_enriched, build() is not called."""
        doc_id = "pre-enriched"
        conn.execute(
            "INSERT INTO document_status "
            "(document_id, status, source, scope, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, "graph_enriched", "test.txt", "global", "2026-01-01", "2026-01-01"),
        )
        conn.commit()

        await pipeline_with_builder._enricher._enrich_graph(doc_id, list(SAMPLE_ENTITIES), "global")

        mock_intra_doc_builder.build.assert_not_awaited()

    @pytest.mark.anyio
    async def test_inferred_edges_stored_in_graph(
        self,
        pipeline_with_builder: IngestPipeline,
        mock_graph_store: MagicMock,
        mock_intra_doc_builder: MagicMock,
    ) -> None:
        """Inferred edges from graph builder are stored in graph store."""
        inferred_edge = Edge(
            source_id="e1",
            target_id="e2",
            relation=RelationType.DEFINES,
            weight=0.5,
        )
        mock_intra_doc_builder.build = AsyncMock(
            return_value=GraphBuildResult(edges_added=1, edges=[inferred_edge])
        )

        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline_with_builder.ingest(Path("test.txt"))

        await asyncio.sleep(0.01)

        edge_calls = mock_graph_store.insert_edge.call_args_list
        inserted = [c[0][0] for c in edge_calls]
        assert any(e.source_id == "e1" and e.target_id == "e2" for e in inserted)

    @pytest.mark.anyio
    async def test_no_enrichment_without_graph_builder(
        self,
        pipeline: IngestPipeline,
        conn: sqlite3.Connection,
    ) -> None:
        """When graph_builder is None, status stays 'indexed'."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        await asyncio.sleep(0.01)

        row = conn.execute(
            "SELECT status FROM document_status WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        assert row[0] == "indexed"

    @pytest.mark.anyio
    async def test_logs_scheduling_message(
        self,
        pipeline_with_builder: IngestPipeline,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """INFO log 'Scheduling graph enrichment for document ...' is emitted."""
        with (
            caplog.at_level(logging.INFO),
            patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf,
        ):
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline_with_builder.ingest(Path("test.txt"))

        assert any("scheduling graph enrichment" in r.message.lower() for r in caplog.records)

    @pytest.mark.anyio
    async def test_builder_failure_does_not_crash_ingest(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """If graph builder raises, ingest result is still returned successfully."""
        failing_builder = MagicMock()
        failing_builder.build = AsyncMock(side_effect=RuntimeError("LLM down"))

        pipe = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            graph_builder=failing_builder,
        )

        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipe.ingest(Path("test.txt"))

        await asyncio.sleep(0.01)

        assert result.status == "indexed"
        assert result.chunk_count == 2

    @pytest.mark.anyio
    async def test_ingest_text_triggers_enrichment(
        self,
        pipeline_with_builder: IngestPipeline,
        mock_intra_doc_builder: MagicMock,
    ) -> None:
        """ingest_text() also triggers graph enrichment."""
        await pipeline_with_builder.ingest_text("hello world")

        await asyncio.sleep(0.01)

        mock_intra_doc_builder.build.assert_awaited_once()

    @pytest.mark.anyio
    async def test_no_enrichment_when_extract_fails(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When extraction fails, graph enrichment is not scheduled."""
        failing_extractor = MagicMock()
        failing_extractor.extract = AsyncMock(side_effect=RuntimeError("LLM down"))

        builder = MagicMock()
        builder.build = AsyncMock(return_value=GraphBuildResult())

        pipe = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=failing_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            graph_builder=builder,
        )

        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipe.ingest(Path("test.txt"))

        await asyncio.sleep(0.01)

        builder.build.assert_not_awaited()


# ---------------------------------------------------------------------------
# Provenance metadata stamping (#410)
# ---------------------------------------------------------------------------


class TestProvenanceStamping:
    """IngestPipeline stamps source_pipeline/source_task in entity/edge metadata."""

    def test_constructor_accepts_pipeline_name(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """IngestPipeline accepts optional pipeline_name parameter."""
        pipe = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            pipeline_name="custom",
        )
        assert pipe._pipeline_name == "custom"

    def test_constructor_defaults_pipeline_name(self, pipeline: IngestPipeline) -> None:
        """pipeline_name defaults to 'ingest'."""
        assert pipeline._pipeline_name == "ingest"

    @pytest.mark.anyio
    async def test_store_extractions_stamps_entity_provenance(
        self,
        pipeline: IngestPipeline,
        mock_graph_store: MagicMock,
    ) -> None:
        """Entities stored via _store_extractions have provenance in metadata."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        # Check every insert_entity call's metadata.
        for call in mock_graph_store.insert_entity.call_args_list:
            entity = call[0][0]
            assert entity.metadata.get("source_pipeline") == "ingest"
            assert entity.metadata.get("source_task") == "entity_extraction"

    @pytest.mark.anyio
    async def test_store_extractions_stamps_edge_provenance(
        self,
        pipeline: IngestPipeline,
        mock_graph_store: MagicMock,
    ) -> None:
        """Edges stored via _store_extractions have provenance in metadata."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipeline.ingest(Path("test.txt"))

        # Edges from extraction (not graph enrichment) should have provenance.
        for call in mock_graph_store.insert_edge.call_args_list:
            edge = call[0][0]
            assert edge.metadata.get("source_pipeline") == "ingest"
            assert edge.metadata.get("source_task") == "entity_extraction"

    @pytest.mark.anyio
    async def test_custom_pipeline_name_propagates(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Custom pipeline_name appears in entity/edge metadata."""
        pipe = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            pipeline_name="custom_pipe",
        )
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipe.ingest(Path("test.txt"))

        for call in mock_graph_store.insert_entity.call_args_list:
            entity = call[0][0]
            assert entity.metadata["source_pipeline"] == "custom_pipe"

    @pytest.mark.anyio
    async def test_enrich_graph_stamps_edge_provenance(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Edges from _enrich_graph have source_task='graph_enrichment' in metadata."""
        inferred_edge = Edge(
            source_id="e1",
            target_id="e2",
            relation=RelationType.DEFINES,
            weight=0.5,
        )
        builder = MagicMock()
        builder.build = AsyncMock(
            return_value=GraphBuildResult(edges_added=1, edges=[inferred_edge])
        )

        pipe = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            graph_builder=builder,
        )

        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            await pipe.ingest(Path("test.txt"))

        await asyncio.sleep(0.01)

        # Find edge calls from enrichment (source_task='graph_enrichment').
        enrichment_edges = [
            call[0][0]
            for call in mock_graph_store.insert_edge.call_args_list
            if call[0][0].metadata.get("source_task") == "graph_enrichment"
        ]
        assert len(enrichment_edges) >= 1
        assert enrichment_edges[0].metadata["source_pipeline"] == "ingest"

    @pytest.mark.anyio
    async def test_entities_without_provenance_unaffected(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """Entities created directly (not through pipeline) have no provenance."""
        store = GraphStore(conn)
        entity = Entity(
            id="plain-ent",
            name="plain",
            entity_type=EntityType.CONCEPT,
            metadata={"custom": "value"},
        )
        store.insert_entity(entity)
        result = store.get_entity("plain-ent")
        assert result is not None
        assert "source_pipeline" not in result.metadata
        assert "source_task" not in result.metadata


# ---------------------------------------------------------------------------
# IngestResult provenance fields (#412)
# ---------------------------------------------------------------------------


class TestIngestResultProvenance:
    """IngestResult includes source_pipeline and source_task fields."""

    def test_default_provenance_fields(self) -> None:
        """IngestResult defaults: source_pipeline='ingest', source_task='full_pipeline'."""
        r = IngestResult(
            document_id="abc",
            chunk_count=1,
            entity_count=1,
            edge_count=0,
            status="indexed",
        )
        assert r.source_pipeline == "ingest"
        assert r.source_task == "full_pipeline"

    @pytest.mark.anyio
    async def test_ingest_populates_provenance(self, pipeline: IngestPipeline) -> None:
        """ingest() result includes source_pipeline from pipeline_name."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipeline.ingest(Path("test.txt"))

        assert result.source_pipeline == "ingest"
        assert result.source_task == "full_pipeline"

    @pytest.mark.anyio
    async def test_ingest_text_populates_provenance(self, pipeline: IngestPipeline) -> None:
        """ingest_text() result includes provenance."""
        result = await pipeline.ingest_text("hello world")
        assert result.source_pipeline == "ingest"
        assert result.source_task == "full_pipeline"

    @pytest.mark.anyio
    async def test_custom_pipeline_name_in_result(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_embedder: MagicMock,
        mock_extractor: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Custom pipeline_name propagates to IngestResult.source_pipeline."""
        pipe = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
            pipeline_name="my_pipe",
        )
        result = await pipe.ingest_text("hello world")
        assert result.source_pipeline == "my_pipe"

    @pytest.mark.anyio
    async def test_skipped_result_has_provenance(self, pipeline: IngestPipeline) -> None:
        """Skipped results include provenance fields."""
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            # First ingest succeeds.
            await pipeline.ingest(Path("test.txt"))
            # Second ingest should be skipped (unchanged content).
            result = await pipeline.ingest(Path("test.txt"))

        assert result.skipped is True
        assert result.source_pipeline == "ingest"
        assert result.source_task == "full_pipeline"

    @pytest.mark.anyio
    async def test_failed_result_has_provenance(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
        mock_vector_store: MagicMock,
        mock_chunker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Failed results include provenance fields."""
        failing_embedder = MagicMock(spec=["embed"])
        failing_embedder.embed.side_effect = RuntimeError("Boom")
        failing_extractor = MagicMock()
        failing_extractor.extract = AsyncMock(side_effect=RuntimeError("Boom"))

        pipe = _make_pipeline(
            conn=conn,
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            embedding_provider=failing_embedder,
            entity_extractor=failing_extractor,
            text_chunker=mock_chunker,
            workspace_root=tmp_path,
        )
        with patch("owlbear.memory.knowledge.ingest.read_file", new_callable=AsyncMock) as mock_rf:
            mock_rf.return_value = SAMPLE_INTAKE
            result = await pipe.ingest(Path("test.txt"))

        assert result.status == "failed"
        assert result.source_pipeline == "ingest"
        assert result.source_task == "full_pipeline"


# ---------------------------------------------------------------------------
# Background task concurrency limit (#649)
# ---------------------------------------------------------------------------

# These tests target a semaphore that limits concurrent _enrich_graph and
# _enrich_inter_doc_graph background tasks.


class TestBgConcurrencyConfig:
    """OwlBearSettings.ingest_bg_concurrency field validation."""

    def test_default_value_is_5(self) -> None:
        """AC-4: Default value of ingest_bg_concurrency is 5."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert settings.ingest_bg_concurrency == 5

    def test_rejects_zero(self) -> None:
        """AC-3: ingest_bg_concurrency=0 raises ValidationError.

        Precondition: the field must exist on the model (not just
        rejected as an unknown kwarg).
        """
        from owlbear.config import OwlBearSettings

        # Guard: field must be declared (xfail triggers here).
        assert "ingest_bg_concurrency" in OwlBearSettings.model_fields
        with pytest.raises(ValidationError):
            OwlBearSettings(ingest_bg_concurrency=0)

    def test_rejects_negative(self) -> None:
        """AC-3: ingest_bg_concurrency=-1 raises ValidationError.

        Precondition: the field must exist on the model (not just
        rejected as an unknown kwarg).
        """
        from owlbear.config import OwlBearSettings

        # Guard: field must be declared (xfail triggers here).
        assert "ingest_bg_concurrency" in OwlBearSettings.model_fields
        with pytest.raises(ValidationError):
            OwlBearSettings(ingest_bg_concurrency=-1)


class TestBgConcurrencySemaphore:
    """GraphEnricher._bg_semaphore construction and bounds."""

    def test_constructor_default_semaphore_value(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
    ) -> None:
        """AC-5: Default _bg_semaphore has value 5."""
        store = MagicMock(spec=DocumentStore)
        store.conn = conn
        enricher = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=None,
            inter_doc_builder=None,
            document_store=store,
            pipeline_name="ingest",
        )
        assert enricher._bg_semaphore._value == 5

    def test_constructor_override_semaphore_value(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
    ) -> None:
        """AC-6: bg_concurrency=3 sets _bg_semaphore._value to 3."""
        store = MagicMock(spec=DocumentStore)
        store.conn = conn
        enricher = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=None,
            inter_doc_builder=None,
            document_store=store,
            pipeline_name="ingest",
            bg_concurrency=3,
        )
        assert enricher._bg_semaphore._value == 3

    @pytest.mark.anyio
    async def test_enrich_graph_bounded_by_semaphore(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
    ) -> None:
        """AC-1: With bg_concurrency=2, at most 2 _enrich_graph calls run simultaneously."""
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
            # Yield control so other tasks can start.
            await asyncio.sleep(0.05)
            async with lock:
                current -= 1
            return GraphBuildResult(edges_added=0, edges=[])

        mock_builder = MagicMock()
        mock_builder.build = slow_build

        store = MagicMock(spec=DocumentStore)
        store.conn = conn
        enricher = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=mock_builder,
            inter_doc_builder=None,
            document_store=store,
            pipeline_name="ingest",
            bg_concurrency=2,
        )

        # Launch 5 concurrent _enrich_graph calls.
        tasks = [
            asyncio.create_task(enricher._enrich_graph(f"doc-{i}", SAMPLE_ENTITIES, "global"))
            for i in range(5)
        ]
        await asyncio.gather(*tasks)

        # At most 2 should have run concurrently.
        assert max_concurrent <= 2

    @pytest.mark.anyio
    async def test_all_tasks_complete(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
    ) -> None:
        """AC-2: All 5 enrichment calls complete (no drops) with semaphore throttling."""
        completed: list[str] = []

        async def tracking_build(
            _entities: list,
            *,
            scope: str,  # noqa: ARG001
            document_id: str,
        ) -> GraphBuildResult:
            await asyncio.sleep(0.02)
            completed.append(document_id)
            return GraphBuildResult(edges_added=0, edges=[])

        mock_builder = MagicMock()
        mock_builder.build = tracking_build

        store = MagicMock(spec=DocumentStore)
        store.conn = conn
        enricher = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=mock_builder,
            inter_doc_builder=None,
            document_store=store,
            pipeline_name="ingest",
            bg_concurrency=2,
        )

        tasks = [
            asyncio.create_task(enricher._enrich_graph(f"doc-{i}", SAMPLE_ENTITIES, "global"))
            for i in range(5)
        ]
        await asyncio.gather(*tasks)

        assert len(completed) == 5
        assert set(completed) == {f"doc-{i}" for i in range(5)}

    @pytest.mark.anyio
    async def test_enrich_inter_doc_graph_bounded_by_semaphore(
        self,
        conn: sqlite3.Connection,
        mock_graph_store: MagicMock,
    ) -> None:
        """AC-7: _enrich_inter_doc_graph also respects the shared semaphore."""
        max_concurrent = 0
        current = 0
        lock = asyncio.Lock()

        async def slow_inter_build(
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
            return GraphBuildResult(edges_added=0, edges=[])

        mock_inter_builder = MagicMock()
        mock_inter_builder.build = slow_inter_build

        store = MagicMock(spec=DocumentStore)
        store.conn = conn
        enricher = GraphEnricher(
            conn=conn,
            graph_store=mock_graph_store,
            graph_builder=None,
            inter_doc_builder=mock_inter_builder,
            document_store=store,
            pipeline_name="ingest",
            bg_concurrency=2,
        )

        tasks = [
            asyncio.create_task(
                enricher._enrich_inter_doc_graph(f"doc-{i}", SAMPLE_ENTITIES, "global")
            )
            for i in range(5)
        ]
        await asyncio.gather(*tasks)

        assert max_concurrent <= 2


# ===========================================================================
# cancel= parameter — cooperative cancellation seam (task #880)
# ===========================================================================


def _minimal_cancel_pipeline(
    extractor: MagicMock | None = None,
    chunker: MagicMock | None = None,
) -> IngestPipeline:
    """IngestPipeline with all-mock deps suitable for cancel contract tests."""
    store = MagicMock()
    store.check_content_changed.return_value = (True, None)
    store.embedding_provider = MagicMock(spec=["embed"])
    store.embedding_provider.embed.return_value = []
    return IngestPipeline(
        store=store,
        entity_extractor=extractor or MagicMock(),
        text_chunker=chunker or MagicMock(),
        workspace_root=Path("/tmp"),  # noqa: S108
    )


class TestFromAC_IngestCancellation:
    """cancel= stops _run_extract at chunk boundaries; CancelledError propagates."""

    @pytest.mark.asyncio
    async def test_run_extract_stops_before_next_chunk_when_cancel_is_set_between_calls(
        self,
    ) -> None:
        """_run_extract(chunks, cancel=) does not process the next chunk once cancel fires."""
        cancel = asyncio.Event()
        calls: list[str] = []

        async def tracking_extract(text: str, _metadata: dict) -> ExtractionResult:
            calls.append(text)
            cancel.set()  # fires after first extraction; second chunk should not run
            return ExtractionResult(entities=[], edges=[])

        extractor = MagicMock()
        extractor.extract = tracking_extract

        pipeline = _minimal_cancel_pipeline(extractor=extractor)
        chunks = [Chunk(text=f"c{i}", index=i, metadata={}) for i in range(3)]

        result = await pipeline._run_extract(chunks, cancel=cancel)

        assert len(result) == 1
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_cancelled_error_from_extractor_propagates_through_ingest_text(
        self,
    ) -> None:
        """asyncio.CancelledError raised by the extractor propagates out of ingest_text."""
        extractor = MagicMock()
        extractor.extract = AsyncMock(side_effect=asyncio.CancelledError())

        chunker = MagicMock()
        chunker.chunk.return_value = [Chunk(text="chunk 0", index=0, metadata={})]

        pipeline = _minimal_cancel_pipeline(extractor=extractor, chunker=chunker)

        with pytest.raises(asyncio.CancelledError):
            await pipeline.ingest_text("some text", cancel=asyncio.Event())

    @pytest.mark.asyncio
    async def test_ingest_text_threads_cancel_into_extraction_stopping_at_chunk_boundary(
        self,
    ) -> None:
        """cancel= threaded from ingest_text into _run_extract stops extraction after one chunk."""
        cancel = asyncio.Event()
        extract_calls: list[str] = []

        async def tracking_extract(text: str, _metadata: dict) -> ExtractionResult:
            extract_calls.append(text)
            cancel.set()  # fires after first chunk — second should not run
            return ExtractionResult(entities=[], edges=[])

        extractor = MagicMock()
        extractor.extract = tracking_extract

        chunker = MagicMock()
        chunker.chunk.return_value = [
            Chunk(text=f"chunk {i}", index=i, metadata={}) for i in range(3)
        ]

        pipeline = _minimal_cancel_pipeline(extractor=extractor, chunker=chunker)

        await pipeline.ingest_text("some text", cancel=cancel)

        assert len(extract_calls) == 1
