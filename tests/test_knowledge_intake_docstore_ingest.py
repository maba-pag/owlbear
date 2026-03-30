"""RED-phase tests for intake, document_store, and ingest pipeline upgrades (#206).

Tests the contract for:
  - owlbear_knowledge.intake: IntakeResult model, read_file, read_url, read_text
  - owlbear_knowledge.document_store: DocumentStore (new module, doesn't exist yet)
  - owlbear_knowledge.ingest: IngestPipeline upgrade (cancel, delta detection, ingest method)

All tests that import from intake.py or document_store.py fail with ImportError —
those modules do not yet exist. Ingest upgrade tests fail because the new pipeline
methods/constructor args are not yet implemented.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    from owlbear_knowledge.schema import init_db

    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


# ---------------------------------------------------------------------------
# intake.py — IntakeResult model
# ---------------------------------------------------------------------------


class TestFromAC_IntakeResult:
    """IntakeResult is a frozen Pydantic model with content, source, metadata fields."""

    def test_intake_result_importable(self) -> None:
        """IntakeResult can be imported from owlbear_knowledge.intake."""
        from owlbear_knowledge.intake import IntakeResult  # noqa: F401

    def test_intake_result_has_content_field(self) -> None:
        """IntakeResult stores the content field."""
        from owlbear_knowledge.intake import IntakeResult

        result = IntakeResult(content="hello world", source="test", metadata={})
        assert result.content == "hello world"

    def test_intake_result_has_source_field(self) -> None:
        """IntakeResult stores the source field."""
        from owlbear_knowledge.intake import IntakeResult

        result = IntakeResult(content="text", source="file://test.txt", metadata={})
        assert result.source == "file://test.txt"

    def test_intake_result_has_metadata_field(self) -> None:
        """IntakeResult stores the metadata dict field."""
        from owlbear_knowledge.intake import IntakeResult

        result = IntakeResult(content="text", source="test", metadata={"key": "value"})
        assert result.metadata["key"] == "value"

    def test_intake_result_is_frozen(self) -> None:
        """IntakeResult is immutable — assigning a field raises TypeError or ValidationError."""
        from owlbear_knowledge.intake import IntakeResult

        result = IntakeResult(content="hello", source="test", metadata={})
        with pytest.raises((TypeError, Exception)):
            result.content = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# intake.py — read_file
# ---------------------------------------------------------------------------


class TestFromAC_ReadFile:
    """read_file reads a file asynchronously and returns IntakeResult with file metadata."""

    @pytest.mark.asyncio
    async def test_read_file_success_returns_intake_result(self, tmp_path: Path) -> None:
        """read_file returns IntakeResult with the file's text as content."""
        from owlbear_knowledge.intake import IntakeResult, read_file

        target = tmp_path / "test.txt"
        target.write_text("hello world")
        result = await read_file(target, workspace_root=tmp_path)
        assert isinstance(result, IntakeResult)
        assert result.content == "hello world"

    @pytest.mark.asyncio
    async def test_read_file_metadata_source_type_is_file(self, tmp_path: Path) -> None:
        """read_file sets metadata['source_type'] = 'file'."""
        from owlbear_knowledge.intake import read_file

        target = tmp_path / "doc.md"
        target.write_text("content")
        result = await read_file(target, workspace_root=tmp_path)
        assert result.metadata.get("source_type") == "file"

    @pytest.mark.asyncio
    async def test_read_file_metadata_has_fetched_at(self, tmp_path: Path) -> None:
        """read_file sets a non-empty metadata['fetched_at'] timestamp."""
        from owlbear_knowledge.intake import read_file

        target = tmp_path / "doc.md"
        target.write_text("content")
        result = await read_file(target, workspace_root=tmp_path)
        assert "fetched_at" in result.metadata
        assert result.metadata["fetched_at"]

    @pytest.mark.asyncio
    async def test_read_file_sandbox_rejection_path_traversal(self, tmp_path: Path) -> None:
        """read_file raises PermissionError when the path escapes workspace_root."""
        from owlbear_knowledge.intake import read_file

        with pytest.raises(PermissionError):
            await read_file(Path("../outside.txt"), workspace_root=tmp_path)

    @pytest.mark.asyncio
    async def test_read_file_missing_raises_file_not_found(self, tmp_path: Path) -> None:
        """read_file raises FileNotFoundError for a non-existent path inside workspace."""
        from owlbear_knowledge.intake import read_file

        with pytest.raises(FileNotFoundError):
            await read_file(tmp_path / "nonexistent.txt", workspace_root=tmp_path)

    @pytest.mark.asyncio
    async def test_read_file_source_contains_path(self, tmp_path: Path) -> None:
        """read_file sets source to a string that includes the file path."""
        from owlbear_knowledge.intake import read_file

        target = tmp_path / "file.txt"
        target.write_text("data")
        result = await read_file(target, workspace_root=tmp_path)
        assert "file.txt" in result.source or str(target) in result.source


