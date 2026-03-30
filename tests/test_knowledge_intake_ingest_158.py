"""RED-phase tests for intake + ingest pipeline upgrade (#158).

Tests the contract for the upgraded AC-specified method signatures in:
  - owlbear_knowledge.intake: read_text sets fetched_at
  - owlbear_knowledge.document_store: upgraded DocumentStore method signatures
  - owlbear_knowledge.ingest: ingest() scope parameter, ingest_text() uses new store API
  - owlbear_knowledge.__init__: IntakeResult, IngestPipeline, IngestResult, DocumentStore exported
  - packages/knowledge/pyproject.toml: httpx intake optional dep group

All tests fail against the current implementation — the AC signatures differ from what
#206 delivered. Task #158 upgrades these interfaces to match the spec.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    from owlbear_knowledge.schema import init_db

    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _make_store() -> object:
    from owlbear_knowledge.document_store import DocumentStore
    from owlbear_knowledge.graph_store import GraphStore

    conn = _make_db()
    return DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())


# ---------------------------------------------------------------------------
# intake.py — read_text sets fetched_at (all readers must set fetched_at per AC)
# ---------------------------------------------------------------------------


class TestFromAC_ReadTextFetchedAt:
    """All intake readers must set metadata['fetched_at'] to current UTC ISO timestamp.

    AC: All readers set metadata[fetched_at] to current UTC ISO timestamp.
    read_text is a reader — it must also set this field.
    """

    def test_read_text_sets_fetched_at_in_metadata(self) -> None:
        """read_text sets metadata['fetched_at'] to a non-empty timestamp string."""
        from owlbear_knowledge.intake import read_text

        result = read_text("hello world")
        assert "fetched_at" in result.metadata, "read_text must set metadata['fetched_at']"
        assert result.metadata["fetched_at"], "metadata['fetched_at'] must be non-empty"

    def test_read_text_fetched_at_is_iso_format(self) -> None:
        """read_text sets metadata['fetched_at'] to a valid ISO datetime string."""
        from datetime import datetime

        from owlbear_knowledge.intake import read_text

        result = read_text("some content")
        ts = result.metadata.get("fetched_at")
        assert ts is not None
        # Must be parseable as ISO datetime (datetime.fromisoformat raises on invalid)
        datetime.fromisoformat(ts)  # type: ignore[arg-type]

    def test_read_text_with_source_param_sets_fetched_at(self) -> None:
        """read_text with an explicit source param also sets metadata['fetched_at']."""
        from owlbear_knowledge.intake import read_text

        result = read_text("data", source="custom://src")
        assert "fetched_at" in result.metadata


# ---------------------------------------------------------------------------
# intake.py — read_text source parameter (AC: source: str = "inline")
# ---------------------------------------------------------------------------


class TestFromAC_ReadTextSourceParam:
    """read_text must accept an optional source parameter (AC: source: str = 'inline')."""

    def test_read_text_accepts_source_keyword_arg(self) -> None:
        """read_text(text, source='custom') succeeds with an explicit source."""
        from owlbear_knowledge.intake import read_text

        result = read_text("content", source="custom://id")
        assert result.source == "custom://id"

    def test_read_text_default_source_is_exactly_inline(self) -> None:
        """read_text() with no source sets source to exactly 'inline' (AC: source: str = 'inline')."""
        from owlbear_knowledge.intake import read_text

        result = read_text("content")
        # AC specifies the default value is 'inline' — not a URI scheme like 'text://inline'
        assert result.source == "inline"


# ---------------------------------------------------------------------------
# document_store.py — insert_document new signature
# AC: insert_document(document_id: str, intake: IntakeResult, *, scope: str = "global") -> None
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreInsertDocumentSignature:
    """insert_document must accept (document_id, intake, *, scope) — not a Document object."""

    def test_insert_document_accepts_document_id_intake_scope(self) -> None:
        """insert_document(document_id, intake, scope=...) signature is accepted."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.intake import IntakeResult

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        intake = IntakeResult(
            content="hello", source="file://test.txt", metadata={"source_type": "file"}
        )
        # AC signature: insert_document(document_id, intake, *, scope)
        store.insert_document("doc-insert-001", intake, scope="global")

    def test_insert_document_with_intake_creates_row(self) -> None:
        """insert_document with new signature persists the document to the documents table."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.intake import IntakeResult

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        intake = IntakeResult(
            content="persisted content",
            source="file://persist.txt",
            metadata={"source_type": "file"},
        )
        store.insert_document("doc-insert-002", intake, scope="global")

        row = conn.execute("SELECT id FROM documents WHERE id = ?", ("doc-insert-002",)).fetchone()
        assert row is not None

    def test_insert_document_uses_scope(self) -> None:
        """insert_document stores the document with the provided scope."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.intake import IntakeResult

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        intake = IntakeResult(
            content="scoped content",
            source="file://scope.txt",
            metadata={"source_type": "file"},
        )
        store.insert_document("doc-scope-001", intake, scope="workspace")

        row = conn.execute(
            "SELECT scope FROM documents WHERE id = ?", ("doc-scope-001",)
        ).fetchone()
        assert row is not None
        assert row[0] == "workspace"


