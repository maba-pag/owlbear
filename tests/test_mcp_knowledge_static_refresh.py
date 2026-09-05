"""Assembled Knowledge MCP regressions for durable static URL refresh."""

from __future__ import annotations

import hashlib
import math
import socket
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.fetcher import HttpxContentFetcher
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge_mcp import server

FIXTURE_URL = "https://fixture.example/article"
SECOND_FIXTURE_URL = "https://fixture.example/secondary"
_EMBEDDING_DIMENSION = 32


async def _public_fixture_resolver(_hostname: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


class _ResponseTransport:
    def __init__(
        self,
        responses: Iterable[tuple[str, str] | Exception],
    ) -> None:
        self.responses = list(responses)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("https://fixture.example/")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        content, media_type = response
        return httpx.Response(
            200,
            headers={"content-type": media_type},
            text=content,
            request=request,
        )


class _DeterministicEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    @staticmethod
    def _embed_text(text: str) -> list[float]:
        vector = [0.0] * _EMBEDDING_DIMENSION
        for token in text.lower().split():
            bucket = int.from_bytes(hashlib.sha256(token.encode()).digest()[:2], "big") % _EMBEDDING_DIMENSION
            vector[bucket] += 1.0
        return vector


class _DeterministicVectorStore:
    def __init__(self) -> None:
        self.vectors: dict[str, tuple[list[float], str]] = {}
        self.events: list[tuple[str, str]] = []

    def store_embedding(
        self,
        entity_or_doc_id: str,
        embedding: object,
        _embedding_type: str,
        *,
        scope: str,
    ) -> None:
        if not isinstance(embedding, list):
            message = "deterministic vectors require dense lists"
            raise TypeError(message)
        self.events.append(("store", entity_or_doc_id))
        self.vectors[entity_or_doc_id] = (list(embedding), scope)

    def delete_embedding(self, entity_or_doc_id: str) -> bool:
        self.events.append(("delete", entity_or_doc_id))
        return self.vectors.pop(entity_or_doc_id, None) is not None

    def search_similar(
        self,
        query_embedding: object,
        *,
        top_k: int,
        embedding_type: str,
        scopes: list[str] | None,
    ) -> list[tuple[str, float]]:
        _ = embedding_type
        if not isinstance(query_embedding, list):
            message = "deterministic queries require dense lists"
            raise TypeError(message)
        self.events.append(("search", ""))
        ranked = [
            (chunk_id, self._cosine_similarity(query_embedding, vector))
            for chunk_id, (vector, scope) in self.vectors.items()
            if scopes is None or scope in scopes
        ]
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot_product / (left_norm * right_norm)


class _ToggleEmbeddingProvider(_DeterministicEmbeddingProvider):
    def __init__(self) -> None:
        self.failure_message: str | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.failure_message is not None:
            raise RuntimeError(self.failure_message)
        return super().embed(texts)


class _VectorWriteError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("vector writer secret")


class _VectorQueryError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("vector query secret")


class _PersistenceError(sqlite3.OperationalError):
    def __init__(self) -> None:
        super().__init__("database path secret")


class _FailingVectorStore(_DeterministicVectorStore):
    def __init__(self, *, fail_on_store: bool = False, fail_on_search: bool = False) -> None:
        super().__init__()
        self.fail_on_store = fail_on_store
        self.fail_on_search = fail_on_search

    def store_embedding(
        self,
        entity_or_doc_id: str,
        embedding: object,
        embedding_type: str,
        *,
        scope: str,
    ) -> None:
        if self.fail_on_store:
            raise _VectorWriteError
        super().store_embedding(entity_or_doc_id, embedding, embedding_type, scope=scope)

    def search_similar(
        self,
        query_embedding: object,
        *,
        top_k: int,
        embedding_type: str,
        scopes: list[str] | None,
    ) -> list[tuple[str, float]]:
        if self.fail_on_search:
            raise _VectorQueryError
        return super().search_similar(
            query_embedding,
            top_k=top_k,
            embedding_type=embedding_type,
            scopes=scopes,
        )


class _FailingPersistenceConnection(sqlite3.Connection):
    fail_content_reads = False

    def execute(self, sql: str, parameters: object = ()) -> sqlite3.Cursor:
        if self.fail_content_reads and "FROM content_documents" in sql:
            raise _PersistenceError
        return super().execute(sql, parameters)


def _assembled_context(  # noqa: PLR0913
    tmp_path: Path,
    responses: Iterable[tuple[str, str] | Exception],
    *,
    embedding_provider: object | None = None,
    vector_store: object | None = None,
    connection_factory: type[sqlite3.Connection] = sqlite3.Connection,
    resolver_calls: list[tuple[str, int]] | None = None,
) -> tuple[SimpleNamespace, server.AppContext, object]:
    (tmp_path / ".owlbear").mkdir()
    database_path = tmp_path / ".owlbear/knowledge/local.db"
    database_path.parent.mkdir()
    connection = sqlite3.connect(database_path, factory=connection_factory)
    resolved_vector_store = vector_store if vector_store is not None else _DeterministicVectorStore()
    resolved_embedding_provider = (
        embedding_provider if embedding_provider is not None else _DeterministicEmbeddingProvider()
    )

    async def resolver(hostname: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        if resolver_calls is not None:
            resolver_calls.append((hostname, port))
        return await _public_fixture_resolver(hostname, port)

    http_fetcher = HttpxContentFetcher(
        transport=httpx.MockTransport(_ResponseTransport(responses)),
        resolver=resolver,
    )
    app_context = server.build_app_context(
        workspace_root=tmp_path,
        conn=connection,
        factories=server.KnowledgeRuntimeFactories(
            http_response_fetcher_factory=lambda: http_fetcher,
            embedding_provider_factory=lambda: resolved_embedding_provider,
            vector_store_factory=lambda _location: resolved_vector_store,
        ),
    )
    tool_context = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=app_context))
    return tool_context, app_context, resolved_vector_store


