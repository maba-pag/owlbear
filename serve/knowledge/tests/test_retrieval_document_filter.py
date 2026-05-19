"""Retrieval vector filtering regressions."""

from __future__ import annotations

from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.retrieval import GraphAugmentedRetriever


class FakeVectorStore:
    def __init__(self, results: list[tuple[str, float]] | None = None) -> None:
        self.embedding_type: str | None = None
        self.results = results or []

    def search_similar(
        self,
        _query_embedding: object,
        top_k: int = 5,
        embedding_type: str | None = None,
        *,
        scopes: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        _ = top_k, scopes
        self.embedding_type = embedding_type
        return self.results


class FakeEmbeddingProvider:
    def embed(self, _queries: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3]]


class FakeGraphStore:
    def __init__(self) -> None:
        self.max_depth_seen: int | None = None
        self.seed = Entity(
            id="seed",
            name="Seed",
            entity_type=EntityType.CONCEPT,
            chunk_id="chunk-seed",
            document_id="doc-seed",
        )
        self.first_hop = Entity(
            id="first-hop",
            name="First Hop",
            entity_type=EntityType.CONCEPT,
            description="first hop",
            document_id="doc-seed",
        )
        self.second_hop = Entity(
            id="second-hop",
            name="Second Hop",
            entity_type=EntityType.CONCEPT,
            description="second hop",
            document_id="doc-seed",
        )

    def list_entities(self, *, scopes: list[str] | None = None) -> list[Entity]:
        _ = scopes
        return [self.seed]

    def get_entities_by_chunk_ids(self, chunk_ids: set[str], *, scopes: list[str] | None = None) -> list[Entity]:
        _ = scopes
        return [self.seed] if self.seed.chunk_id in chunk_ids else []

    def get_entity(self, entity_id: str) -> Entity | None:
        entities = {
            self.seed.id: self.seed,
            self.first_hop.id: self.first_hop,
            self.second_hop.id: self.second_hop,
        }
        return entities.get(entity_id)

    def get_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
        scopes: list[str] | None = None,
    ) -> list[tuple[Entity, Edge]]:
        _ = entity_id, scopes
        self.max_depth_seen = max_depth
        neighbors = [
            (self.first_hop, Edge(source_id="seed", target_id="first-hop", relation=RelationType.RELATED_TO)),
        ]
        if max_depth >= 2:
            neighbors.append(
                (
                    self.second_hop,
                    Edge(source_id="first-hop", target_id="second-hop", relation=RelationType.RELATED_TO),
                )
            )
        return neighbors


class MultiSeedGraphStore:
    def list_entities(self, *, scopes: list[str] | None = None) -> list[Entity]:
        _ = scopes
        return [
            Entity(
                id="seed-a",
                name="Seed A",
                entity_type=EntityType.CONCEPT,
                chunk_id="chunk-a",
                document_id="doc-a",
            ),
            Entity(
                id="seed-b",
                name="Seed B",
                entity_type=EntityType.CONCEPT,
                chunk_id="chunk-b",
                document_id="doc-b",
            ),
        ]

    def get_entities_by_chunk_ids(self, chunk_ids: set[str], *, scopes: list[str] | None = None) -> list[Entity]:
        _ = scopes
        all_entities = self.list_entities()
        return [e for e in all_entities if e.chunk_id in chunk_ids]

    def get_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
        scopes: list[str] | None = None,
    ) -> list[tuple[Entity, Edge]]:
        _ = max_depth, scopes
        if entity_id == "seed-a":
            return [
                (
                    Entity(
                        id="neighbor-a",
                        name="Neighbor A",
                        entity_type=EntityType.CONCEPT,
                        description="visible context",
                        document_id="doc-a",
                    ),
                    Edge(source_id="seed-a", target_id="neighbor-a", relation=RelationType.RELATED_TO),
                )
            ]
        return [
            (
                Entity(
                    id="neighbor-b",
                    name="Neighbor B",
                    entity_type=EntityType.CONCEPT,
                    description="hidden context",
                    document_id="doc-b",
                ),
                Edge(source_id="seed-b", target_id="neighbor-b", relation=RelationType.RELATED_TO),
            )
        ]


class ImportanceGraphStore:
    def list_entities(self, *, scopes: list[str] | None = None) -> list[Entity]:
        _ = scopes
        return [
            Entity(
                id="seed",
                name="Seed",
                entity_type=EntityType.CONCEPT,
                chunk_id="chunk-seed",
                document_id="doc-seed",
            )
        ]

    def get_entities_by_chunk_ids(self, chunk_ids: set[str], *, scopes: list[str] | None = None) -> list[Entity]:
        _ = scopes
        return [e for e in self.list_entities() if e.chunk_id in chunk_ids]

    def get_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
        scopes: list[str] | None = None,
    ) -> list[tuple[Entity, Edge]]:
        _ = entity_id, max_depth, scopes
        return [
            (
                Entity(
                    id="low",
                    name="LowImportance",
                    entity_type=EntityType.CONCEPT,
                    description="low neighbor",
                    document_id="doc-seed",
                    importance=0.1,
                ),
                Edge(source_id="seed", target_id="low", relation=RelationType.RELATED_TO),
            ),
            (
                Entity(
                    id="high",
                    name="HighImportance",
                    entity_type=EntityType.CONCEPT,
                    description="high neighbor",
                    document_id="doc-seed",
                    importance=0.9,
                ),
                Edge(source_id="seed", target_id="high", relation=RelationType.RELATED_TO),
            ),
        ]


