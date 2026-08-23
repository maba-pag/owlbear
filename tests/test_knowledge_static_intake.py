"""Durable regressions for response-aware static URL ingestion."""

from __future__ import annotations

import socket
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from owlbear_knowledge._ssrf import SSRFProtectionError
from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.fetcher import (
    ContentFetcher,
    HttpResponse,
    HttpResponseFetcher,
    HttpxContentFetcher,
)
from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.intake import IntakeResult, read_url
from owlbear_knowledge.protocols.graph import EvidenceInvalidationResult
from owlbear_knowledge.protocols.ingest import RefreshRequest
from owlbear_knowledge.protocols.sources import (
    ConfiguredSourceRecord,
    FetchTransport,
    SourceHealth,
    SourceHealthReport,
    SourceKind,
    SourceState,
    SourceUpdate,
    UrlListConfig,
)
from owlbear_knowledge.source_fetcher import CompositeSourceFetcher
from owlbear_knowledge.stores.content import ContentStore

FIXTURE_URL = "https://fixture.example/article"


async def _public_fixture_resolver(_hostname: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


async def _empty_resolver(_hostname: str, _port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return []


class _StaticResponseFetcher:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response

    async def fetch_response(self, _url: str) -> HttpResponse:
        return self.response


def _url_source(url: str = FIXTURE_URL) -> ConfiguredSourceRecord:
    now = datetime.now(tz=UTC)
    return ConfiguredSourceRecord(
        id="source-1",
        name="Static fixture",
        state=SourceState.ACTIVE,
        kind=SourceKind.URL_LIST,
        fetch_method=FetchTransport.HTTP,
        config=UrlListConfig(urls=(url,)),
        health=SourceHealth.UNKNOWN,
        refreshable=True,
        enrich=False,
        created_at=now,
        updated_at=now,
    )


def _unused_content_fetcher_factory(_method: FetchTransport) -> ContentFetcher:
    raise AssertionError


@pytest.mark.asyncio
async def test_httpx_fetch_response_preserves_metadata_and_validates_before_transport() -> None:
    body = "<html><body><article>Fixture article</article></body></html>"
    events: list[str] = []

    async def resolver(hostname: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        events.append(f"resolver:{hostname}:{port}")
        return await _public_fixture_resolver(hostname, port)

    def transport(request: httpx.Request) -> httpx.Response:
        events.append(f"transport:{request.url}")
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=body,
            request=request,
        )

    fetcher = HttpxContentFetcher(transport=httpx.MockTransport(transport), resolver=resolver)

    response = await fetcher.fetch_response(FIXTURE_URL)

    assert isinstance(fetcher, ContentFetcher)
    assert isinstance(fetcher, HttpResponseFetcher)
    assert response == HttpResponse(content=body, media_type="text/html")
    assert events == [
        "resolver:fixture.example:443",
        f"transport:{FIXTURE_URL}",
    ]

    events.clear()
    assert await fetcher.fetch(FIXTURE_URL) == body
    assert events == [
        "resolver:fixture.example:443",
        f"transport:{FIXTURE_URL}",
    ]


@pytest.mark.asyncio
async def test_httpx_fetch_response_rejects_empty_resolution_before_transport() -> None:
    transport_calls = 0

    def transport(_request: httpx.Request) -> httpx.Response:
        nonlocal transport_calls
        transport_calls += 1
        return httpx.Response(200, text="unexpected")

    fetcher = HttpxContentFetcher(transport=httpx.MockTransport(transport), resolver=_empty_resolver)

    with pytest.raises(SSRFProtectionError, match="did not resolve to an IP address"):
        await fetcher.fetch_response(FIXTURE_URL)

    assert transport_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_type", "expected_media_type"),
    [
        ("text/html; charset=utf-8", "text/html"),
        ("application/xhtml+xml", "application/xhtml+xml"),
        ("text/plain; charset=utf-8", "text/plain"),
        ("text/markdown", "text/markdown"),
        ("text/x-markdown", "text/x-markdown"),
    ],
)
async def test_read_url_classifies_and_normalizes_supported_media(
    media_type: str,
    expected_media_type: str,
) -> None:
    if expected_media_type in {"text/html", "application/xhtml+xml"}:
        content = "<html><body><article><h1>Fixture title</h1><p>Body text</p></article></body></html>"
    else:
        content = "  Fixture   title\n\n\nBody  text  "
    response_fetcher = _StaticResponseFetcher(HttpResponse(content=content, media_type=media_type))

    if expected_media_type in {"text/html", "application/xhtml+xml"}:
        result = await read_url(FIXTURE_URL, fetcher=response_fetcher)
    else:
        with patch(
            "owlbear_knowledge.intake.extract_content",
            side_effect=AssertionError("text media must not invoke HTML extraction"),
        ):
            result = await read_url(FIXTURE_URL, fetcher=response_fetcher)

    assert isinstance(result, IntakeResult)
    assert result.media_type == expected_media_type
    expected_content = (
        "Fixture title\nBody text"
        if expected_media_type in {"text/html", "application/xhtml+xml"}
        else "Fixture title\n\nBody text"
    )
    assert result.content == expected_content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        HttpResponse(content="anything", media_type="application/json"),
        HttpResponse(content="   \n\n", media_type="text/plain"),
    ],
)
async def test_url_list_does_not_create_documents_for_unsupported_or_empty_content(
    tmp_path: Path,
    response: HttpResponse,
) -> None:
    response_fetcher = _StaticResponseFetcher(response)
    composite = CompositeSourceFetcher(
        workspace_root=tmp_path,
        content_fetcher_factory=_unused_content_fetcher_factory,
        http_response_fetcher_factory=lambda: response_fetcher,
    )

    result = await composite.fetch_source(_url_source())

    assert result.documents == ()
    assert len(result.errors) == 1