async def _register_fixture_source(tool_context: SimpleNamespace, urls: Iterable[str] | None = None) -> str:
    source_urls = list(urls) if urls is not None else [FIXTURE_URL]
    registered = await server.register_knowledge_source(
        tool_context,
        name="Static fixture article",
        kind="url_list",
        fetch_method="http",
        config={"kind": "url_list", "urls": source_urls},
    )
    return registered["id"]


def _sqlite_counts(connection: sqlite3.Connection) -> tuple[int, int, int]:
    source_count = int(connection.execute("SELECT COUNT(*) FROM source_registry").fetchone()[0])
    document_count = int(connection.execute("SELECT COUNT(*) FROM content_documents").fetchone()[0])
    chunk_count = int(connection.execute("SELECT COUNT(*) FROM content_chunks").fetchone()[0])
    return source_count, document_count, chunk_count


def _assert_refresh_failure(
    response: dict[str, object], *, stage: str, code: str, retryable: bool, message: str
) -> None:
    assert response["sources_refreshed"] == 0
    assert response["documents_created"] == 0
    assert response["documents_replaced"] == 0
    assert response["documents_unchanged"] == 0
    assert response["chunks_created"] == 0
    assert response["chunks_replaced"] == 0
    errors = response["errors"]
    assert isinstance(errors, list)
    assert len(errors) == 1
    failure = errors[0]
    assert failure["stage"] == stage
    assert failure["code"] == code
    assert failure["retryable"] is retryable
    assert failure["message"] == message
    assert isinstance(failure["timestamp"], str)