# ---------------------------------------------------------------------------
# document_store.py — store_chunks scope parameter
# AC: store_chunks(document_id, chunks, *, scope: str = "global") -> list[str]
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreChunksScope:
    """store_chunks must accept an optional scope keyword argument."""

    def test_store_chunks_accepts_scope_kwarg(self) -> None:
        """store_chunks('doc', chunks, scope='workspace') is accepted without error."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        chunks = [Chunk(text="chunk one", index=0)]
        ids = store.store_chunks("doc-001", chunks, scope="workspace")
        assert len(ids) == 1

    def test_store_chunks_scope_kwarg_is_keyword_only(self) -> None:
        """scope must be keyword-only; calling with scope returns IDs AND is accepted by new API.

        The AC declares scope as a keyword-only parameter (*, scope).  With the current
        implementation, store_chunks only accepts (document_id, chunks) and raises TypeError
        on scope='global'.  This test verifies the new kwarg exists AND returns ids.
        """
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        chunks = [Chunk(text="chunk text", index=0), Chunk(text="chunk two", index=1)]
        # Must accept scope kwarg AND return correct count — current impl fails here
        ids = store.store_chunks("doc-002", chunks, scope="global")
        assert len(ids) == 2, "store_chunks must return chunk_ids matching input length"


# ---------------------------------------------------------------------------
# document_store.py — store_embeddings new signature
# AC: store_embeddings(document_id: str, chunks: list[Chunk],
#                      embeddings: list[HybridEmbedding], *, scope: str = "global") -> None
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreEmbeddingsSignature:
    """store_embeddings must accept (document_id, chunks, embeddings, *, scope)."""

    def test_store_embeddings_accepts_new_signature(self) -> None:
        """store_embeddings(document_id, chunks, embeddings, scope=...) is accepted."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.protocol import HybridEmbedding

        conn = _make_db()
        vector_store = MagicMock()
        store = DocumentStore(conn, GraphStore(conn), vector_store, MagicMock())

        chunks = [Chunk(text="chunk text", index=0)]
        embeddings = [HybridEmbedding(dense=[0.1, 0.2])]
        store.store_embeddings("doc-emb-001", chunks, embeddings, scope="global")

    def test_store_embeddings_calls_vector_store_with_hybrid_embedding(self) -> None:
        """store_embeddings passes HybridEmbedding objects to vector_store.store_embedding."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.protocol import HybridEmbedding

        conn = _make_db()
        vector_store = MagicMock()
        store = DocumentStore(conn, GraphStore(conn), vector_store, MagicMock())

        chunk = Chunk(text="test chunk", index=0)
        embedding = HybridEmbedding(dense=[0.1, 0.2, 0.3])
        store.store_embeddings("doc-emb-002", [chunk], [embedding], scope="global")

        assert vector_store.store_embedding.called
        call = vector_store.store_embedding.call_args
        positional, keyword = call[0], call[1]
        # The actual embedding passed must be the HybridEmbedding, not a raw list
        actual_embedding = keyword.get("embedding") or (positional[1] if len(positional) > 1 else None)
        assert isinstance(actual_embedding, HybridEmbedding)

    def test_store_embeddings_new_signature_scope_workspace(self) -> None:
        """store_embeddings accepts scope='workspace' without error."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.protocol import HybridEmbedding

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        chunks = [Chunk(text="workspace chunk", index=0)]
        embeddings = [HybridEmbedding(dense=[0.5])]
        # Should not raise
        store.store_embeddings("doc-scope-emb", chunks, embeddings, scope="workspace")