# ---------------------------------------------------------------------------
# intake.py — read_url
# ---------------------------------------------------------------------------


class TestFromAC_ReadUrl:
    """read_url fetches a URL asynchronously and returns IntakeResult with url metadata."""

    @pytest.mark.asyncio
    async def test_read_url_success_returns_intake_result(self) -> None:
        """read_url returns IntakeResult on a 2xx HTTP response."""
        from owlbear_knowledge.intake import IntakeResult, read_url

        mock_response = MagicMock()
        mock_response.text = "fetched content"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear_knowledge.intake.httpx.AsyncClient", return_value=mock_client):
            result = await read_url("https://example.com/doc")

        assert isinstance(result, IntakeResult)
        assert result.content == "fetched content"

    @pytest.mark.asyncio
    async def test_read_url_metadata_source_type_is_url(self) -> None:
        """read_url sets metadata['source_type'] = 'url'."""
        from owlbear_knowledge.intake import read_url

        mock_response = MagicMock()
        mock_response.text = "content"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("owlbear_knowledge.intake.httpx.AsyncClient", return_value=mock_client):
            result = await read_url("https://example.com/doc")

        assert result.metadata.get("source_type") == "url"

    @pytest.mark.asyncio
    async def test_read_url_error_raises_http_status_error(self) -> None:
        """read_url raises httpx.HTTPStatusError on a non-2xx response."""
        import httpx

        from owlbear_knowledge.intake import read_url

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("owlbear_knowledge.intake.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await read_url("https://example.com/missing")


# ---------------------------------------------------------------------------
# intake.py — read_text
# ---------------------------------------------------------------------------


class TestFromAC_ReadText:
    """read_text is a synchronous wrapper returning IntakeResult with source_type='text'."""

    def test_read_text_returns_intake_result(self) -> None:
        """read_text returns an IntakeResult for a plain string."""
        from owlbear_knowledge.intake import IntakeResult, read_text

        result = read_text("hello world")
        assert isinstance(result, IntakeResult)
        assert result.content == "hello world"

    def test_read_text_metadata_source_type_is_text(self) -> None:
        """read_text sets metadata['source_type'] = 'text'."""
        from owlbear_knowledge.intake import read_text

        result = read_text("some content")
        assert result.metadata.get("source_type") == "text"

    def test_read_text_is_synchronous(self) -> None:
        """read_text must be a regular (non-async) function."""
        import inspect

        from owlbear_knowledge.intake import read_text

        assert not inspect.iscoroutinefunction(read_text)


# ---------------------------------------------------------------------------
# document_store.py — DocumentStore constructor
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreConstructor:
    """DocumentStore constructor accepts conn, GraphStore, VectorStoreProtocol, EmbeddingProvider."""

    def test_document_store_importable(self) -> None:
        """DocumentStore can be imported from owlbear_knowledge.document_store."""
        from owlbear_knowledge.document_store import DocumentStore  # noqa: F401

    def test_document_store_accepts_all_required_args(self) -> None:
        """DocumentStore can be instantiated with all four required arguments."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        assert store is not None


# ---------------------------------------------------------------------------
# document_store.py — insert_document
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreInsert:
    """insert_document persists a document row retrievable from the documents table."""

    def test_insert_document_creates_row_in_db(self) -> None:
        """insert_document writes a row to the documents table."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Document

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        doc = Document(id="doc-001", title="Test", content="hello", metadata={}, scope="global")
        store.insert_document(doc)

        row = conn.execute("SELECT id FROM documents WHERE id = ?", ("doc-001",)).fetchone()
        assert row is not None
        assert row[0] == "doc-001"


# ---------------------------------------------------------------------------
# document_store.py — store_chunks
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreChunks:
    """store_chunks inserts chunk rows and returns chunk_ids matching input count."""

    def test_store_chunks_returns_ids_matching_input_count(self) -> None:
        """store_chunks returns a list of IDs with the same length as the chunks list."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        chunks = [
            Chunk(text="chunk one", index=0),
            Chunk(text="chunk two", index=1),
            Chunk(text="chunk three", index=2),
        ]
        ids = store.store_chunks("doc-001", chunks)
        assert len(ids) == 3

    def test_store_chunks_returns_string_ids(self) -> None:
        """store_chunks returns string IDs."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        ids = store.store_chunks("doc-001", [Chunk(text="text", index=0)])
        assert all(isinstance(cid, str) for cid in ids)

    def test_store_chunks_inserts_rows_in_db(self) -> None:
        """store_chunks persists chunk rows to the chunks table."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.store_chunks("doc-002", [Chunk(text="chunk text", index=0)])

        rows = conn.execute(
            "SELECT id FROM chunks WHERE document_id = ?", ("doc-002",)
        ).fetchall()
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# document_store.py — store_embeddings
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreEmbeddings:
    """store_embeddings calls VectorStoreProtocol.store_embedding for each chunk."""

    def test_store_embeddings_calls_vector_store_once_per_chunk(self) -> None:
        """store_embeddings calls vector_store.store_embedding exactly N times for N chunks."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        vector_store = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

        store.store_embeddings(["cid-1", "cid-2"], ["text one", "text two"])
        assert vector_store.store_embedding.call_count == 2

    def test_store_embeddings_passes_correct_chunk_id(self) -> None:
        """store_embeddings calls store_embedding with the correct chunk ID."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        vector_store = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [[0.1]]
        store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

        store.store_embeddings(["cid-abc"], ["hello"])
        call_args = vector_store.store_embedding.call_args
        positional = call_args[0]
        keyword = call_args[1]
        actual_id = keyword.get("entity_or_doc_id") or (positional[0] if positional else None)
        assert actual_id == "cid-abc"


# ---------------------------------------------------------------------------
# document_store.py — store_extractions
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreExtractions:
    """store_extractions calls insert_entity/insert_edge on GraphStore and returns counts."""

    def test_store_extractions_returns_entity_edge_tuple(self) -> None:
        """store_extractions returns a (entity_count, edge_count) tuple."""
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType

        conn = _make_db()
        graph = GraphStore(conn)
        store = DocumentStore(conn, graph, MagicMock(), MagicMock())

        entity = Entity(name="Alpha", entity_type=EntityType.CONCEPT)
        edge = Edge(
            source_id=entity.id,
            target_id=entity.id,
            relation=RelationType.RELATED_TO,
        )
        entity_count, edge_count = store.store_extractions(
            [ExtractionResult(entities=[entity], edges=[edge])]
        )
        assert entity_count == 1
        assert edge_count == 1

    def test_store_extractions_calls_insert_entity(self) -> None:
        """store_extractions calls graph_store.insert_entity for each entity."""
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.models import Entity, EntityType

        conn = _make_db()
        mock_graph = MagicMock()
        store = DocumentStore(conn, mock_graph, MagicMock(), MagicMock())

        entity = Entity(name="TestEntity", entity_type=EntityType.CONCEPT)
        store.store_extractions([ExtractionResult(entities=[entity], edges=[])])
        mock_graph.insert_entity.assert_called()

    def test_store_extractions_calls_insert_edge(self) -> None:
        """store_extractions calls graph_store.insert_edge for each edge."""
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType

        conn = _make_db()
        mock_graph = MagicMock()
        store = DocumentStore(conn, mock_graph, MagicMock(), MagicMock())

        entity = Entity(name="E1", entity_type=EntityType.CONCEPT)
        edge = Edge(
            source_id=entity.id,
            target_id=entity.id,
            relation=RelationType.RELATED_TO,
        )
        store.store_extractions([ExtractionResult(entities=[entity], edges=[edge])])
        mock_graph.insert_edge.assert_called()


# ---------------------------------------------------------------------------
# document_store.py — store_entity_embeddings
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreEntityEmbeddings:
    """store_entity_embeddings embeds entity descriptions and stores with embedding_type='entity'."""

    def test_store_entity_embeddings_calls_embed(self) -> None:
        """store_entity_embeddings calls embedder.embed with entity descriptions."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Entity, EntityType

        conn = _make_db()
        vector_store = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [[0.1, 0.2]]
        store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

        entities = [Entity(name="Concept", entity_type=EntityType.CONCEPT, description="A concept")]
        store.store_entity_embeddings(entities)
        embedder.embed.assert_called()

    def test_store_entity_embeddings_uses_entity_embedding_type(self) -> None:
        """store_entity_embeddings calls vector_store.store_embedding with embedding_type='entity'."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Entity, EntityType

        conn = _make_db()
        vector_store = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [[0.5, 0.6]]
        store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

        entities = [Entity(name="E", entity_type=EntityType.CONCEPT, description="desc")]
        store.store_entity_embeddings(entities)

        assert vector_store.store_embedding.called
        call = vector_store.store_embedding.call_args
        positional, keyword = call[0], call[1]
        actual_type = keyword.get("embedding_type") or (positional[2] if len(positional) > 2 else None)
        assert actual_type == "entity"


# ---------------------------------------------------------------------------
# document_store.py — delete_document_data
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreDelete:
    """delete_document_data cascade-deletes document, chunks, and associated rows."""

    def test_delete_document_data_removes_document_row(self) -> None:
        """delete_document_data removes the row from the documents table."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Document

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        doc = Document(id="del-001", title="Delete Me", content="bye", metadata={}, scope="global")
        store.insert_document(doc)
        store.delete_document_data("del-001")

        row = conn.execute("SELECT id FROM documents WHERE id = ?", ("del-001",)).fetchone()
        assert row is None

    def test_delete_document_data_removes_chunk_rows(self) -> None:
        """delete_document_data removes chunk rows for the document."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Document

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        doc = Document(id="del-002", title="T", content="c", metadata={}, scope="global")
        store.insert_document(doc)
        store.store_chunks("del-002", [Chunk(text="chunk text", index=0)])
        store.delete_document_data("del-002")

        rows = conn.execute(
            "SELECT id FROM chunks WHERE document_id = ?", ("del-002",)
        ).fetchall()
        assert rows == []

    def test_delete_document_data_removes_document_status_row(self) -> None:
        """delete_document_data removes the document_status row for the document."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.set_status("del-003", "ok", source="file://del.txt")
        store.delete_document_data("del-003")

        row = conn.execute(
            "SELECT document_id FROM document_status WHERE document_id = ?", ("del-003",)
        ).fetchone()
        assert row is None


# ---------------------------------------------------------------------------
# document_store.py — status roundtrip
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreStatus:
    """set_status then find_status_by_source returns the correct DocumentStatus."""

    def test_status_roundtrip_status_field(self) -> None:
        """set_status + find_status_by_source returns a record with the set status."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.set_status("doc-status-001", "completed", source="file://test.txt")

        found = store.find_status_by_source("file://test.txt")
        assert found is not None
        assert found.status == "completed"

    def test_status_roundtrip_document_id(self) -> None:
        """find_status_by_source returns a record with the correct document_id."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.set_status("doc-id-xyz", "ok", source="file://test2.txt")

        found = store.find_status_by_source("file://test2.txt")
        assert found is not None
        assert found.document_id == "doc-id-xyz"

    def test_find_status_by_source_returns_none_for_unknown_source(self) -> None:
        """find_status_by_source returns None when the source has no record."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        assert store.find_status_by_source("file://not-seen.txt") is None


# ---------------------------------------------------------------------------
# document_store.py — check_content_changed
# ---------------------------------------------------------------------------


class TestFromAC_CheckContentChanged:
    """check_content_changed contract: new=>(True,None), unchanged=>(False,id), changed=>(True,id)."""

    def test_new_content_returns_true_none(self) -> None:
        """check_content_changed returns (True, None) on first-time source."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())

        changed, doc_id = store.check_content_changed("file://new-source.txt", "brand new text")
        assert changed is True
        assert doc_id is None

    def test_unchanged_content_returns_false_doc_id(self) -> None:
        """check_content_changed returns (False, doc_id) when content hash matches."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        content = "same content unchanged"
        store.set_status("doc-unchanged", "ok", source="file://same.txt")
        store.update_content_hash("doc-unchanged", content)

        changed, doc_id = store.check_content_changed("file://same.txt", content)
        assert changed is False
        assert doc_id == "doc-unchanged"

    def test_changed_content_returns_true_doc_id(self) -> None:
        """check_content_changed returns (True, doc_id) when content hash differs."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.set_status("doc-changed", "ok", source="file://changed.txt")
        store.update_content_hash("doc-changed", "original content")

        changed, doc_id = store.check_content_changed(
            "file://changed.txt", "completely new content"
        )
        assert changed is True
        assert doc_id == "doc-changed"


# ---------------------------------------------------------------------------
# ingest.py upgrade — constructor with optional CancelSignal
# ---------------------------------------------------------------------------


class TestFromAC_IngestPipelineConstructor:
    """IngestPipeline constructor accepts DocumentStore, EntityExtractor, TextChunker, optional CancelSignal."""

    def test_ingest_pipeline_accepts_cancel_signal_kwarg(self) -> None:
        """IngestPipeline can be instantiated with an optional cancel_signal keyword arg."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline

        cancel_signal = MagicMock()
        cancel_signal.is_set.return_value = False

        pipeline = IngestPipeline(
            document_store=MagicMock(),
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
            cancel_signal=cancel_signal,
        )
        assert pipeline is not None


# ---------------------------------------------------------------------------
# ingest.py upgrade — ingest_text calls new DocumentStore methods
# ---------------------------------------------------------------------------


class TestFromAC_IngestTextUpgrade:
    """ingest_text now delegates to new DocumentStore.store_chunks and store_embeddings."""

    @pytest.mark.asyncio
    async def test_ingest_text_calls_store_chunks(self) -> None:
        """ingest_text calls document_store.store_chunks after chunking content."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline

        doc_store = MagicMock()
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)
        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
        )
        await pipeline.ingest_text("some text to ingest")
        doc_store.store_chunks.assert_called()

    @pytest.mark.asyncio
    async def test_ingest_text_calls_store_embeddings(self) -> None:
        """ingest_text calls document_store.store_embeddings after chunking."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline

        doc_store = MagicMock()
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)
        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
        )
        await pipeline.ingest_text("text for embedding")
        doc_store.store_embeddings.assert_called()


# ---------------------------------------------------------------------------
# ingest.py upgrade — ingest(IntakeResult) method
# ---------------------------------------------------------------------------


class TestFromAC_IngestMethod:
    """ingest(IntakeResult) -> IngestResult with correct entity/edge counts."""

    def test_ingest_method_exists_on_pipeline(self) -> None:
        """IngestPipeline must have an ingest method."""
        from owlbear_knowledge.ingest import IngestPipeline

        assert hasattr(IngestPipeline, "ingest")

    @pytest.mark.asyncio
    async def test_ingest_accepts_intake_result_returns_ingest_result(self) -> None:
        """ingest(IntakeResult) returns an IngestResult instance with status='ok'."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline, IngestResult
        from owlbear_knowledge.intake import IntakeResult

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)
        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
        )
        intake = IntakeResult(
            content="text to ingest", source="test://src", metadata={"source_type": "text"}
        )
        result = await pipeline.ingest(intake)
        assert isinstance(result, IngestResult)
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_ingest_result_includes_entity_and_edge_counts(self) -> None:
        """ingest returns IngestResult with entity_count and edge_count from extractions."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult
        from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType

        entity = Entity(name="A", entity_type=EntityType.CONCEPT)
        edge = Edge(source_id=entity.id, target_id=entity.id, relation=RelationType.RELATED_TO)

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (1, 1)

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(
            return_value=ExtractionResult(entities=[entity], edges=[edge])
        )
        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=TextChunker(),
        )
        intake = IntakeResult(content="text", source="s://x", metadata={})
        result = await pipeline.ingest(intake)
        assert result.entity_count == 1
        assert result.edge_count == 1


# ---------------------------------------------------------------------------
# ingest.py upgrade — delta detection
# ---------------------------------------------------------------------------


class TestFromAC_DeltaDetection:
    """ingest returns status='skipped' when content hash is unchanged."""

    @pytest.mark.asyncio
    async def test_unchanged_content_returns_skipped_status(self) -> None:
        """ingest returns IngestResult(status='skipped') when check_content_changed is False."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (False, "existing-doc-id")
        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
        )
        intake = IntakeResult(
            content="same content", source="file://doc.txt", metadata={"source_type": "file"}
        )
        result = await pipeline.ingest(intake)
        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_skipped_result_has_zero_chunk_count(self) -> None:
        """ingest with skipped status returns chunk_count=0 (no work done)."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (False, "doc-id-skip")
        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
        )
        intake = IntakeResult(content="unchanged", source="src://x", metadata={})
        result = await pipeline.ingest(intake)
        assert result.chunk_count == 0


# ---------------------------------------------------------------------------
# ingest.py upgrade — CancelSignal
# ---------------------------------------------------------------------------


class TestFromAC_CancelSignalIngest:
    """ingest returns status='cancelled' when cancel_signal.is_set() is True."""

    @pytest.mark.asyncio
    async def test_cancel_signal_set_returns_cancelled_status(self) -> None:
        """ingest returns IngestResult(status='cancelled') when signal is set before ingestion."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        cancel_signal = MagicMock()
        cancel_signal.is_set.return_value = True
        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
            cancel_signal=cancel_signal,
        )
        intake = IntakeResult(content="content", source="src://cancel", metadata={})
        result = await pipeline.ingest(intake)
        assert result.status == "cancelled"


