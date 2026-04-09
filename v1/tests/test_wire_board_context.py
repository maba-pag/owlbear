"""Tests for #771 — Wire BoardContextProvider into agent turn() instructions.

Contract tests for:
- OwlBearAgent.__init__ accepts optional board_context_provider
- turn() calls provider.get_context() and merges with knowledge context
- Graceful degradation on provider exception
- No instructions= when both sources empty/None
- Config: board_context_enabled bool in OwlBearSettings (default True)
- Bootstrap wiring when enabled/disabled
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from owlbear.core.agent import OwlBearAgent
from owlbear.memory.session import SessionStore

# ---------------------------------------------------------------------------
# Helpers (same pattern as test_agent.py)
# ---------------------------------------------------------------------------


def _import_settings() -> type:
    """Import OwlBearSettings without polluting module scope."""
    from owlbear.config import OwlBearSettings

    return OwlBearSettings


def _mock_result(output: str, messages: list[object]) -> MagicMock:
    """Build a mock PydanticAI AgentRunResult."""
    result = MagicMock()
    result.output = output
    result.all_messages.return_value = messages
    return result


def _simple_messages() -> list[object]:
    return [
        ModelRequest(parts=[UserPromptPart(content="hi")]),
        ModelResponse(parts=[TextPart(content="ok")]),
    ]


def _make_agent(
    tmp_path: Path,
    *,
    board_context_provider: object | None = None,
    knowledge_service: object | None = None,
) -> OwlBearAgent:
    """Construct an OwlBearAgent with optional board_context_provider and knowledge_service."""
    return OwlBearAgent(
        model="test",
        session=SessionStore(tmp_path / "s.jsonl"),
        board_context_provider=board_context_provider,
        knowledge_service=knowledge_service,
    )


def _wire_mock_inner(agent: OwlBearAgent, output: str = "ok") -> MagicMock:
    """Replace agent.inner with a mock and return the mock run."""
    mock = _mock_result(output, _simple_messages())
    agent.inner = MagicMock()
    agent.inner.run = AsyncMock(return_value=mock)
    return agent.inner.run


# ---------------------------------------------------------------------------
# AC 1: OwlBearAgent.__init__ accepts optional board_context_provider
# ---------------------------------------------------------------------------


class TestFromAC_BoardContextInit:
    """OwlBearAgent.__init__ accepts optional board_context_provider parameter."""

    def test_init_defaults_provider_to_none(self, tmp_path: Path) -> None:
        """board_context_provider defaults to None when not provided."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        assert agent._board_context_provider is None

    def test_init_accepts_provider(self, tmp_path: Path) -> None:
        """board_context_provider can be set via __init__."""
        provider = AsyncMock()
        agent = _make_agent(tmp_path, board_context_provider=provider)
        assert agent._board_context_provider is provider


# ---------------------------------------------------------------------------
# AC 2: turn() calls board_context_provider.get_context() before knowledge
# AC 3: Board context and knowledge context concatenated
# AC 5: No instructions= kwarg when both sources return None/empty
# AC 8: Unit tests covering all combinations
# ---------------------------------------------------------------------------


