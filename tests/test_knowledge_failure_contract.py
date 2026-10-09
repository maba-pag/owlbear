"""Durable regressions for typed Knowledge workflow failures."""

from __future__ import annotations

import socket
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from owlbear_knowledge._ssrf import SSRFProtectionError, check_url_allowed
from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.fetcher import (
    MAX_RESPONSE_BYTES,
    REQUEST_TIMEOUT_SECONDS,
    HttpResponse,
    HttpxContentFetcher,
)
from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.protocols.common import BoundaryModel
from owlbear_knowledge.protocols.content import ContentIngestRequest, ContentSearchQuery
from owlbear_knowledge.protocols.failures import (
    KnowledgeFailure,
    KnowledgeFailureCode,
    KnowledgeFailureStage,
    KnowledgeOperationError,
)
from owlbear_knowledge.protocols.fetcher import FetchedDocument, FetchError, FetchResult
from owlbear_knowledge.protocols.ingest import (
    IngestAcquisitionFailure,
    IngestDocument,
    IngestRequest,
    IngestResult,
    RefreshRequest,
)
from owlbear_knowledge.protocols.query import QueryRequest
from owlbear_knowledge.protocols.sources import (
    AuthenticatedWebConfig,
    ConfiguredSourceRecord,
    FetchTransport,
    FileGlobConfig,
    InlineConfig,
    SourceConfig,
    SourceHealth,
    SourceKind,
    SourceRegistration,
    SourceState,
    UrlListConfig,
)
from owlbear_knowledge.query_facade import QueryFacade
from owlbear_knowledge.source_fetcher import CompositeSourceFetcher
from owlbear_knowledge.stores.content import ContentStore

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _failure(
    stage: KnowledgeFailureStage,
    code: KnowledgeFailureCode,
    *,
    retryable: bool,
    message: str = "safe failure message",
) -> KnowledgeFailure:
    return KnowledgeFailure(stage=stage, code=code, retryable=retryable, message=message)


def _source(url: str = "https://fixture.example/article") -> ConfiguredSourceRecord:
    return ConfiguredSourceRecord(
        id="source-1",
        name="Fixture source",
        state=SourceState.ACTIVE,
        kind=SourceKind.URL_LIST,
        fetch_method=FetchTransport.HTTP,
        config=UrlListConfig(urls=(url,)),
        health=SourceHealth.UNKNOWN,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _sources(source: ConfiguredSourceRecord) -> MagicMock:
    sources = MagicMock(name="sources")
    sources.get_source.return_value = source
    sources.list_sources.return_value = (source,)
    sources.record_health.return_value = source
    sources.update_source.return_value = source
    return sources


def _coordinator(
    source: ConfiguredSourceRecord,
    *,
    content: object | None = None,
    fetcher: object | None = None,
) -> tuple[IngestCoordinator, MagicMock]:
    sources = _sources(source)
    enrichment = MagicMock(name="enrichment")
    enrichment.enqueue_chunks.return_value = 0
    coordinator = IngestCoordinator(
        sources=sources,
        content=content or MagicMock(name="content"),
        enrichment=enrichment,
        graph=MagicMock(name="graph"),
        fetcher=fetcher,
    )
    return coordinator, sources


class _StaticResponseFetcher:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response

    async def fetch_response(self, _url: str) -> HttpResponse:
        return self.response


class _EmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(index)] for index, _text in enumerate(texts)]


class _VectorStore:
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
        embedding_type: str,
        scopes: list[str] | None,
    ) -> list[tuple[str, float]]:
        del embedding_type, scopes
        return [(chunk_id, 1.0) for chunk_id in list(self.vectors)[:top_k]]


def _content_store(
    *,
    db: object | None = None,
    embedding_provider: object | None = None,
    vector_store: object | None = None,
) -> ContentStore:
    connection = db or sqlite3.connect(":memory:")
    store = ContentStore(
        db=connection,  # type: ignore[arg-type]
        vector_store=vector_store or _VectorStore(),
        embedding_provider=embedding_provider or _EmbeddingProvider(),
        chunker=TextChunker(target_tokens=512, overlap_tokens=0),
    )
    if db is None:
        store.ensure_tables()
    return store


def _content_request() -> ContentIngestRequest:
    return ContentIngestRequest(source_id="source-1", title="Fixture", text="content")


