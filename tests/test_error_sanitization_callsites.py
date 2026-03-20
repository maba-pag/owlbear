"""Tests for error_to_user_message() integration at channel-facing call sites.

Task #606: Verify every channel.send / typer.echo that interpolates an exception
variable wraps it in error_to_user_message() so raw exception internals never
reach the user.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from conftest import MockChannel  # type: ignore[import-untyped]
from typer.testing import CliRunner

from owlbear.core.deps import OwlBearDeps
from owlbear.core.hooks import HookRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

runner = CliRunner()


# ---------------------------------------------------------------------------
# daemon.py — 3 channel.send sites
# ---------------------------------------------------------------------------


class TestDaemonSanitisesErrors:
    """daemon._recover_from_error wraps exceptions in error_to_user_message."""

    @pytest.mark.asyncio
    async def test_transient_exhausted_sends_sanitized(self, tmp_path: Path) -> None:
        """After transient retries exhausted, channel gets safe message."""
        from owlbear.daemon import run_daemon

        exc = httpx.ConnectError("connection refused")
        channel = MockChannel(["hello", None])
        agent = AsyncMock()
        agent.turn = AsyncMock(side_effect=exc)

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock):
            await (run_daemon(channel=channel, agent=agent, config_dir=tmp_path))

        error_msgs = [m for m in channel.sent if m.startswith("Error:")]
        assert error_msgs
        # Must use sanitized "Connection failed", not raw "connection refused"
        assert "Connection failed" in error_msgs[0]
        assert "connection refused" not in error_msgs[0]

    @pytest.mark.asyncio
    async def test_auth_refresh_failure_sends_sanitized(self, tmp_path: Path) -> None:
        """Auth refresh path wraps retry_exc in error_to_user_message."""
        from owlbear.daemon import run_daemon

        # Trigger AUTH category
        auth_exc = httpx.HTTPStatusError(
            "Unauthorized",
            request=httpx.Request("GET", "https://api.example.com/secret?token=abc123"),
            response=httpx.Response(401),
        )
        channel = MockChannel(["hello", None])
        agent = AsyncMock()
        agent.turn = AsyncMock(side_effect=auth_exc)
        agent.update_model = MagicMock()

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("token refresh failed with secret_key=x"),
        ):
            await (
                run_daemon(
                    channel=channel,
                    agent=agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        error_msgs = [m for m in channel.sent if m.startswith("Error:")]
        assert error_msgs
        # Sensitive key value must be scrubbed
        assert "secret_key=x" not in error_msgs[0]

    @pytest.mark.asyncio
    async def test_permanent_error_sends_sanitized(self, tmp_path: Path) -> None:
        """Permanent errors use error_to_user_message, not raw str(exc)."""
        from owlbear.daemon import run_daemon

        exc = httpx.ConnectError("connection to https://api.secret.com/v1?key=abc refused")
        channel = MockChannel(["hello", None])
        agent = AsyncMock()
        agent.turn = AsyncMock(side_effect=exc)

        await (run_daemon(channel=channel, agent=agent, config_dir=tmp_path))

        error_msgs = [m for m in channel.sent if m.startswith("Error:")]
        assert error_msgs
        # ConnectError maps to "Connection failed" — URL with key never shown
        assert "Connection failed" in error_msgs[0]
        assert "key=abc" not in error_msgs[0]


# ---------------------------------------------------------------------------
# cli.py — REPL (_chat_loop) handler
# ---------------------------------------------------------------------------


class TestCliReplSanitisesErrors:
    """cli._chat_loop wraps exc in error_to_user_message before channel.send."""

    def test_repl_exception_sanitized(self) -> None:
        """REPL exception handler sends safe message, not raw exc."""
        from bearclaw.cli import app

        _FAKE_CONFIG = PurePosixPath("/fake/.owlbear")  # noqa: N806
        exc = httpx.ConnectError("secret-internal-host:8080 refused")

        settings = MagicMock()
        settings.chat_model = "gpt-4o"
        settings.config_dir = _FAKE_CONFIG
        settings_cls = MagicMock(return_value=settings)

        session = MagicMock()
        session.load.return_value = []
        session.path = _FAKE_CONFIG / "sessions" / "s.jsonl"
        session_cls = MagicMock(return_value=session)

        agent = MagicMock()
        agent.turn = AsyncMock(side_effect=exc)

        async def _fake_bootstrap(*_a: object, **_kw: object) -> MagicMock:
            from owlbear.channels.cli import CLIChannel

            result = MagicMock()
            result.agent = agent
            result.channel = CLIChannel()
            return result

        bootstrap_fn = AsyncMock(side_effect=_fake_bootstrap)

        with (
            patch("owlbear.config.OwlBearSettings", settings_cls),
            patch("bearclaw.commands.chat.SessionStore", session_cls),
            patch("bearclaw.commands.chat.bootstrap", bootstrap_fn),
        ):
            result = runner.invoke(app, ["chat"], input="hello\nexit\n")

        assert result.exit_code == 0
        # Must show sanitized message
        assert "Connection failed" in result.output
        assert "secret-internal-host" not in result.output


# ---------------------------------------------------------------------------
# cli.py — Slack auth & test commands
# ---------------------------------------------------------------------------


class TestCliSlackAuthSanitisesErrors:
    """Slack auth/test commands wrap HTTPError in error_to_user_message."""

    def test_slack_auth_sanitized(self) -> None:
        """slack auth typer.echo uses error_to_user_message."""
        from bearclaw.cli import app

        exc = httpx.HTTPStatusError(
            "error",
            request=httpx.Request("POST", "https://slack.com/api/auth.test"),
            response=httpx.Response(401),
        )
        with (
            patch("bearclaw.commands.slack._require_slack_settings") as mock_settings,
            patch("bearclaw.commands.slack._slack_ssl_context"),
            patch("bearclaw.commands.slack.httpx.post", side_effect=exc),
        ):
            mock_settings.return_value = MagicMock(
                slack_bot_token=MagicMock(get_secret_value=MagicMock(return_value="xoxb-fake")),
            )
            result = runner.invoke(app, ["slack", "auth"])

        assert result.exit_code != 0
        # Raw exc with request URL must not appear
        assert "xoxb-fake" not in result.output
        # Should contain the sanitized message
        assert "HTTP request failed" in result.output

    def test_slack_test_sanitized(self) -> None:
        """slack test typer.echo uses error_to_user_message."""
        from bearclaw.cli import app

        exc = httpx.HTTPStatusError(
            "error",
            request=httpx.Request("POST", "https://slack.com/api/chat.postMessage"),
            response=httpx.Response(500),
        )
        with (
            patch("bearclaw.commands.slack._require_slack_settings") as mock_settings,
            patch("bearclaw.commands.slack._slack_ssl_context"),
            patch("bearclaw.commands.slack.httpx.post", side_effect=exc),
        ):
            mock_settings.return_value = MagicMock(
                slack_bot_token=MagicMock(get_secret_value=MagicMock(return_value="xoxb-secret")),
                slack_channel_id="C123",
            )
            result = runner.invoke(app, ["slack", "test"])

        assert result.exit_code != 0
        assert "xoxb-secret" not in result.output
        assert "HTTP request failed" in result.output


# ---------------------------------------------------------------------------
# cli.py — Login
# ---------------------------------------------------------------------------


class TestCliLoginSanitisesErrors:
    """Login failure wraps exc in error_to_user_message."""

    def test_login_failure_sanitized(self) -> None:
        from bearclaw.cli import app

        exc = RuntimeError("OAuth token=ghp_XXXX123 exchange failed")
        with patch("bearclaw.commands.auth._login_async", side_effect=exc):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code != 0
        # Token value must be scrubbed from the output
        assert "ghp_XXXX123" not in result.output


# ---------------------------------------------------------------------------
# web_search.py — URL not leaked in error
# ---------------------------------------------------------------------------


class TestWebSearchSanitisesErrors:
    """WebSearchToolset._web_read wraps exc with error_to_user_message, strips URL."""

    @pytest.mark.asyncio
    async def test_url_not_in_error_message(self) -> None:
        from owlbear.tools.web_search import WebSearchToolset

        toolset = WebSearchToolset()
        url = "https://example.com/page?api_key=secret456"

        client = AsyncMock()
        client.get.side_effect = httpx.HTTPError("connection failed")
        cm = AsyncMock()
        cm.__aenter__.return_value = client
        cm.__aexit__.return_value = False

        with patch("owlbear.tools.web_search.httpx.AsyncClient", return_value=cm):
            result = await toolset._web_read(url)

        assert isinstance(result, str)
        # URL with api_key must not appear in the error
        assert "api_key=secret456" not in result
        assert url not in result


# ---------------------------------------------------------------------------
# delegation.py — wrapped in ToolError message
# ---------------------------------------------------------------------------


class TestDelegationSanitisesErrors:
    """DelegationToolset wraps exc in error_to_user_message."""

    @pytest.mark.asyncio
    async def test_delegation_failure_sanitized(self) -> None:
        from owlbear.core.delegation import DelegationToolset

        inner_agent = MagicMock()
        inner_agent.run = AsyncMock(
            side_effect=RuntimeError("connect to https://api.corp/v1?token=ghp_abc failed")
        )

        registry = MagicMock()
        registry.get.return_value = inner_agent
        registry.definitions = {"builder": MagicMock()}

        deps = OwlBearDeps(
            hooks=HookRegistry(),
            agent_registry=registry,
            delegation_depth=0,
        )
        ctx = MagicMock()
        ctx.deps = deps
        ctx.usage = MagicMock()

        ts = DelegationToolset()
        result = await (ts._delegate(ctx, agent_name="builder", task="do it"))

        parsed = json.loads(result)
        # Token must not appear in the error message
        assert "ghp_abc" not in parsed["message"]
        assert "token=" not in parsed["message"] or "REDACTED" in parsed["message"]
