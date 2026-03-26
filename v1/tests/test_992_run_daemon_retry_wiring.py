"""RED-phase tests for run_daemon() retry executor wiring — #992.

Tests describe the contract for AC3:

    In run_daemon() autonomous block, after state = OrchestratorState()
    and before asyncio.TaskGroup starts: if agent.hooks.reaction_executors
    is not None, set agent.hooks.reaction_executors["retry"] to
    make_retry_executor(state=state, kanban=kanban_toolset,
    max_attempts=settings.task_retry_max_attempts, ...).

All tests MUST FAIL until AC3 is implemented in owlbear.daemon.run_daemon().
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import MockChannel  # type: ignore[import-untyped]

from owlbear.core.hooks import HookRegistry
from owlbear.daemon import run_daemon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_agent(hooks: HookRegistry) -> MagicMock:
    """Build a mock agent backed by a real HookRegistry."""
    agent = MagicMock()
    agent.hooks = hooks
    agent.session = MagicMock()
    agent.session.path = Path("/fake/session")
    agent.session.load.return_value = []
    return agent


def _make_autonomous_settings() -> MagicMock:
    """Build mock settings for autonomous mode with retry config fields."""
    settings = MagicMock()
    settings.autonomous_mode = True
    settings.heartbeat_enabled = False
    settings.lint_gate_enabled = False
    settings.task_retry_max_attempts = 3
    settings.task_retry_backoff_base = 10.0
    settings.task_retry_backoff_max = 320.0
    return settings


async def _fake_poll_loop_exit(*, shutdown_event: asyncio.Event, **_kwargs: object) -> None:
    """poll_loop stub — signals shutdown immediately so run_daemon can exit."""
    shutdown_event.set()


async def _fake_channel_loop(
    shutdown_event: asyncio.Event,
    *_args: object,
    **_kwargs: object,
) -> None:
    """channel_loop stub — waits for shutdown signal then returns."""
    await shutdown_event.wait()


# ---------------------------------------------------------------------------
# AC3: run_daemon wires make_retry_executor into reaction_executors["retry"]
# ---------------------------------------------------------------------------


class TestFromAC_RunDaemonRetryWiring:
    """AC3: run_daemon wires make_retry_executor into hooks.reaction_executors['retry']
    when reaction_executors is not None in autonomous mode."""

    @pytest.mark.asyncio
    async def test_retry_executor_wired_when_reaction_executors_set(self, tmp_path: Path) -> None:
        """AC3 happy path: after run_daemon() in autonomous mode, reaction_executors['retry']
        is set to a callable."""
        hooks = HookRegistry()
        hooks.reaction_executors = {}  # not None — triggers wiring
        agent = _make_mock_agent(hooks)

        with (
            patch("owlbear.daemon.poll_loop", side_effect=_fake_poll_loop_exit),
            patch("owlbear.daemon.channel_loop", side_effect=_fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            await run_daemon(
                channel=MockChannel([None]),
                agent=agent,
                config_dir=tmp_path,
                settings=_make_autonomous_settings(),
                kanban_toolset=AsyncMock(),
                agent_registry=MagicMock(),
            )

        assert "retry" in hooks.reaction_executors
        assert callable(hooks.reaction_executors["retry"])

    @pytest.mark.asyncio
    async def test_retry_executor_wired_value_is_async_callable(self, tmp_path: Path) -> None:
        """AC3: the wired value must be an async callable (coroutine function)."""
        import asyncio as _asyncio

        hooks = HookRegistry()
        hooks.reaction_executors = {}
        agent = _make_mock_agent(hooks)

        with (
            patch("owlbear.daemon.poll_loop", side_effect=_fake_poll_loop_exit),
            patch("owlbear.daemon.channel_loop", side_effect=_fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            await run_daemon(
                channel=MockChannel([None]),
                agent=agent,
                config_dir=tmp_path,
                settings=_make_autonomous_settings(),
                kanban_toolset=AsyncMock(),
                agent_registry=MagicMock(),
            )

        executor = hooks.reaction_executors["retry"]
        assert _asyncio.iscoroutinefunction(executor)

    @pytest.mark.asyncio
    async def test_wired_executor_schedules_retry_on_failure(self, tmp_path: Path) -> None:
        """AC3 functional: the wired executor, when called with a failure payload,
        schedules a RetryEntry in the OrchestratorState that run_daemon creates."""
        from owlbear.daemon import OrchestratorState, RetryEntry

        hooks = HookRegistry()
        hooks.reaction_executors = {}
        agent = _make_mock_agent(hooks)

        captured_state: list[OrchestratorState] = []

        async def fake_poll_loop_capture(
            *, state: OrchestratorState, shutdown_event: asyncio.Event, **_kwargs: object
        ) -> None:
            captured_state.append(state)
            shutdown_event.set()

        with (
            patch("owlbear.daemon.poll_loop", side_effect=fake_poll_loop_capture),
            patch("owlbear.daemon.channel_loop", side_effect=_fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            await run_daemon(
                channel=MockChannel([None]),
                agent=agent,
                config_dir=tmp_path,
                settings=_make_autonomous_settings(),
                kanban_toolset=AsyncMock(),
                agent_registry=MagicMock(),
            )

        assert len(captured_state) == 1
        state = captured_state[0]
        executor = hooks.reaction_executors["retry"]

        # Invoke the executor with a failure payload
        await executor({"task_id": "99", "outcome": "failure", "error": "test-err"})

        assert "99" in state.retries
        entry = state.retries["99"]
        assert isinstance(entry, RetryEntry)
        assert entry.attempt == 1
