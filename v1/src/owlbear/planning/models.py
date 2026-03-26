"""Pydantic models for project definition and planning.

``ProjectDefinition`` captures the structured output of the project-scoping
workflow: name, goals, requirements, acceptance criteria, and optional
metadata (tech stack, risks, open questions).

``Requirement`` is a frozen sub-model representing a single functional or
non-functional requirement with a priority level.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Requirement(BaseModel):
    """A single project requirement — functional or non-functional."""

    model_config = ConfigDict(frozen=True)

    description: str
    kind: Literal["functional", "non-functional"]
    priority: str = "important"


class ProjectDefinition(BaseModel):
    """Structured project definition produced by the planning workflow.

    Contains five required fields that capture the core project scope,
    plus three optional fields that default to empty lists for incremental
    refinement.
    """

    model_config = ConfigDict(frozen=True)

    # Required fields
    name: str
    description: str
    goals: list[str]
    requirements: list[Requirement]
    acceptance_criteria: list[str]

    # Optional fields — default to empty lists
    tech_stack: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
