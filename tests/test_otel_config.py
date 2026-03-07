"""Tests for OTel configuration and Agent.instrument_all() at daemon startup.

Covers tasks #230 (tests), #216 (instrument_all), #218 (otel_endpoint config).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.config import OwlBearSettings

# ---------------------------------------------------------------------------
# Task #218 — otel_endpoint config field
# ---------------------------------------------------------------------------


class TestOtelEndpointConfig:
    """OwlBearSettings.otel_endpoint field behaviour."""

    def test_otel_endpoint_default_none(self, default_settings: OwlBearSettings) -> None:
        """otel_endpoint should be None by default."""
        assert default_settings.otel_endpoint is None

    def test_otel_endpoint_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_OTEL_ENDPOINT env var should set otel_endpoint."""
        monkeypatch.setenv("OWLBEAR_OTEL_ENDPOINT", "http://localhost:4318")
        settings = OwlBearSettings()
        assert settings.otel_endpoint == "http://localhost:4318"

    def test_otel_endpoint_accepts_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """otel_endpoint should accept any string URL."""
        monkeypatch.setenv("OWLBEAR_OTEL_ENDPOINT", "https://otel.example.com:4317")
        settings = OwlBearSettings()
        assert settings.otel_endpoint == "https://otel.example.com:4317"

    def test_otel_endpoint_is_optional_str(self) -> None:
        """The field type should be str | None with default None."""
        field_info = OwlBearSettings.model_fields["otel_endpoint"]
        assert field_info.default is None


# ---------------------------------------------------------------------------
# Task #216 — Agent.instrument_all() called at daemon startup
# ---------------------------------------------------------------------------


class TestInstrumentAllAtStartup:
    """run_daemon calls Agent.instrument_all() before the loop."""

    @pytest.mark.asyncio
    async def test_instrument_all_called_during_startup(self, tmp_path: Path) -> None:
        """Agent.instrument_all() should be called once at daemon startup."""
        channel = MagicMock()
        channel.name = "mock"
        channel.receive = AsyncMock(return_value=None)  # immediate EOF
        channel.send = AsyncMock()

        agent = MagicMock()
        agent.turn = AsyncMock(return_value="ok")
        agent.hooks.emit = AsyncMock()

        with patch("owlbear.daemon.Agent") as mock_agent_cls:
            from owlbear.daemon import run_daemon

            await run_daemon(channel=channel, agent=agent, config_dir=tmp_path)

            mock_agent_cls.instrument_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_instrument_all_called_before_receive(self, tmp_path: Path) -> None:
        """instrument_all() must happen before the first channel.receive()."""
        call_order: list[str] = []

        channel = MagicMock()
        channel.name = "mock"

        async def _receive(*, prompt: str | None = None) -> str | None:  # noqa: ARG001
            call_order.append("receive")
            return None

        channel.receive = _receive
        channel.send = AsyncMock()

        agent = MagicMock()
        agent.turn = AsyncMock(return_value="ok")
        agent.hooks.emit = AsyncMock()

        with patch("owlbear.daemon.Agent") as mock_agent_cls:
            mock_agent_cls.instrument_all.side_effect = lambda: call_order.append("instrument_all")

            from owlbear.daemon import run_daemon

            await run_daemon(channel=channel, agent=agent, config_dir=tmp_path)

        assert call_order.index("instrument_all") < call_order.index("receive")

    @pytest.mark.asyncio
    async def test_instrument_all_does_not_raise_without_tracer(self, tmp_path: Path) -> None:
        """instrument_all() should not raise even without a TracerProvider."""
        channel = MagicMock()
        channel.name = "mock"
        channel.receive = AsyncMock(return_value=None)
        channel.send = AsyncMock()

        agent = MagicMock()
        agent.turn = AsyncMock(return_value="ok")
        agent.hooks.emit = AsyncMock()

        # Don't mock Agent — let the real instrument_all() run (it's a no-op)
        from owlbear.daemon import run_daemon

        # Should not raise
        await run_daemon(channel=channel, agent=agent, config_dir=tmp_path)


# ---------------------------------------------------------------------------
# Task #218 — logfire.configure() called when otel_endpoint is set
# ---------------------------------------------------------------------------


