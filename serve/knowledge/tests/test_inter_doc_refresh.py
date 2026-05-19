"""Inter-document graph refresh hooks should be activation-safe."""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Coroutine
from typing import Any

import pytest

from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_builder import GraphBuildResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.inter_doc_graph_builder import InterDocGraphBuilder
from owlbear_knowledge.models import Document, Edge, Entity, EntityType, KnowledgeSource, RelationType, SourceType
from owlbear_knowledge.refresh import RefreshOrchestrator
from owlbear_knowledge.schema import init_db


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(connection)
    return connection


def _source(scope: str = "proof") -> KnowledgeSource:
    return KnowledgeSource(
        id="src-main",
        name="Source",
        source_type=SourceType.URL_LIST,
        fetch_method="http",
        enrich=True,
        config={"urls": ["https://example.test"]},
        scope=scope,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _seed_two_documents(graph: GraphStore, *, scope: str = "proof") -> None:
    graph.insert_document(Document(id="doc-new", title="New", content="new", scope=scope, source_id="src-new"))
    graph.insert_document(Document(id="doc-old", title="Old", content="old", scope=scope, source_id="src-old"))
    graph.insert_entity(
        Entity(id="ent-new", name="Shared", entity_type=EntityType.CONCEPT, scope=scope, document_id="doc-new")
    )
    graph.insert_entity(
        Entity(id="ent-old", name="Shared", entity_type=EntityType.CONCEPT, scope=scope, document_id="doc-old")
    )


class RecordingBuilder:
    def __init__(self) -> None:
        self.entities_seen: list[tuple[str, str | None, str]] = []

    async def build(self, entities: list[Entity], scope: str = "global") -> GraphBuildResult:
        _ = scope
        self.entities_seen = [(entity.id, entity.document_id, entity.scope) for entity in entities]
        return GraphBuildResult(
            edges=[
                Edge(
                    source_id="ent-new",
                    target_id="ent-old",
                    relation=RelationType.RELATED_TO,
                    scope="wrong-scope",
                )
            ],
            edges_added=1,
        )


class CapturingVectorStore:
    def __init__(self) -> None:
        self.scopes_seen: list[list[str] | None] = []
        self.embedding_types_seen: list[str | None] = []

    def get_embedding(self, _entity_id: str) -> list[float]:
        return [0.1]

    def search_similar(
        self,
        _embedding: object,
        *,
        top_k: int = 10,
        embedding_type: str | None = None,
        scopes: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        _ = top_k
        self.scopes_seen.append(scopes)
        self.embedding_types_seen.append(embedding_type)
        return []


class MissingEmbeddingVectorStore:
    def __init__(self) -> None:
        self.search_called = False

    def get_embedding(self, _entity_id: str) -> None:
        return None

    def search_similar(self, _embedding: object, **_kwargs: object) -> list[tuple[str, float]]:
        self.search_called = True
        msg = "search_similar should not be called without an embedding"
        raise AssertionError(msg)


class EdgeExtractor:
    def __init__(self, edges: list[Edge] | None = None) -> None:
        self.edges = edges or [Edge(source_id="ent-new", target_id="ent-old", relation=RelationType.RELATED_TO)]
        self.prompts: list[str] = []

    async def extract(self, prompt: str) -> ExtractionResult:
        self.prompts.append(prompt)
        return ExtractionResult(edges=self.edges)


@pytest.mark.asyncio
async def test_refresh_inter_doc_hook_uses_scope_entities_and_persists_edges(
    conn: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = GraphStore(conn)
    _seed_two_documents(graph)
    builder = RecordingBuilder()
    scheduled: list[Coroutine[Any, Any, None]] = []

    def capture_task(coro: Coroutine[Any, Any, None]) -> asyncio.Future[None]:
        scheduled.append(coro)
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        future.set_result(None)
        return future

    monkeypatch.setattr(asyncio, "create_task", capture_task)
    orchestrator = RefreshOrchestrator(
        store=object(),
        pipeline=object(),
        inter_doc_builder=builder,
        graph_store=graph,
    )

    orchestrator._schedule_inter_doc_build(_source(), "doc-new")
    assert scheduled
    await scheduled[0]

    assert {entity_id for entity_id, _, _ in builder.entities_seen} == {"ent-new", "ent-old"}
    row = conn.execute("SELECT source_id, target_id, document_id, scope FROM edges").fetchone()
    assert row == ("ent-new", "ent-old", "doc-new", "proof")


@pytest.mark.asyncio
async def test_inter_doc_builder_stamps_scope_document_and_vector_scope(conn: sqlite3.Connection) -> None:
    graph = GraphStore(conn)
    _seed_two_documents(graph)
    entities = graph.list_entities(scopes=["proof"])
    vector_store = CapturingVectorStore()
    extractor = EdgeExtractor()
    builder = InterDocGraphBuilder(extractor, vector_store, graph)

    result = await builder.build(entities, scope="proof")

    assert len(result.edges) == 1
    assert "ent-new | Shared" in extractor.prompts[0]
    assert "ent-old | Shared" in extractor.prompts[0]
    edge = result.edges[0]
    assert edge.scope == "proof"
    assert edge.metadata["source"] == "inter_doc_inference"
    assert edge.metadata["doc_pair"] == ["doc-new", "doc-old"]
    assert edge.metadata["source_pair"] == ["src-new", "src-old"]
    assert edge.metadata["document_id"] == "doc-new"
    assert vector_store.scopes_seen == [["proof"], ["proof"]]
    assert vector_store.embedding_types_seen == ["entity", "entity"]


@pytest.mark.asyncio
async def test_inter_doc_builder_keeps_canonical_candidates_without_entity_embeddings(
    conn: sqlite3.Connection,
) -> None:
    graph = GraphStore(conn)
    _seed_two_documents(graph)
    vector_store = MissingEmbeddingVectorStore()
    builder = InterDocGraphBuilder(EdgeExtractor(), vector_store, graph)

    result = await builder.build(graph.list_entities(scopes=["proof"]), scope="proof")

    assert len(result.edges) == 1
    assert vector_store.search_called is False


@pytest.mark.asyncio
async def test_inter_doc_builder_drops_edges_outside_candidate_pairs(conn: sqlite3.Connection) -> None:
    graph = GraphStore(conn)
    _seed_two_documents(graph)
    vector_store = MissingEmbeddingVectorStore()
    extractor = EdgeExtractor(edges=[Edge(source_id="missing", target_id="ent-old", relation=RelationType.RELATED_TO)])
    builder = InterDocGraphBuilder(extractor, vector_store, graph)

    result = await builder.build(graph.list_entities(scopes=["proof"]), scope="proof")

    assert result.edges == []
    assert result.edges_added == 0
