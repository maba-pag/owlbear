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

from owlbear_knowledge.fetcher import HttpxContentFetcher
from owlbear_knowledge_mcp import server

FIXTURE_URL = "https://fixture.example/article"
_EMBEDDING_DIMENSION = 32


async def _public_fixture_resolver(_hostname: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


class _ResponseTransport:
    def __init__(self, responses: Iterable[tuple[str, str]]) -> None:
        self.responses = list(responses)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert str(request.url) == FIXTURE_URL
        content, media_type = self.responses.pop(0)
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


def _assembled_context(
    tmp_path: Path,
    responses: Iterable[tuple[str, str]],
) -> tuple[SimpleNamespace, server.AppContext, _DeterministicVectorStore]:
    (tmp_path / ".owlbear").mkdir()
    database_path = tmp_path / ".owlbear/knowledge/local.db"
    database_path.parent.mkdir()
    connection = sqlite3.connect(database_path)
    vector_store = _DeterministicVectorStore()
    http_fetcher = HttpxContentFetcher(
        transport=httpx.MockTransport(_ResponseTransport(responses)),
        resolver=_public_fixture_resolver,
    )
    app_context = server.build_app_context(
        workspace_root=tmp_path,
        conn=connection,
        factories=server.KnowledgeRuntimeFactories(
            http_response_fetcher_factory=lambda: http_fetcher,
            embedding_provider_factory=_DeterministicEmbeddingProvider,
            vector_store_factory=lambda _location: vector_store,
        ),
    )
    tool_context = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=app_context))
    return tool_context, app_context, vector_store


async def _register_fixture_source(tool_context: SimpleNamespace) -> str:
    registered = await server.register_knowledge_source(
        tool_context,
        name="Static fixture article",
        kind="url_list",
        fetch_method="http",
        config={"kind": "url_list", "urls": [FIXTURE_URL]},
    )
    return registered["id"]


@pytest.mark.asyncio
async def test_assembled_refresh_persists_and_searches_static_html(tmp_path: Path) -> None:
    html_body = (
        "<html><body><nav>Fixture navigation</nav>"
        "<article><h1>Static refresh aurora</h1>"
        "<p>Unique assembled article phrase.</p></article>"
        "<script>Fixture script payload</script></body></html>"
    )
    tool_context, app_context, vector_store = _assembled_context(
        tmp_path,
        [(html_body, "text/html; charset=utf-8")],
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
        assert vector_store.events[0][0] == "store"
        assert vector_store.events[-1][0] == "search"
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
        document_row = app_context.conn.execute("SELECT document_id FROM content_documents").fetchone()
        assert document_row is not None
        first_document_id = str(document_row["document_id"])
        first_document = app_context.content_store.get_document(first_document_id)
        first_chunk_id = app_context.content_store.list_chunks(first_document_id)[0].id

        unchanged = await server.refresh_knowledge_source(tool_context, source_id)
        unchanged_stats = app_context.content_store.stats()
        replaced = await server.refresh_knowledge_source(tool_context, source_id)
        search_results = await server.knowledge_search(tool_context, "fresh static phrase")

        assert first["documents_created"] == 1
        assert first["chunks_created"] == 1
        assert unchanged["documents_unchanged"] == 1
        assert unchanged["documents_created"] == 0
        assert unchanged["documents_replaced"] == 0
        assert unchanged["chunks_created"] == 0
        assert unchanged["chunks_replaced"] == 0
        assert unchanged_stats.documents == first_stats.documents == 1
        assert unchanged_stats.chunks == first_stats.chunks == 1
        assert replaced["documents_replaced"] == 1
        assert replaced["chunks_created"] == 1
        assert replaced["chunks_replaced"] == 1
        assert first_document is not None
        assert app_context.content_store.get_document(first_document_id) is not None
        assert "Fresh static phrase" in search_results[0]["snippet"]
        assert all("Stable static phrase" not in item["snippet"] for item in search_results)
        delete_index = vector_store.events.index(("delete", first_chunk_id))
        replacement_store_index = next(
            index for index, event in enumerate(vector_store.events) if index > delete_index and event[0] == "store"
        )
        search_index = next(
            index
            for index, event in enumerate(vector_store.events)
            if index > replacement_store_index and event[0] == "search"
        )
        assert delete_index < replacement_store_index < search_index
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