def _unused_content_fetcher_factory(_method: FetchTransport) -> object:
    raise AssertionError


async def _public_resolver(_hostname: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


async def _blocked_resolver(_hostname: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]


async def _empty_resolver(_hostname: str, _port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return []


async def _failing_resolver(_hostname: str, _port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    message = "resolver token and internal path"
    raise OSError(message)


def test_failure_code_literal_is_complete_and_protocol_is_public() -> None:
    assert get_args(KnowledgeFailureCode) == (
        "agent_capture_required",
        "browser_capture_failed",
        "url_rejected",
        "dns_failure",
        "transport_failure",
        "http_status",
        "timeout",
        "response_too_large",
        "unsupported_media_type",
        "content_boundary_missing",
        "extraction_failed",
        "processing_failed",
        "persistence_failed",
        "embedding_failed",
        "embedding_dependency_missing",
        "embedding_model_unavailable",
        "embedding_tls_configuration",
        "embedding_tls_failed",
        "embedding_download_failed",
        "vector_write_failed",
        "query_embedding_failed",
        "vector_query_failed",
    )
    assert issubclass(KnowledgeFailure, BoundaryModel)
    assert KnowledgeFailureStage.QUERY.value == "query"


@pytest.mark.parametrize(
    ("kind", "fetch_method", "config"),
    [
        (SourceKind.URL_LIST, FetchTransport.HTTP, UrlListConfig(urls=("https://fixture.example",))),
        (SourceKind.URL_LIST, FetchTransport.BROWSER, UrlListConfig(urls=("https://fixture.example",))),
        (SourceKind.FILE_GLOB, FetchTransport.FILESYSTEM, FileGlobConfig(patterns=("*.md",))),
        (SourceKind.INLINE, FetchTransport.NONE, InlineConfig()),
        (
            SourceKind.AUTHENTICATED_WEB,
            FetchTransport.BROWSER,
            AuthenticatedWebConfig(base_url="https://fixture.example", auth_profile="fixture"),
        ),
    ],
)
def test_source_registration_accepts_supported_kind_transport_pairs(
    kind: SourceKind,
    fetch_method: FetchTransport,
    config: SourceConfig,
) -> None:
    registration = SourceRegistration(
        name="Fixture source",
        kind=kind,
        fetch_method=fetch_method,
        config=config,
    )

    assert registration.kind is kind
    assert registration.fetch_method is fetch_method


@pytest.mark.parametrize(
    ("kind", "fetch_method", "config", "accepted"),
    [
        (
            SourceKind.URL_LIST,
            FetchTransport.FILESYSTEM,
            UrlListConfig(urls=("https://user:secret@fixture.example",)),
            "http, browser",
        ),
        (SourceKind.FILE_GLOB, FetchTransport.HTTP, FileGlobConfig(patterns=("*.md",)), "filesystem"),
        (SourceKind.INLINE, FetchTransport.BROWSER, InlineConfig(), "none"),
    ],
)
def test_source_registration_rejects_unsupported_transport_without_echoing_config(
    kind: SourceKind,
    fetch_method: FetchTransport,
    config: SourceConfig,
    accepted: str,
) -> None:
    with pytest.raises(ValueError, match=f"{kind.value} sources accept fetch transports: {accepted}") as caught:
        SourceRegistration(
            name="Fixture source",
            kind=kind,
            fetch_method=fetch_method,
            config=config,
        )

    message = str(caught.value)
    assert f"{kind.value} sources accept fetch transports: {accepted}" in message
    assert "secret" not in message


def test_ingest_request_requires_a_document_or_acquisition_failure() -> None:
    with pytest.raises(ValueError, match="At least one document or acquisition failure"):
        IngestRequest(source_id="source-1")

    failure = _failure(KnowledgeFailureStage.ACQUISITION, "timeout", retryable=True)
    request = IngestRequest(
        source_id="source-1",
        acquisition_failures=(IngestAcquisitionFailure(uri="https://fixture.example/a", failure=failure),),
    )

    assert request.documents == ()
    assert request.acquisition_failures[0].failure == failure


@pytest.mark.asyncio
async def test_browser_url_list_refresh_requires_capture_without_side_effects() -> None:
    source = _source().model_copy(update={"fetch_method": FetchTransport.BROWSER})
    fetcher = MagicMock(name="fetcher")
    fetcher.fetch_source = AsyncMock()
    content = MagicMock(name="content")
    content.ingest = AsyncMock()
    coordinator, sources = _coordinator(source, content=content, fetcher=fetcher)

    result = await coordinator.refresh(RefreshRequest())

    assert result.sources_refreshed == 0
    assert len(result.errors) == 1
    assert result.errors[0].failure == KnowledgeFailure(
        stage=KnowledgeFailureStage.ACQUISITION,
        code="agent_capture_required",
        retryable=False,
        message="Browser capture is required for this source",
    )
    fetcher.fetch_source.assert_not_awaited()
    content.ingest.assert_not_awaited()
    sources.record_health.assert_not_called()
    sources.update_source.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_records_failed_health_for_all_acquisition_failures() -> None:
    url_a = "https://user:secret@fixture.example/a"
    url_b = "https://user:secret@fixture.example/b"
    source = _source(url_a)
    failures = (
        _failure(KnowledgeFailureStage.ACQUISITION, "timeout", retryable=True, message="Request timed out"),
        _failure(KnowledgeFailureStage.ACQUISITION, "http_status", retryable=False, message="Status 503"),
    )
    fetcher = MagicMock(name="fetcher")
    fetcher.fetch_source = AsyncMock(
        return_value=FetchResult(
            errors=(
                FetchError(uri=url_a, error=failures[0].message, failure=failures[0]),
                FetchError(uri=url_b, error=failures[1].message, failure=failures[1]),
            )
        )
    )
    content = MagicMock(name="content")
    content.ingest = AsyncMock()
    coordinator, sources = _coordinator(source, content=content, fetcher=fetcher)

    result = await coordinator.refresh(RefreshRequest())

    assert result.sources_refreshed == 0
    assert len(result.ingest_results) == 1
    ingest_result = result.ingest_results[0]
    assert ingest_result.documents_processed == 2
    assert ingest_result.errors == failures
    assert [error.failure for error in result.errors] == list(failures)
    assert len(result.errors) == 2
    report = sources.record_health.call_args.args[1]
    assert report.health is SourceHealth.FAILED
    assert report.message == "processed=2, succeeded=0, failed=2, failure_codes=http_status,timeout"
    assert report.checked_at == ingest_result.completed_at
    assert "secret" not in report.message
    assert all("secret" not in error.error for error in result.errors)
    content.ingest.assert_not_awaited()
    sources.update_source.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_degrades_health_when_acquisition_and_document_succeed() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        content = _content_store(db=connection)
        content.ensure_tables()
        source = _source()
        failure = _failure(KnowledgeFailureStage.ACQUISITION, "timeout", retryable=True)
        fetcher = MagicMock(name="fetcher")
        fetcher.fetch_source = AsyncMock(
            return_value=FetchResult(
                documents=(FetchedDocument(title="Fixture", text="content", uri=source.config.urls[0]),),
                errors=(FetchError(uri=source.config.urls[0], error=failure.message, failure=failure),),
            )
        )
        coordinator, sources = _coordinator(source, content=content, fetcher=fetcher)

        result = await coordinator.refresh(RefreshRequest())

        assert result.sources_refreshed == 1
        assert len(result.errors) == 1
        assert result.errors[0].failure == failure
        ingest_result = result.ingest_results[0]
        assert ingest_result.documents_created == 1
        report = sources.record_health.call_args.args[1]
        assert report.health is SourceHealth.DEGRADED
        assert report.message == "processed=2, succeeded=1, failed=1, failure_codes=timeout"
        assert report.checked_at == ingest_result.completed_at
        sources.update_source.assert_called_once()
    finally:
        connection.close()


@pytest.mark.asyncio
async def test_ingest_success_records_ok_health_without_last_error() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        content = _content_store(db=connection)
        content.ensure_tables()
        source = _source()
        coordinator, sources = _coordinator(source, content=content)

        result = await coordinator.ingest(
            IngestRequest(
                source_id=source.id,
                documents=(
                    IngestDocument(title="First", text="first content"),
                    IngestDocument(title="Second", text="second content"),
                ),
            )
        )

        assert result.documents_created == 2
        report = sources.record_health.call_args.args[1]
        assert report.health is SourceHealth.OK
        assert report.message is None
        assert report.checked_at == result.completed_at
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("error_type", "error_message"),
    [
        (RuntimeError, "runtime sentinel"),
        (ValueError, "value sentinel"),
        (LookupError, "lookup sentinel"),
        (TypeError, "type sentinel"),
        (AttributeError, "attribute sentinel"),
        (KeyError, "key sentinel"),
    ],
)
@pytest.mark.asyncio
async def test_untyped_document_failures_are_redacted_and_counted(
    error_type: type[Exception],
    error_message: str,
) -> None:
    source = _source()
    content = MagicMock(name="content")
    content.ingest = AsyncMock(side_effect=error_type(error_message))
    coordinator, sources = _coordinator(source, content=content)

    result = await coordinator.ingest(
        IngestRequest(
            source_id=source.id,
            documents=(
                IngestDocument(title="First", text="first content"),
                IngestDocument(title="Second", text="second content"),
            ),
        )
    )

    assert result.documents_processed == 2
    assert len(result.errors) == 2
    assert all(failure.code == "processing_failed" for failure in result.errors)
    assert all(failure.message == "Document processing failed" for failure in result.errors)
    assert all(error_message not in failure.message for failure in result.errors)
    report = sources.record_health.call_args.args[1]
    assert report.health is SourceHealth.FAILED
    assert report.message == "processed=2, succeeded=0, failed=2, failure_codes=processing_failed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "resolver", "code"),
    [
        ("ftp://fixture.example/article", _public_resolver, "url_rejected"),
        ("http://[::1", _public_resolver, "url_rejected"),
        ("https://fixture.example/article", _blocked_resolver, "url_rejected"),
        ("https://fixture.example/article", _failing_resolver, "dns_failure"),
        ("https://fixture.example/article", _empty_resolver, "dns_failure"),
    ],
)
async def test_ssrf_failures_are_typed_and_redacted(
    url: str,
    resolver: object,
    code: str,
) -> None:
    with pytest.raises(SSRFProtectionError) as caught:
        await check_url_allowed(url, resolver=resolver)  # type: ignore[arg-type]

    failure = caught.value.failure
    assert failure.stage is KnowledgeFailureStage.ACQUISITION
    assert failure.code == code
    assert "127.0.0.1" not in failure.message
    assert "internal path" not in failure.message
    assert "token" not in failure.message


@pytest.mark.asyncio
async def test_http_timeout_and_response_size_fail_closed_with_named_limits() -> None:
    assert REQUEST_TIMEOUT_SECONDS > 0
    assert MAX_RESPONSE_BYTES > 0

    def timeout_transport(request: httpx.Request) -> httpx.Response:
        message = "adapter token and body"
        raise httpx.ReadTimeout(message, request=request)

    timeout_fetcher = HttpxContentFetcher(
        transport=httpx.MockTransport(timeout_transport),
        resolver=_public_resolver,
    )
    with pytest.raises(KnowledgeOperationError) as timeout_error:
        await timeout_fetcher.fetch_response("https://fixture.example/article")
    assert timeout_error.value.failure.code == "timeout"
    assert "adapter token" not in timeout_error.value.failure.message

    def large_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"x" * (MAX_RESPONSE_BYTES + 1),
            request=request,
        )

    large_fetcher = HttpxContentFetcher(
        transport=httpx.MockTransport(large_transport),
        resolver=_public_resolver,
    )
    with pytest.raises(KnowledgeOperationError) as size_error:
        await large_fetcher.fetch_response("https://fixture.example/article")
    assert size_error.value.failure.code == "response_too_large"