class TestFromAC_BoardContextTurnConcatenation:
    """turn() merges board and knowledge context into instructions= string."""

    def test_turn_calls_get_context(self, tmp_path: Path) -> None:
        """When provider is set, turn() calls get_context()."""
        provider = AsyncMock()
        provider.get_context.return_value = "Board: 3 tasks in-progress"
        agent = _make_agent(tmp_path, board_context_provider=provider)
        _wire_mock_inner(agent)

        asyncio.run(agent.turn("What should I work on?"))

        provider.get_context.assert_called_once()

    def test_board_only_passed_as_instructions(self, tmp_path: Path) -> None:
        """When only board provider returns content, instructions= is board text."""
        provider = AsyncMock()
        provider.get_context.return_value = "Board: 3 tasks"
        agent = _make_agent(tmp_path, board_context_provider=provider)
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        assert call_kwargs.kwargs["instructions"] == "Board: 3 tasks"

    def test_knowledge_only_passed_as_instructions(self, tmp_path: Path) -> None:
        """When only knowledge service returns content, instructions= is knowledge text."""
        svc = MagicMock()
        svc.query_for_context.return_value = "Relevant knowledge: snippet"
        agent = _make_agent(tmp_path, knowledge_service=svc)
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        assert call_kwargs.kwargs["instructions"] == "Relevant knowledge: snippet"

    def test_both_sources_concatenated(self, tmp_path: Path) -> None:
        """When both return content, board comes first, separated by double newline."""
        provider = AsyncMock()
        provider.get_context.return_value = "Board: 3 tasks"
        svc = MagicMock()
        svc.query_for_context.return_value = "Knowledge: doc snippet"

        agent = _make_agent(
            tmp_path,
            board_context_provider=provider,
            knowledge_service=svc,
        )
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        instructions = call_kwargs.kwargs["instructions"]
        # Board first, knowledge second
        assert instructions.startswith("Board: 3 tasks")
        assert "Knowledge: doc snippet" in instructions
        assert instructions == "Board: 3 tasks\n\nKnowledge: doc snippet"

    def test_no_instructions_when_neither_source_has_content(self, tmp_path: Path) -> None:
        """When both sources return None/empty, instructions= kwarg is not passed."""
        provider = AsyncMock()
        provider.get_context.return_value = ""
        svc = MagicMock()
        svc.query_for_context.return_value = None

        agent = _make_agent(
            tmp_path,
            board_context_provider=provider,
            knowledge_service=svc,
        )
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        assert "instructions" not in call_kwargs.kwargs

    def test_no_instructions_when_no_provider_and_no_service(self, tmp_path: Path) -> None:
        """When neither provider nor service is configured, no instructions= kwarg."""
        agent = _make_agent(tmp_path)
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        assert "instructions" not in call_kwargs.kwargs

    def test_board_empty_string_skipped(self, tmp_path: Path) -> None:
        """Provider returning empty string is treated as no board context."""
        provider = AsyncMock()
        provider.get_context.return_value = ""
        svc = MagicMock()
        svc.query_for_context.return_value = "Knowledge only"

        agent = _make_agent(
            tmp_path,
            board_context_provider=provider,
            knowledge_service=svc,
        )
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        # Should be knowledge only, not "\n\nKnowledge only"
        assert call_kwargs.kwargs["instructions"] == "Knowledge only"

    def test_knowledge_none_with_board_present(self, tmp_path: Path) -> None:
        """Knowledge service returning None with board present → board only."""
        provider = AsyncMock()
        provider.get_context.return_value = "Board state"
        svc = MagicMock()
        svc.query_for_context.return_value = None

        agent = _make_agent(
            tmp_path,
            board_context_provider=provider,
            knowledge_service=svc,
        )
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        assert call_kwargs.kwargs["instructions"] == "Board state"


# ---------------------------------------------------------------------------
# AC 2: turn() calls board context BEFORE knowledge service
# ---------------------------------------------------------------------------


class TestFromAC_BoardContextCallOrder:
    """Board context provider is called before knowledge service."""

    def test_provider_called_before_knowledge_service(self, tmp_path: Path) -> None:
        """get_context() is called before query_for_context() in turn()."""
        call_order: list[str] = []

        async def fake_get_context() -> str:
            call_order.append("board")
            return "board ctx"

        provider = AsyncMock()
        provider.get_context = fake_get_context

        svc = MagicMock()

        def fake_query(_prompt: str) -> str:
            call_order.append("knowledge")
            return "knowledge ctx"

        svc.query_for_context = fake_query

        agent = _make_agent(
            tmp_path,
            board_context_provider=provider,
            knowledge_service=svc,
        )
        _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        assert call_order == ["board", "knowledge"]


# ---------------------------------------------------------------------------
# AC 4: Graceful degradation — provider exception → log WARNING, continue
# ---------------------------------------------------------------------------