# ---------------------------------------------------------------------------
# ingest.py upgrade — parallel embed + extract
# ---------------------------------------------------------------------------


class TestFromAC_ParallelOperations:
    """ingest calls both store_embeddings and store_extractions (embed + extract concurrently)."""

    @pytest.mark.asyncio
    async def test_both_embed_and_extract_called(self) -> None:
        """ingest invokes both store_embeddings (embed) and mock extractor.extract."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=TextChunker(target_tokens=10),
        )
        intake = IntakeResult(
            content="text with some words here", source="src://parallel", metadata={}
        )
        await pipeline.ingest(intake)

        mock_extractor.extract.assert_called()
        doc_store.store_embeddings.assert_called()


# ---------------------------------------------------------------------------
# ingest.py upgrade — error handling
# ---------------------------------------------------------------------------


class TestFromAC_IngestErrorHandling:
    """ingest returns status='failed' when an unexpected internal exception occurs."""

    @pytest.mark.asyncio
    async def test_internal_exception_returns_failed_status(self) -> None:
        """ingest returns IngestResult(status='failed') on unexpected runtime error."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        doc_store = MagicMock()
        doc_store.check_content_changed.side_effect = RuntimeError("unexpected failure")

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
        )
        intake = IntakeResult(content="text", source="src://err", metadata={})
        result = await pipeline.ingest(intake)
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# ingest.py upgrade — IngestResult status Literal validation
# ---------------------------------------------------------------------------


