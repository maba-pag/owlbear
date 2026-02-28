"""Tests for owlbear.memory.knowledge.models — Entity, Edge, Document."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.models import (
    Document,
    Edge,
    Entity,
    EntityType,
    RelationType,
)

# -- EntityType enum ---------------------------------------------------------


class TestEntityType:
    """EntityType StrEnum has all 6 expected values."""

    @pytest.mark.parametrize(
        "value",
        ["file", "function", "class_", "decision", "pattern", "concept"],
    )
    def test_valid_values(self, value: str) -> None:
        assert EntityType(value) == value

    def test_member_count(self) -> None:
        assert len(EntityType) == 6


# -- RelationType enum -------------------------------------------------------


class TestRelationType:
    """RelationType StrEnum has all 6 expected values."""

    @pytest.mark.parametrize(
        "value",
        ["defines", "imports", "depends_on", "related_to", "implements", "documents"],
    )
    def test_valid_values(self, value: str) -> None:
        assert RelationType(value) == value

    def test_member_count(self) -> None:
        assert len(RelationType) == 6


# -- Entity model ------------------------------------------------------------


class TestEntity:
    """Entity Pydantic model with frozen config."""

    def test_construction_with_all_fields(self) -> None:
        e = Entity(
            id="abc123",
            name="my_func",
            entity_type=EntityType.FUNCTION,
            description="A helper function",
            metadata={"lang": "python"},
        )
        assert e.id == "abc123"
        assert e.name == "my_func"
        assert e.entity_type == EntityType.FUNCTION
        assert e.description == "A helper function"
        assert e.metadata == {"lang": "python"}

    def test_default_id_is_uuid4_hex(self) -> None:
        e = Entity(name="x", entity_type=EntityType.FILE)
        assert len(e.id) == 32
        assert e.id.isalnum()

    def test_default_description_empty(self) -> None:
        e = Entity(name="x", entity_type=EntityType.FILE)
        assert e.description == ""

    def test_default_metadata_empty_dict(self) -> None:
        e = Entity(name="x", entity_type=EntityType.FILE)
        assert e.metadata == {}

    def test_immutability(self) -> None:
        e = Entity(name="x", entity_type=EntityType.FILE)
        with pytest.raises(ValidationError):
            e.name = "y"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        e = Entity(
            id="deadbeef" * 4,
            name="Cls",
            entity_type=EntityType.CLASS_,
            description="A class",
            metadata={"key": "val"},
        )
        restored = Entity.model_validate(e.model_dump())
        assert restored == e

    def test_rejects_invalid_entity_type(self) -> None:
        with pytest.raises(ValidationError):
            Entity(name="x", entity_type="not_a_type")  # type: ignore[arg-type]


# -- Edge model --------------------------------------------------------------


class TestEdge:
    """Edge Pydantic model with frozen config."""

    def test_construction_with_all_fields(self) -> None:
        edge = Edge(
            id="edge1",
            source_id="src1",
            target_id="tgt1",
            relation=RelationType.IMPORTS,
            weight=0.5,
            metadata={"note": "direct"},
        )
        assert edge.id == "edge1"
        assert edge.source_id == "src1"
        assert edge.target_id == "tgt1"
        assert edge.relation == RelationType.IMPORTS
        assert edge.weight == 0.5
        assert edge.metadata == {"note": "direct"}

    def test_default_id_is_uuid4_hex(self) -> None:
        edge = Edge(
            source_id="a",
            target_id="b",
            relation=RelationType.DEFINES,
        )
        assert len(edge.id) == 32
        assert edge.id.isalnum()

    def test_default_weight(self) -> None:
        edge = Edge(
            source_id="a",
            target_id="b",
            relation=RelationType.DEFINES,
        )
        assert edge.weight == 1.0

    def test_default_metadata_empty_dict(self) -> None:
        edge = Edge(
            source_id="a",
            target_id="b",
            relation=RelationType.DEFINES,
        )
        assert edge.metadata == {}

    def test_immutability(self) -> None:
        edge = Edge(
            source_id="a",
            target_id="b",
            relation=RelationType.DEFINES,
        )
        with pytest.raises(ValidationError):
            edge.weight = 2.0  # type: ignore[misc]

    def test_round_trip(self) -> None:
        edge = Edge(
            id="e" * 32,
            source_id="s1",
            target_id="t1",
            relation=RelationType.DEPENDS_ON,
            weight=0.75,
            metadata={"x": 1},
        )
        restored = Edge.model_validate(edge.model_dump())
        assert restored == edge

    def test_weight_rejects_negative(self) -> None:
        with pytest.raises(ValidationError):
            Edge(
                source_id="a",
                target_id="b",
                relation=RelationType.DEFINES,
                weight=-0.1,
            )

    def test_rejects_invalid_relation(self) -> None:
        with pytest.raises(ValidationError):
            Edge(
                source_id="a",
                target_id="b",
                relation="bogus",  # type: ignore[arg-type]
            )


# -- Document model -----------------------------------------------------------


class TestDocument:
    """Document Pydantic model with frozen config."""

    def test_construction_with_all_fields(self) -> None:
        doc = Document(
            id="doc1",
            title="README",
            content="Hello world",
            metadata={"format": "md"},
        )
        assert doc.id == "doc1"
        assert doc.title == "README"
        assert doc.content == "Hello world"
        assert doc.metadata == {"format": "md"}

    def test_default_id_is_uuid4_hex(self) -> None:
        doc = Document(title="T", content="C")
        assert len(doc.id) == 32
        assert doc.id.isalnum()

    def test_default_metadata_empty_dict(self) -> None:
        doc = Document(title="T", content="C")
        assert doc.metadata == {}

    def test_immutability(self) -> None:
        doc = Document(title="T", content="C")
        with pytest.raises(ValidationError):
            doc.title = "New"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        doc = Document(
            id="d" * 32,
            title="Design",
            content="Body text",
            metadata={"author": "owl"},
        )
        restored = Document.model_validate(doc.model_dump())
        assert restored == doc