@pytest.mark.asyncio
async def test_assembled_refresh_persists_and_searches_static_html(tmp_path: Path) -> None:
    html_body = (
        "<html><body><nav>Fixture navigation</nav>"
        "<article><h1>Static refresh aurora</h1>"
        "<p>Unique assembled article phrase.</p></article>"
        "<script>Fixture script payload</script></body></html>"
    )
    resolver_calls: list[tuple[str, int]] = []
    tool_context, app_context, vector_store = _assembled_context(
        tmp_path,
        [(html_body, "text/html; charset=utf-8")],
        resolver_calls=resolver_calls,
    )
    try:
        source_id = await _register_fixture_source(tool_context)

        refresh = await server.refresh_knowledge_source(tool_context, source_id)
        search_results = await server.knowledge_search(tool_context, "unique assembled article phrase")

        assert refresh == {
            "source_id": source_id,
            "sources_refreshed": 1,
            "documents_created": 1,
            "documents_replaced": 0,
            "documents_unchanged": 0,
            "chunks_created": 1,
            "chunks_replaced": 0,
            "errors": [],
        }
        assert len(search_results) == 1
        assert "Unique assembled article phrase." in search_results[0]["snippet"]
        assert app_context.content_store is not None
        assert app_context.content_store.stats().documents == 1
        assert app_context.content_store.stats().chunks == 1
        assert resolver_calls == [("fixture.example", 443)]
        assert _sqlite_counts(app_context.conn) == (1, 1, 1)
        chunk_row = app_context.conn.execute("SELECT id FROM content_chunks").fetchone()
        assert chunk_row is not None
        assert isinstance(vector_store, _DeterministicVectorStore)
        assert vector_store.events == [("store", chunk_row["id"]), ("search", "")]
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_refresh_reports_unchanged_and_replaced_content(tmp_path: Path) -> None:
    tool_context, app_context, vector_store = _assembled_context(
        tmp_path,
        [
            ("Stable static phrase\n\nTail", "text/plain"),
            ("  Stable   static phrase\n\nTail  ", "text/plain"),
            ("Fresh static phrase\n\nTail", "text/plain"),
        ],
    )
    try:
        source_id = await _register_fixture_source(tool_context)

        first = await server.refresh_knowledge_source(tool_context, source_id)
        assert app_context.content_store is not None
        first_stats = app_context.content_store.stats()
        first_counts = _sqlite_counts(app_context.conn)
        document_row = app_context.conn.execute("SELECT document_id FROM content_documents").fetchone()
        assert document_row is not None
        first_document_id = str(document_row["document_id"])
        first_document = app_context.content_store.get_document(first_document_id)
        first_chunk_id = app_context.content_store.list_chunks(first_document_id)[0].id

        unchanged = await server.refresh_knowledge_source(tool_context, source_id)
        unchanged_stats = app_context.content_store.stats()
        unchanged_counts = _sqlite_counts(app_context.conn)
        replaced = await server.refresh_knowledge_source(tool_context, source_id)
        replaced_counts = _sqlite_counts(app_context.conn)
        replacement_chunk_id = app_context.content_store.list_chunks(first_document_id)[0].id
        search_results = await server.knowledge_search(tool_context, "fresh static phrase")

        assert first["documents_created"] == 1
        assert first["chunks_created"] == 1
        assert unchanged["documents_unchanged"] == 1
        assert unchanged["documents_created"] == 0
        assert unchanged["documents_replaced"] == 0
        assert unchanged["chunks_created"] == 0
        assert unchanged["chunks_replaced"] == 0
        assert unchanged["sources_refreshed"] == 1
        assert unchanged["errors"] == []
        assert unchanged_stats.documents == first_stats.documents == 1
        assert unchanged_stats.chunks == first_stats.chunks == 1
        assert first_counts == unchanged_counts == replaced_counts == (1, 1, 1)
        assert replaced["documents_replaced"] == 1
        assert replaced["chunks_created"] == 1
        assert replaced["chunks_replaced"] == 1
        assert first_document is not None
        assert replacement_chunk_id != first_chunk_id
        assert app_context.content_store.get_document(first_document_id) is not None
        assert "Fresh static phrase" in search_results[0]["snippet"]
        assert all("Stable static phrase" not in item["snippet"] for item in search_results)
        assert isinstance(vector_store, _DeterministicVectorStore)
        delete_index = vector_store.events.index(("delete", first_chunk_id))
        replacement_store_index = next(
            index for index, event in enumerate(vector_store.events) if index > delete_index and event[0] == "store"
        )
        search_index = next(
            index
            for index, event in enumerate(vector_store.events)
            if index > replacement_store_index and event[0] == "search"
        )
        assert vector_store.events[replacement_store_index] == ("store", replacement_chunk_id)
        assert delete_index < replacement_store_index < search_index
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_refresh_returns_typed_acquisition_failure(tmp_path: Path) -> None:
    tool_context, app_context, _vector_store = _assembled_context(tmp_path, [httpx.ConnectError("transport secret")])
    try:
        source_id = await _register_fixture_source(tool_context)

        response = await server.refresh_knowledge_source(tool_context, source_id)

        _assert_refresh_failure(
            response,
            stage="acquisition",
            code="transport_failure",
            retryable=True,
            message="HTTP transport failed",
        )
        assert response["errors"][0]["source_id"] == source_id
        assert "transport secret" not in str(response)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_refresh_returns_typed_extraction_failure(tmp_path: Path) -> None:
    tool_context, app_context, _vector_store = _assembled_context(
        tmp_path,
        [("<html><body><article>fixture</article></body></html>", "text/html")],
    )
    try:
        source_id = await _register_fixture_source(tool_context)

        with patch(
            "owlbear_knowledge.intake.extract_content",
            side_effect=RuntimeError("extractor secret"),
        ):
            response = await server.refresh_knowledge_source(tool_context, source_id)

        _assert_refresh_failure(
            response,
            stage="extraction",
            code="extraction_failed",
            retryable=False,
            message="Response extraction failed",
        )
        assert app_context.content_store is not None
        assert app_context.content_store.stats().documents == 0
        assert "extractor secret" not in str(response)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_refresh_returns_typed_persistence_failure(tmp_path: Path) -> None:
    tool_context, app_context, _vector_store = _assembled_context(
        tmp_path,
        [("persistence fixture", "text/plain")],
        connection_factory=_FailingPersistenceConnection,
    )
    try:
        source_id = await _register_fixture_source(tool_context)
        assert isinstance(app_context.conn, _FailingPersistenceConnection)
        app_context.conn.fail_content_reads = True

        response = await server.refresh_knowledge_source(tool_context, source_id)

        _assert_refresh_failure(
            response,
            stage="persistence",
            code="persistence_failed",
            retryable=True,
            message="Content persistence failed",
        )
        app_context.conn.fail_content_reads = False
        assert app_context.content_store is not None
        assert app_context.content_store.stats().documents == 0
        assert "database path secret" not in str(response)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_refresh_returns_typed_embedding_failure(tmp_path: Path) -> None:
    embedding_provider = _ToggleEmbeddingProvider()
    embedding_provider.failure_message = "embedding secret"
    tool_context, app_context, _vector_store = _assembled_context(
        tmp_path,
        [("embedding fixture", "text/plain")],
        embedding_provider=embedding_provider,
    )
    try:
        source_id = await _register_fixture_source(tool_context)

        response = await server.refresh_knowledge_source(tool_context, source_id)

        _assert_refresh_failure(
            response,
            stage="indexing",
            code="embedding_failed",
            retryable=True,
            message="Document embedding failed",
        )
        assert "embedding secret" not in str(response)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_refresh_returns_typed_vector_write_failure(tmp_path: Path) -> None:
    vector_store = _FailingVectorStore(fail_on_store=True)
    tool_context, app_context, _vector_store = _assembled_context(
        tmp_path,
        [("vector fixture", "text/plain")],
        vector_store=vector_store,
    )
    try:
        source_id = await _register_fixture_source(tool_context)

        response = await server.refresh_knowledge_source(tool_context, source_id)

        _assert_refresh_failure(
            response,
            stage="indexing",
            code="vector_write_failed",
            retryable=True,
            message="Vector write failed",
        )
        assert "vector writer secret" not in str(response)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_refresh_preserves_partial_url_list_success(tmp_path: Path) -> None:
    tool_context, app_context, _vector_store = _assembled_context(
        tmp_path,
        [
            ("Successful partial fixture", "text/plain"),
            httpx.ConnectError("partial transport secret"),
        ],
    )
    try:
        source_id = await _register_fixture_source(tool_context, urls=(FIXTURE_URL, SECOND_FIXTURE_URL))

        response = await server.refresh_knowledge_source(tool_context, source_id)

        assert response["source_id"] == source_id
        assert response["sources_refreshed"] == 1
        assert response["documents_created"] == 1
        assert response["documents_replaced"] == 0
        assert response["documents_unchanged"] == 0
        assert response["chunks_created"] == 1
        assert response["chunks_replaced"] == 0
        assert len(response["errors"]) == 1
        assert response["errors"][0]["source_id"] == source_id
        assert response["errors"][0]["stage"] == "acquisition"
        assert response["errors"][0]["code"] == "transport_failure"
        assert response["errors"][0]["retryable"] is True
        assert response["errors"][0]["message"] == "HTTP transport failed"
        assert "partial transport secret" not in str(response)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_search_returns_typed_query_embedding_failure(tmp_path: Path) -> None:
    embedding_provider = _ToggleEmbeddingProvider()
    tool_context, app_context, _vector_store = _assembled_context(
        tmp_path,
        [("query failure fixture", "text/plain")],
        embedding_provider=embedding_provider,
    )
    try:
        source_id = await _register_fixture_source(tool_context)
        refresh = await server.refresh_knowledge_source(tool_context, source_id)
        assert refresh["errors"] == []
        embedding_provider.failure_message = "query embedding secret"

        response = await server.knowledge_search(tool_context, "query failure fixture")

        assert response == {
            "stage": "query",
            "code": "query_embedding_failed",
            "retryable": True,
            "message": "Query embedding failed",
        }
        assert "query embedding secret" not in str(response)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
