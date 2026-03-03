"""Tests for owlbear.memory.knowledge.evaluator — LLM-based relevance scoring."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models
import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.evaluator import (
    EVALUATION_PROMPT,
    EvaluationResult,
    SourceEvaluator,
)

# Block real LLM calls — TestModel and FunctionModel are exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_result(
    *,
    relevance_score: float = 0.85,
    tags: list[str] | None = None,
    summary: str = "A useful Python article on async patterns.",
    worth_ingesting: bool = True,
) -> EvaluationResult:
    """Build a sample EvaluationResult for tests."""
    return EvaluationResult(
        relevance_score=relevance_score,
        tags=tags or ["python", "async"],
        summary=summary,
        worth_ingesting=worth_ingesting,
    )


def _mock_agent_run(output: EvaluationResult) -> AsyncMock:
    """Build an AsyncMock for Agent.run() returning the given EvaluationResult."""
    mock_result = MagicMock()
    mock_result.output = output
    return AsyncMock(return_value=mock_result)


SAMPLE_PROJECT_CONTEXT = {
    "name": "OwlBear",
    "description": "An always-on AI development system.",
    "goals": ["Autonomous coding", "Knowledge management"],
}


# ---------------------------------------------------------------------------
# EvaluationResult model
# ---------------------------------------------------------------------------


class TestEvaluationResult:
    """EvaluationResult is a frozen Pydantic model with score, tags, summary, worth_ingesting."""

    def test_default_values(self) -> None:
        result = EvaluationResult(
            relevance_score=0.7,
            tags=["test"],
            summary="A test summary.",
            worth_ingesting=True,
        )
        assert result.relevance_score == 0.7
        assert result.tags == ["test"]
        assert result.summary == "A test summary."
        assert result.worth_ingesting is True

    def test_frozen(self) -> None:
        result = _sample_result()
        with pytest.raises(ValidationError):
            result.relevance_score = 0.0  # type: ignore[misc]

    def test_score_bounds_low(self) -> None:
        """Score of 0.0 is valid."""
        result = EvaluationResult(
            relevance_score=0.0,
            tags=[],
            summary="Not relevant.",
            worth_ingesting=False,
        )
        assert result.relevance_score == 0.0

    def test_score_bounds_high(self) -> None:
        """Score of 1.0 is valid."""
        result = EvaluationResult(
            relevance_score=1.0,
            tags=["perfect"],
            summary="Perfectly relevant.",
            worth_ingesting=True,
        )
        assert result.relevance_score == 1.0

    def test_score_below_zero_rejected(self) -> None:
        """Score below 0 is rejected by validation."""
        with pytest.raises(ValidationError):
            EvaluationResult(
                relevance_score=-0.1,
                tags=[],
                summary="Invalid.",
                worth_ingesting=False,
            )

    def test_score_above_one_rejected(self) -> None:
        """Score above 1 is rejected by validation."""
        with pytest.raises(ValidationError):
            EvaluationResult(
                relevance_score=1.1,
                tags=[],
                summary="Invalid.",
                worth_ingesting=False,
            )


# ---------------------------------------------------------------------------
# EVALUATION_PROMPT
# ---------------------------------------------------------------------------


class TestEvaluationPrompt:
    """EVALUATION_PROMPT constant exists and references evaluation criteria."""

    def test_prompt_is_nonempty_string(self) -> None:
        assert isinstance(EVALUATION_PROMPT, str)
        assert len(EVALUATION_PROMPT) > 0

    def test_prompt_mentions_relevance(self) -> None:
        assert "relevance" in EVALUATION_PROMPT.lower()

    def test_prompt_mentions_score(self) -> None:
        assert "score" in EVALUATION_PROMPT.lower()


# ---------------------------------------------------------------------------
# evaluate() — happy path with project context
# ---------------------------------------------------------------------------


class TestEvaluateWithProjectContext:
    """evaluate() with project_context returns scored EvaluationResult."""

    def test_returns_evaluation_result(self) -> None:
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result()
        evaluator._agent.run = _mock_agent_run(sample)

        result = asyncio.run(evaluator.evaluate("Some content here", SAMPLE_PROJECT_CONTEXT))

        assert isinstance(result, EvaluationResult)
        assert result.relevance_score == 0.85

    def test_prompt_includes_content(self) -> None:
        """The prompt passed to agent.run() includes the content excerpt."""
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result()
        evaluator._agent.run = _mock_agent_run(sample)

        asyncio.run(evaluator.evaluate("Python async patterns guide", SAMPLE_PROJECT_CONTEXT))

        call_args = evaluator._agent.run.call_args
        prompt_text = call_args[0][0]
        assert "Python async patterns guide" in prompt_text

    def test_prompt_includes_project_name(self) -> None:
        """The prompt includes project name from context."""
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result()
        evaluator._agent.run = _mock_agent_run(sample)

        asyncio.run(evaluator.evaluate("Some content", SAMPLE_PROJECT_CONTEXT))

        call_args = evaluator._agent.run.call_args
        prompt_text = call_args[0][0]
        assert "OwlBear" in prompt_text

    def test_prompt_includes_project_description(self) -> None:
        """The prompt includes project description from context."""
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result()
        evaluator._agent.run = _mock_agent_run(sample)

        asyncio.run(evaluator.evaluate("Some content", SAMPLE_PROJECT_CONTEXT))

        call_args = evaluator._agent.run.call_args
        prompt_text = call_args[0][0]
        assert "always-on AI development system" in prompt_text

    def test_prompt_includes_project_goals(self) -> None:
        """The prompt includes project goals from context."""
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result()
        evaluator._agent.run = _mock_agent_run(sample)

        asyncio.run(evaluator.evaluate("Some content", SAMPLE_PROJECT_CONTEXT))

        call_args = evaluator._agent.run.call_args
        prompt_text = call_args[0][0]
        assert "Autonomous coding" in prompt_text

    def test_tags_propagated(self) -> None:
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result(tags=["knowledge-graph", "retrieval"])
        evaluator._agent.run = _mock_agent_run(sample)

        result = asyncio.run(evaluator.evaluate("Graph retrieval", SAMPLE_PROJECT_CONTEXT))

        assert result.tags == ["knowledge-graph", "retrieval"]

    def test_summary_propagated(self) -> None:
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result(summary="Great article on graphs.")
        evaluator._agent.run = _mock_agent_run(sample)

        result = asyncio.run(evaluator.evaluate("Graph article", SAMPLE_PROJECT_CONTEXT))

        assert result.summary == "Great article on graphs."

    def test_worth_ingesting_propagated(self) -> None:
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result(worth_ingesting=False)
        evaluator._agent.run = _mock_agent_run(sample)

        result = asyncio.run(evaluator.evaluate("Low quality", SAMPLE_PROJECT_CONTEXT))

        assert result.worth_ingesting is False


# ---------------------------------------------------------------------------
# evaluate() — content truncation
# ---------------------------------------------------------------------------


class TestContentTruncation:
    """Content is truncated to first 2000 characters for the prompt."""

    def test_long_content_truncated(self) -> None:
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result()
        evaluator._agent.run = _mock_agent_run(sample)

        long_content = "x" * 5000
        asyncio.run(evaluator.evaluate(long_content, SAMPLE_PROJECT_CONTEXT))

        call_args = evaluator._agent.run.call_args
        prompt_text = call_args[0][0]
        # The content portion should be at most 2000 chars
        # (prompt may contain project context too, but content excerpt is truncated)
        assert "x" * 2000 in prompt_text
        assert "x" * 2001 not in prompt_text

    def test_short_content_not_truncated(self) -> None:
        evaluator = SourceEvaluator(model="test")
        sample = _sample_result()
        evaluator._agent.run = _mock_agent_run(sample)

        short_content = "Short content here"
        asyncio.run(evaluator.evaluate(short_content, SAMPLE_PROJECT_CONTEXT))

        call_args = evaluator._agent.run.call_args
        prompt_text = call_args[0][0]
        assert "Short content here" in prompt_text


# ---------------------------------------------------------------------------
# evaluate() — no project context (graceful fallback)
# ---------------------------------------------------------------------------


class TestEvaluateWithoutProjectContext:
    """evaluate() without project context returns neutral score 0.5."""

    def test_none_context_returns_neutral_score(self) -> None:
        evaluator = SourceEvaluator(model="test")

        result = asyncio.run(evaluator.evaluate("Some content", project_context=None))

        assert result.relevance_score == 0.5

    def test_none_context_returns_neutral_tags(self) -> None:
        evaluator = SourceEvaluator(model="test")

        result = asyncio.run(evaluator.evaluate("Some content", project_context=None))

        assert result.tags == []

    def test_none_context_returns_summary(self) -> None:
        evaluator = SourceEvaluator(model="test")

        result = asyncio.run(evaluator.evaluate("Some content", project_context=None))

        assert isinstance(result.summary, str)
        assert len(result.summary) > 0

    def test_none_context_worth_ingesting_true(self) -> None:
        """Without project context, worth_ingesting defaults to True (neutral)."""
        evaluator = SourceEvaluator(model="test")

        result = asyncio.run(evaluator.evaluate("Some content", project_context=None))

        assert result.worth_ingesting is True

    def test_no_llm_call_when_no_context(self) -> None:
        """When project_context is None, the agent should NOT be called."""
        evaluator = SourceEvaluator(model="test")
        evaluator._agent.run = AsyncMock(side_effect=AssertionError("Should not be called"))

        # This should NOT raise — the agent.run mock should never be invoked
        result = asyncio.run(evaluator.evaluate("Some content", project_context=None))

        assert result.relevance_score == 0.5
        evaluator._agent.run.assert_not_called()


# ---------------------------------------------------------------------------
# evaluate() — LLM failure fallback
# ---------------------------------------------------------------------------


class TestEvaluateLlmFailure:
    """evaluate() gracefully handles LLM failures."""

    def test_llm_exception_returns_neutral_result(self) -> None:
        evaluator = SourceEvaluator(model="test")
        evaluator._agent.run = AsyncMock(side_effect=RuntimeError("LLM down"))

        result = asyncio.run(evaluator.evaluate("Some content", SAMPLE_PROJECT_CONTEXT))

        assert isinstance(result, EvaluationResult)
        assert result.relevance_score == 0.5

    def test_llm_exception_returns_empty_tags(self) -> None:
        evaluator = SourceEvaluator(model="test")
        evaluator._agent.run = AsyncMock(side_effect=RuntimeError("LLM down"))

        result = asyncio.run(evaluator.evaluate("Some content", SAMPLE_PROJECT_CONTEXT))

        assert result.tags == []

    def test_llm_exception_worth_ingesting_false(self) -> None:
        """On LLM failure, worth_ingesting should be False (conservative)."""
        evaluator = SourceEvaluator(model="test")
        evaluator._agent.run = AsyncMock(side_effect=RuntimeError("LLM down"))

        result = asyncio.run(evaluator.evaluate("Some content", SAMPLE_PROJECT_CONTEXT))

        assert result.worth_ingesting is False


# ---------------------------------------------------------------------------
# evaluate() — empty/whitespace content
# ---------------------------------------------------------------------------


class TestEvaluateEmptyContent:
    """evaluate() handles empty or whitespace-only content."""

    def test_empty_string_returns_neutral(self) -> None:
        evaluator = SourceEvaluator(model="test")

        result = asyncio.run(evaluator.evaluate("", SAMPLE_PROJECT_CONTEXT))

        assert result.relevance_score == 0.0
        assert result.worth_ingesting is False

    def test_whitespace_only_returns_neutral(self) -> None:
        evaluator = SourceEvaluator(model="test")

        result = asyncio.run(evaluator.evaluate("   \n\t  ", SAMPLE_PROJECT_CONTEXT))

        assert result.relevance_score == 0.0
        assert result.worth_ingesting is False