class TestFromAC_IngestResultStatusValues:
    """IngestResult status must be typed to only allow: ok, failed, skipped, cancelled."""

    def test_ingest_result_rejects_invalid_status(self) -> None:
        """IngestResult raises a validation error for unsupported status values."""
        from pydantic import ValidationError

        from owlbear_knowledge.ingest import IngestResult

        with pytest.raises((ValidationError, ValueError)):
            IngestResult(
                document_id="doc-001",
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="not_a_valid_status_value",
            )


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestFromAC_E2EIngest:
    """E2E: text input with mock extractor verifies graph + vector stores are populated."""

    @pytest.mark.asyncio
    async def test_e2e_entities_and_edges_in_graph_store(self) -> None:
        """E2E ingest with canned extractor populates graph_store with entities and edges."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult
        from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType

        conn = _make_db()
        graph = GraphStore(conn)

        entity_a = Entity(name="Alpha", entity_type=EntityType.CONCEPT)
        entity_b = Entity(name="Beta", entity_type=EntityType.CONCEPT)
        edge = Edge(
            source_id=entity_a.id,
            target_id=entity_b.id,
            relation=RelationType.RELATED_TO,
        )
        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(
            return_value=ExtractionResult(entities=[entity_a, entity_b], edges=[edge])
        )

        vector_store = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [[0.1, 0.2]]

        doc_store = DocumentStore(conn, graph, vector_store, embedder)
        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=TextChunker(target_tokens=50),
        )
        intake = IntakeResult(
            content="Alpha and Beta are related concepts.",
            source="test://e2e",
            metadata={"source_type": "text"},
        )
        result = await pipeline.ingest(intake)
        assert result.status == "ok"
        assert result.entity_count == 2
        assert result.edge_count == 1

    @pytest.mark.asyncio
    async def test_e2e_vector_store_receives_embeddings(self) -> None:
        """E2E ingest calls vector_store.store_embedding at least once."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult
        from owlbear_knowledge.models import Entity, EntityType

        conn = _make_db()
        graph = GraphStore(conn)

        entity = Entity(name="Gamma", entity_type=EntityType.CONCEPT, description="a gamma entity")
        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(
            return_value=ExtractionResult(entities=[entity], edges=[])
        )

        vector_store = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [[0.1, 0.2, 0.3]]

        doc_store = DocumentStore(conn, graph, vector_store, embedder)
        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=TextChunker(target_tokens=50),
        )
        intake = IntakeResult(
            content="Gamma is a concept.",
            source="test://e2e-embed",
            metadata={"source_type": "text"},
        )
        await pipeline.ingest(intake)
        assert vector_store.store_embedding.called