@pytest.mark.asyncio
async def test_source_fetcher_keeps_partial_success_and_redacts_adapter_text(tmp_path: Path) -> None:
    url = "https://fixture.example/article?token=secret"
    response_fetcher = _StaticResponseFetcher(HttpResponse(content="unused", media_type="text/plain"))
    response_fetcher.fetch_response = AsyncMock(  # type: ignore[method-assign]
        side_effect=httpx.HTTPStatusError(
            "token=secret response body",
            request=httpx.Request("GET", url),
            response=httpx.Response(503),
        )
    )
    composite = CompositeSourceFetcher(
        workspace_root=tmp_path,
        content_fetcher_factory=_unused_content_fetcher_factory,
        http_response_fetcher_factory=lambda: response_fetcher,
    )

    result = await composite.fetch_source(_source(url))

    assert len(result.errors) == 1
    error = result.errors[0]
    assert error.failure is not None
    assert error.failure.code == "http_status"
    assert error.error == error.failure.message
    assert "secret" not in error.error
    assert "secret" not in error.uri


@pytest.mark.asyncio
async def test_extraction_failure_does_not_persist_document(tmp_path: Path) -> None:
    source = _source()
    response_fetcher = _StaticResponseFetcher(HttpResponse(content="binary", media_type="application/json"))
    composite = CompositeSourceFetcher(
        workspace_root=tmp_path,
        content_fetcher_factory=_unused_content_fetcher_factory,
        http_response_fetcher_factory=lambda: response_fetcher,
    )
    content = _content_store()
    coordinator, sources = _coordinator(source, content=content, fetcher=composite)

    result = await coordinator.refresh(RefreshRequest())

    assert result.sources_refreshed == 0
    assert result.errors[0].failure is not None
    assert result.errors[0].failure.code == "unsupported_media_type"
    assert content.stats().documents == 0
    sources.update_source.assert_not_called()


