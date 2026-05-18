"""Pydantic models for the knowledge graph: Entity, Edge, Document."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

# -- Enums -------------------------------------------------------------------


class EntityType(StrEnum):
    """Classification of knowledge-graph entities."""

    FILE = "file"
    FUNCTION = "function"
    CLASS_ = "class_"
    DECISION = "decision"
    PATTERN = "pattern"
    CONCEPT = "concept"
    REQUIREMENT = "requirement"
    SOLUTION = "solution"
    PROCEDURE = "procedure"
    POLICY = "policy"
    STANDARD = "standard"
    SYSTEM = "system"
    TOOL = "tool"
    PROCESS = "process"
    ROLE = "role"
    PERSON = "person"
    TEAM = "team"
    COMPONENT = "component"
    SERVICE = "service"


class RelationType(StrEnum):
    """Classification of edges between entities."""

    DEFINES = "defines"
    IMPORTS = "imports"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    IMPLEMENTS = "implements"
    DOCUMENTS = "documents"
    GOVERNED_BY = "governed_by"
    GOVERNS = "governs"
    SUPERSEDES_VERSION = "supersedes_version"
    BUILT_ON = "built_on"
    COMPONENT_OF = "component_of"
    CREATES = "creates"
    DESCRIBES = "describes"
    EXECUTES = "executes"
    EXTENDS = "extends"
    FOLLOWS = "follows"
    GUIDES = "guides"
    HOSTS = "hosts"
    INSTANCE_OF = "instance_of"
    INTEGRATES_WITH = "integrates_with"
    INVOKES = "invokes"
    MANAGES = "manages"
    PART_OF = "part_of"
    PRODUCES = "produces"
    REGISTERS = "registers"
    REQUIRES = "requires"
    REPLACES = "replaces"
    RERANKS_WITH = "reranks_with"
    RUNS_IN = "runs_in"
    RUNS_ON = "runs_on"
    SAME_AS = "same_as"
    SIMILAR_TO = "similar_to"
    SUPPORTS = "supports"
    USES = "uses"
    WRAPS = "wraps"


class SourceType(StrEnum):
    """Classification of knowledge sources."""

    URL_LIST = "url_list"
    FILE_GLOB = "file_glob"
    AUTHENTICATED_WEB = "authenticated_web"
    INLINE = "inline"


# -- Helpers -----------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_LEAD_TRAIL_RE = re.compile(r"^[^\w\s]+|[^\w\s]+$")
_ARTICLES_RE = re.compile(r"^(the|a|an)(\s+|$)")


def _uuid_hex() -> str:
    """Generate a uuid4 hex string (32 alphanumeric characters)."""
    return uuid4().hex


def _canonicalize(name: str) -> str:
    """Return lowercase, whitespace-collapsed, article/punct-stripped form of *name*."""
    s = name.lower()
    s = _WHITESPACE_RE.sub(" ", s).strip()
    s = _PUNCT_LEAD_TRAIL_RE.sub("", s).strip()
    return _ARTICLES_RE.sub("", s).strip()


# -- Models ------------------------------------------------------------------


class KnowledgeSource(BaseModel):
    """A registered knowledge source — where content comes from."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_uuid_hex)
    name: str
    source_type: SourceType
    fetch_method: str = ""
    enrich: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    scope: str = "global"
    enabled: bool = True
    priority: int = 0
    last_refreshed_at: str | None = None
    last_checked_at: str | None = None
    last_error: str | None = None
    created_at: str
    updated_at: str


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
    chunk_id: str | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)

    @computed_field
    @property
    def canonical_name(self) -> str:
        """Derived canonical form: lowercase, whitespace-collapsed, article/punct-stripped."""
        return _canonicalize(self.name)


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


class PageStatus(StrEnum):
    """Status of a SourcePage in the crawl/approval lifecycle."""

    DISCOVERED = "discovered"
    APPROVED = "approved"
    REJECTED = "rejected"
    INGESTED = "ingested"
    STALE = "stale"


class SourcePage(BaseModel):
    """A page belonging to an authenticated-web knowledge source."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_uuid_hex)
    source_id: str
    url: str
    status: PageStatus
    extraction_hash: str | None = None
    last_extracted: str | None = None


class Document(BaseModel):
    """A text document stored in the knowledge graph."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_uuid_hex)
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    scope: str = "global"
    source_id: str | None = None