async def test_assembled_search_returns_typed_vector_query_failure(tmp_path: Path) -> None:
    vector_store = _FailingVectorStore()
    tool_context, app_context, _vector_store = _assembled_context(
        tmp_path,
        [("vector query fixture", "text/plain")],
        vector_store=vector_store,
    )
    try:
        source_id = await _register_fixture_source(tool_context)
        refresh = await server.refresh_knowledge_source(tool_context, source_id)
        assert refresh["errors"] == []
        vector_store.fail_on_search = True

        response = await server.knowledge_search(tool_context, "vector query fixture")

        assert response == {
            "stage": "query",
            "code": "vector_query_failed",
            "retryable": True,
            "message": "Vector search failed",
        }
        assert "vector query secret" not in str(response)
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_type", "body", "phrase"),
    [
        ("text/plain", "  Plain unique phrase  \n\nBody  ", "Plain unique phrase"),
        ("text/markdown", "# Markdown unique phrase\n\nBody", "Markdown unique phrase"),
        ("text/x-markdown", "## X-markdown unique phrase\n\nBody", "X-markdown unique phrase"),
    ],
)
async def test_assembled_refresh_persists_text_media_without_html_extraction(
    tmp_path: Path,
    media_type: str,
    body: str,
    phrase: str,
) -> None:
    tool_context, app_context, _vector_store = _assembled_context(tmp_path, [(body, media_type)])
    try:
        source_id = await _register_fixture_source(tool_context)

        with patch(
            "owlbear_knowledge.intake.extract_content",
            side_effect=AssertionError("text media must not invoke HTML extraction"),
        ):
            refresh = await server.refresh_knowledge_source(tool_context, source_id)
        search_results = await server.knowledge_search(tool_context, phrase)

        assert refresh["documents_created"] == 1
        assert len(search_results) == 1
        assert phrase in search_results[0]["snippet"]
        assert app_context.content_store is not None
        assert app_context.content_store.stats().documents == 1
    finally:
        app_context.conn.close()