@pytest.mark.asyncio
async def test_empty_extraction_is_content_boundary_failure_without_persisting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("owlbear_knowledge.intake.extract_content", lambda *_args, **_kwargs: "")
    response_fetcher = _StaticResponseFetcher(
        HttpResponse(content="<html><body>shell</body></html>", media_type="text/html")
    )
    composite = CompositeSourceFetcher(
        workspace_root=tmp_path,
        content_fetcher_factory=_unused_content_fetcher_factory,
        http_response_fetcher_factory=lambda: response_fetcher,
    )
    content = _content_store()
    coordinator, _sources_mock = _coordinator(_source(), content=content, fetcher=composite)

    result = await coordinator.refresh(RefreshRequest())

    assert result.sources_refreshed == 0
    assert result.errors[0].failure is not None
    assert result.errors[0].failure.code == "content_boundary_missing"
    assert content.stats().documents == 0


@pytest.mark.asyncio
async def test_content_store_attributes_lower_adapter_failures() -> None:
    failing_db = MagicMock(name="db")
    failing_db.execute.side_effect = sqlite3.OperationalError("/internal/db token")
    store = _content_store(db=failing_db)
    with pytest.raises(KnowledgeOperationError) as persistence_error:
        await store.ingest(_content_request())
    assert persistence_error.value.failure.stage is KnowledgeFailureStage.PERSISTENCE
    assert persistence_error.value.failure.code == "persistence_failed"
    assert "/internal/db" not in persistence_error.value.failure.message

    class FailingEmbedding:
        def embed(self, _texts: list[str]) -> list[list[float]]:
            message = "embedding token and response body"
            raise RuntimeError(message)

    embedding_store = _content_store(embedding_provider=FailingEmbedding())
    with pytest.raises(KnowledgeOperationError) as embedding_error:
        await embedding_store.ingest(_content_request())
    assert embedding_error.value.failure.stage is KnowledgeFailureStage.INDEXING
    assert embedding_error.value.failure.code == "embedding_failed"
    assert "response body" not in embedding_error.value.failure.message

    class FailingVector(_VectorStore):
        def store_embedding(self, _chunk_id: str, _vector: object, _embedding_type: str, *, scope: str) -> None:
            del scope
            message = "vector token"
            raise RuntimeError(message)

    vector_store = _content_store(vector_store=FailingVector())
    with pytest.raises(KnowledgeOperationError) as vector_error:
        await vector_store.ingest(_content_request())
    assert vector_error.value.failure.stage is KnowledgeFailureStage.INDEXING
    assert vector_error.value.failure.code == "vector_write_failed"


