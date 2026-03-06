"""Tests for owlbear.core.agent — OwlBearAgent wrapper."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import Model
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.toolsets.abstract import AbstractToolset

from owlbear.channels.cli import CLIChannel
from owlbear.core.agent import OwlBearAgent
from owlbear.core.deps import OwlBearDeps
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.memory.context import ContextManager
from owlbear.memory.session import SessionStore
from owlbear.memory.usage import UsageTracker


def _mock_result(output: str, messages: list[object]) -> MagicMock:
    """Build a mock PydanticAI AgentRunResult."""
    result = MagicMock()
    result.output = output
    result.all_messages.return_value = messages
    return result


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestOwlBearAgentCreate:
    """OwlBearAgent composes all OwlBear components."""

    def test_create_with_all_components(self, tmp_path: Path) -> None:
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            context=ContextManager(tmp_path),
            hooks=HookRegistry(),
            channel=CLIChannel(),
        )
        assert agent is not None

    def test_create_minimal(self, tmp_path: Path) -> None:
        """Only model and session are required; others have defaults."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert agent is not None

    def test_hooks_default_to_empty_registry(self, tmp_path: Path) -> None:
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert isinstance(agent.hooks, HookRegistry)

    def test_create_with_toolsets(self, tmp_path: Path) -> None:
        """OwlBearAgent forwards toolsets to inner Agent."""
        ts = FunctionToolset([])
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            toolsets=[ts],
        )
        assert len(agent.inner._user_toolsets) == 1
        assert isinstance(agent.inner._user_toolsets[0], AbstractToolset)

    def test_create_without_toolsets_backward_compat(self, tmp_path: Path) -> None:
        """Omitting toolsets preserves current behavior (no toolsets)."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert agent.inner._user_toolsets == []


# ---------------------------------------------------------------------------
# Single turn (mocked LLM)
# ---------------------------------------------------------------------------


class TestOwlBearAgentTurn:
    """turn() sends one prompt to the LLM and returns the response."""

    def test_turn_returns_response_text(self, tmp_path: Path) -> None:
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        mock = _mock_result(
            "Hello from OwlBear!",
            [
                ModelRequest(parts=[UserPromptPart(content="hi")]),
                ModelResponse(parts=[TextPart(content="Hello from OwlBear!")]),
            ],
        )
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        result = asyncio.run(agent.turn("hi"))
        assert result == "Hello from OwlBear!"

    def test_turn_persists_messages(self, tmp_path: Path) -> None:
        session = SessionStore(tmp_path / "s.jsonl")
        agent = OwlBearAgent(model="test", session=session)

        mock = _mock_result(
            "response",
            [
                ModelRequest(parts=[UserPromptPart(content="q")]),
                ModelResponse(parts=[TextPart(content="response")]),
            ],
        )
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("q"))
        loaded = session.load()
        assert len(loaded) == 2

    def test_turn_passes_history(self, tmp_path: Path) -> None:
        """turn() passes existing session history to the LLM."""
        session = SessionStore(tmp_path / "s.jsonl")
        session.append(ModelRequest(parts=[UserPromptPart(content="old")]))
        session.append(ModelResponse(parts=[TextPart(content="old reply")]))

        agent = OwlBearAgent(model="test", session=session)

        mock = _mock_result(
            "new reply",
            [
                ModelRequest(parts=[UserPromptPart(content="old")]),
                ModelResponse(parts=[TextPart(content="old reply")]),
                ModelRequest(parts=[UserPromptPart(content="new")]),
                ModelResponse(parts=[TextPart(content="new reply")]),
            ],
        )
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("new"))

        call_kwargs = agent.inner.run.call_args
        assert call_kwargs.kwargs.get("message_history") is not None
        assert len(call_kwargs.kwargs["message_history"]) == 2


# ---------------------------------------------------------------------------
# Hook emission
# ---------------------------------------------------------------------------


class TestOwlBearAgentHooks:
    """turn() emits hooks at the right moments."""

    def test_emits_on_message_hook(self, tmp_path: Path) -> None:
        hooks = HookRegistry()
        events: list[str] = []
        hooks.register(HookEvent.ON_MESSAGE, lambda _: events.append("on_message"))

        agent = OwlBearAgent(model="test", session=SessionStore(tmp_path / "s.jsonl"), hooks=hooks)

        mock = _mock_result(
            "ok",
            [
                ModelRequest(parts=[UserPromptPart(content="hi")]),
                ModelResponse(parts=[TextPart(content="ok")]),
            ],
        )
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("hi"))
        assert "on_message" in events

    def test_emits_on_error_hook(self, tmp_path: Path) -> None:
        hooks = HookRegistry()
        errors: list[object] = []
        hooks.register(HookEvent.ON_ERROR, errors.append)

        agent = OwlBearAgent(model="test", session=SessionStore(tmp_path / "s.jsonl"), hooks=hooks)
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(side_effect=RuntimeError("LLM failed"))

        with contextlib.suppress(RuntimeError):
            asyncio.run(agent.turn("hi"))

        assert len(errors) == 1


# ---------------------------------------------------------------------------
# Context injection
# ---------------------------------------------------------------------------


class TestOwlBearAgentContext:
    """Context file is injected as agent instructions."""

    def test_context_used_as_instructions(self, tmp_path: Path) -> None:
        (tmp_path / "context.md").write_text("You are OwlBear.", encoding="utf-8")
        context = ContextManager(tmp_path)
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            context=context,
        )
        assert agent.inner._instructions == ["You are OwlBear."]


# ---------------------------------------------------------------------------
# Usage recording: cost + premium requests
# ---------------------------------------------------------------------------


def _mock_result_with_usage(
    output: str,
    messages: list[object],
    *,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Build a mock PydanticAI result that includes a .usage() method."""
    result = MagicMock()
    result.output = output
    result.all_messages.return_value = messages
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_tokens = 0
    usage.cache_write_tokens = 0
    usage.requests = 1
    usage.tool_calls = 0
    result.usage.return_value = usage
    return result


