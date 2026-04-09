"""Tests for SourceEvaluator — LLM callable injection (#523).

Updated from #138 stub tests to use the new llm_fn-injected constructor.
Covers: constructor w/ llm_fn, evaluate() three-path flow (empty / no-context
/ valid), exception handling, and module-level helpers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from owlbear_knowledge.evaluator import EvaluationResult, SourceEvaluator


# ---------------------------------------------------------------------------
# TestFromAC_SourceEvaluator
# ---------------------------------------------------------------------------


class TestFromAC_SourceEvaluator:  # noqa: N801
    """AC: SourceEvaluator(llm_fn) constructor and evaluate() paths for #523."""

    # -- Constructor --

    def test_constructor_accepts_llm_fn_keyword(self) -> None:
        """SourceEvaluator(llm_fn=<async callable>) instantiates correctly."""
        mock_result = EvaluationResult(relevance_score=0.9, tags=[], summary="ok")
        llm_fn: AsyncMock = AsyncMock(return_value=mock_result)
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        assert evaluator is not None

    # -- evaluate(): empty / whitespace content --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_empty_content_returns_zero_relevance(self) -> None:
        """Empty content returns EvaluationResult(relevance_score=0.0)."""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="", project_context={"name": "proj"})
        assert result.relevance_score == 0.0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_empty_content_returns_specific_summary(self) -> None:
        """Empty content returns summary 'Empty content -- nothing to evaluate.'"""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="", project_context=None)
        assert result.summary == "Empty content -- nothing to evaluate."

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_empty_content_worth_ingesting_false(self) -> None:
        """Empty content returns worth_ingesting=False."""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="", project_context=None)
        assert result.worth_ingesting is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_empty_content_no_llm_call(self) -> None:
        """Empty content does NOT call llm_fn."""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        await evaluator.evaluate(content="", project_context=None)
        llm_fn.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_whitespace_content_short_circuits(self) -> None:
        """Whitespace-only content returns zero-score without calling llm_fn."""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="   \t\n  ", project_context=None)
        assert result.relevance_score == 0.0
        llm_fn.assert_not_awaited()

    # -- evaluate(): project_context is None --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_none_context_no_llm_call(self) -> None:
        """project_context=None does NOT call llm_fn."""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        await evaluator.evaluate(content="valid content", project_context=None)
        llm_fn.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_none_context_returns_default_relevance(self) -> None:
        """project_context=None returns relevance_score=0.5 (from _default_result)."""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="valid content", project_context=None)
        assert result.relevance_score == 0.5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_none_context_returns_worth_ingesting_true(self) -> None:
        """project_context=None returns worth_ingesting=True (from _default_result)."""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="valid content", project_context=None)
        assert result.worth_ingesting is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_none_context_default_summary_text(self) -> None:
        """project_context=None returns summary containing 'No project context available'."""
        llm_fn: AsyncMock = AsyncMock()
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="valid content", project_context=None)
        assert "No project context available" in result.summary

    # -- evaluate(): valid content + project_context --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_valid_calls_llm_fn_once(self) -> None:
        """evaluate(content, project_context) with valid args awaits llm_fn once."""
        mock_result = EvaluationResult(relevance_score=0.9, tags=["ai"], summary="relevant")
        llm_fn: AsyncMock = AsyncMock(return_value=mock_result)
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        await evaluator.evaluate(content="some content", project_context={"name": "project"})
        llm_fn.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_valid_returns_llm_fn_result(self) -> None:
        """evaluate() returns the EvaluationResult produced by llm_fn."""
        mock_result = EvaluationResult(
            relevance_score=0.9, tags=["ai"], summary="relevant", worth_ingesting=True
        )
        llm_fn: AsyncMock = AsyncMock(return_value=mock_result)
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(
            content="some content", project_context={"name": "project"}
        )
        assert result.relevance_score == 0.9
        assert result.summary == "relevant"
        assert result.worth_ingesting is True

    # -- evaluate(): exception path --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_exception_returns_neutral_relevance(self) -> None:
        """When llm_fn raises, evaluate() returns relevance_score=0.5."""
        llm_fn: AsyncMock = AsyncMock(side_effect=RuntimeError("LLM error"))
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="content", project_context={"name": "proj"})
        assert result.relevance_score == 0.5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_exception_returns_failure_summary(self) -> None:
        """When llm_fn raises, summary is 'Evaluation failed -- returning neutral score.'"""
        llm_fn: AsyncMock = AsyncMock(side_effect=ValueError("bad response"))
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="content", project_context={"name": "proj"})
        assert result.summary == "Evaluation failed -- returning neutral score."

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_exception_worth_ingesting_false(self) -> None:
        """When llm_fn raises, worth_ingesting=False."""
        llm_fn: AsyncMock = AsyncMock(side_effect=RuntimeError("error"))
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(content="content", project_context={"name": "proj"})
        assert result.worth_ingesting is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_exception_logs_warning_with_exc_info(self) -> None:
        """When llm_fn raises, logger.warning is called with exc_info=True."""
        llm_fn: AsyncMock = AsyncMock(side_effect=RuntimeError("error"))
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        with patch("owlbear_knowledge.evaluator.logger") as mock_logger:
            await evaluator.evaluate(content="content", project_context={"name": "proj"})
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs.get("exc_info") is True


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