@pytest.mark.asyncio
async def test_content_store_and_query_facade_preserve_query_failure_carriers() -> None:
    class FailingQueryEmbedding:
        def embed(self, _texts: list[str]) -> list[list[float]]:
            message = "query token"
            raise RuntimeError(message)

    embedding_store = _content_store(embedding_provider=FailingQueryEmbedding())
    with pytest.raises(KnowledgeOperationError) as embedding_error:
        await embedding_store.search(ContentSearchQuery(text="query"))
    assert embedding_error.value.failure.stage is KnowledgeFailureStage.QUERY
    assert embedding_error.value.failure.code == "query_embedding_failed"

    class FailingQueryVector(_VectorStore):
        def search_similar(
            self,
            _query_embedding: object,
            *,
            top_k: int,
            embedding_type: str,
            scopes: list[str] | None,
        ) -> list[tuple[str, float]]:
            del top_k, embedding_type, scopes
            message = "vector query token"
            raise RuntimeError(message)

    vector_store = _content_store(vector_store=FailingQueryVector())
    with pytest.raises(KnowledgeOperationError) as vector_error:
        await vector_store.search(ContentSearchQuery(text="query"))
    assert vector_error.value.failure.stage is KnowledgeFailureStage.QUERY
    assert vector_error.value.failure.code == "vector_query_failed"

    failure = _failure(KnowledgeFailureStage.QUERY, "vector_query_failed", retryable=True)
    content = MagicMock(name="content")
    content.search = AsyncMock(side_effect=KnowledgeOperationError(failure))
    facade = QueryFacade(content=content, graph=MagicMock(name="graph"))
    with pytest.raises(KnowledgeOperationError) as facade_error:
        await facade.search(QueryRequest(text="query", include_graph=False))
    assert facade_error.value.failure == failure


