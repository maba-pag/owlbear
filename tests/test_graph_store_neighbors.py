"""Tests for GraphStore.get_neighbors() — BFS traversal over knowledge graph."""

from __future__ import annotations

import sqlite3

import pytest

from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.models import (
    Edge,
    Entity,
    EntityType,
    RelationType,
)
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store() -> GraphStore:
    """In-memory SQLite graph store with schema initialized."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return GraphStore(conn)


def _entity(name: str, scope: str = "global") -> Entity:
    """Shortcut to build a named entity."""
    return Entity(name=name, entity_type=EntityType.CONCEPT, scope=scope)


def _edge(
    source: Entity,
    target: Entity,
    relation: RelationType = RelationType.RELATED_TO,
    scope: str = "global",
) -> Edge:
    """Shortcut to build an edge between two entities."""
    return Edge(
        source_id=source.id,
        target_id=target.id,
        relation=relation,
        scope=scope,
    )


def _seed_chain(store: GraphStore, n: int, scope: str = "global") -> list[Entity]:
    """Insert a linear chain A→B→C→…  of *n* entities and return them."""
    entities = [_entity(f"node_{i}", scope=scope) for i in range(n)]
    for e in entities:
        store.insert_entity(e)
    for i in range(n - 1):
        store.insert_edge(_edge(entities[i], entities[i + 1], scope=scope))
    return entities


# ---------------------------------------------------------------------------
# Tests: basic neighbor discovery
# ---------------------------------------------------------------------------


class TestGetNeighborsBasic:
    """Direct (depth=1) neighbor discovery."""

    def test_returns_direct_neighbors_with_edges(self, store: GraphStore) -> None:
        """get_neighbors(A, depth=1) on A→B returns [(B, edge_AB)]."""
        a, b = _entity("A"), _entity("B")
        store.insert_entity(a)
        store.insert_entity(b)
        edge_ab = _edge(a, b)
        store.insert_edge(edge_ab)

        result = store.get_neighbors(a.id, max_depth=1)

        assert len(result) == 1
        neighbor, connecting_edge = result[0]
        assert neighbor.id == b.id
        assert connecting_edge.id == edge_ab.id

    def test_bidirectional_outgoing(self, store: GraphStore) -> None:
        """A→B: get_neighbors(A) finds B via outgoing edge."""
        a, b = _entity("A"), _entity("B")
        store.insert_entity(a)
        store.insert_entity(b)
        store.insert_edge(_edge(a, b))

        result = store.get_neighbors(a.id)
        neighbor_ids = {ent.id for ent, _ in result}
        assert b.id in neighbor_ids

    def test_bidirectional_incoming(self, store: GraphStore) -> None:
        """A→B: get_neighbors(B) finds A via incoming edge."""
        a, b = _entity("A"), _entity("B")
        store.insert_entity(a)
        store.insert_entity(b)
        store.insert_edge(_edge(a, b))

        result = store.get_neighbors(b.id)
        neighbor_ids = {ent.id for ent, _ in result}
        assert a.id in neighbor_ids

    def test_multiple_neighbors(self, store: GraphStore) -> None:
        """Hub entity with 3 outgoing edges returns all 3 neighbors."""
        hub = _entity("hub")
        spokes = [_entity(f"spoke_{i}") for i in range(3)]
        store.insert_entity(hub)
        for s in spokes:
            store.insert_entity(s)
            store.insert_edge(_edge(hub, s))

        result = store.get_neighbors(hub.id)
        neighbor_ids = {ent.id for ent, _ in result}
        assert neighbor_ids == {s.id for s in spokes}


# ---------------------------------------------------------------------------
# Tests: depth parameter (multi-hop BFS)
# ---------------------------------------------------------------------------


class TestGetNeighborsDepth:
    """Multi-hop BFS traversal."""

    def test_depth_2_returns_two_hop_neighbors(self, store: GraphStore) -> None:
        """A→B→C: get_neighbors(A, depth=2) returns B and C."""
        entities = _seed_chain(store, 3)
        a, b, c = entities

        result = store.get_neighbors(a.id, max_depth=2)
        neighbor_ids = {ent.id for ent, _ in result}
        assert b.id in neighbor_ids
        assert c.id in neighbor_ids

    def test_depth_1_excludes_two_hop(self, store: GraphStore) -> None:
        """A→B→C: get_neighbors(A, depth=1) returns only B, not C."""
        entities = _seed_chain(store, 3)
        a, b, c = entities

        result = store.get_neighbors(a.id, max_depth=1)
        neighbor_ids = {ent.id for ent, _ in result}
        assert b.id in neighbor_ids
        assert c.id not in neighbor_ids

    def test_cycle_does_not_loop(self, store: GraphStore) -> None:
        """A→B→C→A: BFS visited-set prevents infinite loop."""
        a, b, c = _entity("A"), _entity("B"), _entity("C")
        for e in (a, b, c):
            store.insert_entity(e)
        store.insert_edge(_edge(a, b))
        store.insert_edge(_edge(b, c))
        store.insert_edge(_edge(c, a))

        # depth=10 would loop without visited set
        result = store.get_neighbors(a.id, max_depth=10)
        neighbor_ids = {ent.id for ent, _ in result}
        # Should find B and C but not A itself
        assert a.id not in neighbor_ids
        assert b.id in neighbor_ids
        assert c.id in neighbor_ids


# ---------------------------------------------------------------------------
# Tests: max_nodes cap
# ---------------------------------------------------------------------------


class TestGetNeighborsMaxNodes:
    """BFS expansion cap."""

    def test_max_nodes_caps_results(self, store: GraphStore) -> None:
        """Hub with 25 spokes, max_nodes=5 returns at most 5."""
        hub = _entity("hub")
        store.insert_entity(hub)
        for i in range(25):
            spoke = _entity(f"spoke_{i}")
            store.insert_entity(spoke)
            store.insert_edge(_edge(hub, spoke))

        result = store.get_neighbors(hub.id, max_nodes=5)
        assert len(result) <= 5

    def test_default_max_nodes_is_20(self, store: GraphStore) -> None:
        """Hub with 30 spokes, default max_nodes returns at most 20."""
        hub = _entity("hub")
        store.insert_entity(hub)
        for i in range(30):
            spoke = _entity(f"spoke_{i}")
            store.insert_entity(spoke)
            store.insert_edge(_edge(hub, spoke))

        result = store.get_neighbors(hub.id)
        assert len(result) <= 20


# ---------------------------------------------------------------------------
# Tests: scopes filtering
# ---------------------------------------------------------------------------


class TestGetNeighborsScopes:
    """Scope-based edge filtering."""

    def test_scopes_filter_edges(self, store: GraphStore) -> None:
        """Only edges matching the requested scopes are traversed."""
        a = _entity("A", scope="proj-x")
        b = _entity("B", scope="proj-x")
        c = _entity("C", scope="proj-y")
        for e in (a, b, c):
            store.insert_entity(e)
        store.insert_edge(_edge(a, b, scope="proj-x"))
        store.insert_edge(_edge(a, c, scope="proj-y"))

        result = store.get_neighbors(a.id, scopes=["proj-x"])
        neighbor_ids = {ent.id for ent, _ in result}
        assert b.id in neighbor_ids
        assert c.id not in neighbor_ids

    def test_scopes_none_returns_all(self, store: GraphStore) -> None:
        """scopes=None traverses all edges regardless of scope."""
        a = _entity("A", scope="proj-x")
        b = _entity("B", scope="proj-x")
        c = _entity("C", scope="proj-y")
        for e in (a, b, c):
            store.insert_entity(e)
        store.insert_edge(_edge(a, b, scope="proj-x"))
        store.insert_edge(_edge(a, c, scope="proj-y"))

        result = store.get_neighbors(a.id, scopes=None)
        neighbor_ids = {ent.id for ent, _ in result}
        assert b.id in neighbor_ids
        assert c.id in neighbor_ids


# ---------------------------------------------------------------------------
# Tests: unknown entity
# ---------------------------------------------------------------------------


class TestGetNeighborsUnknown:
    """Edge case: entity_id that doesn't exist."""

    def test_unknown_entity_returns_empty(self, store: GraphStore) -> None:
        """get_neighbors('nonexistent') returns [] without error."""
        result = store.get_neighbors("nonexistent")
        assert result == []