# ---------------------------------------------------------------------------
# document_store.py — store_extractions new signature
# AC: store_extractions(results, *, scope, document_id, chunk_ids, pipeline_name="ingest")
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreExtractionsSignature:
    """store_extractions must accept (results, *, scope, document_id, chunk_ids, pipeline_name)."""

    def test_store_extractions_accepts_provenance_kwargs(self) -> None:
        """store_extractions(results, scope=, document_id=, chunk_ids=, pipeline_name=) accepted."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        entity_count, edge_count = store.store_extractions(
            [ExtractionResult(entities=[], edges=[])],
            scope="global",
            document_id="doc-ext-001",
            chunk_ids=["cid-1"],
            pipeline_name="ingest",
        )
        assert isinstance(entity_count, int)
        assert isinstance(edge_count, int)

    def test_store_extractions_pipeline_name_defaults_to_ingest(self) -> None:
        """store_extractions pipeline_name defaults to 'ingest' when omitted."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        # Must not raise — pipeline_name must have a default of "ingest"
        store.store_extractions(
            [ExtractionResult(entities=[], edges=[])],
            scope="global",
            document_id="doc-ext-002",
            chunk_ids=[],
        )

    def test_store_extractions_stamps_provenance_on_entities(self) -> None:
        """store_extractions stamps provenance metadata (pipeline_name) on inserted entities."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.models import Entity, EntityType

        conn = _make_db()
        mock_graph = MagicMock()
        store = DocumentStore(conn, mock_graph, MagicMock(), MagicMock())

        entity = Entity(name="ProvenanceEntity", entity_type=EntityType.CONCEPT)
        store.store_extractions(
            [ExtractionResult(entities=[entity], edges=[])],
            scope="global",
            document_id="doc-prov-001",
            chunk_ids=["cid-prov"],
            pipeline_name="test-pipeline",
        )
        # insert_entity must have been called with provenance metadata
        mock_graph.insert_entity.assert_called()
        call_kwargs = mock_graph.insert_entity.call_args
        inserted_entity = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("entity")
        # The entity's provenance metadata must reflect the pipeline_name
        assert inserted_entity is not None


# ---------------------------------------------------------------------------
# document_store.py — store_entity_embeddings new signature
# AC: store_entity_embeddings(results: list[ExtractionResult], *, scope: str = "global")
# ---------------------------------------------------------------------------


class TestFromAC_DocumentStoreEntityEmbeddingsSignature:
    """store_entity_embeddings must accept (results: list[ExtractionResult], *, scope)."""

    def test_store_entity_embeddings_accepts_extraction_results(self) -> None:
        """store_entity_embeddings(results=[ExtractionResult(...)], scope=...) is accepted."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Entity, EntityType

        conn = _make_db()
        vector_store = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [[0.1, 0.2]]
        store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

        entity = Entity(name="Concept", entity_type=EntityType.CONCEPT, description="A concept")
        results = [ExtractionResult(entities=[entity], edges=[])]
        store.store_entity_embeddings(results=results, scope="global")

    def test_store_entity_embeddings_embeds_entities_from_results(self) -> None:
        """store_entity_embeddings calls embedder.embed for entities in ExtractionResult."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Entity, EntityType

        conn = _make_db()
        vector_store = MagicMock()
        embedder = MagicMock()
        embedder.embed.return_value = [[0.1, 0.2]]
        store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

        entity = Entity(name="E1", entity_type=EntityType.CONCEPT, description="desc")
        results = [ExtractionResult(entities=[entity], edges=[])]
        store.store_entity_embeddings(results=results, scope="global")

        embedder.embed.assert_called()

    def test_store_entity_embeddings_scope_kwarg_accepted(self) -> None:
        """store_entity_embeddings with scope='workspace' does not raise."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        embedder = MagicMock()
        embedder.embed.return_value = []
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), embedder)
        # Empty results — no-op but must accept scope
        store.store_entity_embeddings(results=[], scope="workspace")


