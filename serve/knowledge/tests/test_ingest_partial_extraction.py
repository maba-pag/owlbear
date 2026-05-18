"""Partial extraction failures should not corrupt chunk provenance."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

import owlbear_knowledge.refresh as refresh_module
from owlbear_knowledge.chunker import Chunk
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline, IngestResult
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import Entity, EntityType, KnowledgeSource, SourceType
from owlbear_knowledge.refresh import RefreshOrchestrator
from owlbear_knowledge.schema import init_db


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(connection)
    return connection


class TwoChunker:
    def chunk(self, _text: str, *, metadata: dict[str, object] | None = None) -> list[Chunk]:
        chunk_metadata = dict(metadata or {})
        return [
            Chunk(text="first", index=0, metadata=chunk_metadata),
            Chunk(text="second", index=1, metadata=chunk_metadata),
        ]


class PartiallyFailingExtractor:
    async def extract(self, text: str, metadata: dict[str, object] | None = None) -> ExtractionResult:
        _ = metadata
        if text == "first":
            message = "first chunk extraction failed"
            raise RuntimeError(message)
        return ExtractionResult(
            entities=[Entity(name="SecondEntity", entity_type=EntityType.CONCEPT, description="from second chunk")]
        )


class FailsFirstChunkOnceExtractor:
    def __init__(self) -> None:
        self.failed_once = False

    async def extract(self, text: str, metadata: dict[str, object] | None = None) -> ExtractionResult:
        _ = metadata
        if text == "first" and not self.failed_once:
            self.failed_once = True
            message = "transient first chunk extraction failed"
            raise RuntimeError(message)
        return ExtractionResult(
            entities=[Entity(name=f"{text.title()}Entity", entity_type=EntityType.CONCEPT, description=text)]
        )


def _document_store(conn: sqlite3.Connection) -> DocumentStore:
    graph_store = GraphStore(conn)
    vector_store = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 10, [0.2] * 10]
    return DocumentStore(conn, graph_store, vector_store, embedder)


@pytest.mark.asyncio
async def test_partial_extraction_keeps_successful_entity_on_original_chunk(conn: sqlite3.Connection) -> None:
    pipeline = IngestPipeline(_document_store(conn), PartiallyFailingExtractor(), TwoChunker())

    result = await pipeline.ingest_text("ignored", source_url="file://partial.md")

    assert result.status == "partial"
    assert len(result.warnings) == 1
    second_chunk_id = conn.execute("SELECT id FROM chunks WHERE content = 'second'").fetchone()[0]
    entity_row = conn.execute("SELECT name, chunk_id FROM entities").fetchone()
    assert entity_row == ("SecondEntity", second_chunk_id)
    status_row = conn.execute("SELECT status, error FROM document_status").fetchone()
    assert status_row[0] == "partial"
    assert "first chunk extraction failed" in status_row[1]


@pytest.mark.asyncio
async def test_partial_extraction_is_retried_for_same_content(conn: sqlite3.Connection) -> None:
    pipeline = IngestPipeline(_document_store(conn), FailsFirstChunkOnceExtractor(), TwoChunker())

    first = await pipeline.ingest_text("ignored", source_url="file://partial.md")
    second = await pipeline.ingest_text("ignored", source_url="file://partial.md")

    assert first.status == "partial"
    assert second.status == "ok"
    assert conn.execute("SELECT status, error FROM document_status").fetchone() == ("ok", None)
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 2


class UpdatingStore:
    def __init__(self) -> None:
        self.updated: KnowledgeSource | None = None

    def update(self, source: KnowledgeSource) -> None:
        self.updated = source


class PartialPipeline:
    async def ingest(self, _intake: IntakeResult, *, scope: str, source_id: str) -> IngestResult:
        return IngestResult(
            document_id="doc-1",
            chunk_count=2,
            entity_count=1,
            edge_count=0,
            status="partial",
            warnings=[f"partial graph extraction for {source_id} in {scope}"],
        )


@pytest.mark.asyncio
async def test_refresh_counts_partial_ingest_and_surfaces_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    async def read_url(_url: str) -> IntakeResult:
        return IntakeResult(content="content", source="https://example.test/doc", metadata={"source_type": "url"})

    store = UpdatingStore()
    source = KnowledgeSource(
        id="src-1",
        name="Source",
        source_type=SourceType.URL_LIST,
        fetch_method="http",
        enrich=True,
        config={"urls": ["https://example.test/doc"]},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr(refresh_module._intake, "read_url", read_url)
    orchestrator = RefreshOrchestrator(store=store, pipeline=PartialPipeline())

    result = await orchestrator.refresh(source)

    assert result.refreshed == 0
    assert result.partial == 1
    assert result.failed == 0
    assert result.warnings == ["partial graph extraction for src-1 in global"]
    assert store.updated is not None
    assert store.updated.last_error == "partial graph extraction for src-1 in global"


@pytest.mark.asyncio
async def test_refresh_url_list_without_urls_reports_failure() -> None:
    store = UpdatingStore()
    source = KnowledgeSource(
        id="src-1",
        name="Source",
        source_type=SourceType.URL_LIST,
        fetch_method="http",
        enrich=True,
        config={},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    orchestrator = RefreshOrchestrator(store=store, pipeline=object())

    result = await orchestrator.refresh(source)

    assert result.failed == 1
    assert result.errors == ["source has no URL configured"]
    assert store.updated is not None
    assert store.updated.last_error == "source has no URL configured"