def _simple_messages() -> list[object]:
    return [
        ModelRequest(parts=[UserPromptPart(content="hi")]),
        ModelResponse(parts=[TextPart(content="ok")]),
    ]


class TestUsageRecordCostAndPremium:
    """_record_usage() enriches UsageRecord with cost and premium requests."""

    def test_record_includes_estimated_cost(self, tmp_path: Path) -> None:
        """calc_estimated_cost result is stored in the UsageRecord."""
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
            provider="copilot",
        )

        mock = _mock_result_with_usage("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        with patch(
            "owlbear.memory.usage_cost.calc_estimated_cost", return_value=0.0042
        ) as mock_calc:
            asyncio.run(agent.turn("hi"))
            mock_calc.assert_called_once_with("test", "copilot", 100, 50)

        records = tracker.load()
        assert len(records) == 1
        assert records[0].estimated_cost_usd == 0.0042

    def test_record_includes_premium_requests_for_copilot(self, tmp_path: Path) -> None:
        """get_premium_requests is called when provider == 'copilot'."""
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
            provider="copilot",
        )

        mock = _mock_result_with_usage("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        with (
            patch("owlbear.memory.usage_cost.calc_estimated_cost", return_value=None),
            patch(
                "owlbear.providers.copilot_multipliers.get_premium_requests",
                return_value=1.0,
            ) as mock_pr,
        ):
            asyncio.run(agent.turn("hi"))
            mock_pr.assert_called_once_with("test")

        records = tracker.load()
        assert len(records) == 1
        assert records[0].premium_requests == 1.0

    def test_no_premium_requests_for_non_copilot_provider(self, tmp_path: Path) -> None:
        """get_premium_requests is NOT called when provider != 'copilot'."""
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
            provider="openai",
        )

        mock = _mock_result_with_usage("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        with (
            patch("owlbear.memory.usage_cost.calc_estimated_cost", return_value=None),
            patch(
                "owlbear.providers.copilot_multipliers.get_premium_requests",
            ) as mock_pr,
        ):
            asyncio.run(agent.turn("hi"))
            mock_pr.assert_not_called()

        records = tracker.load()
        assert len(records) == 1
        assert records[0].premium_requests is None

    def test_cost_import_error_returns_none(self, tmp_path: Path) -> None:
        """If calc_estimated_cost import fails, estimated_cost_usd is None."""
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
            provider="copilot",
        )

        mock = _mock_result_with_usage("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        with (
            patch(
                "owlbear.memory.usage_cost.calc_estimated_cost",
                side_effect=Exception("boom"),
            ),
            patch(
                "owlbear.providers.copilot_multipliers.get_premium_requests",
                return_value=1.0,
            ),
        ):
            asyncio.run(agent.turn("hi"))

        records = tracker.load()
        assert len(records) == 1
        assert records[0].estimated_cost_usd is None

    def test_provider_defaults_to_copilot(self, tmp_path: Path) -> None:
        """provider parameter defaults to 'copilot'."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert agent.provider == "copilot"

    def test_provider_configurable(self, tmp_path: Path) -> None:
        """provider parameter can be set to any value."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            provider="openai",
        )
        assert agent.provider == "openai"

    def test_record_uses_configured_provider(self, tmp_path: Path) -> None:
        """The UsageRecord uses the agent's provider, not hardcoded."""
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
            provider="azure",
        )

        mock = _mock_result_with_usage("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        with patch("owlbear.memory.usage_cost.calc_estimated_cost", return_value=None):
            asyncio.run(agent.turn("hi"))

        records = tracker.load()
        assert len(records) == 1
        assert records[0].provider == "azure"


# ---------------------------------------------------------------------------
# OwlBearDeps dataclass
# ---------------------------------------------------------------------------


class TestOwlBearDeps:
    """OwlBearDeps is a dataclass carrying shared agent dependencies."""

    def test_construct_with_all_fields(self, tmp_path: Path) -> None:
        hooks = HookRegistry()
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        deps = OwlBearDeps(hooks=hooks, tracker=tracker)
        assert deps.hooks is hooks
        assert deps.tracker is tracker

    def test_tracker_defaults_to_none(self) -> None:
        hooks = HookRegistry()
        deps = OwlBearDeps(hooks=hooks)
        assert deps.hooks is hooks
        assert deps.tracker is None

    def test_is_dataclass(self) -> None:
        import dataclasses

        assert dataclasses.is_dataclass(OwlBearDeps)

    def test_agent_registry_defaults_to_none(self) -> None:
        hooks = HookRegistry()
        deps = OwlBearDeps(hooks=hooks)
        assert deps.agent_registry is None

    def test_delegation_depth_defaults_to_zero(self) -> None:
        hooks = HookRegistry()
        deps = OwlBearDeps(hooks=hooks)
        assert deps.delegation_depth == 0

    def test_construct_with_agent_registry_and_delegation_depth(self) -> None:
        hooks = HookRegistry()
        mock_registry = MagicMock()
        deps = OwlBearDeps(
            hooks=hooks,
            agent_registry=mock_registry,
            delegation_depth=2,
        )
        assert deps.agent_registry is mock_registry
        assert deps.delegation_depth == 2

    def test_dataclass_replace_delegation_depth(self) -> None:
        import dataclasses

        hooks = HookRegistry()
        deps = OwlBearDeps(hooks=hooks)
        replaced = dataclasses.replace(deps, delegation_depth=3)
        assert replaced.delegation_depth == 3
        assert deps.delegation_depth == 0  # original unchanged


# ---------------------------------------------------------------------------
# OwlBearAgent deps injection
# ---------------------------------------------------------------------------


class TestOwlBearAgentDeps:
    """OwlBearAgent constructs OwlBearDeps and passes it to inner Agent.run()."""

    def test_agent_creates_deps_from_params(self, tmp_path: Path) -> None:
        hooks = HookRegistry()
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            hooks=hooks,
            tracker=tracker,
        )
        assert isinstance(agent._deps, OwlBearDeps)
        assert agent._deps.hooks is hooks
        assert agent._deps.tracker is tracker

    def test_agent_deps_default_tracker_none(self, tmp_path: Path) -> None:
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert isinstance(agent._deps, OwlBearDeps)
        assert agent._deps.tracker is None

    def test_turn_passes_deps_to_inner_run(self, tmp_path: Path) -> None:
        hooks = HookRegistry()
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            hooks=hooks,
            tracker=tracker,
        )

        mock = _mock_result(
            "ok",
            [
                ModelRequest(parts=[UserPromptPart(content="hi")]),
                ModelResponse(parts=[TextPart(content="ok")]),
            ],
        )
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("hi"))

        call_kwargs = agent.inner.run.call_args
        assert call_kwargs.kwargs.get("deps") is agent._deps

    def test_inner_agent_typed_with_deps(self, tmp_path: Path) -> None:
        """Inner Agent is Agent[OwlBearDeps, str], not Agent[None, str]."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        # PydanticAI Agent stores the deps type — verify it's not None
        assert isinstance(agent._deps, OwlBearDeps)


# ---------------------------------------------------------------------------
# history_processors forwarding
# ---------------------------------------------------------------------------


class TestOwlBearAgentHistoryProcessors:
    """OwlBearAgent forwards history_processors to inner PydanticAI Agent."""

    def test_history_processors_forwarded_to_inner_agent(self, tmp_path: Path) -> None:
        """When history_processors are provided, they appear on the inner Agent."""

        def _noop_processor(messages: list) -> list:
            return messages

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            history_processors=[_noop_processor],
        )
        assert len(agent.inner.history_processors) == 1
        assert agent.inner.history_processors[0] is _noop_processor

    def test_history_processors_default_none(self, tmp_path: Path) -> None:
        """Omitting history_processors keeps backwards-compatible default."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        # PydanticAI normalises None → [] internally
        assert agent.inner.history_processors == []

    def test_multiple_history_processors(self, tmp_path: Path) -> None:
        """Multiple processors are forwarded in order."""

        def _proc_a(messages: list) -> list:
            return messages

        def _proc_b(messages: list) -> list:
            return messages

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            history_processors=[_proc_a, _proc_b],
        )
        assert len(agent.inner.history_processors) == 2
        assert agent.inner.history_processors[0] is _proc_a
        assert agent.inner.history_processors[1] is _proc_b


