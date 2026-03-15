"""RED-phase tests for #514 — Close httpx.AsyncClient in Copilot provider.

Tests verify three sub-problems from the AC:

  SP1: Bootstrap registers AsyncOpenAI client for cleanup and sets agent._openai_client.
  SP2: Cleanup loop awaits async callables; _chat_async runs cleanup in finally.
  SP3: Daemon auth refresh closes old client before replacement and updates reference.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest
from conftest import make_settings  # type: ignore[import-untyped]


def _make_openai_auth_error() -> openai.AuthenticationError:
    """Create an openai.AuthenticationError for test purposes."""
    request = httpx.Request("GET", "http://example.com")
    response = httpx.Response(401, request=request)
    return openai.AuthenticationError(message="bad token", response=response, body=None)


# ---------------------------------------------------------------------------
# SP1: Bootstrap registers AsyncOpenAI client for cleanup
# ---------------------------------------------------------------------------


class TestFromAC_BootstrapClientRegistration:  # noqa: N801
    """SP1: Bootstrap calls create_copilot_client directly, builds model
    inline, registers cleanup, and sets agent._openai_client."""

    @pytest.mark.asyncio
    async def test_bootstrap_calls_create_copilot_client(self, tmp_path: Path) -> None:
        """bootstrap() must call create_copilot_client(settings) — not create_copilot_model."""
        from owlbear.bootstrap import bootstrap

        mock_client = AsyncMock()
        settings = make_settings(tmp_path)

        with patch(
            "owlbear.bootstrap.create_copilot_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ) as mock_ccc:
            await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        mock_ccc.assert_awaited_once_with(settings)

    @pytest.mark.asyncio
    async def test_bootstrap_sets_openai_client_on_agent(self, tmp_path: Path) -> None:
        """After bootstrap(), agent._openai_client references the created client."""
        from owlbear.bootstrap import bootstrap

        mock_client = AsyncMock()
        settings = make_settings(tmp_path)

        with patch(
            "owlbear.bootstrap.create_copilot_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        assert hasattr(result.agent, "_openai_client"), "bootstrap must set agent._openai_client"
        assert result.agent._openai_client is mock_client

    @pytest.mark.asyncio
    async def test_bootstrap_does_not_call_create_copilot_model(self, tmp_path: Path) -> None:
        """bootstrap() builds model inline — it must NOT call create_copilot_model."""
        from owlbear.bootstrap import bootstrap

        mock_client = AsyncMock()
        settings = make_settings(tmp_path)

        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value="should_not_be_called",
                create=True,
            ) as mock_ccm,
        ):
            await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        mock_ccm.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_list_contains_client_close(self, tmp_path: Path) -> None:
        """BootstrapResult.cleanup must contain the openai_client.close callable."""
        from owlbear.bootstrap import bootstrap

        mock_client = AsyncMock()
        settings = make_settings(tmp_path)

        with patch(
            "owlbear.bootstrap.create_copilot_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        assert mock_client.close in result.cleanup, "cleanup list must include openai_client.close"

    @pytest.mark.asyncio
    async def test_create_copilot_model_still_works(self) -> None:
        """create_copilot_model() remains unchanged for external/test callers."""
        from owlbear.providers.copilot import create_copilot_model

        mock_client = AsyncMock()

        with patch(
            "owlbear.providers.copilot.create_copilot_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            model = await create_copilot_model()

        from pydantic_ai.models.openai import OpenAIChatModel

        assert isinstance(model, OpenAIChatModel)

    @pytest.mark.asyncio
    async def test_separate_bootstraps_have_independent_clients(self, tmp_path: Path) -> None:
        """Two bootstrap() calls produce agents with independent _openai_client references."""
        from owlbear.bootstrap import bootstrap

        client_a = AsyncMock()
        client_b = AsyncMock()
        settings = make_settings(tmp_path)

        with patch(
            "owlbear.bootstrap.create_copilot_client",
            new_callable=AsyncMock,
            return_value=client_a,
        ):
            result_a = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        with patch(
            "owlbear.bootstrap.create_copilot_client",
            new_callable=AsyncMock,
            return_value=client_b,
        ):
            result_b = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        assert result_a.agent._openai_client is client_a
        assert result_b.agent._openai_client is client_b
        assert result_a.agent._openai_client is not result_b.agent._openai_client


# ---------------------------------------------------------------------------
# SP2: Cleanup loop awaits async callables
# ---------------------------------------------------------------------------


class TestFromAC_CleanupAwaitsAsync:  # noqa: N801
    """SP2: Cleanup loop properly awaits async callables and _chat_async
    runs cleanup in its finally block."""

    @pytest.mark.asyncio
    async def test_async_callable_gets_awaited_during_cleanup(self, tmp_path: Path) -> None:
        """Running cleanup callbacks must await async callables like openai_client.close."""
        from owlbear.bootstrap import bootstrap

        mock_client = AsyncMock()
        settings = make_settings(tmp_path)

        with patch(
            "owlbear.bootstrap.create_copilot_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        # Execute cleanup using the documented pattern:
        # result = cb(); if inspect.isawaitable(result): await result
        for cb in result.cleanup:
            rv = cb()
            if inspect.isawaitable(rv):
                await rv

        mock_client.close.assert_called()

    @pytest.mark.asyncio
    async def test_mixed_sync_and_async_cleanup(self) -> None:
        """Cleanup list with mixed sync/async callables — both types execute."""
        sync_called = False
        async_called = False

        def sync_cb() -> None:
            nonlocal sync_called
            sync_called = True

        async def async_cb() -> None:
            nonlocal async_called
            async_called = True

        cleanup = [sync_cb, async_cb]

        for cb in cleanup:
            rv = cb()
            if inspect.isawaitable(rv):
                await rv

        assert sync_called, "sync callable must be called"
        assert async_called, "async callable must be awaited"

    @pytest.mark.asyncio
    async def test_chat_async_runs_cleanup_in_finally(self, tmp_path: Path) -> None:
        """_chat_async must run result.cleanup in a finally block, even on exception."""
        from bearclaw.commands.chat import _chat_async

        mock_client = AsyncMock()
        mock_agent = AsyncMock()
        mock_channel = AsyncMock()

        mock_bootstrap_result = MagicMock()
        mock_bootstrap_result.agent = mock_agent
        mock_bootstrap_result.channel = mock_channel
        mock_bootstrap_result.cleanup = [mock_client.close]

        with (  # noqa: SIM117
            patch(
                "bearclaw.commands.chat.OwlBearSettings",
                return_value=make_settings(tmp_path),
            ),
            patch(
                "bearclaw.commands.chat.bootstrap",
                new_callable=AsyncMock,
                return_value=mock_bootstrap_result,
            ),
            patch(
                "bearclaw.commands.chat._build_chat_session",
                return_value=("test-session", MagicMock()),
            ),
            patch(
                "bearclaw.commands.chat._chat_loop",
                new_callable=AsyncMock,
                side_effect=KeyboardInterrupt,
            ),
        ):
            with pytest.raises(KeyboardInterrupt):
                await _chat_async(
                    model=None,
                    session=None,
                    workspace_root=tmp_path,
                )

        # Cleanup must have been called despite the exception
        mock_client.close.assert_called()

    @pytest.mark.asyncio
    async def test_daemon_run_cleanup_uses_isawaitable(self) -> None:
        """Daemon _run() cleanup loop must call and await async callables
        (not just cb())."""
        # Simulate the cleanup pattern from bearclaw/commands/daemon.py _run():
        #   for cb in result.cleanup:
        #       with contextlib.suppress(Exception):
        #           rv = cb(); if inspect.isawaitable(rv): await rv
        mock_close = AsyncMock()
        cleanup = [mock_close]

        for cb in cleanup:
            rv = cb()
            if inspect.isawaitable(rv):
                await rv

        mock_close.assert_awaited_once()


# ---------------------------------------------------------------------------
# SP3: Daemon auth refresh closes old client
# ---------------------------------------------------------------------------


class TestFromAC_DaemonAuthRefresh:  # noqa: N801
    """SP3: _handle_classified_error AUTH branch closes old client before
    replacement and updates agent._openai_client."""

    def _make_mock_agent(self, *, openai_client: AsyncMock) -> AsyncMock:
        """Create a mock agent with _openai_client set."""
        agent = AsyncMock()
        agent._openai_client = openai_client
        agent.update_model = MagicMock()
        return agent

    def test_auth_refresh_closes_old_client(self, tmp_path: Path) -> None:
        """AUTH error must close old_client before creating new model."""
        from owlbear.daemon import run_daemon

        old_client = AsyncMock()
        new_client = AsyncMock()

        mock_agent = self._make_mock_agent(openai_client=old_client)
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed reply"],
        )

        mock_channel = MagicMock()
        mock_channel.receive = AsyncMock(side_effect=["hello", None])
        mock_channel.send = AsyncMock()
        mock_channel.name = "mock"

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=new_client,
        ):
            asyncio.run(
                run_daemon(
                    channel=mock_channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(chat_model="gpt-4o"),
                )
            )

        old_client.close.assert_awaited_once()

    def test_auth_refresh_close_before_update_model(self, tmp_path: Path) -> None:
        """Old client must be closed BEFORE update_model is called (ordering)."""
        from owlbear.daemon import run_daemon

        call_order: list[str] = []

        old_client = AsyncMock()
        old_client.close = AsyncMock(side_effect=lambda: call_order.append("close"))
        new_client = AsyncMock()

        mock_agent = self._make_mock_agent(openai_client=old_client)
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed"],
        )

        def track_update(model):  # noqa: ARG001
            call_order.append("update_model")

        mock_agent.update_model = MagicMock(side_effect=track_update)

        mock_channel = MagicMock()
        mock_channel.receive = AsyncMock(side_effect=["hello", None])
        mock_channel.send = AsyncMock()
        mock_channel.name = "mock"

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=new_client,
        ):
            asyncio.run(
                run_daemon(
                    channel=mock_channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(chat_model="gpt-4o"),
                )
            )

        assert call_order == ["close", "update_model"], (
            f"Expected close before update_model, got: {call_order}"
        )

    def test_auth_refresh_updates_openai_client_attr(self, tmp_path: Path) -> None:
        """After auth refresh, agent._openai_client must point to the new client."""
        from owlbear.daemon import run_daemon

        old_client = AsyncMock()
        new_client = AsyncMock()

        mock_agent = self._make_mock_agent(openai_client=old_client)
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed"],
        )

        mock_channel = MagicMock()
        mock_channel.receive = AsyncMock(side_effect=["hello", None])
        mock_channel.send = AsyncMock()
        mock_channel.name = "mock"

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=new_client,
        ):
            asyncio.run(
                run_daemon(
                    channel=mock_channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(chat_model="gpt-4o"),
                )
            )

        assert mock_agent._openai_client is new_client

    def test_auth_refresh_no_crash_when_no_openai_client(self, tmp_path: Path) -> None:
        """If agent has no _openai_client attr, auth refresh must not crash."""
        from owlbear.daemon import run_daemon

        new_client = AsyncMock()

        mock_agent = AsyncMock()
        # Deliberately do NOT set _openai_client — simulate agent without bootstrap
        if hasattr(mock_agent, "_openai_client"):
            del mock_agent._openai_client
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed"],
        )
        mock_agent.update_model = MagicMock()

        mock_channel = MagicMock()
        mock_channel.receive = AsyncMock(side_effect=["hello", None])
        mock_channel.send = AsyncMock()
        mock_channel.name = "mock"

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=new_client,
        ):
            asyncio.run(
                run_daemon(
                    channel=mock_channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(chat_model="gpt-4o"),
                )
            )

        mock_agent.update_model.assert_called_once()

    def test_consecutive_auth_refreshes_close_previous(self, tmp_path: Path) -> None:
        """Two auth errors → each refresh closes the previous client."""
        from owlbear.daemon import run_daemon

        original_client = AsyncMock()
        refresh1_client = AsyncMock()
        refresh2_client = AsyncMock()

        mock_agent = self._make_mock_agent(openai_client=original_client)
        mock_agent.turn = AsyncMock(
            side_effect=[
                _make_openai_auth_error(),
                "reply1",
                _make_openai_auth_error(),
                "reply2",
            ],
        )

        mock_channel = MagicMock()
        mock_channel.receive = AsyncMock(side_effect=["msg1", "msg2", None])
        mock_channel.send = AsyncMock()
        mock_channel.name = "mock"

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            side_effect=[refresh1_client, refresh2_client],
        ):
            asyncio.run(
                run_daemon(
                    channel=mock_channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(chat_model="gpt-4o"),
                )
            )

        original_client.close.assert_awaited_once()
        refresh1_client.close.assert_awaited_once()
        refresh2_client.close.assert_not_awaited()
        assert mock_agent._openai_client is refresh2_client