class TestFromAC_BoardContextGracefulDegradation:
    """Provider exceptions are caught, logged, and the turn continues."""

    def test_turn_continues_on_provider_exception(self, tmp_path: Path) -> None:
        """When provider.get_context() raises, turn() still succeeds."""
        provider = AsyncMock()
        provider.get_context.side_effect = RuntimeError("subprocess failed")

        agent = _make_agent(tmp_path, board_context_provider=provider)
        _wire_mock_inner(agent)

        result = asyncio.run(agent.turn("hi"))
        assert result == "ok"

    def test_provider_exception_no_instructions(self, tmp_path: Path) -> None:
        """When provider raises and no knowledge service, no instructions= passed."""
        provider = AsyncMock()
        provider.get_context.side_effect = OSError("cmd not found")

        agent = _make_agent(tmp_path, board_context_provider=provider)
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        assert "instructions" not in call_kwargs.kwargs

    def test_provider_exception_knowledge_still_used(self, tmp_path: Path) -> None:
        """When provider raises but knowledge service works, knowledge used alone."""
        provider = AsyncMock()
        provider.get_context.side_effect = RuntimeError("board dead")
        svc = MagicMock()
        svc.query_for_context.return_value = "Knowledge ctx"

        agent = _make_agent(
            tmp_path,
            board_context_provider=provider,
            knowledge_service=svc,
        )
        run_mock = _wire_mock_inner(agent)

        asyncio.run(agent.turn("hi"))

        call_kwargs = run_mock.call_args
        assert call_kwargs.kwargs["instructions"] == "Knowledge ctx"

    def test_provider_exception_logs_warning(self, tmp_path: Path) -> None:
        """Provider exception is logged at WARNING level."""
        provider = AsyncMock()
        provider.get_context.side_effect = RuntimeError("boom")

        agent = _make_agent(tmp_path, board_context_provider=provider)
        _wire_mock_inner(agent)

        with patch("owlbear.core.agent.logger") as mock_logger:
            asyncio.run(agent.turn("hi"))
            mock_logger.warning.assert_called()
            # Check that at least one warning mentions board context
            warning_msgs = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("oard" in msg or "board" in msg.lower() for msg in warning_msgs)

    def test_both_raise_no_instructions(self, tmp_path: Path) -> None:
        """When both provider and knowledge service raise, no instructions= kwarg."""
        provider = AsyncMock()
        provider.get_context.side_effect = RuntimeError("board dead")
        svc = MagicMock()
        svc.query_for_context.side_effect = RuntimeError("knowledge dead")

        agent = _make_agent(
            tmp_path,
            board_context_provider=provider,
            knowledge_service=svc,
        )
        run_mock = _wire_mock_inner(agent)

        result = asyncio.run(agent.turn("hi"))
        assert result == "ok"

        call_kwargs = run_mock.call_args
        assert "instructions" not in call_kwargs.kwargs


# ---------------------------------------------------------------------------
# AC 6: Config — board_context_enabled bool in OwlBearSettings (default True)
# ---------------------------------------------------------------------------


class TestFromAC_BoardContextConfig:
    """OwlBearSettings has board_context_enabled bool, default True."""

    def test_default_is_true(self) -> None:
        """board_context_enabled defaults to True."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert settings.board_context_enabled is True

    def test_env_override_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """board_context_enabled can be set to False via env var."""
        from owlbear.config import OwlBearSettings

        monkeypatch.setenv("OWLBEAR_BOARD_CONTEXT_ENABLED", "false")
        settings = OwlBearSettings()
        assert settings.board_context_enabled is False

    def test_env_override_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """board_context_enabled can be set to True via env var."""
        from owlbear.config import OwlBearSettings

        monkeypatch.setenv("OWLBEAR_BOARD_CONTEXT_ENABLED", "true")
        settings = OwlBearSettings()
        assert settings.board_context_enabled is True


# ---------------------------------------------------------------------------
# AC 7: Bootstrap wiring
# ---------------------------------------------------------------------------


class TestFromAC_BoardContextBootstrap:
    """Bootstrap constructs BoardContextProvider when enabled and passes to agent."""

    @pytest.mark.asyncio
    async def test_bootstrap_passes_provider_when_enabled(self, tmp_path: Path) -> None:
        """When board_context_enabled=True, bootstrap passes a BoardContextProvider to agent."""
        from owlbear.bootstrap import bootstrap
        from owlbear.core.board_context import BoardContextProvider

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings_cls = _import_settings()
        settings = settings_cls(board_context_enabled=True)

        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.agent._board_context_provider is not None
        assert isinstance(result.agent._board_context_provider, BoardContextProvider)

    @pytest.mark.asyncio
    async def test_bootstrap_no_provider_when_disabled(self, tmp_path: Path) -> None:
        """When board_context_enabled=False, agent gets board_context_provider=None."""
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings_cls = _import_settings()
        settings = settings_cls(board_context_enabled=False)

        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.agent._board_context_provider is None

    def test_provider_has_async_get_context(self) -> None:
        """BoardContextProvider must have an async get_context() method."""
        from owlbear.core.board_context import BoardContextProvider

        provider = BoardContextProvider.__new__(BoardContextProvider)
        assert hasattr(provider, "get_context")
        assert asyncio.iscoroutinefunction(provider.get_context)

    @pytest.mark.asyncio
    async def test_bootstrap_provider_default_matches_config_default(self, tmp_path: Path) -> None:
        """Default settings (board_context_enabled=True) → provider is wired."""
        from owlbear.bootstrap import bootstrap
        from owlbear.core.board_context import BoardContextProvider

        settings_cls = _import_settings()
        settings = settings_cls()  # defaults

        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        # Default is enabled, so provider must be wired
        assert isinstance(result.agent._board_context_provider, BoardContextProvider)
