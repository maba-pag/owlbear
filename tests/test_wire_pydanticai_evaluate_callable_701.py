"""RED-phase tests for #701 — Wire PydanticAI evaluate callable for SourceEvaluator.

Implementation plan: Factory ``make_pydantic_evaluate_fn(model)`` is added to
``owlbear_knowledge.evaluator``. It constructs a PydanticAI Agent and returns an async
EvaluateFn. ``server.py``'s ``make_evaluate_fn`` is updated to delegate to the factory,
catching ImportError and falling back to the existing no-op stub when pydantic-ai is absent.

AC coverage map:
  AC1 (factory in owlbear_knowledge creates EvaluateFn from model string):
    test_factory_function_exported_from_evaluator
    test_factory_returns_callable
    test_factory_callable_is_coroutine_function
    test_factory_constructs_agent_with_model_arg
    test_factory_constructs_agent_with_evaluation_result_output_type
    test_factory_constructs_agent_with_evaluation_prompt_as_system_prompt
  AC2 (server.py wires SourceEvaluator with PydanticAI callable):
    test_make_evaluate_fn_source_references_pydantic_factory
    test_make_evaluate_fn_delegates_to_pydantic_factory_when_available
  AC3 (produces real relevance scores with LLM):
    test_factory_callable_passes_prompt_to_agent_run
    test_factory_callable_returns_agent_run_output
  AC4 (graceful degradation when pydantic-ai not installed):
    test_make_evaluate_fn_source_contains_import_error_handler
    test_make_evaluate_fn_falls_back_gracefully_on_import_error

Test categories:
  happy: 2 (factory exported, callable returned)
  edge: 4 (Agent args: model, output_type, system_prompt; coroutine check)
  error: 2 (ImportError source check, ImportError fallback behavior)
  boundary: 4 (delegation when available, prompt pass-through, output mapping, fallback callable)
  Total: 12 — all FAIL
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.evaluator import EVALUATION_PROMPT, EvaluationResult


class TestFromAC_PydanticAIFactory:  # noqa: N801
    """AC1, AC3: make_pydantic_evaluate_fn factory in owlbear_knowledge.evaluator."""

    # -------------------------------------------------------------------------
    # AC1 — Factory exists and returns correct type
    # -------------------------------------------------------------------------

    def test_factory_function_exported_from_evaluator(self) -> None:
        """AC1: evaluator module must export make_pydantic_evaluate_fn.

        FAILS now: attribute does not exist — added by #701.
        """
        from owlbear_knowledge import evaluator  # noqa: PLC0415

        assert hasattr(evaluator, "make_pydantic_evaluate_fn"), (
            "owlbear_knowledge.evaluator must export make_pydantic_evaluate_fn (added by #701)"
        )

    def test_factory_returns_callable(self) -> None:
        """AC1: make_pydantic_evaluate_fn(model) must return a callable EvaluateFn.

        FAILS now: function does not exist — ImportError on import.
        """
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn  # type: ignore[attr-defined]  # noqa: PLC0415

        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = MagicMock()
        with patch.dict("sys.modules", {"pydantic_ai": mock_pydantic_ai}):
            fn = make_pydantic_evaluate_fn("gpt-4o-mini")
        assert callable(fn), "make_pydantic_evaluate_fn must return a callable EvaluateFn"

    def test_factory_callable_is_coroutine_function(self) -> None:
        """AC1: The returned callable must be an async coroutine function.

        EvaluateFn = Callable[[str], Awaitable[EvaluationResult]] requires async def.
        FAILS now: function does not exist.
        """
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn  # type: ignore[attr-defined]  # noqa: PLC0415

        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = MagicMock()
        with patch.dict("sys.modules", {"pydantic_ai": mock_pydantic_ai}):
            fn = make_pydantic_evaluate_fn("gpt-4o-mini")
        assert inspect.iscoroutinefunction(fn), (
            "Returned callable must be async def to satisfy EvaluateFn = Callable[[str], Awaitable[...]]"
        )

    # -------------------------------------------------------------------------
    # Edge — Agent constructor arguments
    # -------------------------------------------------------------------------

    def test_factory_constructs_agent_with_model_arg(self) -> None:
        """AC1: PydanticAI Agent must be constructed with the supplied model string.

        FAILS now: function does not exist.
        """
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn  # type: ignore[attr-defined]  # noqa: PLC0415

        mock_agent_cls = MagicMock()
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent_cls
        with patch.dict("sys.modules", {"pydantic_ai": mock_pydantic_ai}):
            make_pydantic_evaluate_fn("gpt-4o-mini")
        call_args = mock_agent_cls.call_args
        assert call_args is not None, "pydantic_ai.Agent must be called inside make_pydantic_evaluate_fn"
        model_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("model")
        assert model_arg == "gpt-4o-mini", (
            f"Agent must be constructed with model='gpt-4o-mini', got: {model_arg!r}"
        )

    def test_factory_constructs_agent_with_evaluation_result_output_type(self) -> None:
        """AC1: PydanticAI Agent must use output_type=EvaluationResult.

        FAILS now: function does not exist.
        """
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn  # type: ignore[attr-defined]  # noqa: PLC0415

        mock_agent_cls = MagicMock()
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent_cls
        with patch.dict("sys.modules", {"pydantic_ai": mock_pydantic_ai}):
            make_pydantic_evaluate_fn("gpt-4o-mini")
        call_args = mock_agent_cls.call_args
        assert call_args is not None, "pydantic_ai.Agent must be called"
        output_type = call_args.kwargs.get("output_type")
        assert output_type is EvaluationResult, (
            f"Agent must be constructed with output_type=EvaluationResult, got: {output_type!r}"
        )

    def test_factory_constructs_agent_with_evaluation_prompt_as_system_prompt(self) -> None:
        """AC1: PydanticAI Agent must use EVALUATION_PROMPT as system_prompt.

        FAILS now: function does not exist.
        """
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn  # type: ignore[attr-defined]  # noqa: PLC0415

        mock_agent_cls = MagicMock()
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent_cls
        with patch.dict("sys.modules", {"pydantic_ai": mock_pydantic_ai}):
            make_pydantic_evaluate_fn("gpt-4o-mini")
        call_args = mock_agent_cls.call_args
        assert call_args is not None, "pydantic_ai.Agent must be called"
        system_prompt = call_args.kwargs.get("system_prompt")
        assert system_prompt == EVALUATION_PROMPT, (
            "Agent must be constructed with system_prompt=EVALUATION_PROMPT from evaluator module"
        )

    # -------------------------------------------------------------------------
    # AC3 — Factory callable forwards prompt and returns LLM output
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_factory_callable_passes_prompt_to_agent_run(self) -> None:
        """AC3: The async callable must pass its prompt string to agent.run(prompt).

        FAILS now: function does not exist.
        """
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn  # type: ignore[attr-defined]  # noqa: PLC0415

        expected_output = EvaluationResult(relevance_score=0.8, worth_ingesting=True, summary="ok")
        mock_run_result = MagicMock()
        mock_run_result.output = expected_output
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_run_result)
        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent_cls
        with patch.dict("sys.modules", {"pydantic_ai": mock_pydantic_ai}):
            fn = make_pydantic_evaluate_fn("gpt-4o-mini")

        await fn("my evaluation prompt")
        mock_agent_instance.run.assert_awaited_once_with("my evaluation prompt")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_factory_callable_returns_agent_run_output(self) -> None:
        """AC3: The async callable must return agent.run(prompt).output directly.

        FAILS now: function does not exist.
        """
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn  # type: ignore[attr-defined]  # noqa: PLC0415

        expected_output = EvaluationResult(
            relevance_score=0.9, worth_ingesting=True, summary="highly relevant"
        )
        mock_run_result = MagicMock()
        mock_run_result.output = expected_output
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_run_result)
        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent_cls
        with patch.dict("sys.modules", {"pydantic_ai": mock_pydantic_ai}):
            fn = make_pydantic_evaluate_fn("gpt-4o-mini")

        result = await fn("test prompt")
        assert result is expected_output, (
            "Callable must return agent.run(prompt).output — the EvaluationResult from PydanticAI"
        )


class TestFromAC_ServerMakeEvaluateFnWiring:  # noqa: N801
    """AC2, AC4: make_evaluate_fn delegation and ImportError fallback in server.py."""

    # -------------------------------------------------------------------------
    # AC2 — make_evaluate_fn delegates to PydanticAI factory
    # -------------------------------------------------------------------------

    def test_make_evaluate_fn_source_references_pydantic_factory(self) -> None:
        """AC2: make_evaluate_fn source must reference make_pydantic_evaluate_fn.

        FAILS now: current stub body does not call make_pydantic_evaluate_fn.
        """
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        src = inspect.getsource(server.make_evaluate_fn)
        assert "make_pydantic_evaluate_fn" in src, (
            "make_evaluate_fn must delegate to make_pydantic_evaluate_fn (not yet wired — #701)"
        )

    def test_make_evaluate_fn_delegates_to_pydantic_factory_when_available(self) -> None:
        """AC2: When make_pydantic_evaluate_fn is importable, make_evaluate_fn must call it.

        Uses patch.object(create=True) to inject the factory before it exists in the module.
        FAILS now: make_evaluate_fn never calls make_pydantic_evaluate_fn.
        """
        import owlbear_knowledge.evaluator as ev  # noqa: PLC0415
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        sentinel_fn = AsyncMock(
            return_value=EvaluationResult(relevance_score=0.7, worth_ingesting=True, summary="")
        )
        mock_factory = MagicMock(return_value=sentinel_fn)

        with patch.object(ev, "make_pydantic_evaluate_fn", mock_factory, create=True):
            result_fn = server.make_evaluate_fn("gpt-4o-mini")

        mock_factory.assert_called_once_with("gpt-4o-mini")
        assert result_fn is sentinel_fn, (
            "make_evaluate_fn must return the callable from make_pydantic_evaluate_fn when available"
        )

    # -------------------------------------------------------------------------
    # AC4 — ImportError fallback
    # -------------------------------------------------------------------------

    def test_make_evaluate_fn_source_contains_import_error_handler(self) -> None:
        """AC4: make_evaluate_fn must contain an ImportError handler for graceful degradation.

        FAILS now: current stub has no ImportError try/except.
        """
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        src = inspect.getsource(server.make_evaluate_fn)
        assert "ImportError" in src, (
            "make_evaluate_fn must handle ImportError to degrade gracefully when pydantic-ai absent"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_make_evaluate_fn_falls_back_gracefully_on_import_error(self) -> None:
        """AC4: When make_pydantic_evaluate_fn raises ImportError, result is still a valid callable.

        Gated on the source reference check — fails fast in RED phase because
        make_evaluate_fn is still a stub that doesn't call make_pydantic_evaluate_fn.
        """
        from owlbear_mcp_knowledge import server  # noqa: PLC0415

        src = inspect.getsource(server.make_evaluate_fn)
        assert "make_pydantic_evaluate_fn" in src, (
            "AC4 gate: make_evaluate_fn must delegate to make_pydantic_evaluate_fn first (#701 not yet wired)"
        )

        import owlbear_knowledge.evaluator as ev  # noqa: PLC0415

        with patch.object(
            ev,
            "make_pydantic_evaluate_fn",
            side_effect=ImportError("pydantic_ai not installed"),
            create=True,
        ):
            fn = server.make_evaluate_fn("test-model")

        assert callable(fn), "Fallback must be a callable EvaluateFn"
        result = await fn("any prompt")
        assert isinstance(result, EvaluationResult)
        assert result.worth_ingesting is True, (
            "Fallback must not suppress bookmark ingestion (worth_ingesting must remain True)"
        )
