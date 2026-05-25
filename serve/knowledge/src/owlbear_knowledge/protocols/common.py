"""Shared boundary foundations for the knowledge module protocol surface.

This file contains ONLY types used by two or more modules:
  - BoundaryModel base class (frozen, strict, extra=forbid)
  - JsonValue recursive type (JSON-safe value constraint)
  - Metadata type alias
  - EntityType / RelationType vocabularies (shared across Graph, Enrichment, Query)
  - canonicalize_name helper (entity identity normalisation)

Module-specific enums and models live in their respective module files.
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Recursive JSON-safe value type (PEP 695, Python 3.12+)
# ---------------------------------------------------------------------------

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]

Metadata = dict[str, JsonValue]
"""Arbitrary key-value metadata constrained to JSON-serialisable values."""


# ---------------------------------------------------------------------------
# Boundary model base
# ---------------------------------------------------------------------------


class BoundaryModel(BaseModel):
    """Immutable, strict base for all protocol boundary types.

    All boundary types inherit this to guarantee:
      - Frozen (immutable after construction).
      - Strict (no string-to-int coercion; callers supply correct types).
      - Extra fields rejected (typos and drift caught at construction).
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


# ---------------------------------------------------------------------------
# Shared vocabularies (D10 — lean: 12 entity + 13 relation, no SAME_AS)
# ---------------------------------------------------------------------------


class EntityType(StrEnum):
    """Classification of knowledge graph entities."""

    CONCEPT = "concept"
    DOCUMENT = "document"
    EVENT = "event"
    LOCATION = "location"
    METRIC = "metric"
    ORGANIZATION = "organization"
    PERSON = "person"
    PROCESS = "process"
    PRODUCT = "product"
    STANDARD = "standard"
    TECHNOLOGY = "technology"
    TOOL = "tool"


class RelationType(StrEnum):
    """Typed relationships between entities.

    SAME_AS is deliberately excluded — use Graph.add_alias for identity
    merging (CP1, CP18).
    """

    AUTHORED_BY = "authored_by"
    BELONGS_TO = "belongs_to"
    COMPLIES_WITH = "complies_with"
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"
    DERIVED_FROM = "derived_from"
    IMPLEMENTS = "implements"
    MANAGES = "manages"
    MENTIONS = "mentions"
    PRODUCED_BY = "produced_by"
    REFERENCES = "references"
    RELATED_TO = "related_to"
    REQUIRES = "requires"


# ---------------------------------------------------------------------------
# Canonical name helper
# ---------------------------------------------------------------------------

_WHITESPACE_RUN = re.compile(r"\s+")
_TRAILING_PUNCT = re.compile(r"[.,;:!?]+$")


def canonicalize_name(raw: str) -> str:
    """Normalise an entity name to its canonical form.

    Steps:
      1. Unicode NFC normalisation.
      2. Lowercase.
      3. Collapse whitespace runs to single space.
      4. Strip leading/trailing whitespace.
      5. Strip trailing punctuation (.,;:!?).

    This function defines entity identity together with ``EntityType``
    (CP1). Two names that canonicalize to the same string and share the
    same entity_type refer to the same entity row. Graph entities are
    global — scope does not participate in identity.

    Contract (CP1): extraction agents are responsible for upstream name
    cleanup beyond what this normaliser handles (article removal,
    abbreviation expansion). Identity drift across agents is an agent
    bug, not an engine bug.
    """
    nfc = unicodedata.normalize("NFC", raw)
    lower = nfc.lower()
    collapsed = _WHITESPACE_RUN.sub(" ", lower)
    stripped = collapsed.strip()
    return _TRAILING_PUNCT.sub("", stripped)
