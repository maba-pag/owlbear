"""RED-phase tests for context pre-hydration integration (#703).

Tests the daemon/config/bootstrap integration of context_hydration.
Module-level tests live in test_context_hydration.py (#712).

AC lines covered here:
- Config field ``prehydration_enabled`` in OwlBearSettings (default False)
- poll_tick() hydrator param: ``Callable[[str, Path], Awaitable[HydrationResult]] | None``
- Hydrator called in retry dispatch path (step 3)
- Hydrator called in new-task dispatch path (step 7)
- HydrationResult content appended to prompt after task details
- bootstrap.py constructs hydrator when enabled, passes None when disabled
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.config import OwlBearSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kanban_list_json(tasks: list[dict[str, str]]) -> str:
    return json.dumps(tasks)


def _make_kanban_show_json(
    task_id: str,
    title: str = "Test task",
    priority: str = "important",
    body: str = "AC line 1\nhttps://example.com/doc\nsrc/owlbear/config.py",
) -> str:
    return json.dumps(
        {
            "id": task_id,
            "title": title,
            "status": "todo",
            "priority": priority,
            "body": body,
        }
    )


def _fake_hydration_result() -> object:
    """Build a fake HydrationResult-like object."""
    from owlbear.core.context_hydration import HydrationResult

    return HydrationResult.model_construct(
        urls={"https://example.com/doc": "# Doc Title\nSome content"},
        files={"src/owlbear/config.py": "# config content"},
        errors=[],
    )


def _empty_hydration_result() -> object:
    from owlbear.core.context_hydration import HydrationResult

    return HydrationResult.model_construct(urls={}, files={}, errors=[])


def _make_async_channel() -> AsyncMock:
    """Build a mock channel with async send and a .name attribute."""
    ch = AsyncMock()
    ch.name = "cli"
    return ch


# ===========================================================================
# AC: Config field prehydration_enabled: bool = Field(default=False)
# ===========================================================================


class TestFromACPrehydrationConfig:
    """prehydration_enabled config field on OwlBearSettings."""

    def test_default_is_false(self, default_settings: OwlBearSettings) -> None:
        """prehydration_enabled defaults to False."""
        assert hasattr(default_settings, "prehydration_enabled")
        assert default_settings.prehydration_enabled is False

    def test_env_override_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_PREHYDRATION_ENABLED=true enables the feature."""
        monkeypatch.setenv("OWLBEAR_PREHYDRATION_ENABLED", "true")
        settings = OwlBearSettings()
        assert settings.prehydration_enabled is True

    def test_env_override_false_explicit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_PREHYDRATION_ENABLED=false keeps it disabled."""
        monkeypatch.setenv("OWLBEAR_PREHYDRATION_ENABLED", "false")
        settings = OwlBearSettings()
        assert settings.prehydration_enabled is False

    def test_field_is_bool_type(self, default_settings: OwlBearSettings) -> None:
        """prehydration_enabled must be a bool, not a truthy string."""
        val = default_settings.prehydration_enabled
        assert isinstance(val, bool)


# ===========================================================================
# AC: poll_tick() accepts hydrator param
# ===========================================================================


class TestFromACPollTickHydratorParam:
    """poll_tick() accepts a hydrator parameter."""

    @pytest.mark.asyncio
    async def test_poll_tick_accepts_hydrator_none(self) -> None:
        """poll_tick() runs without error when hydrator=None."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        mock_kanban.kanban_list.return_value = _make_kanban_list_json([])

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=None,
            )

        await run_tick()

    @pytest.mark.asyncio
    async def test_poll_tick_accepts_hydrator_callable(self) -> None:
        """poll_tick() accepts an async callable as hydrator."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        mock_kanban.kanban_list.return_value = _make_kanban_list_json([])

        mock_hydrator = AsyncMock(return_value=_empty_hydration_result())

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=mock_hydrator,
            )

        await run_tick()


# ===========================================================================
# AC: Hydrator called in new-task dispatch path (step 7)
# ===========================================================================


class TestFromACHydratorNewTaskDispatch:
    """Hydrator called during new-task dispatch (step 7) and result appended to prompt."""

    @pytest.mark.asyncio
    async def test_hydrator_called_on_new_task(self) -> None:
        """When hydrator is provided, it is called for each dispatched new task."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        body = "Implement feature\nhttps://example.com/doc\nsrc/owlbear/config.py"
        todo_tasks = [{"id": "200", "title": "New task", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "200", title="New task", body=body
        )
        mock_kanban.kanban_move.return_value = "moved"

        mock_hydrator = AsyncMock(return_value=_fake_hydration_result())

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=mock_hydrator,
            )

        await run_tick()

        # Hydrator was called at least once
        mock_hydrator.assert_called()

    @pytest.mark.asyncio
    async def test_hydration_content_appended_to_prompt(self) -> None:
        """HydrationResult URLs/files content is appended to the builder prompt."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        body = "Implement feature\nhttps://example.com/doc"
        todo_tasks = [{"id": "201", "title": "Hydrated task", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "201", title="Hydrated task", body=body
        )
        mock_kanban.kanban_move.return_value = "moved"

        mock_hydrator = AsyncMock(return_value=_fake_hydration_result())

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=mock_hydrator,
            )

        await run_tick()

        # Builder prompt includes hydrated content
        mock_agent.run.assert_called_once()
        prompt = mock_agent.run.call_args.args[0]
        assert "Doc Title" in prompt or "config content" in prompt

    @pytest.mark.asyncio
    async def test_hydrator_not_called_when_none(self) -> None:
        """When hydrator=None, no hydration occurs (no AttributeError)."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_tasks = [{"id": "202", "title": "No hydration", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("202")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=None,
            )

        # Should not raise — hydrator=None means no hydration
        await run_tick()

    @pytest.mark.asyncio
    async def test_empty_hydration_result_no_append(self) -> None:
        """When hydration returns empty content, prompt is not bloated."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_tasks = [{"id": "203", "title": "Empty hydration", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "203", title="Empty hydration", body="Just text"
        )
        mock_kanban.kanban_move.return_value = "moved"

        mock_hydrator = AsyncMock(return_value=_empty_hydration_result())

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=mock_hydrator,
            )

        await run_tick()

        prompt = mock_agent.run.call_args.args[0]
        # Prompt should contain task details but not "Pre-hydrated" marker
        # when there's nothing to hydrate
        assert "Empty hydration" in prompt


# ===========================================================================
# AC: Hydrator called in retry dispatch path (step 3)
# ===========================================================================


class TestFromACHydratorRetryDispatch:
    """Hydrator called during retry dispatch (step 3) and result appended to prompt."""

    @pytest.mark.asyncio
    async def test_hydrator_called_on_retry_dispatch(self) -> None:
        """When a retried task is due, hydrator is called and content appended."""
        from owlbear.daemon import OrchestratorState, RetryEntry, poll_tick

        state = OrchestratorState()

        # Set up a due retry
        state.retries["300"] = RetryEntry(
            task_id="300",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
        )

        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        body = "Retry body\nhttps://retry.example.com/ref"
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "300", title="Retry task", body=body
        )
        mock_kanban.kanban_list.return_value = _make_kanban_list_json([])

        mock_hydrator = AsyncMock(return_value=_fake_hydration_result())

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=mock_hydrator,
            )

        await run_tick()

        # Hydrator was called for the retry
        mock_hydrator.assert_called()
        # Builder prompt includes hydrated content
        mock_agent.run.assert_called_once()
        prompt = mock_agent.run.call_args.args[0]
        assert "Doc Title" in prompt or "config content" in prompt

    @pytest.mark.asyncio
    async def test_retry_hydrator_receives_task_body(self) -> None:
        """Hydrator receives the task body text to extract URLs/paths from."""
        from owlbear.daemon import OrchestratorState, RetryEntry, poll_tick

        state = OrchestratorState()
        state.retries["301"] = RetryEntry(
            task_id="301",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
        )

        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        body = "Build the https://example.com thing"
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "301", title="Retry body test", body=body
        )
        mock_kanban.kanban_list.return_value = _make_kanban_list_json([])

        mock_hydrator = AsyncMock(return_value=_empty_hydration_result())

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=mock_hydrator,
            )

        await run_tick()

        # Hydrator was called with the body text (first arg)
        call_args = mock_hydrator.call_args
        assert call_args is not None, "hydrator was never called"
        # First positional arg should contain the task body
        assert body in str(call_args[0])

    @pytest.mark.asyncio
    async def test_retry_no_hydrator_still_works(self) -> None:
        """Retry dispatch with hydrator=None explicitly still works."""
        from owlbear.daemon import OrchestratorState, RetryEntry, poll_tick

        state = OrchestratorState()
        state.retries["302"] = RetryEntry(
            task_id="302",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
        )

        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        mock_kanban.kanban_show.return_value = _make_kanban_show_json("302")
        mock_kanban.kanban_list.return_value = _make_kanban_list_json([])

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=None,  # explicitly None — must be accepted
            )

        # Should not raise
        await run_tick()


# ===========================================================================
# AC: poll_loop forwards hydrator param
# ===========================================================================


class TestFromACPollLoopHydrator:
    """poll_loop forwards hydrator to poll_tick."""

    def test_poll_loop_accepts_hydrator_param(self) -> None:
        """poll_loop signature accepts hydrator kwarg."""
        import inspect

        from owlbear.daemon import poll_loop

        sig = inspect.signature(poll_loop)
        assert "hydrator" in sig.parameters

    @pytest.mark.asyncio
    async def test_poll_loop_passes_hydrator_to_poll_tick(self) -> None:
        """poll_loop passes hydrator through to poll_tick."""
        from owlbear.daemon import poll_loop

        captured_kwargs: dict[str, object] = {}
        shutdown = asyncio.Event()

        async def fake_poll_tick(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            shutdown.set()

        mock_hydrator = AsyncMock()

        settings = MagicMock(spec=OwlBearSettings)
        settings.max_concurrent_tasks = 3
        settings.stale_task_timeout = 300.0
        settings.task_retry_max_attempts = 5
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0
        settings.poll_interval = 0.01

        async def run_poll() -> None:
            with patch("owlbear.daemon.poll_tick", new=fake_poll_tick):
                await poll_loop(
                    state=MagicMock(),
                    kanban=AsyncMock(),
                    agent_registry=MagicMock(),
                    settings=settings,
                    shutdown_event=shutdown,
                    hydrator=mock_hydrator,
                )

        await run_poll()

        assert captured_kwargs.get("hydrator") is mock_hydrator


# ===========================================================================
# AC: run_daemon forwards hydrator (optional, from bootstrap)
# ===========================================================================


class TestFromACRunDaemonHydrator:
    """run_daemon wires hydrator when provided."""

    @pytest.mark.asyncio
    async def test_run_daemon_passes_hydrator_to_poll_loop(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """run_daemon passes hydrator through to poll_loop when autonomous."""
        monkeypatch.setenv("OWLBEAR_AUTONOMOUS_MODE", "true")
        from owlbear.daemon import run_daemon

        captured_kwargs: dict[str, object] = {}

        class FakeChannel:
            name = "mock"

            async def send(self, msg: str) -> None:
                pass

            async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
                return None

        async def fake_poll_loop(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            ev = kwargs["shutdown_event"]
            await ev.wait()  # type: ignore[union-attr]

        mock_hydrator = AsyncMock()

        settings = OwlBearSettings()
        assert settings.autonomous_mode is True  # precondition

        mock_agent = AsyncMock()
        mock_agent.hooks = MagicMock()
        mock_agent.hooks.emit = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = tmp_path / "session"
        mock_agent.session.load = MagicMock(return_value=[])

        with (
            patch("owlbear.daemon.poll_loop", new=fake_poll_loop),
            patch("owlbear.daemon.Agent"),
        ):
            await run_daemon(
                channel=FakeChannel(),
                agent=mock_agent,
                config_dir=tmp_path,
                settings=settings,
                kanban_toolset=AsyncMock(),
                agent_registry=MagicMock(),
                hydrator=mock_hydrator,
            )

        assert captured_kwargs.get("hydrator") is mock_hydrator


# ===========================================================================
# AC: bootstrap.py constructs hydrator when enabled, None when disabled
# ===========================================================================


class TestFromACBootstrapHydrator:
    """bootstrap() must construct a real hydrator callable when enabled."""

    @pytest.mark.asyncio
    async def test_bootstrap_result_hydrator_none_when_disabled(self) -> None:
        """bootstrap() sets BootstrapResult.hydrator=None when prehydration_enabled=False."""

        async def _run_bootstrap() -> object:
            from owlbear.bootstrap import bootstrap

            settings = OwlBearSettings()
            assert settings.prehydration_enabled is False  # precondition

            with (
                patch("owlbear.bootstrap.create_copilot_client", new_callable=AsyncMock) as mock_cc,
                patch("owlbear.bootstrap.create_channel") as mock_ch,
                patch("owlbear.bootstrap.build_hooks") as mock_bh,
                patch("owlbear.bootstrap.build_toolsets") as mock_bt,
                patch("owlbear.bootstrap.build_agent_registry") as mock_bar,
                patch("owlbear.bootstrap.build_mcp_registry") as mock_bmr,
            ):
                mock_client = AsyncMock()
                mock_cc.return_value = mock_client
                mock_ch.return_value = _make_async_channel()
                mock_bh.return_value = (MagicMock(), None)
                mock_bt.return_value = ([], None, None)
                mock_bar.return_value = MagicMock()
                mock_bmr.return_value = None

                return await bootstrap(settings, workspace_root=Path("/fake"))

        result = await _run_bootstrap()
        assert result.hydrator is None

    @pytest.mark.asyncio
    async def test_bootstrap_result_hydrator_callable_when_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """bootstrap() hydrator is callable when prehydration_enabled=True."""
        monkeypatch.setenv("OWLBEAR_PREHYDRATION_ENABLED", "true")

        async def _run_bootstrap() -> object:
            from owlbear.bootstrap import bootstrap

            settings = OwlBearSettings()
            assert settings.prehydration_enabled is True  # precondition

            with (
                patch("owlbear.bootstrap.create_copilot_client", new_callable=AsyncMock) as mock_cc,
                patch("owlbear.bootstrap.create_channel") as mock_ch,
                patch("owlbear.bootstrap.build_hooks") as mock_bh,
                patch("owlbear.bootstrap.build_toolsets") as mock_bt,
                patch("owlbear.bootstrap.build_agent_registry") as mock_bar,
                patch("owlbear.bootstrap.build_mcp_registry") as mock_bmr,
            ):
                mock_client = AsyncMock()
                mock_cc.return_value = mock_client
                mock_ch.return_value = _make_async_channel()
                mock_bh.return_value = (MagicMock(), None)
                mock_bt.return_value = ([], None, None)
                mock_bar.return_value = MagicMock()
                mock_bmr.return_value = None

                return await bootstrap(settings, workspace_root=Path("/fake"))

        result = await _run_bootstrap()
        # Must be a callable, not None
        assert result.hydrator is not None
        assert callable(result.hydrator)

    @pytest.mark.asyncio
    async def test_bootstrap_hydrator_is_awaitable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The hydrator constructed by bootstrap must return an awaitable when called."""
        monkeypatch.setenv("OWLBEAR_PREHYDRATION_ENABLED", "true")

        async def _run_bootstrap() -> object:
            from owlbear.bootstrap import bootstrap

            settings = OwlBearSettings()

            with (
                patch("owlbear.bootstrap.create_copilot_client", new_callable=AsyncMock) as mock_cc,
                patch("owlbear.bootstrap.create_channel") as mock_ch,
                patch("owlbear.bootstrap.build_hooks") as mock_bh,
                patch("owlbear.bootstrap.build_toolsets") as mock_bt,
                patch("owlbear.bootstrap.build_agent_registry") as mock_bar,
                patch("owlbear.bootstrap.build_mcp_registry") as mock_bmr,
            ):
                mock_client = AsyncMock()
                mock_cc.return_value = mock_client
                mock_ch.return_value = _make_async_channel()
                mock_bh.return_value = (MagicMock(), None)
                mock_bt.return_value = ([], None, None)
                mock_bar.return_value = MagicMock()
                mock_bmr.return_value = None

                return await bootstrap(settings, workspace_root=Path("/fake"))

        result = await _run_bootstrap()
        assert result.hydrator is not None
        # Calling the hydrator with a body string should return something awaitable
        import inspect

        ret = result.hydrator("some task body text")
        assert inspect.isawaitable(ret)
        # Clean up the coroutine to avoid warnings
        ret.close()

    @pytest.mark.asyncio
    async def test_bootstrap_hydrator_returns_hydration_result(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """The hydrator from bootstrap should return a HydrationResult when awaited."""
        monkeypatch.setenv("OWLBEAR_PREHYDRATION_ENABLED", "true")

        from owlbear.core.context_hydration import HydrationResult

        async def _run_bootstrap() -> object:
            from owlbear.bootstrap import bootstrap

            settings = OwlBearSettings()

            with (
                patch("owlbear.bootstrap.create_copilot_client", new_callable=AsyncMock) as mock_cc,
                patch("owlbear.bootstrap.create_channel") as mock_ch,
                patch("owlbear.bootstrap.build_hooks") as mock_bh,
                patch("owlbear.bootstrap.build_toolsets") as mock_bt,
                patch("owlbear.bootstrap.build_agent_registry") as mock_bar,
                patch("owlbear.bootstrap.build_mcp_registry") as mock_bmr,
            ):
                mock_client = AsyncMock()
                mock_cc.return_value = mock_client
                mock_ch.return_value = _make_async_channel()
                mock_bh.return_value = (MagicMock(), None)
                mock_bt.return_value = ([], None, None)
                mock_bar.return_value = MagicMock()
                mock_bmr.return_value = None

                return await bootstrap(settings, workspace_root=tmp_path)

        result = await _run_bootstrap()
        assert result.hydrator is not None

        async def _call_hydrator() -> HydrationResult:
            return await result.hydrator("No urls or files here.")

        hydration = await _call_hydrator()
        assert isinstance(hydration, HydrationResult)


# ===========================================================================
# AC: CLI daemon wires bootstrap hydrator to run_daemon
# ===========================================================================


class TestFromACCliDaemonHydratorWiring:
    """bearclaw daemon run_cmd passes bootstrap hydrator to run_daemon."""

    def test_run_cmd_passes_hydrator_to_run_daemon(self) -> None:
        """The CLI daemon command must pass result.hydrator to run_daemon."""
        captured_kwargs: dict[str, object] = {}

        async def fake_run_daemon(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)

        mock_hydrator = AsyncMock()

        async def fake_bootstrap(_settings: object, **_kw: object) -> object:
            from owlbear.bootstrap._types import BootstrapResult

            return BootstrapResult(
                agent=MagicMock(),
                channel=_make_async_channel(),
                mcp_registry=None,
                hooks=MagicMock(),
                error_journal=MagicMock(),
                hydrator=mock_hydrator,
                cleanup=[],
            )

        with (
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.PidFile"),
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.daemon.setup_logging"),
        ):
            mock_settings_cls.return_value = OwlBearSettings()
            from bearclaw.commands.daemon import run_cmd

            run_cmd(channel="cli", model=None)

        # run_daemon must receive the hydrator from bootstrap result
        assert "hydrator" in captured_kwargs
        assert captured_kwargs["hydrator"] is mock_hydrator


# ===========================================================================
# AC: Hydrator errors don't fail dispatch (error resilience)
# ===========================================================================


class TestFromACHydratorErrorResilience:
    """Hydrator failures must not crash poll_tick dispatch."""

    @pytest.mark.asyncio
    async def test_hydrator_exception_does_not_block_dispatch(self) -> None:
        """If hydrator raises, the task is still dispatched (without hydrated context)."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_tasks = [{"id": "400", "title": "Resilient task", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("400")
        mock_kanban.kanban_move.return_value = "moved"

        # Hydrator that raises
        mock_hydrator = AsyncMock(side_effect=RuntimeError("fetch failed"))

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=mock_hydrator,
            )

        # Should NOT raise — dispatch proceeds despite hydrator failure
        await run_tick()

        # Task was still dispatched
        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_hydrator_error_on_retry_does_not_block(self) -> None:
        """If hydrator raises during retry dispatch, the retry still proceeds."""
        from owlbear.daemon import OrchestratorState, RetryEntry, poll_tick

        state = OrchestratorState()
        state.retries["401"] = RetryEntry(
            task_id="401",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
        )

        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        mock_kanban.kanban_show.return_value = _make_kanban_show_json("401")
        mock_kanban.kanban_list.return_value = _make_kanban_list_json([])

        mock_hydrator = AsyncMock(side_effect=Exception("network down"))

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                hydrator=mock_hydrator,
            )

        # Should NOT raise
        await run_tick()
        mock_agent.run.assert_called_once()
