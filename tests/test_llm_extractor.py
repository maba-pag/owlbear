"""RED-phase tests for LLMExtractor class (task #698 / #689).

Covers refined AC from #698:
  AC2: LLMExtractor satisfies async StructuredExtractor protocol
       (isinstance() check + inspect.iscoroutinefunction() on extract)
  AC3: PydanticAI Agent instantiated with model string and output_type=ExtractionResult
  AC4: LLM failure returns empty ExtractionResult — no exception raised to caller
  AC5: System prompt covers all 6 EntityType and all 7 RelationType enum values

All tests FAIL (RED) — owlbear_knowledge.llm_extractor does not yet exist.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.llm_extractor import LLMExtractor  # RED: module does not exist yet
from owlbear_knowledge.models import EntityType, RelationType
from owlbear_knowledge.protocol import StructuredExtractor


class TestFromAC_LLMExtractor:
    """AC2-AC5: LLMExtractor protocol compliance, Agent wiring, degradation, and prompt coverage."""

    # -------------------------------------------------------------------------
    # AC2: async StructuredExtractor protocol satisfaction
    # -------------------------------------------------------------------------

    def test_llm_extractor_satisfies_structured_extractor_isinstance(self) -> None:
        """LLMExtractor instance passes isinstance(obj, StructuredExtractor)."""
        with patch("pydantic_ai.Agent"):
            extractor = LLMExtractor("openai:gpt-4o")
        assert isinstance(extractor, StructuredExtractor)

    def test_llm_extractor_extract_is_coroutine_function(self) -> None:
        """LLMExtractor.extract() is declared as an async coroutine function."""
        assert inspect.iscoroutinefunction(LLMExtractor.extract), (
            "LLMExtractor.extract() is not async — must be declared 'async def extract'"
        )

    def test_llm_extractor_extract_is_not_plain_sync(self) -> None:
        """LLMExtractor.extract() is not a plain synchronous function."""
        is_plain_sync = inspect.isfunction(LLMExtractor.extract) and not inspect.iscoroutinefunction(
            LLMExtractor.extract
        )
        assert not is_plain_sync, "LLMExtractor.extract() is a plain sync function — must be declared async"

    # -------------------------------------------------------------------------
    # AC3: PydanticAI Agent instantiated with model + output_type=ExtractionResult
    # -------------------------------------------------------------------------

    def test_pydantic_agent_instantiated_with_model_string(self) -> None:
        """pydantic_ai.Agent is called with the model string passed to LLMExtractor.__init__."""
        with patch("pydantic_ai.Agent") as mock_agent_cls:
            LLMExtractor("openai:gpt-4o-mini")
        mock_agent_cls.assert_called_once()
        positional_args = mock_agent_cls.call_args[0]
        assert positional_args[0] == "openai:gpt-4o-mini", (
            f"Agent not called with expected model string; got: {positional_args}"
        )

    def test_pydantic_agent_instantiated_with_output_type_extraction_result(self) -> None:
        """pydantic_ai.Agent is called with output_type=ExtractionResult."""
        with patch("pydantic_ai.Agent") as mock_agent_cls:
            LLMExtractor("openai:gpt-4o")
        kwargs = mock_agent_cls.call_args[1]
        assert kwargs.get("output_type") is ExtractionResult, (
            f"Agent not called with output_type=ExtractionResult; got output_type={kwargs.get('output_type')}"
        )

    @pytest.mark.asyncio
    async def test_extract_awaits_agent_run_with_prompt(self) -> None:
        """extract(prompt) awaits agent.run(prompt) on the internal Agent instance."""
        mock_run_result = MagicMock()
        mock_run_result.output = ExtractionResult()
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_run_result)
        with patch("pydantic_ai.Agent", return_value=mock_agent):
            extractor = LLMExtractor("openai:gpt-4o")
        prompt = "extract entities from this text sentinel_abc123"
        await extractor.extract(prompt)
        mock_agent.run.assert_awaited_once_with(prompt)

    @pytest.mark.asyncio
    async def test_extract_returns_agent_run_output_attribute(self) -> None:
        """extract() returns the .output attribute of the result from agent.run()."""
        expected = ExtractionResult()
        mock_run_result = MagicMock()
        mock_run_result.output = expected
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_run_result)
        with patch("pydantic_ai.Agent", return_value=mock_agent):
            extractor = LLMExtractor("openai:gpt-4o")
        result = await extractor.extract("any prompt")
        assert result is expected

    # -------------------------------------------------------------------------
    # AC4: Graceful degradation on LLM failure
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_llm_runtime_error_returns_empty_extraction_result(self) -> None:
        """RuntimeError from agent.run() is caught — returns empty ExtractionResult, not raised."""
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("LLM call failed sentinel"))
        with patch("pydantic_ai.Agent", return_value=mock_agent):
            extractor = LLMExtractor("openai:gpt-4o")
        result = await extractor.extract("some prompt")
        assert isinstance(result, ExtractionResult)
        assert result.entities == []
        assert result.edges == []

    @pytest.mark.asyncio
    async def test_llm_failure_does_not_propagate_exception(self) -> None:
        """Any exception from agent.run() is swallowed — not re-raised to the caller."""
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=Exception("unexpected LLM error sentinel"))
        with patch("pydantic_ai.Agent", return_value=mock_agent):
            extractor = LLMExtractor("openai:gpt-4o")
        try:
            result = await extractor.extract("prompt that triggers exception path")
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"LLM failure propagated unexpectedly: {exc}")
        assert isinstance(result, ExtractionResult)

    @pytest.mark.asyncio
    async def test_llm_value_error_returns_empty_not_raises(self) -> None:
        """ValueError from agent.run() is also swallowed — returns empty ExtractionResult."""
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=ValueError("bad model response sentinel"))
        with patch("pydantic_ai.Agent", return_value=mock_agent):
            extractor = LLMExtractor("openai:gpt-4o")
        result = await extractor.extract("prompt for value error path")
        assert isinstance(result, ExtractionResult)
        assert result.entities == []

    # -------------------------------------------------------------------------
    # AC5: System prompt covers all enum values
    # -------------------------------------------------------------------------

    def test_system_prompt_contains_all_entity_type_values(self) -> None:
        """System prompt contains all 6 EntityType values: file, function, class_, decision, pattern, concept."""
        with patch("pydantic_ai.Agent") as mock_agent_cls:
            LLMExtractor("openai:gpt-4o")
        kwargs = mock_agent_cls.call_args[1]
        system_prompt = kwargs.get("system_prompt", "")
        assert isinstance(system_prompt, str), "system_prompt kwarg must be a string"
        for entity_type in EntityType:
            assert entity_type.value in system_prompt, (
                f"EntityType.{entity_type.name} value '{entity_type.value}' not found in system prompt"
            )

    def test_system_prompt_contains_all_relation_type_values(self) -> None:
        """System prompt contains all 7 RelationType values including governed_by."""
        with patch("pydantic_ai.Agent") as mock_agent_cls:
            LLMExtractor("openai:gpt-4o")
        kwargs = mock_agent_cls.call_args[1]
        system_prompt = kwargs.get("system_prompt", "")
        assert isinstance(system_prompt, str), "system_prompt kwarg must be a string"
        for relation_type in RelationType:
            assert relation_type.value in system_prompt, (
                f"RelationType.{relation_type.name} value '{relation_type.value}' not found in system prompt"
            )

    def test_system_prompt_contains_governed_by_boundary(self) -> None:
        """Boundary: 'governed_by' is explicitly present — missing from existing EXTRACTION_PROMPT (extractor.py)."""
        with patch("pydantic_ai.Agent") as mock_agent_cls:
            LLMExtractor("openai:gpt-4o")
        kwargs = mock_agent_cls.call_args[1]
        system_prompt = kwargs.get("system_prompt", "")
        assert "governed_by" in system_prompt, (
            "RelationType.GOVERNED_BY ('governed_by') missing from system prompt — "
            "the existing EXTRACTION_PROMPT in extractor.py omits it; LLMExtractor must include it"
        )

    def test_system_prompt_contains_class_underscore_entity_type(self) -> None:
        """Boundary: EntityType.CLASS_ value 'class_' is present — name differs from the string value."""
        with patch("pydantic_ai.Agent") as mock_agent_cls:
            LLMExtractor("openai:gpt-4o")
        kwargs = mock_agent_cls.call_args[1]
        system_prompt = kwargs.get("system_prompt", "")
        assert "class_" in system_prompt, (
            "EntityType.CLASS_ value 'class_' not found in system prompt"
        )
