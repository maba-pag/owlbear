"""Integration tests: mock LLM project definition flow.

Verifies the end-to-end pipeline:
  1. Build a ProjectDefinition with sample data
  2. Pass to ProjectDefinitionExtractor (mock Agent.run) → valid ProjectDefinition
  3. Feed result into project_definition_to_markdown() → validates markdown output

Uses the _mock_agent_run pattern from test_knowledge_extractor.py.
Does NOT test planner agent multi-turn conversation (out of scope).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models

from owlbear.planning.extractor import ProjectDefinitionExtractor
from owlbear.planning.markdown import project_definition_to_markdown
from owlbear.planning.models import ProjectDefinition, Requirement

# Block real LLM calls — TestModel and FunctionModel are exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_definition() -> ProjectDefinition:
    """Build a fully-populated sample ProjectDefinition."""
    return ProjectDefinition(
        name="OwlBear",
        description="An always-on AI development system.",
        goals=["Autonomous coding", "Full build pipeline"],
        requirements=[
            Requirement(
                description="Must run locally",
                kind="functional",
                priority="needed",
            ),
            Requirement(
                description="Sub-second response",
                kind="non-functional",
                priority="important",
            ),
        ],
        acceptance_criteria=["Tests pass", "Ruff clean"],
        tech_stack=["Python 3.12", "PydanticAI"],
        risks=["LLM latency"],
        open_questions=["Voice I/O timeline?"],
    )


def _minimal_definition() -> ProjectDefinition:
    """Build a ProjectDefinition with only required fields (optionals empty)."""
    return ProjectDefinition(
        name="MinimalProject",
        description="A bare-bones project.",
        goals=["Ship something"],
        requirements=[
            Requirement(description="Basic feature", kind="functional"),
        ],
        acceptance_criteria=["It works"],
    )


def _mock_agent_run(output: ProjectDefinition) -> AsyncMock:
    """Build an AsyncMock for Agent.run() returning the given ProjectDefinition."""
    mock_result = MagicMock()
    mock_result.output = output
    return AsyncMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# Extractor integration — mock Agent.run, verify output shape
# ---------------------------------------------------------------------------


class TestExtractorIntegration:
    """Mock extractor returns a valid ProjectDefinition with populated fields."""

    def test_extract_returns_valid_definition(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("We want to build an AI system."))

        assert isinstance(result, ProjectDefinition)

    def test_name_and_description_populated(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("We want to build an AI system."))

        assert result.name == "OwlBear"
        assert result.description == "An always-on AI development system."

    def test_goals_non_empty(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("We want to build an AI system."))

        assert len(result.goals) > 0

    def test_requirements_at_least_one(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("We want to build an AI system."))

        assert len(result.requirements) >= 1
        for req in result.requirements:
            assert isinstance(req, Requirement)


# ---------------------------------------------------------------------------
# Markdown generation — section headers present
# ---------------------------------------------------------------------------


class TestMarkdownSectionHeaders:
    """project_definition_to_markdown() output contains required section headers."""

    def test_contains_goals_header(self) -> None:
        md = project_definition_to_markdown(_sample_definition())
        assert "## Goals\n" in md

    def test_contains_requirements_header(self) -> None:
        md = project_definition_to_markdown(_sample_definition())
        assert "## Requirements\n" in md

    def test_contains_acceptance_criteria_header(self) -> None:
        md = project_definition_to_markdown(_sample_definition())
        assert "## Acceptance Criteria\n" in md

    def test_contains_description_header(self) -> None:
        md = project_definition_to_markdown(_sample_definition())
        assert "## Description\n" in md


# ---------------------------------------------------------------------------
# Markdown generation — optional empty sections omitted
# ---------------------------------------------------------------------------


class TestOptionalSectionsOmitted:
    """Empty optional sections are omitted from markdown output."""

    def test_no_tech_stack_when_empty(self) -> None:
        md = project_definition_to_markdown(_minimal_definition())
        assert "## Tech Stack" not in md

    def test_no_risks_when_empty(self) -> None:
        md = project_definition_to_markdown(_minimal_definition())
        assert "## Risks" not in md

    def test_no_open_questions_when_empty(self) -> None:
        md = project_definition_to_markdown(_minimal_definition())
        assert "## Open Questions" not in md

    def test_populated_optional_sections_present(self) -> None:
        md = project_definition_to_markdown(_sample_definition())
        assert "## Tech Stack\n" in md
        assert "## Risks\n" in md
        assert "## Open Questions\n" in md


# ---------------------------------------------------------------------------
# End-to-end pipeline: mock extractor → markdown → validate
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    """Full pipeline: mock extract → markdown generation → validate output."""

    def test_pipeline_produces_valid_markdown(self) -> None:
        # Step 1: mock extractor returns a ProjectDefinition
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        definition = asyncio.run(extractor.extract("Build an AI dev system."))

        # Step 2: pass to markdown generator
        md = project_definition_to_markdown(definition)

        # Step 3: validate markdown structure
        assert isinstance(md, str)
        assert md.startswith("# OwlBear\n")
        assert "## Goals\n" in md
        assert "## Requirements\n" in md
        assert "## Acceptance Criteria\n" in md
        assert "- Autonomous coding\n" in md
        assert "- [ ] Tests pass\n" in md

    def test_pipeline_with_minimal_definition(self) -> None:
        # Step 1: mock extractor returns a minimal ProjectDefinition
        extractor = ProjectDefinitionExtractor(model="test")
        minimal = _minimal_definition()
        extractor._agent.run = _mock_agent_run(minimal)

        definition = asyncio.run(extractor.extract("Just build something."))

        # Step 2: pass to markdown generator
        md = project_definition_to_markdown(definition)

        # Step 3: validate — required sections present, optional omitted
        assert md.startswith("# MinimalProject\n")
        assert "## Goals\n" in md
        assert "## Requirements\n" in md
        assert "## Acceptance Criteria\n" in md
        assert "## Tech Stack" not in md
        assert "## Risks" not in md
        assert "## Open Questions" not in md

    def test_pipeline_requirements_render_correctly(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        definition = asyncio.run(extractor.extract("Build an AI dev system."))
        md = project_definition_to_markdown(definition)

        # "needed" is non-default → shown; "important" is default → hidden
        assert "Must run locally (priority: needed)" in md
        assert "Sub-second response\n" in md
        assert "Sub-second response (priority:" not in md