# ---------------------------------------------------------------------------
# Model instance support + update_model()
# ---------------------------------------------------------------------------


class TestOwlBearAgentModelInstance:
    """OwlBearAgent accepts Model instances (not just str) and supports update_model()."""

    def test_construct_with_model_instance(self, tmp_path: Path) -> None:
        """OwlBearAgent accepts a Model instance and forwards it to inner Agent."""
        mock_model = MagicMock(spec=Model)
        mock_model.model_name = "mock-model-v1"
        agent = OwlBearAgent(
            model=mock_model,
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        # inner Agent should receive the Model instance, not a string
        assert agent.inner.model is not None

    def test_model_name_extracted_from_model_instance(self, tmp_path: Path) -> None:
        """_model_name is extracted from Model.model_name when model is an instance."""
        mock_model = MagicMock(spec=Model)
        mock_model.model_name = "gpt-4o-copilot"
        agent = OwlBearAgent(
            model=mock_model,
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert agent._model_name == "gpt-4o-copilot"

    def test_string_model_still_works(self, tmp_path: Path) -> None:
        """Passing model as str continues to work (backwards compat)."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert agent._model_name == "test"

    def test_update_model_changes_inner_model(self, tmp_path: Path) -> None:
        """update_model() sets inner Agent's model to the new value."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        new_model = MagicMock(spec=Model)
        new_model.model_name = "new-model"
        agent.update_model(new_model)
        assert agent.inner.model is new_model

    def test_update_model_updates_model_name_from_instance(self, tmp_path: Path) -> None:
        """update_model() updates _model_name from Model.model_name attribute."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        new_model = MagicMock(spec=Model)
        new_model.model_name = "refreshed-gpt-4o"
        agent.update_model(new_model)
        assert agent._model_name == "refreshed-gpt-4o"

    def test_update_model_with_string(self, tmp_path: Path) -> None:
        """update_model() also accepts a plain string."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        agent.update_model("gpt-4.1")
        assert agent._model_name == "gpt-4.1"
        assert agent.inner.model == "gpt-4.1"


# ---------------------------------------------------------------------------
# Knowledge context injection (#425 / #408)
# ---------------------------------------------------------------------------


class TestOwlBearAgentKnowledgeInjection:
    """turn() auto-injects knowledge context via instructions= parameter."""

    def test_init_accepts_knowledge_service_none_default(self, tmp_path: Path) -> None:
        """knowledge_service defaults to None when not provided."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert agent._knowledge_service is None

    def test_init_accepts_knowledge_service(self, tmp_path: Path) -> None:
        """knowledge_service can be set via __init__."""
        svc = MagicMock()
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            knowledge_service=svc,
        )
        assert agent._knowledge_service is svc

    def test_turn_calls_query_for_context(self, tmp_path: Path) -> None:
        """When knowledge_service is set, turn() calls query_for_context(prompt)."""
        svc = MagicMock()
        svc.query_for_context.return_value = "Relevant knowledge:\n\n- doc: snippet"

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            knowledge_service=svc,
        )
        mock = _mock_result("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("What is X?"))

        svc.query_for_context.assert_called_once_with("What is X?")

    def test_turn_passes_instructions_to_inner_run(self, tmp_path: Path) -> None:
        """query_for_context result is passed as instructions= to inner.run()."""
        svc = MagicMock()
        svc.query_for_context.return_value = "Relevant knowledge:\n\n- doc: snippet"

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            knowledge_service=svc,
        )
        mock = _mock_result("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("What is X?"))

        call_kwargs = agent.inner.run.call_args
        assert call_kwargs.kwargs["instructions"] == "Relevant knowledge:\n\n- doc: snippet"

    def test_turn_no_instructions_when_service_is_none(self, tmp_path: Path) -> None:
        """When knowledge_service is None, instructions= is NOT passed."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        mock = _mock_result("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("hi"))

        call_kwargs = agent.inner.run.call_args
        assert "instructions" not in call_kwargs.kwargs

    def test_turn_passes_none_instructions_when_service_returns_none(self, tmp_path: Path) -> None:
        """When service returns None, instructions=None passed (PydanticAI ignores it)."""
        svc = MagicMock()
        svc.query_for_context.return_value = None

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            knowledge_service=svc,
        )
        mock = _mock_result("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("hi"))

        call_kwargs = agent.inner.run.call_args
        assert call_kwargs.kwargs["instructions"] is None

    def test_turn_continues_on_service_exception(self, tmp_path: Path) -> None:
        """When knowledge_service raises, turn() logs WARNING and continues."""
        svc = MagicMock()
        svc.query_for_context.side_effect = RuntimeError("embedding failed")

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            knowledge_service=svc,
        )
        mock = _mock_result("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        # Should NOT raise
        result = asyncio.run(agent.turn("hi"))
        assert result == "ok"

        # inner.run() should have been called WITHOUT instructions
        call_kwargs = agent.inner.run.call_args
        assert "instructions" not in call_kwargs.kwargs

    def test_turn_logs_warning_on_service_exception(self, tmp_path: Path) -> None:
        """Exception from knowledge_service is logged at WARNING level."""
        svc = MagicMock()
        svc.query_for_context.side_effect = RuntimeError("DB corrupt")

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            knowledge_service=svc,
        )
        mock = _mock_result("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        with patch("owlbear.core.agent.logger") as mock_logger:
            asyncio.run(agent.turn("hi"))
            mock_logger.warning.assert_called_once()
            assert "Knowledge context injection failed" in mock_logger.warning.call_args[0][0]

    def test_existing_turn_behavior_preserved(self, tmp_path: Path) -> None:
        """With no knowledge_service, turn() works exactly as before."""
        hooks = HookRegistry()
        events: list[str] = []
        hooks.register(HookEvent.ON_MESSAGE, lambda _: events.append("msg"))

        session = SessionStore(tmp_path / "s.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=session,
            hooks=hooks,
        )
        mock = _mock_result("reply", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        result = asyncio.run(agent.turn("hello"))

        assert result == "reply"
        assert "msg" in events
        # Verify no instructions kwarg
        call_kwargs = agent.inner.run.call_args
        assert "instructions" not in call_kwargs.kwargs
