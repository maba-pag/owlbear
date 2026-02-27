"""Tests for owlbear.core.agent — OwlBearAgent wrapper."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from owlbear.channels.cli import CLIChannel
from owlbear.core.agent import OwlBearAgent
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.memory.context import ContextManager
from owlbear.memory.session import SessionStore


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