class _DeterministicEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(index)] for index, _text in enumerate(texts)]


class _DeterministicVectorStore:
    def __init__(self) -> None:
        self.vectors: dict[str, object] = {}

    def store_embedding(self, chunk_id: str, vector: object, _embedding_type: str, *, scope: str) -> None:
        self.vectors[chunk_id] = (vector, scope)

    def delete_embedding(self, chunk_id: str) -> None:
        self.vectors.pop(chunk_id, None)

    def search_similar(
        self,
        _query_embedding: object,
        *,
        top_k: int,
        _embedding_type: str,
        scopes: list[str] | None,
    ) -> list[tuple[str, float]]:
        del scopes
        return [(chunk_id, 1.0) for chunk_id in list(self.vectors)[:top_k]]


class _SourceRegistry:
    def __init__(self, source: ConfiguredSourceRecord) -> None:
        self.source = source

    def get_source(self, source_id: str) -> ConfiguredSourceRecord | None:
        return self.source if source_id == self.source.id else None

    def list_sources(
        self,
        *,
        scope: str | None = None,
        state: SourceState | None = None,
    ) -> tuple[ConfiguredSourceRecord, ...]:
        del scope
        return (self.source,) if state in (None, SourceState.ACTIVE) else ()

    def update_source(self, _source_id: str, _update: SourceUpdate) -> ConfiguredSourceRecord:
        return self.source

    def record_health(self, _source_id: str, _report: SourceHealthReport) -> ConfiguredSourceRecord:
        return self.source


class _NoopEnrichment:
    def discard_chunks(self, _chunk_ids: tuple[str, ...]) -> None:
        pass


class _NoopGraph:
    def invalidate_evidence_by_chunks(self, _chunk_ids: tuple[str, ...]) -> EvidenceInvalidationResult:
        return EvidenceInvalidationResult()


class _ResponseSequence:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = responses

    async def fetch_response(self, _url: str) -> HttpResponse:
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_refresh_preserves_identity_for_normalized_unchanged_and_changed_content(tmp_path: Path) -> None:
    source = _url_source()
    source_store = _SourceRegistry(source)
    response_sequence = _ResponseSequence(
        [
            HttpResponse(content="Stable  phrase\n\n\nTail", media_type="text/plain"),
            HttpResponse(content="Stable phrase\n\nTail", media_type="text/plain"),
            HttpResponse(content="Fresh phrase\n\nTail", media_type="text/plain"),
        ]
    )
    composite = CompositeSourceFetcher(
        workspace_root=tmp_path,
        content_fetcher_factory=_unused_content_fetcher_factory,
        http_response_fetcher_factory=lambda: response_sequence,
    )
    connection = sqlite3.connect(":memory:")
    content_store = ContentStore(
        db=connection,
        vector_store=_DeterministicVectorStore(),
        embedding_provider=_DeterministicEmbeddingProvider(),
        chunker=TextChunker(target_tokens=512, overlap_tokens=0),
    )
    content_store.ensure_tables()
    coordinator = IngestCoordinator(
        sources=source_store,
        content=content_store,
        enrichment=_NoopEnrichment(),
        graph=_NoopGraph(),
        fetcher=composite,
    )

    first = await coordinator.refresh(RefreshRequest())
    first_ingest = first.ingest_results[0]
    first_document = first_ingest.content_results[0]
    first_chunk_ids = set(first_document.chunk_ids)
    first_stats = content_store.stats()

    unchanged = await coordinator.refresh(RefreshRequest())
    unchanged_ingest = unchanged.ingest_results[0]
    unchanged_document = unchanged_ingest.content_results[0]

    replaced = await coordinator.refresh(RefreshRequest())
    replaced_ingest = replaced.ingest_results[0]
    replaced_document = replaced_ingest.content_results[0]
    current_chunk_ids = {chunk.id for chunk in content_store.list_chunks(replaced_document.document_id)}

    assert first_ingest.documents_created == 1
    assert unchanged_ingest.documents_unchanged == 1
    assert replaced_ingest.documents_replaced == 1
    assert unchanged_document.document_id == first_document.document_id == replaced_document.document_id
    assert unchanged_document.chunk_ids == first_document.chunk_ids
    assert content_store.stats().documents == first_stats.documents == 1
    assert content_store.stats().chunks == first_stats.chunks == 1
    assert first_chunk_ids.isdisjoint(current_chunk_ids)
    assert replaced_document.replaced_chunk_ids == tuple(first_chunk_ids)