@pytest.mark.asyncio
@pytest.mark.model
@pytest.mark.timeout(600)
async def test_assembled_refresh_runs_real_bge_m3_with_filesystem_qdrant(tmp_path: Path) -> None:
    embedding_provider = BgeM3EmbeddingProvider(idle_timeout=0)
    vector_store = QdrantVectorStore(location=str(tmp_path / "qdrant"))
    tool_context, app_context, _vector_store = _assembled_context(
        tmp_path,
        [("Real BGE-M3 static phrase\n\nPersistent filesystem vector.", "text/plain")],
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )
    try:
        source_id = await _register_fixture_source(tool_context)

        refresh = await server.refresh_knowledge_source(tool_context, source_id)
        assert refresh["documents_created"] == 1
        assert refresh["chunks_created"] == 1
        assert refresh["errors"] == []

        chunk_row = app_context.conn.execute("SELECT id FROM content_chunks").fetchone()
        assert chunk_row is not None
        chunk_id = str(chunk_row["id"])
        persisted_embedding = vector_store.get_embedding(chunk_id)
        assert persisted_embedding

        search_results = await server.knowledge_search(tool_context, "real BGE-M3 static phrase")
        assert isinstance(search_results, list)
        assert len(search_results) == 1
        assert "Real BGE-M3 static phrase" in search_results[0]["snippet"]
    finally:
        embedding_provider.unload()
        app_context.conn.close()
