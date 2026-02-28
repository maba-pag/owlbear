"""Pydantic models for the knowledge graph: Entity, Edge, Document."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

# -- Enums -------------------------------------------------------------------


class EntityType(StrEnum):
    """Classification of knowledge-graph entities."""

    FILE = "file"
    FUNCTION = "function"
    CLASS_ = "class_"
    DECISION = "decision"
    PATTERN = "pattern"
    CONCEPT = "concept"


class RelationType(StrEnum):
    """Classification of edges between entities."""

    DEFINES = "defines"
    IMPORTS = "imports"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    IMPLEMENTS = "implements"
    DOCUMENTS = "documents"


# -- Helpers -----------------------------------------------------------------


def _uuid_hex() -> str:
    """Generate a uuid4 hex string (32 alphanumeric characters)."""
    return uuid4().hex


# -- Models ------------------------------------------------------------------


class Entity(BaseModel):
    """A node in the knowledge graph."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_uuid_hex)
    name: str
    entity_type: EntityType
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    scope: str = "global"
    document_id: str | None = None


class Edge(BaseModel):
    """A directed relationship between two entities."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_uuid_hex)
    source_id: str
    target_id: str
    relation: RelationType
    weight: float = Field(default=1.0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    scope: str = "global"


class Document(BaseModel):
    """A text document stored in the knowledge graph."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_uuid_hex)
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    scope: str = "global"