# ---------------------------------------------------------------------------
# Retry-cycle additions (reviewer LAX findings)
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreDeleteCascadeEntitiesEdges:
    """delete_document_data must cascade-delete entities and edges for the document.

    Reviewer finding LAX-1: prior tests never inserted entities with document_id set,
    so the entity/edge deletion loop (document_store.py line 162) was never executed.
    This test inserts entities with explicit document_id and verifies the cascade.
    """

    def test_delete_document_data_removes_entities_with_document_id(self) -> None:
        """delete_document_data removes entities whose document_id matches."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Document, Entity, EntityType

        conn = _make_db()
        graph = GraphStore(conn)
        store = DocumentStore(conn, graph, MagicMock(), MagicMock())

        doc = Document(id="del-ent-001", title="T", content="c", metadata={}, scope="global")
        store.insert_document(doc)

        # Insert entities with document_id explicitly set
        entity_a = Entity(name="A", entity_type=EntityType.CONCEPT, document_id="del-ent-001")
        entity_b = Entity(name="B", entity_type=EntityType.CONCEPT, document_id="del-ent-001")
        graph.insert_entity(entity_a)
        graph.insert_entity(entity_b)

        # Precondition: entities exist
        rows_before = conn.execute(
            "SELECT id FROM entities WHERE document_id = ?", ("del-ent-001",)
        ).fetchall()
        assert len(rows_before) == 2

        store.delete_document_data("del-ent-001")

        rows_after = conn.execute(
            "SELECT id FROM entities WHERE document_id = ?", ("del-ent-001",)
        ).fetchall()
        assert rows_after == []

    def test_delete_document_data_removes_edges_for_document_entities(self) -> None:
        """delete_document_data removes edges connected to the document's entities."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Document, Edge, Entity, EntityType, RelationType

        conn = _make_db()
        graph = GraphStore(conn)
        store = DocumentStore(conn, graph, MagicMock(), MagicMock())

        doc = Document(id="del-ent-002", title="T", content="c", metadata={}, scope="global")
        store.insert_document(doc)

        entity_a = Entity(name="A2", entity_type=EntityType.CONCEPT, document_id="del-ent-002")
        entity_b = Entity(name="B2", entity_type=EntityType.CONCEPT, document_id="del-ent-002")
        graph.insert_entity(entity_a)
        graph.insert_entity(entity_b)

        edge = Edge(
            source_id=entity_a.id, target_id=entity_b.id, relation=RelationType.RELATED_TO
        )
        graph.insert_edge(edge)

        # Precondition: edge exists
        edge_row_before = conn.execute(
            "SELECT id FROM edges WHERE source_id = ?", (entity_a.id,)
        ).fetchone()
        assert edge_row_before is not None

        store.delete_document_data("del-ent-002")

        edge_row_after = conn.execute(
            "SELECT id FROM edges WHERE source_id = ? OR target_id = ?",
            (entity_a.id, entity_b.id),
        ).fetchall()
        assert edge_row_after == []


