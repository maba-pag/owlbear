"""Tests for owlbear.planning.extractor — LLM project definition extraction."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models
import pytest

from owlbear.planning.extractor import EXTRACTION_PROMPT, ProjectDefinitionExtractor
from owlbear.planning.models import ProjectDefinition, Requirement

# Block real LLM calls — TestModel and FunctionModel are exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_definition() -> ProjectDefinition:
    """Build a sample ProjectDefinition with all required fields populated."""
    return ProjectDefinition(
        name="OwlBear",
        description="An AI development system",
        goals=["Autonomous coding", "Full build pipeline"],
        requirements=[
            Requirement(
                description="Must run locally",
                kind="functional",
                priority="needed",
            ),
        ],
        acceptance_criteria=["Tests pass", "Ruff clean"],
        tech_stack=["Python 3.12", "PydanticAI"],
        risks=["LLM latency"],
        open_questions=["Voice I/O timeline?"],
    )


def _mock_agent_run(output: ProjectDefinition) -> AsyncMock:
    """Build an AsyncMock for Agent.run() returning the given ProjectDefinition."""
    mock_result = MagicMock()
    mock_result.output = output
    return AsyncMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# EXTRACTION_PROMPT
# ---------------------------------------------------------------------------


class TestExtractionPrompt:
    """EXTRACTION_PROMPT constant exists and references key fields."""

    def test_prompt_is_nonempty_string(self) -> None:
        assert isinstance(EXTRACTION_PROMPT, str)
        assert len(EXTRACTION_PROMPT) > 0

    def test_prompt_references_json(self) -> None:
        assert "json" in EXTRACTION_PROMPT.lower()

    def test_prompt_references_project_fields(self) -> None:
        lower = EXTRACTION_PROMPT.lower()
        assert "name" in lower
        assert "goals" in lower
        assert "requirements" in lower


# ---------------------------------------------------------------------------
# extract() — happy path
# ---------------------------------------------------------------------------


class TestExtractHappyPath:
    """extract() returns a valid ProjectDefinition with all fields populated."""

    def test_returns_project_definition(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("We want to build an AI system..."))

        assert isinstance(result, ProjectDefinition)

    def test_required_fields_populated(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("We want to build an AI system..."))

        assert result.name == "OwlBear"
        assert result.description == "An AI development system"
        assert len(result.goals) == 2
        assert len(result.requirements) == 1
        assert len(result.acceptance_criteria) == 2

    def test_optional_fields_populated(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("We want to build an AI system..."))

        assert result.tech_stack == ["Python 3.12", "PydanticAI"]
        assert result.risks == ["LLM latency"]
        assert result.open_questions == ["Voice I/O timeline?"]

    def test_requirements_are_requirement_instances(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        sample = _sample_definition()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("We want to build an AI system..."))

        for req in result.requirements:
            assert isinstance(req, Requirement)


# ---------------------------------------------------------------------------
# extract() — empty input
# ---------------------------------------------------------------------------


class TestExtractEmptyInput:
    """Empty/whitespace text returns default ProjectDefinition immediately."""

    def test_empty_string(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        extractor._agent.run = _mock_agent_run(_sample_definition())

        result = asyncio.run(extractor.extract(""))

        assert result.name == ""
        assert result.description == ""
        assert result.goals == []
        assert result.requirements == []
        assert result.acceptance_criteria == []
        extractor._agent.run.assert_not_called()

    def test_whitespace_only(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        extractor._agent.run = _mock_agent_run(_sample_definition())

        result = asyncio.run(extractor.extract("   \n\t  "))

        assert result.name == ""
        assert result.goals == []
        extractor._agent.run.assert_not_called()


# ---------------------------------------------------------------------------
# extract() — LLM error
# ---------------------------------------------------------------------------


class TestExtractLLMError:
    """LLM failure returns default ProjectDefinition, no exception propagated."""

    def test_error_returns_default(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        extractor._agent.run = AsyncMock(side_effect=RuntimeError("LLM is down"))

        result = asyncio.run(extractor.extract("some meaningful text"))

        assert isinstance(result, ProjectDefinition)
        assert result.name == ""
        assert result.goals == []

    def test_error_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        extractor._agent.run = AsyncMock(side_effect=RuntimeError("LLM is down"))

        with caplog.at_level(logging.WARNING):
            asyncio.run(extractor.extract("some meaningful text"))

        assert any("extract" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Model override
# ---------------------------------------------------------------------------


class TestModelOverride:
    """ProjectDefinitionExtractor accepts model string and TestModel object."""

    def test_accepts_model_string(self) -> None:
        extractor = ProjectDefinitionExtractor(model="test")
        assert extractor is not None

    def test_accepts_model_object(self) -> None:
        from pydantic_ai.models.test import TestModel

        extractor = ProjectDefinitionExtractor(model=TestModel())
        assert extractor is not None