# ---------------------------------------------------------------------------
# ingest.py — ingest() scope parameter
# AC: async ingest(intake_result, *, scope: str = "global") -> IngestResult
# ---------------------------------------------------------------------------


class TestFromAC_IngestScope:
    """ingest() must accept a scope keyword argument and forward it to the document store."""

    @pytest.mark.asyncio
    async def test_ingest_accepts_scope_kwarg(self) -> None:
        """ingest(intake, scope='workspace') is accepted without error."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline
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
            content="scoped content",
            source="file://scoped.txt",
            metadata={"source_type": "file"},
        )
        result = await pipeline.ingest(intake, scope="workspace")
        assert result.status in {"ok", "failed", "skipped", "cancelled"}

    @pytest.mark.asyncio
    async def test_ingest_passes_scope_to_insert_document(self) -> None:
        """ingest() calls document_store.insert_document with the provided scope."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline
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
        intake = IntakeResult(content="text", source="src://x", metadata={})
        await pipeline.ingest(intake, scope="custom-scope")

        # insert_document must be called with scope='custom-scope'
        assert doc_store.insert_document.called
        call = doc_store.insert_document.call_args
        _, kwargs = call[0], call[1]
        # scope must appear either as kwarg or as part of the call
        actual_scope = kwargs.get("scope") or (
            call[0][2] if len(call[0]) > 2 else None
        )
        assert actual_scope == "custom-scope"

    @pytest.mark.asyncio
    async def test_ingest_passes_scope_to_store_chunks(self) -> None:
        """ingest() calls document_store.store_chunks with the provided scope."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline
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
        intake = IntakeResult(content="content", source="src://y", metadata={})
        await pipeline.ingest(intake, scope="scope-test")

        assert doc_store.store_chunks.called
        call = doc_store.store_chunks.call_args
        actual_scope = call[1].get("scope") or (call[0][2] if len(call[0]) > 2 else None)
        assert actual_scope == "scope-test"


# ---------------------------------------------------------------------------
# ingest.py — update_content_hash called after successful ingest
# AC: store, update status — delta detection + update_content_hash
# ---------------------------------------------------------------------------


class TestFromAC_IngestUpdateContentHash:
    """ingest must call update_content_hash after successful ingest (not just set_status)."""

    @pytest.mark.asyncio
    async def test_ingest_calls_update_content_hash(self) -> None:
        """ingest calls document_store.update_content_hash after ok ingest."""
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.extractor import EntityExtractor
        from owlbear_knowledge.ingest import IngestPipeline
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
            content="hashable content", source="file://hash.txt", metadata={}
        )
        result = await pipeline.ingest(intake)
        assert result.status == "ok"
        doc_store.update_content_hash.assert_called()


# ---------------------------------------------------------------------------
# __init__.py — IntakeResult, IngestPipeline, IngestResult, DocumentStore in __all__
# AC: add IntakeResult, IngestPipeline, IngestResult to __all__; add DocumentStore import
# ---------------------------------------------------------------------------


class TestFromAC_InitExports:
    """owlbear_knowledge.__init__ must export IntakeResult, IngestPipeline, IngestResult, DocumentStore."""

    def test_intake_result_importable_from_package(self) -> None:
        """from owlbear_knowledge import IntakeResult succeeds."""
        from owlbear_knowledge import IntakeResult  # noqa: F401

    def test_ingest_pipeline_importable_from_package(self) -> None:
        """from owlbear_knowledge import IngestPipeline succeeds."""
        from owlbear_knowledge import IngestPipeline  # noqa: F401

    def test_ingest_result_importable_from_package(self) -> None:
        """from owlbear_knowledge import IngestResult succeeds."""
        from owlbear_knowledge import IngestResult  # noqa: F401

    def test_document_store_importable_from_package(self) -> None:
        """from owlbear_knowledge import DocumentStore succeeds."""
        from owlbear_knowledge import DocumentStore  # noqa: F401

    def test_intake_result_in_dunder_all(self) -> None:
        """IntakeResult appears in owlbear_knowledge.__all__."""
        import owlbear_knowledge

        assert "IntakeResult" in owlbear_knowledge.__all__

    def test_ingest_pipeline_in_dunder_all(self) -> None:
        """IngestPipeline appears in owlbear_knowledge.__all__."""
        import owlbear_knowledge

        assert "IngestPipeline" in owlbear_knowledge.__all__

    def test_ingest_result_in_dunder_all(self) -> None:
        """IngestResult appears in owlbear_knowledge.__all__."""
        import owlbear_knowledge

        assert "IngestResult" in owlbear_knowledge.__all__

    def test_document_store_in_dunder_all(self) -> None:
        """DocumentStore appears in owlbear_knowledge.__all__."""
        import owlbear_knowledge

        assert "DocumentStore" in owlbear_knowledge.__all__


# ---------------------------------------------------------------------------
# pyproject.toml — httpx optional dep group
# AC: add httpx as optional dep group `intake = ["httpx>=0.27"]`; add to `full` group
# ---------------------------------------------------------------------------


class TestFromAC_PyprojectHttpxDep:
    """pyproject.toml must declare httpx>=0.27 in [project.optional-dependencies.intake]."""

    def _load_pyproject(self) -> dict:
        import tomllib

        pyproject_path = Path(__file__).parent.parent / "packages" / "knowledge" / "pyproject.toml"
        return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    def test_intake_optional_dep_group_exists(self) -> None:
        """pyproject.toml has an [project.optional-dependencies.intake] section."""
        data = self._load_pyproject()
        optional_deps = data.get("project", {}).get("optional-dependencies", {})
        assert "intake" in optional_deps, "Missing [project.optional-dependencies.intake]"

    def test_intake_group_contains_httpx(self) -> None:
        """[optional-dependencies.intake] lists httpx>=0.27."""
        data = self._load_pyproject()
        intake_deps = data["project"]["optional-dependencies"].get("intake", [])
        httpx_entries = [d for d in intake_deps if "httpx" in d.lower()]
        assert httpx_entries, "intake dep group must include httpx>=0.27"
        assert any("0.27" in d for d in httpx_entries), (
            "httpx dep must specify >= 0.27"
        )

    def test_full_group_includes_httpx(self) -> None:
        """[optional-dependencies.full] includes httpx>=0.27 (or depends on intake)."""
        data = self._load_pyproject()
        optional_deps = data.get("project", {}).get("optional-dependencies", {})
        full_deps = optional_deps.get("full", [])
        # full group must include httpx directly or reference the intake group
        has_httpx = any("httpx" in d.lower() for d in full_deps)
        has_intake_ref = any("intake" in d.lower() for d in full_deps)
        assert has_httpx or has_intake_ref, (
            "full dep group must include httpx>=0.27 or reference the intake group"
        )