@pytest.mark.asyncio
async def test_ingest_records_operation_failures_and_refresh_suppresses_false_success() -> None:
    source = _source()
    failure = _failure(KnowledgeFailureStage.PERSISTENCE, "persistence_failed", retryable=True)
    content = MagicMock(name="content")
    content.ingest = AsyncMock(side_effect=KnowledgeOperationError(failure))
    coordinator, _sources_mock = _coordinator(source, content=content)

    ingest_result = await coordinator.ingest(
        IngestRequest(
            source_id=source.id,
            documents=(IngestDocument(title="Fixture", text="content"),),
        )
    )

    assert ingest_result.documents_processed == 1
    assert ingest_result.documents_created == 0
    assert ingest_result.errors == (failure,)

    fetcher = MagicMock(name="fetcher")
    fetcher.fetch_source = AsyncMock(
        return_value=FetchResult(
            documents=(FetchedDocument(title="Fixture", text="content", uri=source.config.urls[0]),),
        )
    )
    total_failure_coordinator, total_failure_sources = _coordinator(source, fetcher=fetcher)
    total_failure_coordinator.ingest = AsyncMock(
        return_value=IngestResult(
            source_id=source.id,
            documents_processed=1,
            errors=(failure,),
            started_at=_NOW,
            completed_at=_NOW,
        )
    )

    refresh_result = await total_failure_coordinator.refresh(RefreshRequest())

    assert refresh_result.sources_refreshed == 0
    assert refresh_result.ingest_results[0].errors == (failure,)
    assert refresh_result.errors[0].failure == failure
    total_failure_sources.update_source.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_preserves_partial_success_and_zero_document_noop() -> None:
    source = _source()
    fetch_failure = _failure(KnowledgeFailureStage.ACQUISITION, "timeout", retryable=True)
    fetcher = MagicMock(name="fetcher")
    fetcher.fetch_source = AsyncMock(
        return_value=FetchResult(
            documents=(FetchedDocument(title="Fixture", text="content", uri=source.config.urls[0]),),
            errors=(FetchError(uri=source.config.urls[0], error=fetch_failure.message, failure=fetch_failure),),
        )
    )
    coordinator, sources = _coordinator(source, fetcher=fetcher)
    coordinator.ingest = AsyncMock(
        return_value=IngestResult(
            source_id=source.id,
            documents_processed=1,
            documents_created=1,
            errors=(fetch_failure,),
            started_at=_NOW,
            completed_at=_NOW,
        )
    )

    partial = await coordinator.refresh(RefreshRequest())

    assert partial.sources_refreshed == 1
    assert partial.ingest_results[0].documents_created == 1
    assert partial.errors[0].failure == fetch_failure
    sources.update_source.assert_called_once()

    sources.reset_mock()
    fetcher.fetch_source = AsyncMock(return_value=FetchResult())
    noop = await coordinator.refresh(RefreshRequest())

    assert noop.sources_refreshed == 0
    assert noop.errors == ()
    sources.update_source.assert_not_called()
    coordinator.ingest.assert_awaited_once()
