"""Tests for GraphStore edge cases — covers uncovered paths in graph_store.py.

Targets: _load_meta with null/empty, list_entities with empty scopes,
list_entities_for_document with empty scopes, list_edges with empty scopes.
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Document, Edge, Entity, EntityType, RelationType
from owlbear_knowledge.schema import init_db


@pytest.fixture
def gs() -> GraphStore:
    """Graph store backed by in-memory SQLite."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    store = GraphStore(conn)
    # Seed data
    store.insert_document(Document(id="d1", title="D1", content="c1", scope="global"))
    store.insert_entity(
        Entity(
            id="e1",
            name="Alpha",
            entity_type=EntityType.CONCEPT,
            description="desc",
            scope="global",
            document_id="d1",
            chunk_id="ch1",
        )
    )
    store.insert_entity(
        Entity(
            id="e2",
            name="Beta",
            entity_type=EntityType.CONCEPT,
            description="desc2",
            scope="other",
            document_id="d1",
            chunk_id="ch2",
        )
    )
    store.insert_edge(
        Edge(
            id="edge1",
            source_id="e1",
            target_id="e2",
            relation=RelationType.RELATED_TO,
            weight=1.0,
            scope="global",
        )
    )
    return store


class TestLoadMetaEdgeCases:
    def test_null_metadata_returns_empty_dict(self) -> None:
        assert GraphStore._load_meta(None) == {}

    def test_empty_string_metadata_returns_empty_dict(self) -> None:
        assert GraphStore._load_meta("") == {}


class TestListEntitiesEmptyScopes:
    def test_empty_scopes_list_returns_empty(self, gs: GraphStore) -> None:
        """list_entities(scopes=[]) short-circuits to []."""
        assert gs.list_entities(scopes=[]) == []

    def test_none_scopes_returns_all(self, gs: GraphStore) -> None:
        """list_entities(scopes=None) returns all entities."""
        assert len(gs.list_entities(scopes=None)) == 2

    def test_source_pipeline_filter(self, gs: GraphStore) -> None:
        """list_entities(source_pipeline=...) filters by metadata field."""
        # No entities have source_pipeline set, so result should be empty
        assert gs.list_entities(source_pipeline="nonexistent") == []


class TestListEntitiesForDocumentEmptyScopes:
    def test_empty_scopes_list_returns_empty(self, gs: GraphStore) -> None:
        """list_entities_for_document(scopes=[]) short-circuits to []."""
        assert gs.list_entities_for_document("d1", scopes=[]) == []

    def test_scoped_filter_returns_subset(self, gs: GraphStore) -> None:
        """list_entities_for_document with scope filter returns matching entities only."""
        result = gs.list_entities_for_document("d1", scopes=["global"])
        assert len(result) == 1
        assert result[0].id == "e1"


class TestListEdgesEmptyScopes:
    def test_empty_scopes_list_returns_empty(self, gs: GraphStore) -> None:
        """list_edges(scopes=[]) short-circuits to []."""
        assert gs.list_edges(scopes=[]) == []

    def test_none_scopes_returns_all(self, gs: GraphStore) -> None:
        assert len(gs.list_edges(scopes=None)) == 1

    def test_source_pipeline_filter(self, gs: GraphStore) -> None:
        """list_edges(source_pipeline=...) filters by metadata field."""
        assert gs.list_edges(source_pipeline="nonexistent") == []


class TestGetCounts:
    def test_returns_correct_counts(self, gs: GraphStore) -> None:
        docs, entities, edges = gs.get_counts()
        assert docs == 1
        assert entities == 2
        assert edges == 1

    def test_empty_db_returns_zeros(self) -> None:
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        store = GraphStore(conn)
        assert store.get_counts() == (0, 0, 0)
