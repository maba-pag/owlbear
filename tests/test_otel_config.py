"""Tests for OTel configuration and Agent.instrument_all() at daemon startup.

Covers tasks #230 (tests), #216 (instrument_all), #218 (otel_endpoint config).
"""

from __future__ import annotations

import os
import types
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


# ---------------------------------------------------------------------------
# Task #535 — optional logfire import + configure_otel guard
# ---------------------------------------------------------------------------


class TestFromAC_LogfireOptionalImport:
    """owlbear.daemon loads when logfire is absent; configure_otel raises RuntimeError."""

    def _import_without_logfire(self) -> types.ModuleType:
        """Fresh-import owlbear.daemon with logfire absent from sys.modules.

        Removes owlbear.daemon from sys.modules first so that the module-level
        ``try: import logfire`` guard runs from scratch rather than via reload.
        """
        import importlib
        import sys

        with patch.dict(sys.modules, {"logfire": None}):
            sys.modules.pop("owlbear.daemon", None)
            return importlib.import_module("owlbear.daemon")

    def teardown_method(self) -> None:
        """Restore owlbear.daemon to normal (logfire available)."""
        import importlib
        import sys

        sys.modules.pop("owlbear.daemon", None)
        importlib.import_module("owlbear.daemon")

    def test_daemon_import_succeeds_without_logfire(self) -> None:
        """Daemon module loads without error when logfire is absent; logfire attr is None."""
        mod = self._import_without_logfire()
        assert mod.logfire is None

    def test_configure_otel_raises_runtime_error_without_logfire(self) -> None:
        """configure_otel raises RuntimeError mentioning logfire when logfire is absent."""
        mod = self._import_without_logfire()
        with pytest.raises(RuntimeError, match="logfire"):
            mod.configure_otel("http://localhost:4318")


# ---------------------------------------------------------------------------
# Task #535 — configure_otel() happy path (AC line 4)
# ---------------------------------------------------------------------------


class TestFromAC_ConfigureOtelHappyPath:
    """configure_otel() happy path: env var set, logfire.configure called correctly."""

    def test_configure_otel_sets_otel_exporter_endpoint_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """configure_otel sets OTEL_EXPORTER_OTLP_ENDPOINT to the supplied URL."""
        import owlbear.daemon as daemon_mod

        mock_logfire = MagicMock()
        monkeypatch.setattr(daemon_mod, "logfire", mock_logfire)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        daemon_mod.configure_otel("http://localhost:4318")

        assert os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") == "http://localhost:4318"

    def test_configure_otel_calls_logfire_configure_with_exact_kwargs(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """configure_otel calls logfire.configure with send_to_logfire=False, no span processors."""
        import owlbear.daemon as daemon_mod

        mock_logfire = MagicMock()
        monkeypatch.setattr(daemon_mod, "logfire", mock_logfire)

        daemon_mod.configure_otel("http://localhost:4318")

        mock_logfire.configure.assert_called_once_with(
            send_to_logfire=False,
            additional_span_processors=[],
        )


# ---------------------------------------------------------------------------
# Task #535 — no otel_endpoint → configure_otel not invoked (AC line 5)
# ---------------------------------------------------------------------------


class TestFromAC_NoEndpointBehavior:
    """Daemon startup without otel_endpoint does not invoke configure_otel."""

    @pytest.mark.asyncio
    async def test_run_daemon_does_not_set_otel_env_without_endpoint(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When run_daemon is called without otel_endpoint, OTEL env var is not written."""
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        channel = MagicMock()
        channel.name = "mock"
        channel.receive = AsyncMock(return_value=None)
        channel.send = AsyncMock()

        agent = MagicMock()
        agent.turn = AsyncMock(return_value="ok")
        agent.hooks.emit = AsyncMock()

        with patch("owlbear.daemon.Agent"):
            from owlbear.daemon import run_daemon

            await run_daemon(channel=channel, agent=agent, config_dir=tmp_path)

        assert os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") is None


# ---------------------------------------------------------------------------
# Task #535 — scope constraint (AC line 6)
# ---------------------------------------------------------------------------


class TestFromAC_ScopeConstraint:
    """Scope stays within daemon.py; OwlBearSettings gains no new OTel config fields."""

    def test_no_unexpected_otel_logfire_config_fields_in_settings(self) -> None:
        """OwlBearSettings has exactly the expected OTel-related config fields."""
        from owlbear.config import OwlBearSettings

        otel_fields = sorted(
            name
            for name in OwlBearSettings.model_fields
            if "otel" in name.lower() or "logfire" in name.lower()
        )
        assert otel_fields == ["otel_endpoint"]