class TestFromAC_IngestTextErrorHandling:
    """ingest_text returns status='failed' when an unexpected internal exception occurs.

    Reviewer finding LAX-2: TestFromAC_IngestErrorHandling only tests ingest(),
    leaving the ingest_text() except block (ingest.py lines 109-111) unexercised.
    """

    @pytest.mark.asyncio
    async def test_ingest_text_internal_exception_returns_failed_status(self) -> None:
        """ingest_text returns IngestResult(status='failed') on unexpected runtime error."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline

        doc_store = MagicMock()
        doc_store.insert_document.side_effect = RuntimeError("store failure in ingest_text")

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=TextChunker(),
        )
        result = await pipeline.ingest_text("some text that triggers failure")
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_ingest_text_chunker_exception_returns_failed_status(self) -> None:
        """ingest_text returns status='failed' when the chunker itself raises."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline

        doc_store = MagicMock()
        broken_chunker = MagicMock(spec=TextChunker)
        broken_chunker.chunk.side_effect = RuntimeError("chunker exploded")

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=EntityExtractor("stub"),
            text_chunker=broken_chunker,
        )
        result = await pipeline.ingest_text("text that makes chunker fail")
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# Builder-discovered: guard-clause coverage
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Edge cases discovered during GREEN phase — guard-clause paths not triggered by TestFromAC_."""

    def test_store_embeddings_empty_list_is_noop(self) -> None:
        """store_embeddings with empty chunk_ids does nothing and does not call embedder."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        embedder = MagicMock()
        vector_store = MagicMock()
        store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

        store.store_embeddings([], [])

        embedder.embed.assert_not_called()
        vector_store.store_embedding.assert_not_called()

    def test_store_entity_embeddings_empty_list_is_noop(self) -> None:
        """store_entity_embeddings with empty entities does nothing and does not call embedder."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        embedder = MagicMock()
        vector_store = MagicMock()
        store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

        store.store_entity_embeddings([])

        embedder.embed.assert_not_called()
        vector_store.store_embedding.assert_not_called()
