"""Tests for project definition markdown generator."""

from __future__ import annotations

import pytest

from owlbear.planning.markdown import project_definition_to_markdown
from owlbear.planning.models import ProjectDefinition, Requirement

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def full_definition() -> ProjectDefinition:
    """A ProjectDefinition with all fields populated."""
    return ProjectDefinition(
        name="OwlBear",
        description="An always-on AI development system.",
        goals=["Automate dev pipeline", "Laptop-resident"],
        requirements=[
            Requirement(
                description="Must parse user intent",
                kind="functional",
                priority="needed",
            ),
            Requirement(
                description="Must run offline",
                kind="non-functional",
                priority="important",
            ),
            Requirement(
                description="Must support Slack input",
                kind="functional",
                priority="important",
            ),
        ],
        acceptance_criteria=["CLI starts daemon", "Tests pass at 90% coverage"],
        tech_stack=["Python 3.12", "PydanticAI"],
        risks=["LLM latency", "Token cost"],
        open_questions=["Voice I/O scope?"],
    )


@pytest.fixture
def minimal_definition() -> ProjectDefinition:
    """A ProjectDefinition with only required fields (optionals empty)."""
    return ProjectDefinition(
        name="MinimalProject",
        description="A bare-bones project.",
        goals=["Ship something"],
        requirements=[
            Requirement(
                description="Basic feature",
                kind="functional",
            ),
        ],
        acceptance_criteria=["It works"],
    )


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


class TestReturnType:
    """project_definition_to_markdown returns a string."""

    def test_returns_str(self, full_definition: ProjectDefinition) -> None:
        result = project_definition_to_markdown(full_definition)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# H1 — project name
# ---------------------------------------------------------------------------


class TestProjectName:
    """Output contains h1 with the project name."""

    def test_h1_with_project_name(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "# OwlBear\n" in md

    def test_h1_is_first_line(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert md.startswith("# OwlBear\n")


# ---------------------------------------------------------------------------
# Description
# ---------------------------------------------------------------------------


class TestDescription:
    """Output contains a description section."""

    def test_description_section(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "## Description\n" in md
        assert "An always-on AI development system." in md


# ---------------------------------------------------------------------------
# Goals — bullet list
# ---------------------------------------------------------------------------


class TestGoals:
    """Goals rendered as a markdown bullet list."""

    def test_goals_header(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "## Goals\n" in md

    def test_goals_as_bullets(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "- Automate dev pipeline\n" in md
        assert "- Laptop-resident\n" in md


# ---------------------------------------------------------------------------
# Requirements — grouped by kind
# ---------------------------------------------------------------------------


class TestRequirements:
    """Requirements grouped by kind with sub-headers."""

    def test_requirements_header(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "## Requirements\n" in md

    def test_functional_subheader(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "### Functional\n" in md

    def test_non_functional_subheader(
        self, full_definition: ProjectDefinition
    ) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "### Non-Functional\n" in md

    def test_functional_items_listed(
        self, full_definition: ProjectDefinition
    ) -> None:
        md = project_definition_to_markdown(full_definition)
        # "Must parse user intent" has priority "needed" (non-default) → shown
        assert "- Must parse user intent (priority: needed)" in md
        # "Must support Slack input" has priority "important" (default) → hidden
        assert "- Must support Slack input\n" in md

    def test_non_functional_items_listed(
        self, full_definition: ProjectDefinition
    ) -> None:
        md = project_definition_to_markdown(full_definition)
        # priority "important" is default → not shown
        assert "- Must run offline\n" in md

    def test_priority_omitted_when_default(
        self, full_definition: ProjectDefinition
    ) -> None:
        md = project_definition_to_markdown(full_definition)
        # "Must run offline" is priority "important" → no annotation
        assert "Must run offline (priority:" not in md

    def test_priority_shown_when_non_default(
        self, full_definition: ProjectDefinition
    ) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "(priority: needed)" in md

    def test_only_functional_when_no_non_functional(self) -> None:
        defn = ProjectDefinition(
            name="X",
            description="D",
            goals=["G"],
            requirements=[
                Requirement(description="F1", kind="functional"),
            ],
            acceptance_criteria=["AC"],
        )
        md = project_definition_to_markdown(defn)
        assert "### Functional\n" in md
        assert "### Non-Functional\n" not in md


# ---------------------------------------------------------------------------
# Acceptance criteria — checklist
# ---------------------------------------------------------------------------


class TestAcceptanceCriteria:
    """Acceptance criteria rendered as a markdown checklist."""

    def test_ac_header(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "## Acceptance Criteria\n" in md

    def test_ac_as_checklist(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "- [ ] CLI starts daemon\n" in md
        assert "- [ ] Tests pass at 90% coverage\n" in md


# ---------------------------------------------------------------------------
# Optional sections — omitted when empty
# ---------------------------------------------------------------------------


class TestOptionalSectionsEmpty:
    """Empty optional sections are omitted entirely."""

    def test_no_tech_stack_when_empty(
        self, minimal_definition: ProjectDefinition
    ) -> None:
        md = project_definition_to_markdown(minimal_definition)
        assert "## Tech Stack" not in md

    def test_no_risks_when_empty(
        self, minimal_definition: ProjectDefinition
    ) -> None:
        md = project_definition_to_markdown(minimal_definition)
        assert "## Risks" not in md

    def test_no_open_questions_when_empty(
        self, minimal_definition: ProjectDefinition
    ) -> None:
        md = project_definition_to_markdown(minimal_definition)
        assert "## Open Questions" not in md


# ---------------------------------------------------------------------------
# Optional sections — present when populated
# ---------------------------------------------------------------------------


class TestOptionalSectionsPopulated:
    """Non-empty optional sections appear in the output."""

    def test_tech_stack_present(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "## Tech Stack\n" in md
        assert "- Python 3.12\n" in md
        assert "- PydanticAI\n" in md

    def test_risks_present(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "## Risks\n" in md
        assert "- LLM latency\n" in md
        assert "- Token cost\n" in md

    def test_open_questions_present(self, full_definition: ProjectDefinition) -> None:
        md = project_definition_to_markdown(full_definition)
        assert "## Open Questions\n" in md
        assert "- Voice I/O scope?\n" in md
