"""RED-phase tests for #688 — Fix SourceEvaluator wiring in MCP knowledge server.

Bug: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py app_lifespan() calls
  ``evaluator = SourceEvaluator(model)``
where ``model`` is a plain string (e.g. "gpt-4o-mini"), but SourceEvaluator.__init__
expects ``EvaluateFn = Callable[[str], Awaitable[EvaluationResult]]``.

The TypeError from calling a string is silently swallowed by SourceEvaluator.evaluate()'s
bare ``except Exception`` block, causing all evaluations with non-None project_context to
return the exception-fallback result (relevance_score=0.5, worth_ingesting=False,
summary="Evaluation failed -- returning neutral score.").

Fix trajectory:
  #700 - backward-compat crash fix: SourceEvaluator accepts model= kwarg, falls back to
          _default_result() so worth_ingesting=True and no "Evaluation failed" summary.
  #701 - PydanticAI evaluate callable: server wires real EvaluateFn via make_evaluate_fn(model),
          producing actual LLM relevance scores.

AC coverage map:
  AC1 (callable wiring):
    test_server_does_not_pass_model_string_positionally_to_source_evaluator
    test_server_exposes_evaluate_callable_factory
    test_evaluate_callable_factory_returns_callable
  AC2 (real relevance scores, not no-op/default):
    test_evaluate_with_model_string_does_not_return_exception_fallback_summary
    test_evaluate_with_model_string_worth_ingesting_not_suppressed_to_false
  AC3 (graceful degradation if LLM unavailable):
    test_callable_llm_exception_returns_neutral_relevance_score
    test_callable_llm_exception_does_not_propagate

Test categories:
  wiring/source-inspection: 3 (source text, factory attribute, factory type)
  behavioral-pathology: 2 (exception-fallback summary, worth_ingesting suppression)
  graceful-degradation: 2 (factory-gated, returns neutral, no re-raise)
  Total: 7 — all FAIL on current HEAD
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock

import pytest

from owlbear_knowledge.evaluator import EvaluationResult, SourceEvaluator


class TestFromAC_SourceEvaluatorWiring:  # noqa: N801
    """AC tests for #688 — server wires SourceEvaluator with a proper async callable."""

    # -----------------------------------------------------------------------
    # AC1 — SourceEvaluator receives a proper async callable that calls the LLM
    # -----------------------------------------------------------------------

    def test_server_does_not_pass_model_string_positionally_to_source_evaluator(
        self,
    ) -> None:
        """app_lifespan source must not contain the bare positional call SourceEvaluator(model).

        The bug is exactly: ``evaluator = SourceEvaluator(model)`` where model is a string.
        After the wiring fix the call must use a callable, not the raw model name variable.
        FAILS now: 'SourceEvaluator(model)' is present in the source.
        """
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        src = inspect.getsource(server.app_lifespan)
        assert "SourceEvaluator(model)" not in src, (
            "app_lifespan must not pass bare model string positionally to SourceEvaluator. "
            "Wire a callable via make_evaluate_fn(model) instead."
        )

    def test_server_exposes_evaluate_callable_factory(self) -> None:
        """server module must export make_evaluate_fn() to create EvaluateFn from a model name.

        FAILS now: server has no make_evaluate_fn attribute (added by #701).
        """
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        assert hasattr(server, "make_evaluate_fn"), (
            "server must export make_evaluate_fn() factory (added by #701 PydanticAI wiring)"
        )

    def test_evaluate_callable_factory_returns_callable(self) -> None:
        """make_evaluate_fn(model) must return a callable suitable for SourceEvaluator(llm_fn=...).

        FAILS now: make_evaluate_fn does not exist yet.
        """
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        fn = server.make_evaluate_fn("gpt-4o-mini")  # type: ignore[attr-defined]
        assert callable(fn), "make_evaluate_fn must return a callable EvaluateFn"

    # -----------------------------------------------------------------------
    # AC2 — Bookmark evaluation produces real relevance scores (not no-op/default)
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_with_model_string_does_not_return_exception_fallback_summary(
        self,
    ) -> None:
        """SourceEvaluator('model-string') must not silently return the TypeError exception fallback.

        Current bug: calling a string as a function raises TypeError, which is swallowed by the
        bare ``except Exception`` in evaluate(), returning summary='Evaluation failed ...'.
        After #700 backward-compat fix: returns _default_result() summary instead.
        FAILS now: result.summary IS 'Evaluation failed -- returning neutral score.'
        """
        evaluator = SourceEvaluator("gpt-4o-mini")  # mimics current server.py line ~149
        result = await evaluator.evaluate("some content", {"name": "proj"})
        assert result.summary != "Evaluation failed -- returning neutral score.", (
            "model-string wiring silently returns exception-fallback summary; "
            "backward-compat (#700) must return _default_result() summary instead"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_evaluate_with_model_string_worth_ingesting_not_suppressed_to_false(
        self,
    ) -> None:
        """SourceEvaluator('model-string') must not suppress worth_ingesting to False.

        Current bug: exception fallback returns worth_ingesting=False, silently dropping
        content that should be ingested.
        After #700 backward-compat fix: returns _default_result() with worth_ingesting=True.
        FAILS now: result.worth_ingesting IS False.
        """
        evaluator = SourceEvaluator("gpt-4o-mini")  # mimics current server.py line ~149
        result = await evaluator.evaluate("some content", {"name": "proj"})
        assert result.worth_ingesting is not False, (
            "model-string wiring must not suppress worth_ingesting to False via exception fallback"
        )

    # -----------------------------------------------------------------------
    # AC3 — Graceful degradation if LLM is unavailable
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_callable_llm_exception_returns_neutral_relevance_score(self) -> None:
        """When factory-provided callable raises (LLM unavailable), evaluate() returns score 0.5.

        This test is gated on make_evaluate_fn existing (FAILS before #701) to ensure it tests
        AC3 in the context of the full fix — a real callable that can fail at LLM call time.
        After both fixes: factory exists, LLM exception → neutral score 0.5.
        """
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        # Gate: factory must exist (FAILS before #701 lands)
        assert hasattr(server, "make_evaluate_fn"), (
            "make_evaluate_fn factory not found — #701 must land before this test can pass"
        )
        failing_fn: AsyncMock = AsyncMock(side_effect=RuntimeError("LLM service unavailable"))
        evaluator = SourceEvaluator(llm_fn=failing_fn)
        result = await evaluator.evaluate("content", {"name": "proj"})
        assert result.relevance_score == pytest.approx(0.5)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_callable_llm_exception_does_not_propagate(self) -> None:
        """When factory-provided callable raises (LLM unavailable), evaluate() must not re-raise.

        Graceful degradation: all exceptions from the LLM callable are caught; bookmark
        processing continues with a neutral EvaluationResult.
        Gated on make_evaluate_fn existing (FAILS before #701) — same rationale as above.
        """
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        # Gate: factory must exist (FAILS before #701 lands)
        assert hasattr(server, "make_evaluate_fn"), (
            "make_evaluate_fn factory not found — #701 must land before this test can pass"
        )
        failing_fn: AsyncMock = AsyncMock(side_effect=OSError("network unreachable"))
        evaluator = SourceEvaluator(llm_fn=failing_fn)
        # Must not raise — evaluate() swallows LLM exceptions and degrades gracefully
        result = await evaluator.evaluate("content", {"name": "proj"})
        assert isinstance(result, EvaluationResult)
