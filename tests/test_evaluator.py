"""RED-phase tests for SourceEvaluator and EvaluationResult (#138).

Covers:
  - SourceEvaluator instantiation and evaluate() contract (TestFromAC_SourceEvaluator)
  - EvaluationResult model validation and frozen constraint (TestFromAC_EvaluationResult)

All tests fail in RED phase — modules not implemented yet.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear_knowledge.evaluator import EvaluationResult, SourceEvaluator


# ---------------------------------------------------------------------------
# TestFromAC_SourceEvaluator
# ---------------------------------------------------------------------------


class TestFromAC_SourceEvaluator:  # noqa: N801
    """AC: SourceEvaluator instantiation and evaluate() stub contract."""

    def test_instantiates_with_no_args(self) -> None:
        """SourceEvaluator() instantiates without arguments."""
        evaluator = SourceEvaluator()
        assert evaluator is not None

    def test_instantiates_with_model_param(self) -> None:
        """SourceEvaluator(model=...) accepts an optional model parameter."""
        evaluator = SourceEvaluator(model="gpt-4o")
        assert evaluator is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_neutral_fallback_no_llm(self) -> None:
        """evaluate(content='test', project_context=None) returns neutral stub result."""
        evaluator = SourceEvaluator()
        result = await evaluator.evaluate(content="test", project_context=None)
        assert result.relevance_score == 0.5
        assert result.worth_ingesting is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_empty_content_returns_zero_score(self) -> None:
        """evaluate(content='', project_context=None) returns zero relevance, not worth ingesting."""
        evaluator = SourceEvaluator()
        result = await evaluator.evaluate(content="", project_context=None)
        assert result.relevance_score == 0.0
        assert result.worth_ingesting is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_with_project_context_returns_stub_neutral(self) -> None:
        """evaluate(content='test', project_context={'name': 'proj'}) returns stub neutral (no LLM)."""
        evaluator = SourceEvaluator()
        result = await evaluator.evaluate(
            content="test", project_context={"name": "proj"}
        )
        assert result.relevance_score == 0.5
        assert result.worth_ingesting is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_returns_evaluation_result_type(self) -> None:
        """evaluate() always returns an EvaluationResult instance."""
        evaluator = SourceEvaluator()
        result = await evaluator.evaluate(content="hello world", project_context=None)
        assert isinstance(result, EvaluationResult)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_no_llm_call_made(self) -> None:
        """Stub evaluate() does not rely on external LLM (pure schema model default)."""
        # No mocking needed — if LLM were called and credentials missing, this would error.
        evaluator = SourceEvaluator()
        # Should complete without network activity or import of pydantic_ai
        result = await evaluator.evaluate(content="some content", project_context=None)
        assert result is not None


# ---------------------------------------------------------------------------
# TestFromAC_EvaluationResult
# ---------------------------------------------------------------------------


class TestFromAC_EvaluationResult:  # noqa: N801
    """AC: EvaluationResult model validation and frozen constraint."""

    def test_instantiates_with_valid_fields(self) -> None:
        """EvaluationResult validates all fields when all are provided."""
        result = EvaluationResult(
            relevance_score=0.8,
            tags=["science", "research"],
            summary="A relevant article about machine learning",
            worth_ingesting=True,
        )
        assert result.relevance_score == 0.8
        assert result.tags == ["science", "research"]
        assert result.summary == "A relevant article about machine learning"
        assert result.worth_ingesting is True

    def test_default_worth_ingesting_is_false(self) -> None:
        """Default EvaluationResult().worth_ingesting is False."""
        result = EvaluationResult(
            relevance_score=0.5,
            tags=[],
            summary="",
        )
        assert result.worth_ingesting is False

    def test_relevance_score_must_be_float(self) -> None:
        """EvaluationResult validates relevance_score as a numeric (float) field."""
        with pytest.raises(ValidationError):
            EvaluationResult(
                relevance_score="high",  # type: ignore[arg-type]
                tags=[],
                summary="",
            )

    def test_relevance_score_below_zero_is_invalid(self) -> None:
        """relevance_score below 0.0 is rejected (ge=0.0 constraint)."""
        with pytest.raises(ValidationError):
            EvaluationResult(
                relevance_score=-0.1,
                tags=[],
                summary="",
            )

    def test_relevance_score_above_one_is_invalid(self) -> None:
        """relevance_score above 1.0 is rejected (le=1.0 constraint)."""
        with pytest.raises(ValidationError):
            EvaluationResult(
                relevance_score=1.1,
                tags=[],
                summary="",
            )

    def test_relevance_score_boundary_zero_is_valid(self) -> None:
        """relevance_score of exactly 0.0 is valid."""
        result = EvaluationResult(relevance_score=0.0, tags=[], summary="")
        assert result.relevance_score == 0.0

    def test_relevance_score_boundary_one_is_valid(self) -> None:
        """relevance_score of exactly 1.0 is valid."""
        result = EvaluationResult(relevance_score=1.0, tags=[], summary="")
        assert result.relevance_score == 1.0

    def test_tags_is_list_of_str(self) -> None:
        """tags field accepts a list of strings."""
        result = EvaluationResult(
            relevance_score=0.5, tags=["a", "b"], summary="test"
        )
        assert isinstance(result.tags, list)
        assert all(isinstance(t, str) for t in result.tags)

    def test_summary_is_str(self) -> None:
        """summary field accepts a string value."""
        result = EvaluationResult(
            relevance_score=0.5, tags=[], summary="A summary text."
        )
        assert isinstance(result.summary, str)

    def test_worth_ingesting_is_bool(self) -> None:
        """worth_ingesting field is a boolean."""
        result = EvaluationResult(
            relevance_score=0.9, tags=[], summary="", worth_ingesting=True
        )
        assert isinstance(result.worth_ingesting, bool)
        assert result.worth_ingesting is True

    def test_is_frozen_cannot_mutate_relevance_score(self) -> None:
        """EvaluationResult is frozen — mutating relevance_score raises an error."""
        result = EvaluationResult(
            relevance_score=0.5, tags=[], summary="immutable"
        )
        with pytest.raises((TypeError, ValidationError)):
            result.relevance_score = 0.9  # type: ignore[misc]

    def test_is_frozen_cannot_mutate_worth_ingesting(self) -> None:
        """EvaluationResult is frozen — mutating worth_ingesting raises an error."""
        result = EvaluationResult(relevance_score=0.5, tags=[], summary="")
        with pytest.raises((TypeError, ValidationError)):
            result.worth_ingesting = True  # type: ignore[misc]