class TestLogfireConfigureAtStartup:
    """Daemon configures logfire SDK when otel_endpoint is provided."""

    @pytest.mark.asyncio
    async def test_logfire_configure_called_when_endpoint_set(self, tmp_path: Path) -> None:
        """When otel_endpoint is set, logfire.configure() should be called."""
        channel = MagicMock()
        channel.name = "mock"
        channel.receive = AsyncMock(return_value=None)
        channel.send = AsyncMock()

        agent = MagicMock()
        agent.turn = AsyncMock(return_value="ok")
        agent.hooks.emit = AsyncMock()

        with (
            patch("owlbear.daemon.Agent"),
            patch("owlbear.daemon.logfire") as mock_logfire,
        ):
            from owlbear.daemon import run_daemon

            await run_daemon(
                channel=channel,
                agent=agent,
                config_dir=tmp_path,
                otel_endpoint="http://localhost:4318",
            )

            mock_logfire.configure.assert_called_once_with(
                send_to_logfire=False,
                additional_span_processors=[],
            )

    @pytest.mark.asyncio
    async def test_otel_exporter_env_set_when_endpoint_provided(
        self,
        tmp_path: Path,
    ) -> None:
        """OTEL_EXPORTER_OTLP_ENDPOINT env var should be set before logfire.configure()."""
        channel = MagicMock()
        channel.name = "mock"
        channel.receive = AsyncMock(return_value=None)
        channel.send = AsyncMock()

        agent = MagicMock()
        agent.turn = AsyncMock(return_value="ok")
        agent.hooks.emit = AsyncMock()

        captured_env: dict[str, str | None] = {}

        with (
            patch("owlbear.daemon.Agent"),
            patch("owlbear.daemon.logfire") as mock_logfire,
        ):

            def capture_on_configure(**kwargs: object) -> None:  # noqa: ARG001
                captured_env["OTEL_EXPORTER_OTLP_ENDPOINT"] = os.environ.get(
                    "OTEL_EXPORTER_OTLP_ENDPOINT"
                )

            mock_logfire.configure.side_effect = capture_on_configure

            from owlbear.daemon import run_daemon

            await run_daemon(
                channel=channel,
                agent=agent,
                config_dir=tmp_path,
                otel_endpoint="http://localhost:4318",
            )

        assert captured_env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://localhost:4318"

    @pytest.mark.asyncio
    async def test_no_logfire_configure_when_endpoint_none(self, tmp_path: Path) -> None:
        """When otel_endpoint is None, logfire.configure() should NOT be called."""
        channel = MagicMock()
        channel.name = "mock"
        channel.receive = AsyncMock(return_value=None)
        channel.send = AsyncMock()

        agent = MagicMock()
        agent.turn = AsyncMock(return_value="ok")
        agent.hooks.emit = AsyncMock()

        with (
            patch("owlbear.daemon.Agent"),
            patch("owlbear.daemon.logfire") as mock_logfire,
        ):
            from owlbear.daemon import run_daemon

            await run_daemon(
                channel=channel,
                agent=agent,
                config_dir=tmp_path,
            )

            mock_logfire.configure.assert_not_called()

    @pytest.mark.asyncio
    async def test_logfire_configure_before_instrument_all(self, tmp_path: Path) -> None:
        """logfire.configure() must be called before Agent.instrument_all()."""
        call_order: list[str] = []

        channel = MagicMock()
        channel.name = "mock"
        channel.receive = AsyncMock(return_value=None)
        channel.send = AsyncMock()

        agent = MagicMock()
        agent.turn = AsyncMock(return_value="ok")
        agent.hooks.emit = AsyncMock()

        with (
            patch("owlbear.daemon.Agent") as mock_agent_cls,
            patch("owlbear.daemon.logfire") as mock_logfire,
        ):
            mock_logfire.configure.side_effect = lambda **kw: call_order.append("configure")  # noqa: ARG005
            mock_agent_cls.instrument_all.side_effect = lambda: call_order.append("instrument_all")

            from owlbear.daemon import run_daemon

            await run_daemon(
                channel=channel,
                agent=agent,
                config_dir=tmp_path,
                otel_endpoint="http://localhost:4318",
            )

        assert call_order.index("configure") < call_order.index("instrument_all")
