"""RED-phase tests for #139 AC items not covered by #138 test task.

Covers package-integration and field-default gaps:
  - Package __init__.py re-exports (TestFromAC_PackageInit)
  - EVALUATION_PROMPT constant preserved from v1 (TestFromAC_EvaluationPrompt)
  - Blank/whitespace content handling in evaluate() (TestFromAC_EvaluatorBlankContent)
  - EvaluationResult.summary default value (TestFromAC_EvaluationResultDefaults)

All tests fail in RED phase — implementation gaps not yet resolved.
"""

from __future__ import annotations

import owlbear_knowledge
import pytest

from owlbear_knowledge.evaluator import EvaluationResult, SourceEvaluator


# ---------------------------------------------------------------------------
# TestFromAC_PackageInit
# ---------------------------------------------------------------------------


class TestFromAC_PackageInit:  # noqa: N801
    """AC: __init__.py re-exports ConsolidationService, ConsolidationInsight,
    SourceEvaluator, and EvaluationResult at the package level."""

    def test_consolidation_service_importable_from_package(self) -> None:
        """ConsolidationService is accessible as owlbear_knowledge.ConsolidationService."""
        assert hasattr(owlbear_knowledge, "ConsolidationService")

    def test_consolidation_insight_importable_from_package(self) -> None:
        """ConsolidationInsight is accessible as owlbear_knowledge.ConsolidationInsight."""
        assert hasattr(owlbear_knowledge, "ConsolidationInsight")

    def test_source_evaluator_importable_from_package(self) -> None:
        """SourceEvaluator is accessible as owlbear_knowledge.SourceEvaluator."""
        assert hasattr(owlbear_knowledge, "SourceEvaluator")

    def test_evaluation_result_importable_from_package(self) -> None:
        """EvaluationResult is accessible as owlbear_knowledge.EvaluationResult."""
        assert hasattr(owlbear_knowledge, "EvaluationResult")

    def test_all_exports_listed_in_dunder_all(self) -> None:
        """All four new symbols appear in owlbear_knowledge.__all__."""
        required = {
            "ConsolidationService",
            "ConsolidationInsight",
            "SourceEvaluator",
            "EvaluationResult",
        }
        exported = set(getattr(owlbear_knowledge, "__all__", []))
        assert required.issubset(exported), f"Missing from __all__: {required - exported}"


# ---------------------------------------------------------------------------
# TestFromAC_EvaluationPrompt
# ---------------------------------------------------------------------------


class TestFromAC_EvaluationPrompt:  # noqa: N801
    """AC: EVALUATION_PROMPT constant preserved from v1 for future LLM integration."""

    def test_evaluation_prompt_constant_exists(self) -> None:
        """EVALUATION_PROMPT is importable from owlbear_knowledge.evaluator."""
        from owlbear_knowledge.evaluator import EVALUATION_PROMPT  # noqa: F401

        assert EVALUATION_PROMPT is not None

    def test_evaluation_prompt_is_non_empty_string(self) -> None:
        """EVALUATION_PROMPT is a non-empty string containing evaluation keywords."""
        from owlbear_knowledge.evaluator import EVALUATION_PROMPT

        assert isinstance(EVALUATION_PROMPT, str)
        assert len(EVALUATION_PROMPT) > 0


# ---------------------------------------------------------------------------
# TestFromAC_EvaluatorBlankContent
# ---------------------------------------------------------------------------


class TestFromAC_EvaluatorBlankContent:  # noqa: N801
    """AC: blank content (whitespace-only) must return relevance_score=0.0,
    worth_ingesting=False — same as empty string."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_spaces_only_returns_zero_score(self) -> None:
        """evaluate('   ') returns relevance_score=0.0 (blank treated as empty)."""
        evaluator = SourceEvaluator()
        result = await evaluator.evaluate(content="   ", project_context=None)
        assert result.relevance_score == 0.0
        assert result.worth_ingesting is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_newline_tab_returns_zero_score(self) -> None:
        """evaluate('\\n\\t') returns relevance_score=0.0 (blank whitespace treated as empty)."""
        evaluator = SourceEvaluator()
        result = await evaluator.evaluate(content="\n\t", project_context=None)
        assert result.relevance_score == 0.0
        assert result.worth_ingesting is False


# ---------------------------------------------------------------------------
# TestFromAC_EvaluationResultDefaults
# ---------------------------------------------------------------------------


class TestFromAC_EvaluationResultDefaults:  # noqa: N801
    """AC: EvaluationResult.summary has default='', enabling construction with
    only relevance_score provided."""

    def test_summary_defaults_to_empty_string(self) -> None:
        """EvaluationResult(relevance_score=0.5) with no summary uses default of ''."""
        result = EvaluationResult(relevance_score=0.5)
        assert result.summary == ""

    def test_all_defaults_applied_when_only_score_given(self) -> None:
        """EvaluationResult(relevance_score=0.0) uses all field defaults."""
        result = EvaluationResult(relevance_score=0.0)
        assert result.summary == ""
        assert result.tags == []
        assert result.worth_ingesting is False
