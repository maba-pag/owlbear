"""OwlBear project file model."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class OwlbearProjectFile(BaseModel):
    """Pydantic model for owlbear-project.json (schema version 1).

    Validates and parses the project metadata file written by the setup script.
    Extra fields are preserved to allow forward-compatible extensions.
    """

    model_config = ConfigDict(extra="allow")

    schema_version: Literal[1]
    name: str = Field(min_length=1, max_length=100)
    type: Literal["bare", "python-uv", "python-pip", "node"]
    owlbear_path: str = Field(min_length=1)
    created_at: AwareDatetime