class IncomingEdgeGraphStore:
    def list_entities(self, *, scopes: list[str] | None = None) -> list[Entity]:
        _ = scopes
        return [
            Entity(
                id="a",
                name="A",
                entity_type=EntityType.CONCEPT,
                description="seed entity A",
                chunk_id="chunk-a",
                document_id="doc-a",
            )
        ]

    def get_entities_by_chunk_ids(self, chunk_ids: set[str], *, scopes: list[str] | None = None) -> list[Entity]:
        _ = scopes
        return [e for e in self.list_entities() if e.chunk_id in chunk_ids]

    def get_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
        scopes: list[str] | None = None,
    ) -> list[tuple[Entity, Edge]]:
        _ = entity_id, max_depth, scopes
        return [
            (
                Entity(
                    id="b",
                    name="B",
                    entity_type=EntityType.CONCEPT,
                    description="neighbor entity B",
                    document_id="doc-a",
                ),
                Edge(source_id="b", target_id="a", relation=RelationType.DEPENDS_ON),
            )
        ]


def test_graph_augmented_retriever_filters_to_document_embeddings() -> None:
    vector_store = FakeVectorStore()
    retriever = GraphAugmentedRetriever(
        vector_store=vector_store,
        graph_store=FakeGraphStore(),  # type: ignore[arg-type]
        embedding_provider=FakeEmbeddingProvider(),  # type: ignore[arg-type]
    )

    retriever.retrieve("where is the doc?", top_k=3)

    assert vector_store.embedding_type == "document"


def test_graph_augmented_retriever_honors_expansion_depth() -> None:
    vector_store = FakeVectorStore(results=[("chunk-seed", 0.9)])
    graph_store = FakeGraphStore()
    retriever = GraphAugmentedRetriever(
        vector_store=vector_store,
        graph_store=graph_store,  # type: ignore[arg-type]
        embedding_provider=FakeEmbeddingProvider(),  # type: ignore[arg-type]
        expansion_depth=2,
    )

    result = retriever.retrieve("expand", scopes=["proof"])

    assert graph_store.max_depth_seen == 2
    assert "First Hop: first hop" in result.expansion_text
    assert "First Hop --[related_to]--> Second Hop: second hop" in result.expansion_text


def test_graph_augmented_retriever_expands_only_returned_top_k_hits() -> None:
    vector_store = FakeVectorStore(results=[("chunk-a", 0.99), ("chunk-b", 0.98)])
    retriever = GraphAugmentedRetriever(
        vector_store=vector_store,
        graph_store=MultiSeedGraphStore(),  # type: ignore[arg-type]
        embedding_provider=FakeEmbeddingProvider(),  # type: ignore[arg-type]
    )

    result = retriever.retrieve("expand", top_k=1, scopes=["proof"])

    assert result.chunks == [("chunk-a", 0.99)]
    assert "Neighbor A: visible context" in result.expansion_text
    assert "Neighbor B: hidden context" not in result.expansion_text


def test_graph_augmented_retriever_expands_only_threshold_qualified_hits() -> None:
    vector_store = FakeVectorStore(results=[("chunk-a", 0.99), ("chunk-b", 0.1)])
    retriever = GraphAugmentedRetriever(
        vector_store=vector_store,
        graph_store=MultiSeedGraphStore(),  # type: ignore[arg-type]
        embedding_provider=FakeEmbeddingProvider(),  # type: ignore[arg-type]
    )

    result = retriever.retrieve("expand", top_k=2, scopes=["proof"], similarity_threshold=0.5)

    assert result.chunks == [("chunk-a", 0.99)]
    assert "Neighbor A: visible context" in result.expansion_text
    assert "Neighbor B: hidden context" not in result.expansion_text


def test_graph_augmented_retriever_ranks_by_importance_before_neighbor_limit() -> None:
    vector_store = FakeVectorStore(results=[("chunk-seed", 0.9)])
    retriever = GraphAugmentedRetriever(
        vector_store=vector_store,
        graph_store=ImportanceGraphStore(),  # type: ignore[arg-type]
        embedding_provider=FakeEmbeddingProvider(),  # type: ignore[arg-type]
        max_neighbors_per_entity=1,
        weight_by_importance=True,
    )

    result = retriever.retrieve("expand", scopes=["proof"])

    assert "HighImportance: high neighbor" in result.expansion_text
    assert "LowImportance: low neighbor" not in result.expansion_text


def test_graph_augmented_retriever_preserves_incoming_edge_direction() -> None:
    vector_store = FakeVectorStore(results=[("chunk-a", 0.9)])
    retriever = GraphAugmentedRetriever(
        vector_store=vector_store,
        graph_store=IncomingEdgeGraphStore(),  # type: ignore[arg-type]
        embedding_provider=FakeEmbeddingProvider(),  # type: ignore[arg-type]
    )

    result = retriever.retrieve("expand", scopes=["proof"])

    assert "B --[depends_on]--> A: seed entity A" in result.expansion_text
    assert "A --[depends_on]--> B" not in result.expansion_text