# ---------------------------------------------------------------------------
# TestFromAC_SourceEvaluatorModuleFunctions
# ---------------------------------------------------------------------------


class TestFromAC_SourceEvaluatorModuleFunctions:  # noqa: N801
    """AC: MAX_CONTENT_LENGTH, _build_prompt, _default_result module symbols for #523."""

    def test_max_content_length_equals_2000(self) -> None:
        """MAX_CONTENT_LENGTH constant equals 2000."""
        from owlbear_knowledge.evaluator import MAX_CONTENT_LENGTH  # noqa: PLC0415

        assert MAX_CONTENT_LENGTH == 2000

    def test_build_prompt_truncates_long_content(self) -> None:
        """_build_prompt truncates content exceeding MAX_CONTENT_LENGTH chars."""
        from owlbear_knowledge.evaluator import MAX_CONTENT_LENGTH, _build_prompt  # noqa: PLC0415

        unique = "ZQXJK"
        long_content = unique * (MAX_CONTENT_LENGTH // len(unique) + 100)  # ~2500 chars
        ctx: dict[str, object] = {"name": "test_proj"}
        result = _build_prompt(long_content, ctx)
        # Distinctive prefix preserved, but full overlong string is not
        assert unique in result
        assert long_content not in result

    def test_build_prompt_short_content_preserved(self) -> None:
        """_build_prompt preserves content shorter than MAX_CONTENT_LENGTH."""
        from owlbear_knowledge.evaluator import _build_prompt  # noqa: PLC0415

        content = "hello world"
        ctx: dict[str, object] = {"name": "proj"}
        result = _build_prompt(content, ctx)
        assert "hello world" in result

    def test_build_prompt_has_project_context_header(self) -> None:
        """_build_prompt output contains a '## Project Context' section header."""
        from owlbear_knowledge.evaluator import _build_prompt  # noqa: PLC0415

        result = _build_prompt("content", {"name": "proj"})
        assert "## Project Context" in result

    def test_build_prompt_has_content_excerpt_header(self) -> None:
        """_build_prompt output contains a '## Content Excerpt' section header."""
        from owlbear_knowledge.evaluator import _build_prompt  # noqa: PLC0415

        result = _build_prompt("content", {"name": "proj"})
        assert "## Content Excerpt" in result

    def test_default_result_relevance_score(self) -> None:
        """_default_result().relevance_score == 0.5 (neutral)."""
        from owlbear_knowledge.evaluator import _default_result  # noqa: PLC0415

        result = _default_result()
        assert result.relevance_score == 0.5

    def test_default_result_worth_ingesting_true(self) -> None:
        """_default_result().worth_ingesting is True."""
        from owlbear_knowledge.evaluator import _default_result  # noqa: PLC0415

        result = _default_result()
        assert result.worth_ingesting is True

    def test_default_result_summary_contains_no_project_context(self) -> None:
        """_default_result().summary contains 'No project context available'."""
        from owlbear_knowledge.evaluator import _default_result  # noqa: PLC0415

        result = _default_result()
        assert "No project context available" in result.summary

    def test_default_result_tags_empty(self) -> None:
        """_default_result().tags is an empty list."""
        from owlbear_knowledge.evaluator import _default_result  # noqa: PLC0415

        result = _default_result()
        assert result.tags == []


# ---------------------------------------------------------------------------
# TestFromAC_BackwardCompatConstructor (#700)
# ---------------------------------------------------------------------------


class TestFromAC_BackwardCompatConstructor:  # noqa: N801
    """AC: SourceEvaluator backward-compat constructor for #700.

    Covers AC1 (positional model-string accepted), AC2 (callable keyword arg
    still wires fn), and AC3 (evaluate() returns _default_result() when
    instantiated with a model string instead of a callable).
    """

    # -- AC1: positional model string instantiates without error --

    def test_ac1_model_string_positional_instantiates(self) -> None:
        """AC1: SourceEvaluator('gpt-4o-mini') instantiates without raising."""
        evaluator = SourceEvaluator("gpt-4o-mini")
        assert evaluator is not None

    def test_ac1_arbitrary_string_positional_instantiates(self) -> None:
        """AC1: Any string as positional arg does not raise during construction."""
        evaluator = SourceEvaluator("some-other-model")
        assert evaluator is not None

    def test_ac1_none_positional_instantiates(self) -> None:
        """AC1: SourceEvaluator(None) — explicit None — instantiates without raising."""
        evaluator = SourceEvaluator(None)
        assert evaluator is not None

    # -- AC2: callable keyword arg still wires the fn --

    def test_ac2_callable_keyword_still_instantiates(self) -> None:
        """AC2: SourceEvaluator(llm_fn=callable) does not raise."""
        mock_result = EvaluationResult(relevance_score=0.7, tags=[], summary="ok")
        llm_fn: AsyncMock = AsyncMock(return_value=mock_result)
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        assert evaluator is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ac2_callable_keyword_fn_is_invoked(self) -> None:
        """AC2: evaluate() with a wired callable actually awaits it."""
        mock_result = EvaluationResult(relevance_score=0.8, tags=[], summary="wired")
        llm_fn: AsyncMock = AsyncMock(return_value=mock_result)
        evaluator = SourceEvaluator(llm_fn=llm_fn)
        result = await evaluator.evaluate(
            content="valid content", project_context={"name": "proj"}
        )
        llm_fn.assert_awaited_once()
        assert result.relevance_score == 0.8

    # -- AC3: evaluate() returns _default_result() when model string was supplied --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ac3_model_string_evaluate_no_crash(self) -> None:
        """AC3: evaluate(valid_content, valid_context) with model-string instance does not raise."""
        evaluator = SourceEvaluator("gpt-4o-mini")
        result = await evaluator.evaluate(
            content="some content", project_context={"name": "proj"}
        )
        assert isinstance(result, EvaluationResult)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ac3_model_string_evaluate_returns_default_relevance(self) -> None:
        """AC3: evaluate() with model-string instance returns relevance_score=0.5."""
        evaluator = SourceEvaluator("gpt-4o-mini")
        result = await evaluator.evaluate(
            content="some content", project_context={"name": "proj"}
        )
        assert result.relevance_score == 0.5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ac3_model_string_evaluate_returns_worth_ingesting_true(self) -> None:
        """AC3: evaluate() with model-string instance returns worth_ingesting=True."""
        evaluator = SourceEvaluator("gpt-4o-mini")
        result = await evaluator.evaluate(
            content="some content", project_context={"name": "proj"}
        )
        assert result.worth_ingesting is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ac3_model_string_evaluate_default_summary(self) -> None:
        """AC3: evaluate() with model-string instance summary contains 'No project context available'."""
        evaluator = SourceEvaluator("gpt-4o-mini")
        result = await evaluator.evaluate(
            content="some content", project_context={"name": "proj"}
        )
        assert "No project context available" in result.summary

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ac3_none_instance_evaluate_valid_context_returns_default(self) -> None:
        """AC3: SourceEvaluator(None).evaluate(content, context) returns _default_result()."""
        evaluator = SourceEvaluator(None)
        result = await evaluator.evaluate(
            content="relevant text", project_context={"name": "proj", "goals": "learn"}
        )
        assert result.relevance_score == 0.5
        assert result.worth_ingesting is True
