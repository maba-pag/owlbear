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
from owlbear_mcp_knowledge.server import AppContext, get_next_batch, ingest_document


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
    assert conn.execute("SELECT COUNT(*) FROM knowledge_sources WHERE source_type = 'inline'").fetchone()[0] == 2


@pytest.mark.asyncio
async def test_anonymous_text_ingest_creates_claimable_inline_source(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    await ingest_document(
        _ctx(app_ctx),
        text="anonymous claimable content",
        metadata={"title": "Jeff sent x.pdf"},
    )

    source_row = conn.execute(
        "SELECT id, name, source_type, fetch_method, enabled, refreshable, enrich FROM knowledge_sources"
    ).fetchone()
    assert source_row[1:] == ("Jeff sent x.pdf", "inline", "inline", 1, 0, 1)
    assert conn.execute("SELECT source_id FROM documents").fetchone()[0] == source_row[0]
    batch = await get_next_batch(_ctx(app_ctx), limit=1)
    assert len(batch) == 1
    assert batch[0]["source_id"] == source_row[0]
    assert batch[0]["source_name"] == "Jeff sent x.pdf"


@pytest.mark.asyncio
async def test_anonymous_text_ingests_with_same_title_create_distinct_inline_sources(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    first = await ingest_document(_ctx(app_ctx), text="first", metadata={"title": "Repeated Title"})
    second = await ingest_document(_ctx(app_ctx), text="second", metadata={"title": "Repeated Title"})

    assert "status: ok" in first
    assert "status: ok" in second
    rows = conn.execute("SELECT name, source_type FROM knowledge_sources ORDER BY created_at ASC, id ASC").fetchall()
    assert len(rows) == 2
    assert rows[0] == ("Repeated Title", "inline")
    assert rows[1][0].startswith("Repeated Title (")
    assert rows[1][1] == "inline"


@pytest.mark.asyncio
async def test_metadata_url_creates_source_link_for_enrichment(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    source_url = "https://example.test/meta-doc"

    result = await ingest_document(
        _ctx(app_ctx),
        text="metadata url content",
        metadata={"title": "Meta Doc", "url": source_url},
    )

    assert "status: ok" in result
    doc_source_id = conn.execute("SELECT source_id FROM documents").fetchone()[0]
    assert doc_source_id is not None
    source_row = conn.execute(
        "SELECT name, source_type, fetch_method, enrich, config FROM knowledge_sources"
    ).fetchone()
    assert source_row[:4] == (source_url, "url_list", "http", 1)
    assert json.loads(source_row[4])["url"] == source_url
    status = conn.execute("SELECT source, status FROM document_status").fetchone()
    assert status == (source_url, "ok")
    claimable = conn.execute(
        """
        SELECT COUNT(*)
        FROM chunks AS c
        JOIN documents AS d ON d.id = c.document_id
        JOIN knowledge_sources AS ks ON ks.id = d.source_id
        WHERE ks.enrich = 1
        """
    ).fetchone()[0]
    assert claimable == 1


@pytest.mark.asyncio
async def test_global_ingest_does_not_reuse_non_global_source(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    source_url = "https://example.test/shared"
    now = _now()
    assert app_ctx.source_store is not None
    app_ctx.source_store.create(
        KnowledgeSource(
            id="team-src",
            name="Team Source",
            source_type=SourceType.AUTHENTICATED_WEB,
            fetch_method="http",
            enrich=True,
            config={"url": source_url, "urls": [source_url]},
            scope="team",
            created_at=now,
            updated_at=now,
        )
    )

    result = await ingest_document(_ctx(app_ctx), text="global text", source_url=source_url, scope="global")

    assert "status: ok" in result
    linked_row = conn.execute(
        """
        SELECT ks.id, ks.scope
        FROM documents AS d
        JOIN knowledge_sources AS ks ON ks.id = d.source_id
        """
    ).fetchone()
    assert linked_row[0] != "team-src"
    assert linked_row[1] == "global"
    source_scopes = conn.execute("SELECT scope FROM knowledge_sources ORDER BY scope").fetchall()
    assert source_scopes == [("global",), ("team",)]


@pytest.mark.asyncio
async def test_direct_ingest_reuses_url_list_source_for_secondary_url(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    primary_url = "https://example.test/a"
    secondary_url = "https://example.test/b"
    now = _now()
    assert app_ctx.source_store is not None
    app_ctx.source_store.create(
        KnowledgeSource(
            id="url-list-src",
            name="URL List Source",
            source_type=SourceType.URL_LIST,
            fetch_method="http",
            enrich=True,
            config={"url": primary_url, "urls": [primary_url, secondary_url]},
            scope="team",
            created_at=now,
            updated_at=now,
        )
    )

    result = await ingest_document(_ctx(app_ctx), text="secondary text", source_url=secondary_url, scope="team")

    assert "status: ok" in result
    linked_source_id = conn.execute("SELECT source_id FROM documents").fetchone()[0]
    assert linked_source_id == "url-list-src"
    assert conn.execute("SELECT COUNT(*) FROM knowledge_sources").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_plain_metadata_source_label_creates_inline_source(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    result = await ingest_document(
        _ctx(app_ctx),
        text="manual label content",
        metadata={"title": "Manual Doc", "source": "manual upload"},
    )

    assert "status: ok" in result
    doc_source_id = conn.execute("SELECT source_id FROM documents").fetchone()[0]
    assert doc_source_id is not None
    source_row = conn.execute(
        "SELECT name, source_type, fetch_method, enabled, refreshable, config FROM knowledge_sources"
    ).fetchone()
    assert source_row[:5] == ("Manual Doc", "inline", "inline", 1, 0)
    assert json.loads(source_row[5])["source"] == "manual upload"
    assert conn.execute("SELECT source FROM document_status").fetchone()[0] == "manual upload"


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
async def test_metadata_file_url_creates_file_source_kind(
    conn: sqlite3.Connection,
    app_ctx: AppContext,
) -> None:
    await ingest_document(
        _ctx(app_ctx),
        text="metadata local file content",
        metadata={"url": "file://docs/meta.md"},
    )

    doc_source_id = conn.execute("SELECT source_id FROM documents").fetchone()[0]
    assert doc_source_id is not None
    row = conn.execute("SELECT source_type, fetch_method, config FROM knowledge_sources").fetchone()
    assert row[:2] == ("file_glob", "file")
    config = json.loads(row[2])
    assert config["url"] == "file://docs/meta.md"
    assert config["path"] == "docs/meta.md"
    assert config["pattern"] == "docs/meta.md"


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
