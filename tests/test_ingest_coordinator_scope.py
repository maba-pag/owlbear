"""Tests for preserving registered source scope through coordinator ingest."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.protocols.content import ContentIngestRequest, ContentSearchQuery
from owlbear_knowledge.protocols.enrichment import EnrichmentDiscardResult, EnrichmentPurgeResult
from owlbear_knowledge.protocols.failures import KnowledgeFailure, KnowledgeFailureStage, KnowledgeOperationError
from owlbear_knowledge.protocols.graph import EvidenceInvalidationResult
from owlbear_knowledge.protocols.ingest import IngestDocument, IngestRequest, PurgeStatus
from owlbear_knowledge.protocols.sources import (
    ConfiguredSourceRecord,
    FetchTransport,
    InlineConfig,
    SourceDeletionInfo,
    SourceHealth,
    SourceHealthReport,
    SourceKind,
    SourceState,
)
from owlbear_knowledge.stores.content import ContentStore


class _EmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(index)] for index, _text in enumerate(texts)]


class _ScopeAwareVectorStore:
    def __init__(self) -> None:
        self.vectors: dict[str, tuple[object, str]] = {}

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
        del embedding_type
        return [
            (chunk_id, 1.0)
            for chunk_id, (_vector, stored_scope) in self.vectors.items()
            if scopes is None or stored_scope in scopes
        ][:top_k]


@dataclass
class _Runtime:
    coordinator: IngestCoordinator
    source: ConfiguredSourceRecord
    sources: MagicMock
    content: MagicMock
    enrichment: MagicMock
    graph: MagicMock
    content_store: ContentStore
    vectors: _ScopeAwareVectorStore
    connection: sqlite3.Connection


def _source(scope: str) -> ConfiguredSourceRecord:
    now = datetime.now(tz=UTC)
    return ConfiguredSourceRecord(
        id="source-1",
        name="Fixture source",
        scope=scope,
        state=SourceState.ACTIVE,
        kind=SourceKind.INLINE,
        fetch_method=FetchTransport.NONE,
        config=InlineConfig(),
        health=SourceHealth.UNKNOWN,
        created_at=now,
        updated_at=now,
    )


def _runtime(scope: str) -> _Runtime:
    source = _source(scope)
    connection = sqlite3.connect(":memory:")
    vectors = _ScopeAwareVectorStore()
    content_store = ContentStore(
        db=connection,
        vector_store=vectors,
        embedding_provider=_EmbeddingProvider(),
        chunker=TextChunker(target_tokens=512, overlap_tokens=0),
    )
    content_store.ensure_tables()

    sources = MagicMock(name="sources")
    sources.get_source.return_value = source
    sources.record_health.return_value = source

    content = MagicMock(name="content")
    content.ingest = AsyncMock(wraps=content_store.ingest)

    enrichment = MagicMock(name="enrichment")
    enrichment.enqueue_chunks.return_value = 0
    graph = MagicMock(name="graph")
    coordinator = IngestCoordinator(
        sources=sources,
        content=content,
        enrichment=enrichment,
        graph=graph,
    )
    return _Runtime(coordinator, source, sources, content, enrichment, graph, content_store, vectors, connection)


def _request(*documents: IngestDocument) -> IngestRequest:
    return IngestRequest(source_id="source-1", documents=documents, enrich=False)


@pytest.fixture(params=("global", "project:audit"))
def runtime(request: pytest.FixtureRequest) -> _Runtime:
    value = _runtime(request.param)
    yield value
    value.connection.close()


@pytest.mark.asyncio
async def test_registered_scope_reaches_request_persistence_vectors_and_search(runtime: _Runtime) -> None:
    result = await runtime.coordinator.ingest(
        _request(
            IngestDocument(
                title="Fixture",
                text="Scoped fixture content",
                external_id="fixture-1",
            )
        )
    )

    assert result.documents_created == 1
    assert [call.args[0].scope for call in runtime.content.ingest.await_args_list] == [runtime.source.scope]
    content_result = result.content_results[0]
    document = runtime.content_store.get_document(content_result.document_id)
    chunks = runtime.content_store.list_chunks(content_result.document_id)
    assert document is not None
    assert document.scope == runtime.source.scope
    assert {chunk.scope for chunk in chunks} == {runtime.source.scope}
    assert {scope for _vector, scope in runtime.vectors.vectors.values()} == {runtime.source.scope}

    intended = await runtime.content_store.search(ContentSearchQuery(text="fixture", scopes=(runtime.source.scope,)))
    global_only = await runtime.content_store.search(ContentSearchQuery(text="fixture", scopes=("global",)))
    assert len(intended) == 1
    assert len(global_only) == (1 if runtime.source.scope == "global" else 0)


@pytest.mark.asyncio
async def test_registered_scope_is_consistent_for_created_unchanged_and_replaced(runtime: _Runtime) -> None:
    first = await runtime.coordinator.ingest(
        _request(IngestDocument(title="Fixture", text="Stable content", external_id="fixture-1"))
    )
    unchanged = await runtime.coordinator.ingest(
        _request(IngestDocument(title="Fixture", text="Stable content", external_id="fixture-1"))
    )
    replaced = await runtime.coordinator.ingest(
        _request(IngestDocument(title="Fixture", text="Changed content", external_id="fixture-1"))
    )

    assert first.documents_created == 1
    assert unchanged.documents_unchanged == 1
    assert replaced.documents_replaced == 1
    assert len(runtime.content.ingest.await_args_list) == 3
    assert {call.args[0].scope for call in runtime.content.ingest.await_args_list} == {runtime.source.scope}
    current_document = runtime.content_store.get_document(replaced.content_results[0].document_id)
    assert current_document is not None
    assert current_document.scope == runtime.source.scope
    assert {chunk.scope for chunk in runtime.content_store.list_chunks(current_document.document_id)} == {
        runtime.source.scope
    }
    assert {scope for _vector, scope in runtime.vectors.vectors.values()} == {runtime.source.scope}
    assert all(call.args[1].health is SourceHealth.OK for call in runtime.sources.record_health.call_args_list)


@pytest.mark.parametrize("old_scope", ["global", "project:old"])
@pytest.mark.asyncio
async def test_ingest_replaces_same_identity_content_from_old_scope(old_scope: str) -> None:
    runtime = _runtime("project:new")
    try:
        stale = await runtime.content_store.ingest(
            ContentIngestRequest(
                source_id=runtime.source.id,
                title="Fixture",
                text="Scoped fixture content",
                external_id="fixture-1",
                scope=old_scope,
            )
        )

        result = await runtime.coordinator.ingest(
            _request(
                IngestDocument(
                    title="Fixture",
                    text="Scoped fixture content",
                    external_id="fixture-1",
                )
            )
        )

        assert result.documents_replaced == 1
        assert runtime.content_store.get_document(stale.document_id) is None
        assert runtime.enrichment.discard_chunks.call_args.args[0] == stale.chunk_ids
        assert runtime.graph.invalidate_evidence_by_chunks.call_args.args[0] == stale.chunk_ids
        assert await runtime.content_store.search(
            ContentSearchQuery(text="fixture", scopes=(old_scope,))
        ) == ()
        assert len(
            await runtime.content_store.search(
                ContentSearchQuery(text="fixture", scopes=(runtime.source.scope,))
            )
        ) == 1
    finally:
        runtime.connection.close()


@pytest.mark.asyncio
async def test_multi_document_ingest_preserves_scope_for_every_document(runtime: _Runtime) -> None:
    result = await runtime.coordinator.ingest(
        _request(
            IngestDocument(title="First", text="First content", external_id="fixture-1"),
            IngestDocument(title="Second", text="Second content", external_id="fixture-2"),
        )
    )

    assert result.documents_processed == 2
    assert result.documents_created == 2
    assert [call.args[0].scope for call in runtime.content.ingest.await_args_list] == [
        runtime.source.scope,
        runtime.source.scope,
    ]
    assert all(
        runtime.content_store.get_document(content_result.document_id).scope == runtime.source.scope
        for content_result in result.content_results
    )
    assert {scope for _vector, scope in runtime.vectors.vectors.values()} == {runtime.source.scope}
    assert runtime.sources.record_health.call_args.args[1].health is SourceHealth.OK


@pytest.mark.asyncio
async def test_failed_ingest_preserves_scope_and_health_error_contract(runtime: _Runtime) -> None:
    failure = KnowledgeFailure(
        stage=KnowledgeFailureStage.PERSISTENCE,
        code="persistence_failed",
        retryable=True,
        message="Content persistence failed",
    )
    runtime.content.ingest = AsyncMock(side_effect=KnowledgeOperationError(failure))

    result = await runtime.coordinator.ingest(_request(IngestDocument(title="Fixture", text="Failed content")))

    assert result.documents_processed == 1
    assert result.documents_created == 0
    assert result.errors == (failure,)
    assert runtime.content.ingest.await_args.args[0].scope == runtime.source.scope
    health_report: SourceHealthReport = runtime.sources.record_health.call_args.args[1]
    assert health_report.health is SourceHealth.FAILED
    assert health_report.message == "processed=1, succeeded=0, failed=1, created=0, replaced=0, unchanged=0"


@pytest.mark.asyncio
async def test_scoped_content_is_removed_by_source_deletion_cascade(runtime: _Runtime) -> None:
    ingest_result = await runtime.coordinator.ingest(
        _request(IngestDocument(title="Fixture", text="Content to delete", external_id="fixture-1"))
    )
    content_result = ingest_result.content_results[0]
    runtime.content.purge_source = runtime.content_store.purge_source
    runtime.sources.delete_source.return_value = SourceDeletionInfo(
        source_id=runtime.source.id,
        source_name=runtime.source.name,
        scope=runtime.source.scope,
        deleted_at=datetime.now(tz=UTC),
    )
    runtime.enrichment.discard_chunks.return_value = EnrichmentDiscardResult(
        discarded_chunk_ids=content_result.chunk_ids,
        queue_items_removed=0,
    )
    runtime.enrichment.purge_source.return_value = EnrichmentPurgeResult(source_id=runtime.source.id)
    runtime.graph.invalidate_evidence_by_chunks.return_value = EvidenceInvalidationResult()

    purge = await runtime.coordinator.delete_source(runtime.source.id)

    assert purge.status is PurgeStatus.COMPLETE
    assert purge.content.chunk_ids == content_result.chunk_ids
    assert runtime.content_store.get_document(content_result.document_id) is None
    assert runtime.vectors.vectors == {}
