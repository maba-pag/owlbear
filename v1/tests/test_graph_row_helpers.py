"""Tests for _entity_from_row / _edge_from_row DRY helpers on GraphStore.

TDD RED phase for task #529. All tests MUST fail until the builder extracts
the helpers. Tests verify the contract: staticmethod existence, correct
deserialization, importance default, and delegation from CRUD methods.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from unittest.mock import patch

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
def db_conn() -> sqlite3.Connection:
    """In-memory SQLite connection with schema applied."""
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    return conn


@pytest.fixture
def store(db_conn: sqlite3.Connection) -> GraphStore:
    """GraphStore backed by the in-memory database."""
    return GraphStore(db_conn)


# ---------------------------------------------------------------------------
# Sample row tuples (matching SELECT column order in graph.py)
# ---------------------------------------------------------------------------

def _entity_row(
    *,
    importance: float | None = 0.75,
    metadata: str | None = '{"lang": "python"}',
) -> tuple[Any, ...]:
    """Build a 9-element entity row tuple."""
    return (
        "ent-001",         # id
        "my_func",         # name
        "function",        # entity_type
        "A helper func",   # description
        metadata,          # metadata (JSON string or None)
        "global",          # scope
        "doc-001",         # document_id
        "chunk-001",       # chunk_id
        importance,        # importance (float or None)
    )


def _edge_row(
    *,
    metadata: str | None = '{"weight_source": "llm"}',
) -> tuple[Any, ...]:
    """Build a 7-element edge row tuple."""
    return (
        "edge-001",        # id
        "ent-001",         # source_id
        "ent-002",         # target_id
        "depends_on",      # relation
        0.8,               # weight
        metadata,          # metadata (JSON string or None)
        "project-x",       # scope
    )


# ===========================================================================
# AC-1: _entity_from_row exists as staticmethod and deserializes correctly
# ===========================================================================


class TestFromAC_EntityFromRow:  # noqa: N801
    """_entity_from_row(row) staticmethod: 9-element tuple, _load_meta, importance default."""

    def test_entity_from_row_exists_as_staticmethod(self) -> None:
        """The helper must be a staticmethod on GraphStore."""
        attr = getattr(GraphStore, "_entity_from_row", None)
        assert attr is not None, "_entity_from_row not found on GraphStore"
        assert isinstance(
            GraphStore.__dict__["_entity_from_row"], staticmethod
        ), "_entity_from_row must be a @staticmethod"

    def test_returns_entity_model(self) -> None:
        """Must return an Entity instance from a well-formed row."""
        result = GraphStore._entity_from_row(_entity_row())
        assert isinstance(result, Entity)

    def test_maps_all_nine_fields(self) -> None:
        """Every positional element maps to the correct Entity field."""
        row = _entity_row()
        entity = GraphStore._entity_from_row(row)
        assert entity.id == "ent-001"
        assert entity.name == "my_func"
        assert entity.entity_type == EntityType.FUNCTION
        assert entity.description == "A helper func"
        assert entity.metadata == {"lang": "python"}
        assert entity.scope == "global"
        assert entity.document_id == "doc-001"
        assert entity.chunk_id == "chunk-001"
        assert entity.importance == 0.75

    def test_importance_defaults_to_half_when_none(self) -> None:
        """When importance column is NULL (None), default to 0.5."""
        row = _entity_row(importance=None)
        entity = GraphStore._entity_from_row(row)
        assert entity.importance == 0.5

    def test_metadata_deserialized_via_load_meta(self) -> None:
        """metadata column is deserialized through _load_meta (JSON parse)."""
        meta = {"complex": [1, 2, 3], "nested": {"a": True}}
        row = _entity_row(metadata=json.dumps(meta))
        entity = GraphStore._entity_from_row(row)
        assert entity.metadata == meta

    def test_none_metadata_gives_empty_dict(self) -> None:
        """NULL metadata column produces an empty dict (via _load_meta)."""
        row = _entity_row(metadata=None)
        entity = GraphStore._entity_from_row(row)
        assert entity.metadata == {}

    def test_empty_string_metadata_gives_empty_dict(self) -> None:
        """Empty-string metadata column produces an empty dict (via _load_meta)."""
        row = _entity_row(metadata="")
        entity = GraphStore._entity_from_row(row)
        assert entity.metadata == {}


# ===========================================================================
# AC-2: _edge_from_row exists as staticmethod and deserializes correctly
# ===========================================================================


class TestFromAC_EdgeFromRow:  # noqa: N801
    """_edge_from_row(row) staticmethod: 7-element tuple, _load_meta for metadata."""

    def test_edge_from_row_exists_as_staticmethod(self) -> None:
        """The helper must be a staticmethod on GraphStore."""
        attr = getattr(GraphStore, "_edge_from_row", None)
        assert attr is not None, "_edge_from_row not found on GraphStore"
        assert isinstance(
            GraphStore.__dict__["_edge_from_row"], staticmethod
        ), "_edge_from_row must be a @staticmethod"

    def test_returns_edge_model(self) -> None:
        """Must return an Edge instance from a well-formed row."""
        result = GraphStore._edge_from_row(_edge_row())
        assert isinstance(result, Edge)

    def test_maps_all_seven_fields(self) -> None:
        """Every positional element maps to the correct Edge field."""
        row = _edge_row()
        edge = GraphStore._edge_from_row(row)
        assert edge.id == "edge-001"
        assert edge.source_id == "ent-001"
        assert edge.target_id == "ent-002"
        assert edge.relation == RelationType.DEPENDS_ON
        assert edge.weight == 0.8
        assert edge.metadata == {"weight_source": "llm"}
        assert edge.scope == "project-x"

    def test_metadata_deserialized_via_load_meta(self) -> None:
        """metadata column is deserialized through _load_meta."""
        meta = {"source": "test", "tags": ["a", "b"]}
        row = _edge_row(metadata=json.dumps(meta))
        edge = GraphStore._edge_from_row(row)
        assert edge.metadata == meta

    def test_none_metadata_gives_empty_dict(self) -> None:
        """NULL metadata column produces an empty dict."""
        row = _edge_row(metadata=None)
        edge = GraphStore._edge_from_row(row)
        assert edge.metadata == {}


# ===========================================================================
# AC-3: get_entity, list_entities, list_entities_for_document delegate
# ===========================================================================


class TestFromAC_EntityMethodsDelegation:  # noqa: N801
    """All entity CRUD methods must call _entity_from_row (not inline-construct)."""

    @pytest.fixture(autouse=True)
    def _seed_entity(self, store: GraphStore) -> None:
        """Insert a sample entity so queries return results."""
        entity = Entity(
            id="ent-del",
            name="delegated",
            entity_type=EntityType.CONCEPT,
            description="test delegation",
        )
        store.insert_entity(entity)

    def test_get_entity_calls_entity_from_row(self, store: GraphStore) -> None:
        """get_entity must delegate deserialization to _entity_from_row."""
        with patch.object(
            GraphStore, "_entity_from_row", wraps=GraphStore._entity_from_row
        ) as spy:
            result = store.get_entity("ent-del")
            assert result is not None
            spy.assert_called_once()

    def test_list_entities_calls_entity_from_row(self, store: GraphStore) -> None:
        """list_entities must delegate deserialization to _entity_from_row."""
        with patch.object(
            GraphStore, "_entity_from_row", wraps=GraphStore._entity_from_row
        ) as spy:
            results = store.list_entities()
            assert len(results) >= 1
            assert spy.call_count == len(results)

    def test_list_entities_for_document_calls_entity_from_row(
        self, store: GraphStore
    ) -> None:
        """list_entities_for_document must delegate to _entity_from_row."""
        # Insert entity with a specific document_id
        entity = Entity(
            id="ent-doc",
            name="doc-linked",
            entity_type=EntityType.FILE,
            document_id="doc-target",
        )
        store.insert_entity(entity)

        with patch.object(
            GraphStore, "_entity_from_row", wraps=GraphStore._entity_from_row
        ) as spy:
            results = store.list_entities_for_document("doc-target")
            assert len(results) >= 1
            assert spy.call_count == len(results)


# ===========================================================================
# AC-4: get_edge, list_edges delegate to _edge_from_row
# ===========================================================================


class TestFromAC_EdgeMethodsDelegation:  # noqa: N801
    """All edge CRUD methods must call _edge_from_row (not inline-construct)."""

    @pytest.fixture(autouse=True)
    def _seed_entities_and_edge(self, store: GraphStore) -> None:
        """Insert entities and an edge so queries return results."""
        for eid in ("ent-a", "ent-b"):
            store.insert_entity(
                Entity(
                    id=eid,
                    name=eid,
                    entity_type=EntityType.CONCEPT,
                )
            )
        store.insert_edge(
            Edge(
                id="edge-del",
                source_id="ent-a",
                target_id="ent-b",
                relation=RelationType.RELATED_TO,
            )
        )

    def test_get_edge_calls_edge_from_row(self, store: GraphStore) -> None:
        """get_edge must delegate deserialization to _edge_from_row."""
        with patch.object(
            GraphStore, "_edge_from_row", wraps=GraphStore._edge_from_row
        ) as spy:
            result = store.get_edge("edge-del")
            assert result is not None
            spy.assert_called_once()

    def test_list_edges_calls_edge_from_row(self, store: GraphStore) -> None:
        """list_edges must delegate deserialization to _edge_from_row."""
        with patch.object(
            GraphStore, "_edge_from_row", wraps=GraphStore._edge_from_row
        ) as spy:
            results = store.list_edges()
            assert len(results) >= 1
            assert spy.call_count == len(results)


# ===========================================================================
# AC-5: Zero inline Entity/Edge construction from row tuples in graph.py
# ===========================================================================


class TestFromAC_NoInlineConstruction:  # noqa: N801
    """Source-level check: no inline Entity/Edge tuple-indexed construction remains."""

    def _get_graph_source(self) -> str:
        import inspect

        import owlbear.memory.knowledge.graph as mod

        return inspect.getsource(mod)

    def _find_inline_model_constructions(
        self,
        source: str,
        model_name: str,
        helper_name: str,
    ) -> list[int]:
        """Find lines where ``Model(`` starts a block with tuple indexing, outside the helper.

        Scans for ``Entity(`` or ``Edge(`` that opens a multi-line constructor
        containing ``var[N]`` patterns, excluding lines inside the helper method.
        """
        import re

        model_pattern = re.compile(rf"\b{model_name}\(")
        index_pattern = re.compile(r"\w+\[\d+\]")

        lines = source.splitlines()
        inline_starts: list[int] = []
        in_helper = False

        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if f"def {helper_name}" in stripped:
                in_helper = True
                i += 1
                continue
            # A new def at the same or outer indentation ends the helper body.
            if in_helper and re.match(r"\s{0,8}def ", lines[i]):
                in_helper = False

            if not in_helper and model_pattern.search(lines[i]):
                # Scan from this line until closing paren for any tuple indexing.
                paren_depth = 0
                block_has_index = False
                for j in range(i, min(i + 20, len(lines))):
                    paren_depth += lines[j].count("(") - lines[j].count(")")
                    if index_pattern.search(lines[j]):
                        block_has_index = True
                    if paren_depth <= 0:
                        break
                if block_has_index:
                    inline_starts.append(i + 1)  # 1-indexed
            i += 1
        return inline_starts

    def test_no_inline_entity_from_row_in_source(self) -> None:
        """graph.py must not contain inline Entity(...[N]) outside _entity_from_row."""
        source = self._get_graph_source()
        sites = self._find_inline_model_constructions(
            source, "Entity", "_entity_from_row"
        )
        assert sites == [], (
            f"Inline Entity(...[N]) construction found at source lines: {sites}"
        )

    def test_no_inline_edge_from_row_in_source(self) -> None:
        """graph.py must not contain inline Edge(...[N]) outside _edge_from_row."""
        source = self._get_graph_source()
        sites = self._find_inline_model_constructions(
            source, "Edge", "_edge_from_row"
        )
        assert sites == [], (
            f"Inline Edge(...[N]) construction found at source lines: {sites}"
        )
