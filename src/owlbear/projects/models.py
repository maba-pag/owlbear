"""Pydantic model for an OwlBear project.

A ``Project`` represents a single workspace that OwlBear manages.  The ``id``
field is auto-derived from the human-readable ``name`` via slugification.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — Pydantic needs Path at runtime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _slugify(name: str) -> str:
    """Convert a human-readable name into a URL-safe slug.

    Lowercases, replaces whitespace runs with a single hyphen, and strips
    non-alphanumeric / non-hyphen characters.
    """
    slug = name.lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


class Project(BaseModel):
    """A single OwlBear-managed project workspace.

    Fields
    ------
    id : str
        Auto-derived slug from *name* (read-only).
    name : str
        Human-readable project name.
    workspace_path : Path
        Absolute path to the project's workspace directory.
    created_at : datetime
        When the project was first created (defaults to now, UTC).
    last_active : datetime
        When the project was last active (defaults to now, UTC).
    status : ``'active'`` | ``'archived'``
        Current lifecycle status (defaults to ``'active'``).
    """

    model_config = ConfigDict(frozen=True)

    id: str = ""
    name: str
    workspace_path: Path
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    last_active: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    status: Literal["active", "archived"] = "active"

    @model_validator(mode="after")
    def _derive_id(self) -> Project:
        """Set ``id`` from the slugified ``name``."""
        if not self.id:
            object.__setattr__(self, "id", _slugify(self.name))
        return self
