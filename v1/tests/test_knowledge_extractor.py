"""Tests for owlbear.memory.knowledge.extractor — LLM entity extraction."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models
import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.extractor import (
    EXTRACTION_PROMPT,
    EntityExtractor,
    ExtractionResult,
)
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType

# Block real LLM calls — TestModel and FunctionModel are exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_result() -> ExtractionResult:
    """Build a sample ExtractionResult with two entities and one edge."""
    e1 = Entity(name="hello", entity_type=EntityType.FUNCTION, description="A greeting function")
    e2 = Entity(name="Greeter", entity_type=EntityType.CLASS_, description="A greeting class")
    edge = Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.DEFINES)
    return ExtractionResult(entities=[e1, e2], edges=[edge])


def _mock_agent_run(output: ExtractionResult) -> AsyncMock:
    """Build an AsyncMock for Agent.run() returning the given ExtractionResult."""
    mock_result = MagicMock()
    mock_result.output = output
    return AsyncMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# ExtractionResult model
# ---------------------------------------------------------------------------


class TestExtractionResult:
    """ExtractionResult is a frozen Pydantic model with entities and edges."""

    def test_default_empty(self) -> None:
        result = ExtractionResult()
        assert result.entities == []
        assert result.edges == []

    def test_frozen(self) -> None:
        result = ExtractionResult()
        with pytest.raises(ValidationError):
            result.entities = []  # type: ignore[misc]

    def test_accepts_entities_and_edges(self) -> None:
        sample = _sample_result()
        assert len(sample.entities) == 2
        assert len(sample.edges) == 1


# ---------------------------------------------------------------------------
# EXTRACTION_PROMPT
# ---------------------------------------------------------------------------


class TestExtractionPrompt:
    """EXTRACTION_PROMPT constant exists and references JSON schema."""

    def test_prompt_is_nonempty_string(self) -> None:
        assert isinstance(EXTRACTION_PROMPT, str)
        assert len(EXTRACTION_PROMPT) > 0

    def test_prompt_references_json(self) -> None:
        assert "json" in EXTRACTION_PROMPT.lower()


# ---------------------------------------------------------------------------
# extract() — happy path
# ---------------------------------------------------------------------------


class TestExtractHappyPath:
    """extract() returns ExtractionResult with entities and edges."""

    def test_returns_extraction_result(self) -> None:
        extractor = EntityExtractor(model="test")
        sample = _sample_result()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("def hello(): pass"))

        assert isinstance(result, ExtractionResult)

    def test_with_metadata_passes_context(self) -> None:
        """When metadata is provided, it is included in the prompt."""
        extractor = EntityExtractor(model="test")
        sample = _sample_result()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("def hello(): pass", metadata={"lang": "python"}))

        assert isinstance(result, ExtractionResult)
        # Verify the agent was called with enriched prompt text
        call_args = extractor._agent.run.call_args
        assert "metadata" in call_args[0][0].lower() or "python" in call_args[0][0]

    def test_entities_are_entity_instances(self) -> None:
        extractor = EntityExtractor(model="test")
        sample = _sample_result()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("def hello(): pass"))

        assert len(result.entities) == 2
        for entity in result.entities:
            assert isinstance(entity, Entity)

    def test_edges_are_edge_instances(self) -> None:
        extractor = EntityExtractor(model="test")
        sample = _sample_result()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("class Foo: pass"))

        assert len(result.edges) == 1
        for edge in result.edges:
            assert isinstance(edge, Edge)

    def test_entity_fields(self) -> None:
        """Returned entities have id, name, entity_type, description, metadata."""
        extractor = EntityExtractor(model="test")
        sample = _sample_result()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("def hello(): pass"))

        entity = result.entities[0]
        assert entity.id  # non-empty uuid hex
        assert entity.name == "hello"
        assert entity.entity_type == EntityType.FUNCTION
        assert entity.description == "A greeting function"
        assert isinstance(entity.metadata, dict)

    def test_edge_fields(self) -> None:
        """Returned edges have source_id, target_id, relation, weight."""
        extractor = EntityExtractor(model="test")
        sample = _sample_result()
        extractor._agent.run = _mock_agent_run(sample)

        result = asyncio.run(extractor.extract("code"))

        edge = result.edges[0]
        assert edge.source_id
        assert edge.target_id
        assert edge.relation == RelationType.DEFINES
        assert edge.weight == 1.0


# ---------------------------------------------------------------------------
# extract() — empty input
# ---------------------------------------------------------------------------


class TestExtractEmptyInput:
    """Empty text returns empty ExtractionResult immediately (no LLM call)."""

    def test_empty_string(self) -> None:
        extractor = EntityExtractor(model="test")
        extractor._agent.run = _mock_agent_run(_sample_result())

        result = asyncio.run(extractor.extract(""))

        assert result.entities == []
        assert result.edges == []
        extractor._agent.run.assert_not_called()

    def test_whitespace_only(self) -> None:
        extractor = EntityExtractor(model="test")
        extractor._agent.run = _mock_agent_run(_sample_result())

        result = asyncio.run(extractor.extract("   \n\t  "))

        assert result.entities == []
        assert result.edges == []
        extractor._agent.run.assert_not_called()


# ---------------------------------------------------------------------------
# extract() — LLM error
# ---------------------------------------------------------------------------


class TestExtractLLMError:
    """LLM failure returns empty ExtractionResult, no exception propagated."""

    def test_error_returns_empty_result(self) -> None:
        extractor = EntityExtractor(model="test")
        extractor._agent.run = AsyncMock(side_effect=RuntimeError("LLM is down"))

        result = asyncio.run(extractor.extract("some meaningful text"))

        assert isinstance(result, ExtractionResult)
        assert result.entities == []
        assert result.edges == []

    def test_error_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        extractor = EntityExtractor(model="test")
        extractor._agent.run = AsyncMock(side_effect=RuntimeError("LLM is down"))

        with caplog.at_level(logging.WARNING):
            asyncio.run(extractor.extract("some meaningful text"))

        assert any("extract" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Custom model override
# ---------------------------------------------------------------------------


class TestCustomModelOverride:
    """EntityExtractor accepts custom model override."""

    def test_accepts_model_string(self) -> None:
        extractor = EntityExtractor(model="test")
        assert extractor is not None

    def test_accepts_model_object(self) -> None:
        from pydantic_ai.models.test import TestModel

        extractor = EntityExtractor(model=TestModel())
        assert extractor is not None
