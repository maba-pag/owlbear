"""Tests for owlbear.planning.models — ProjectDefinition and Requirement models.

TDD red-phase tests — these will fail on import until the implementation
task (#318) creates src/owlbear/planning/models.py.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear.planning.models import ProjectDefinition, Requirement

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_requirement(
    *,
    description: str = "The system shall accept user input",
    kind: str = "functional",
) -> Requirement:
    """Build a sample Requirement instance."""
    return Requirement(description=description, kind=kind)


def _sample_project_definition(**overrides: object) -> ProjectDefinition:
    """Build a minimal valid ProjectDefinition, with optional overrides."""
    defaults: dict[str, object] = {
        "name": "OwlBear Chat",
        "description": "An AI-powered chat interface for project planning.",
        "goals": ["Enable natural-language project ideation", "Produce structured specs"],
        "requirements": [_sample_requirement()],
        "acceptance_criteria": ["User can describe an idea and receive a project spec"],
    }
    defaults.update(overrides)
    return ProjectDefinition(**defaults)


# ---------------------------------------------------------------------------
# Requirement sub-model
# ---------------------------------------------------------------------------


class TestRequirement:
    """Requirement is a frozen Pydantic model with description and kind."""

    def test_valid_functional(self) -> None:
        req = Requirement(description="Must support login", kind="functional")
        assert req.description == "Must support login"
        assert req.kind == "functional"

    def test_valid_non_functional(self) -> None:
        req = Requirement(description="Latency < 200ms", kind="non-functional")
        assert req.description == "Latency < 200ms"
        assert req.kind == "non-functional"

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValidationError):
            Requirement(description="Some requirement", kind="nice-to-have")

    def test_frozen_assignment_raises(self) -> None:
        req = _sample_requirement()
        with pytest.raises(ValidationError):
            req.description = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ProjectDefinition — required fields
# ---------------------------------------------------------------------------


class TestProjectDefinitionRequired:
    """ProjectDefinition validates all required fields."""

    def test_valid_with_all_required_fields(self) -> None:
        defn = _sample_project_definition()
        assert defn.name == "OwlBear Chat"
        assert defn.description == "An AI-powered chat interface for project planning."
        assert len(defn.goals) == 2
        assert len(defn.requirements) == 1
        assert len(defn.acceptance_criteria) == 1

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProjectDefinition(
                description="desc",
                goals=["g"],
                requirements=[_sample_requirement()],
                acceptance_criteria=["ac"],
            )

    def test_missing_description_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProjectDefinition(
                name="Test",
                goals=["g"],
                requirements=[_sample_requirement()],
                acceptance_criteria=["ac"],
            )

    def test_missing_goals_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProjectDefinition(
                name="Test",
                description="desc",
                requirements=[_sample_requirement()],
                acceptance_criteria=["ac"],
            )

    def test_missing_requirements_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProjectDefinition(
                name="Test",
                description="desc",
                goals=["g"],
                acceptance_criteria=["ac"],
            )

    def test_missing_acceptance_criteria_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProjectDefinition(
                name="Test",
                description="desc",
                goals=["g"],
                requirements=[_sample_requirement()],
            )


# ---------------------------------------------------------------------------
# ProjectDefinition — optional fields default to empty lists
# ---------------------------------------------------------------------------


class TestProjectDefinitionOptionalDefaults:
    """Optional fields default to empty lists when omitted."""

    def test_tech_stack_defaults_empty(self) -> None:
        defn = _sample_project_definition()
        assert defn.tech_stack == []

    def test_risks_defaults_empty(self) -> None:
        defn = _sample_project_definition()
        assert defn.risks == []

    def test_open_questions_defaults_empty(self) -> None:
        defn = _sample_project_definition()
        assert defn.open_questions == []

    def test_optional_fields_accept_values(self) -> None:
        defn = _sample_project_definition(
            tech_stack=["Python", "PydanticAI"],
            risks=["LLM may hallucinate fields"],
            open_questions=["Which LLM model to use?"],
        )
        assert defn.tech_stack == ["Python", "PydanticAI"]
        assert defn.risks == ["LLM may hallucinate fields"]
        assert defn.open_questions == ["Which LLM model to use?"]


# ---------------------------------------------------------------------------
# ProjectDefinition — frozen
# ---------------------------------------------------------------------------


class TestProjectDefinitionFrozen:
    """ProjectDefinition is frozen — attribute assignment raises ValidationError."""

    def test_name_assignment_raises(self) -> None:
        defn = _sample_project_definition()
        with pytest.raises(ValidationError):
            defn.name = "New Name"  # type: ignore[misc]

    def test_goals_assignment_raises(self) -> None:
        defn = _sample_project_definition()
        with pytest.raises(ValidationError):
            defn.goals = ["replaced"]  # type: ignore[misc]

    def test_requirements_assignment_raises(self) -> None:
        defn = _sample_project_definition()
        with pytest.raises(ValidationError):
            defn.requirements = []  # type: ignore[misc]
