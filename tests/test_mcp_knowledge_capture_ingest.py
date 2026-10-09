"""Assembled Knowledge MCP regressions for browser capture rounds and inline ingest."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_knowledge.fetcher import MAX_RESPONSE_BYTES, HttpxContentFetcher
from owlbear_knowledge_mcp import server

_URL_A = "https://fixture.example/a"
_URL_B = "https://fixture.example/b"
_URL_C = "https://fixture.example/c"


class _DeterministicEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text) + 1)] for text in texts]


class _DeterministicVectorStore:
    def __init__(self) -> None:
        self.vectors: dict[str, tuple[list[float], str]] = {}

    def store_embedding(
        self,
        entity_or_doc_id: str,
        embedding: object,
        _embedding_type: str,
        *,
        scope: str,
    ) -> None:
        if not isinstance(embedding, list):
            msg = "deterministic vectors require dense lists"
            raise TypeError(msg)
        self.vectors[entity_or_doc_id] = (list(embedding), scope)

    def delete_embedding(self, entity_or_doc_id: str) -> bool:
        return self.vectors.pop(entity_or_doc_id, None) is not None

    def search_similar(
        self,
        _query_embedding: object,
        *,
        top_k: int,
        embedding_type: str,
        scopes: list[str] | None,
    ) -> list[tuple[str, float]]:
        del embedding_type
        ranked = [
            (chunk_id, 1.0) for chunk_id, (_vector, scope) in self.vectors.items() if scopes is None or scope in scopes
        ]
        return ranked[:top_k]


class _FailingContentReadConnection(sqlite3.Connection):
    fail_content_reads = False

    def execute(self, sql: str, parameters: object = ()) -> sqlite3.Cursor:
        if self.fail_content_reads and "FROM content_documents" in sql:
            msg = "database path token secret"
            raise sqlite3.OperationalError(msg)
        return super().execute(sql, parameters)


def _assembled_context(
    tmp_path: Path,
    *,
    connection_factory: type[sqlite3.Connection] = sqlite3.Connection,
) -> tuple[SimpleNamespace, server.AppContext]:
    marker = tmp_path / ".owlbear"
    marker.mkdir(parents=True, exist_ok=True)
    database_path = marker / "knowledge" / "local.db"
    database_path.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(database_path, factory=connection_factory)
    embedding_provider = _DeterministicEmbeddingProvider()
    vector_store = _DeterministicVectorStore()
    http_fetcher = HttpxContentFetcher()
    app_context = server.build_app_context(
        workspace_root=tmp_path,
        conn=connection,
        factories=server.KnowledgeRuntimeFactories(
            http_response_fetcher_factory=lambda: http_fetcher,
            embedding_provider_factory=lambda: embedding_provider,
            vector_store_factory=lambda _location: vector_store,
        ),
    )
    tool_context = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=app_context))
    return tool_context, app_context


async def _register_browser_source(
    tool_context: SimpleNamespace,
    urls: list[str],
    *,
    scope: str = "capture-test",
    fetch_method: str = "browser",
) -> str:
    source = await server.register_knowledge_source(
        tool_context,
        name=f"Browser fixture {scope}",
        kind="url_list",
        fetch_method=fetch_method,
        config={"kind": "url_list", "urls": urls},
        scope=scope,
        enrich=True,
    )
    return source["id"]


def _captured(url: str, text: str, **details: str) -> dict[str, Any]:
    return {"url": url, "captured": {"text": text, **details}}


def _failed(url: str, status: str, message: str = "") -> dict[str, Any]:
    return {"url": url, "failed": {"status": status, "message": message}}


async def _snippets(tool_context: SimpleNamespace, scope: str) -> list[str]:
    results = await server.knowledge_search(tool_context, query="capture", scopes=[scope], limit=10)
    assert isinstance(results, list)
    return [item["snippet"] for item in results]


async def _source_snapshot(
    tool_context: SimpleNamespace,
    app_context: server.AppContext,
    source_id: str,
) -> tuple[int, str, object]:
    source = next(item for item in await server.list_knowledge_sources(tool_context) if item["id"] == source_id)
    count = int(
        app_context.conn.execute(
            "SELECT COUNT(*) FROM content_documents WHERE source_id = ?",
            (source_id,),
        ).fetchone()[0],
    )
    return count, source["health"], source["last_checked_at"]


@pytest.mark.asyncio
async def test_bound_capture_round_is_typed_idempotent_and_replaces_documents(tmp_path: Path) -> None:
    tool_context, app_context = _assembled_context(tmp_path)
    try:
        scope = "capture-replacement"
        source_id = await _register_browser_source(tool_context, [_URL_A, _URL_B], scope=scope)
        original_captures = [
            _captured(
                _URL_A,
                "alpha original capture",
                title="Alpha article",
                canonical_url="https://fixture.example/a?view=full",
                fetched_at="2026-10-09T00:00:00Z",
                content_hash="alpha-original-hash",
            ),
            _captured(
                _URL_B,
                "beta original capture",
                title="Beta article",
                canonical_url=_URL_B,
                fetched_at="2026-10-09T00:00:00Z",
                content_hash="beta-original-hash",
            ),
        ]

        initial = await server.knowledge_ingest(tool_context, source_id=source_id, captures=original_captures)
        assert isinstance(initial, dict)
        assert initial["source_id"] == source_id
        assert initial["documents_created"] == 2
        assert initial["documents_failed"] == 0
        assert len(set(initial["document_ids"])) == 2
        assert initial["health"] == "ok"
        assert initial["errors"] == []
        document_uris = app_context.conn.execute(
            "SELECT uri FROM content_documents WHERE source_id = ?",
            (source_id,),
        ).fetchall()
        assert {row[0] for row in document_uris} == {
            _URL_A,
            _URL_B,
        }
        document_a = app_context.content_store.get_document(initial["document_ids"][0])
        assert document_a is not None
        assert document_a.metadata == {
            "canonical_url": "https://fixture.example/a?view=full",
            "title": "Alpha article",
            "fetched_at": "2026-10-09T00:00:00Z",
            "content_hash": "alpha-original-hash",
        }

        identical = await server.knowledge_ingest(tool_context, source_id=source_id, captures=original_captures)
        assert identical["documents_unchanged"] == 2
        assert identical["documents_created"] == 0
        assert identical["chunks_created"] == 0

        before_chunks_pending = (await server.knowledge_stats(tool_context))["chunks_pending"]
        replacement = await server.knowledge_ingest(
            tool_context,
            source_id=source_id,
            captures=[
                _captured(
                    _URL_A,
                    "alpha replacement capture",
                    title="Alpha article",
                    canonical_url=_URL_A,
                    fetched_at="2026-10-09T00:01:00Z",
                    content_hash="alpha-replacement-hash",
                ),
                original_captures[1],
            ],
        )
        assert replacement["documents_replaced"] == 1
        assert replacement["documents_unchanged"] == 1
        after_chunks_pending = (await server.knowledge_stats(tool_context))["chunks_pending"]
        assert after_chunks_pending == (
            before_chunks_pending - replacement["chunks_replaced"] + replacement["chunks_created"]
        )
        snippets = await _snippets(tool_context, scope)
        assert any("alpha replacement capture" in snippet for snippet in snippets)
        assert all("alpha original capture" not in snippet for snippet in snippets)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_capture_failures_preserve_last_good_documents_and_record_health(tmp_path: Path) -> None:
    tool_context, app_context = _assembled_context(tmp_path)
    try:
        scope = "capture-failures"
        source_id = await _register_browser_source(tool_context, [_URL_A, _URL_B], scope=scope)
        baseline = [
            _captured(_URL_A, "alpha last good capture"),
            _captured(_URL_B, "beta last good capture"),
        ]
        await server.knowledge_ingest(tool_context, source_id=source_id, captures=baseline)

        mixed = await server.knowledge_ingest(
            tool_context,
            source_id=source_id,
            captures=[
                _failed(_URL_A, "http_error", "agent supplied token secret"),
                _captured(_URL_B, "beta last good capture"),
            ],
        )
        assert mixed["documents_failed"] == 1
        assert mixed["health"] == "degraded"
        assert mixed["errors"][0]["stage"] == "acquisition"
        assert mixed["errors"][0]["code"] == "browser_capture_failed"
        assert "http_error" in mixed["errors"][0]["message"]
        assert "secret" not in str(mixed)
        assert any("alpha last good capture" in snippet for snippet in await _snippets(tool_context, scope))

        failed = await server.knowledge_ingest(
            tool_context,
            source_id=source_id,
            captures=[_failed(_URL_A, "access_denied"), _failed(_URL_B, "http_error")],
        )
        assert failed["documents_created"] == 0
        assert failed["documents_replaced"] == 0
        assert failed["documents_unchanged"] == 0
        assert failed["documents_failed"] == 2
        assert failed["health"] == "failed"
        listed = next(item for item in await server.list_knowledge_sources(tool_context) if item["id"] == source_id)
        assert listed["health"] == "failed"
        snippets = await _snippets(tool_context, scope)
        assert any("alpha last good capture" in snippet for snippet in snippets)
        assert any("beta last good capture" in snippet for snippet in snippets)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_invalid_capture_rounds_refuse_before_writing_source_or_content_state(tmp_path: Path) -> None:
    tool_context, app_context = _assembled_context(tmp_path)
    try:
        source_id = await _register_browser_source(tool_context, [_URL_A, _URL_B], scope="capture-validation")
        invalid_rounds = [
            [_captured(_URL_A, "missing B")],
            [_captured(_URL_A, "registered A"), _captured(_URL_C, "unregistered C")],
            [_captured(_URL_A, "first A"), _captured(_URL_A, "duplicate A")],
            [_failed(_URL_A, "unknown_status"), _captured(_URL_B, "B")],
            [
                {"url": _URL_A, "captured": {"text": "A"}, "failed": {"status": "http_error"}},
                _captured(_URL_B, "B"),
            ],
            [{"url": _URL_A}, _captured(_URL_B, "B")],
        ]

        for capture_round in invalid_rounds:
            before = await _source_snapshot(tool_context, app_context, source_id)
            with pytest.raises(ToolError):
                await server.knowledge_ingest(tool_context, source_id=source_id, captures=capture_round)
            assert await _source_snapshot(tool_context, app_context, source_id) == before

        before = await _source_snapshot(tool_context, app_context, source_id)
        with pytest.raises(ToolError):
            await server.knowledge_ingest(
                tool_context,
                source_id=source_id,
                captures=[_captured(_URL_A, "A"), _captured(_URL_B, "B")],
                text="submitted text must not be ingested",
            )
        assert await _source_snapshot(tool_context, app_context, source_id) == before

        for inline_field in ({"source_url": _URL_A}, {"scope": "other-scope"}):
            before = await _source_snapshot(tool_context, app_context, source_id)
            with pytest.raises(ToolError):
                await server.knowledge_ingest(
                    tool_context,
                    source_id=source_id,
                    captures=[_captured(_URL_A, "A"), _captured(_URL_B, "B")],
                    **inline_field,
                )
            assert await _source_snapshot(tool_context, app_context, source_id) == before

        http_source_id = await _register_browser_source(
            tool_context,
            [_URL_A, _URL_B],
            scope="capture-http-source",
            fetch_method="http",
        )
        with pytest.raises(ToolError):
            await server.knowledge_ingest(
                tool_context,
                source_id=http_source_id,
                captures=[_captured(_URL_A, "A"), _captured(_URL_B, "B")],
            )

        deleted_source_id = await _register_browser_source(tool_context, [_URL_A], scope="capture-deleted-source")
        await server.delete_knowledge_source(tool_context, deleted_source_id)
        with pytest.raises(ToolError):
            await server.knowledge_ingest(
                tool_context,
                source_id=deleted_source_id,
                captures=[_captured(_URL_A, "A")],
            )
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_capture_provenance_is_redacted_oversize_is_refused_and_delete_purges(tmp_path: Path) -> None:
    tool_context, app_context = _assembled_context(tmp_path)
    try:
        scope = "capture-redaction"
        source_id = await _register_browser_source(tool_context, [_URL_A], scope=scope)
        response = await server.knowledge_ingest(
            tool_context,
            source_id=source_id,
            captures=[
                _captured(
                    _URL_A,
                    "unique retained capture text",
                    title="Captured article",
                    canonical_url="https://user:pass@fixture.example/a?token=secret&view=full",
                    fetched_at="2026-10-09T00:00:00Z",
                    content_hash="content-hash",
                ),
            ],
        )
        assert "pass" not in str(response)
        assert "secret" not in str(response)
        document = app_context.content_store.get_document(response["document_ids"][0])
        assert document is not None
        assert document.metadata["canonical_url"] == "https://fixture.example/a?view=full"
        assert "pass" not in document.metadata["canonical_url"]
        assert "secret" not in document.metadata["canonical_url"]

        before = await _source_snapshot(tool_context, app_context, source_id)
        with pytest.raises(ToolError):
            await server.knowledge_ingest(
                tool_context,
                source_id=source_id,
                captures=[_captured(_URL_A, "x" * (MAX_RESPONSE_BYTES + 1))],
            )
        assert await _source_snapshot(tool_context, app_context, source_id) == before

        await server.delete_knowledge_source(tool_context, source_id)
        assert not any("unique retained capture text" in snippet for snippet in await _snippets(tool_context, scope))
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_inline_ingest_has_content_identity_and_redacted_persistence_failures(tmp_path: Path) -> None:
    tool_context, app_context = _assembled_context(tmp_path / "inline")
    try:
        with pytest.raises(ToolError):
            await server.knowledge_ingest(tool_context, text="inline text", captures=[])
        first = await server.knowledge_ingest(tool_context, text="first untitled inline document", scope="inline-test")
        second = await server.knowledge_ingest(
            tool_context, text="second untitled inline document", scope="inline-test"
        )
        assert isinstance(first, dict)
        assert first["documents_created"] == 1
        assert second["documents_created"] == 1
        assert first["document_ids"] != second["document_ids"]
        assert not isinstance(first, str)
        inline_source = next(
            item
            for item in await server.list_knowledge_sources(tool_context, scope="inline-test")
            if item["name"] == "mcp-inline-inline-test"
        )
        assert inline_source["refreshable"] is False
    finally:
        app_context.conn.close()

    failing_context, failing_app = _assembled_context(
        tmp_path / "failure",
        connection_factory=_FailingContentReadConnection,
    )
    try:
        failing_app.conn.fail_content_reads = True
        result = await server.knowledge_ingest(
            failing_context,
            text="inline text that must not appear in the error",
            scope="inline-failure",
        )
        assert isinstance(result, dict)
        assert result["documents_failed"] == 1
        assert result["errors"][0]["code"] == "persistence_failed"
        assert "database path token secret" not in str(result)
        assert "inline text that must not appear" not in str(result)
        inline_source = next(
            item
            for item in await server.list_knowledge_sources(failing_context, scope="inline-failure")
            if item["name"] == "mcp-inline-inline-failure"
        )
        assert inline_source["refreshable"] is False

        with patch.object(
            failing_app.ingest_coordinator,
            "ingest",
            side_effect=RuntimeError("raw exception token secret"),
        ):
            unexpected = await server.knowledge_ingest(
                failing_context,
                text="another private inline document",
                scope="inline-unexpected",
            )
        assert unexpected == {
            "stage": "persistence",
            "code": "persistence_failed",
            "retryable": True,
            "message": "Knowledge ingestion failed",
        }
        assert "raw exception token secret" not in str(unexpected)
    finally:
        failing_app.conn.close()
