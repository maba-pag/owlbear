"""Direct MCP ingestion should use the delta-aware ingest path."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import EntityExtractor
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_knowledge.refresh import RefreshOrchestrator
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore
from owlbear_mcp_knowledge.server import AppContext, ingest_document


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(connection)
    return connection


@pytest.fixture()
def app_ctx(conn: sqlite3.Connection) -> AppContext:
    graph_store = GraphStore(conn)
    vector_store = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 10]
    document_store = DocumentStore(conn, graph_store, vector_store, embedder)
    source_store = KnowledgeSourceStore(conn)
    return AppContext(
        conn=conn,
        query_service=None,
        graph_store=graph_store,
        ingest_pipeline=IngestPipeline(
            document_store,
            EntityExtractor(),
            TextChunker(),
            source_store=source_store,
        ),
        source_store=source_store,
        refresh_orchestrator=None,
    )


def _ctx(app_ctx: AppContext) -> MagicMock:
    context = MagicMock()
    context.request_context.lifespan_context = app_ctx
    return context


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


@pytest.mark.asyncio
async def test_same_source_url_and_content_skips_duplicate_document(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    first = await ingest_document(
        _ctx(app_ctx),
        text="same content",
        metadata={"title": "Doc"},
        source_url="file://docs/direct.md",
    )
    second = await ingest_document(
        _ctx(app_ctx),
        text="same content",
        metadata={"title": "Doc"},
        source_url="file://docs/direct.md",
    )

    assert "status: ok" in first
    assert "status: skipped" in second
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM document_status").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM knowledge_sources").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_same_source_url_changed_content_replaces_existing_document(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    await ingest_document(
        _ctx(app_ctx),
        text="version one",
        metadata={"title": "Doc"},
        source_url="file://docs/direct.md",
    )
    await ingest_document(
        _ctx(app_ctx),
        text="version two",
        metadata={"title": "Doc"},
        source_url="file://docs/direct.md",
    )

    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM document_status").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM knowledge_sources").fetchone()[0] == 1
    content = conn.execute("SELECT content FROM documents").fetchone()[0]
    assert content == "version two"


@pytest.mark.asyncio
async def test_anonymous_text_ingests_remain_independent(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    first = await ingest_document(_ctx(app_ctx), text="anonymous content")
    second = await ingest_document(_ctx(app_ctx), text="anonymous content")

    assert "status: ok" in first
    assert "status: ok" in second
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM knowledge_sources").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_file_source_url_creates_file_source_kind(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    await ingest_document(
        _ctx(app_ctx),
        text="local file content",
        source_url="file://docs/direct.md",
    )

    row = conn.execute("SELECT source_type, fetch_method, config FROM knowledge_sources").fetchone()
    assert row[:2] == ("file_glob", "file")
    config = json.loads(row[2])
    assert config["url"] == "file://docs/direct.md"
    assert config["path"] == "docs/direct.md"
    assert config["pattern"] == "docs/direct.md"


@pytest.mark.asyncio
async def test_direct_file_source_refresh_uses_same_delta_identity(
    tmp_path: Path,
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    file_path = tmp_path / "direct.md"
    file_path.write_text("version one", encoding="utf-8")
    source_url = f"file://{file_path}"

    await ingest_document(_ctx(app_ctx), text="version one", source_url=source_url)
    assert app_ctx.source_store is not None
    assert app_ctx.ingest_pipeline is not None
    source = app_ctx.source_store.list_all()[0]
    refresh = RefreshOrchestrator(
        store=app_ctx.source_store,
        pipeline=app_ctx.ingest_pipeline,
        workspace_root=tmp_path,
    )

    unchanged = await refresh.refresh(source)
    assert unchanged.skipped == 1
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1

    file_path.write_text("version two", encoding="utf-8")
    changed = await refresh.refresh(source)
    assert changed.refreshed == 1
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert conn.execute("SELECT content FROM documents").fetchone()[0] == "version two"


@pytest.mark.asyncio
async def test_legacy_authenticated_web_file_url_refreshes_as_local_file(
    tmp_path: Path,
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    file_path = tmp_path / "legacy.md"
    file_path.write_text("legacy content", encoding="utf-8")
    source_url = f"file://{file_path}"
    assert app_ctx.source_store is not None
    assert app_ctx.ingest_pipeline is not None
    source = KnowledgeSource(
        name=source_url,
        source_type=SourceType.AUTHENTICATED_WEB,
        fetch_method="url",
        enrich=True,
        config={"url": source_url},
        created_at=_now(),
        updated_at=_now(),
    )
    app_ctx.source_store.create(source)

    refresh = RefreshOrchestrator(
        store=app_ctx.source_store,
        pipeline=app_ctx.ingest_pipeline,
        workspace_root=tmp_path,
        content_fetcher=None,
    )
    result = await refresh.refresh(source)

    assert result.refreshed == 1
    assert result.failed == 0
    assert conn.execute("SELECT content FROM documents").fetchone()[0] == "legacy content"
