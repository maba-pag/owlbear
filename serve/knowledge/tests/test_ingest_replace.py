"""Replace-on-change ingest should preserve the last good document on failure."""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import EntityExtractor
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.schema import init_db


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(connection)
    return connection


@pytest.fixture()
def doc_store(conn: sqlite3.Connection) -> DocumentStore:
    graph_store = GraphStore(conn)
    vector_store = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 10]
    return DocumentStore(conn, graph_store, vector_store, embedder)


@pytest.fixture()
def pipeline(doc_store: DocumentStore) -> IngestPipeline:
    return IngestPipeline(doc_store, EntityExtractor(), TextChunker())


def _intake(content: str) -> IntakeResult:
    return IntakeResult(
        content=content,
        source="file://docs/source.md",
        metadata={"source_type": "file"},
    )


@pytest.mark.asyncio
async def test_ingest_uses_metadata_title_and_keeps_source_query(
    conn: sqlite3.Connection,
    doc_store: DocumentStore,
    pipeline: IngestPipeline,
) -> None:
    intake = IntakeResult(
        content="titled content",
        source="file://docs/titled.md",
        metadata={"source_type": "file", "title": "Readable Title"},
    )

    result = await pipeline.ingest(intake, scope="global")

    assert result.status == "ok"
    title, metadata_json = conn.execute(
        "SELECT title, metadata FROM documents WHERE id = ?", (result.document_id,)
    ).fetchone()
    assert title == "Readable Title"
    assert json.loads(metadata_json)["intake_source"] == "file://docs/titled.md"
    document = doc_store.get_document_by_source("file://docs/titled.md")
    assert document is not None
    assert document.title == "Readable Title"


@pytest.mark.asyncio
async def test_replace_failure_preserves_previous_document(
    conn: sqlite3.Connection,
    doc_store: DocumentStore,
    pipeline: IngestPipeline,
) -> None:
    first = await pipeline.ingest(_intake("version one"), scope="global")
    assert first.status == "ok"
    previous_id = first.document_id

    with patch.object(doc_store, "store_chunks", side_effect=RuntimeError("forced replacement failure")):
        second = await pipeline.ingest(_intake("version two"), scope="global")

    assert second.status == "failed"
    rows = conn.execute("SELECT id, content FROM documents").fetchall()
    assert rows == [(previous_id, "version one")]
    status = conn.execute("SELECT document_id, source FROM document_status").fetchone()
    assert status == (previous_id, "file://docs/source.md")


@pytest.mark.asyncio
async def test_replace_success_deletes_previous_document(
    conn: sqlite3.Connection,
    pipeline: IngestPipeline,
) -> None:
    first = await pipeline.ingest(_intake("version one"), scope="global")
    second = await pipeline.ingest(_intake("version two"), scope="global")

    assert first.status == "ok"
    assert second.status == "ok"
    rows = conn.execute("SELECT id, content FROM documents").fetchall()
    assert rows == [(second.document_id, "version two")]
    status = conn.execute("SELECT document_id, source FROM document_status").fetchone()
    assert status == (second.document_id, "file://docs/source.md")
