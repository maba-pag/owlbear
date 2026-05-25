"""Shared boundary foundations for the knowledge module protocol surface.

This file contains ONLY types used by two or more modules:
  - BoundaryModel base class (frozen, extra=forbid)
  - JsonValue recursive type (JSON-safe value constraint)
  - Metadata type alias
  - canonicalize_name helper (entity identity normalisation)

Module-specific enums and models live in their respective module files.
"""

from __future__ import annotations

import re
import unicodedata

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
      - Extra fields rejected (typos and drift caught at construction).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Canonical name helper
# ---------------------------------------------------------------------------

_WHITESPACE_RUN = re.compile(r"\s+")


def canonicalize_name(raw: str) -> str:
    """Normalise an entity name to its canonical form.

    Steps:
      1. Unicode NFC normalisation.
      2. Lowercase.
      3. Collapse whitespace runs to single space.
      4. Strip leading/trailing whitespace.

    This function defines entity identity (together with entity_kind and
    scope). Two names that canonicalize to the same string refer to the
    same entity row.
    """
    nfc = unicodedata.normalize("NFC", raw)
    lower = nfc.lower()
    collapsed = _WHITESPACE_RUN.sub(" ", lower)
    return collapsed.strip()
