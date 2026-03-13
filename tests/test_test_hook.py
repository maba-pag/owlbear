"""Tests for TestVerificationHook — session-end test verification.

Covers: registration on SESSION_END, firing on session end, test pass
scenario, test fail scenario, subprocess timeout, subprocess error,
configurable command, and logging of results.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.test_hook import TestVerificationHook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_CMD = ["uv", "run", "pytest", "tests/", "-m", "not api", "--tb=short", "-q"]


def _run(coro: object) -> None:
    """Convenience wrapper around asyncio.run for coroutines."""
    asyncio.run(coro)  # type: ignore[arg-type]


def _session_payload(session_id: str = "test-session-1") -> dict[str, object]:
    """Build a SESSION_END payload."""
    return {"session_id": session_id}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestTestVerificationHookRegistration:
    """TestVerificationHook registers on HookRegistry SESSION_END."""

    def test_register_adds_to_session_end(self) -> None:
        hook = TestVerificationHook()
        registry = HookRegistry()
        hook.register(registry)
        handlers = registry.handlers.get(HookEvent.SESSION_END, [])
        assert hook in handlers

    def test_register_does_not_add_to_other_events(self) -> None:
        hook = TestVerificationHook()
        registry = HookRegistry()
        hook.register(registry)
        for event in HookEvent:
            if event != HookEvent.SESSION_END:
                assert hook not in registry.handlers.get(event, [])


# ---------------------------------------------------------------------------
# Test pass scenario
# ---------------------------------------------------------------------------


class TestTestVerificationHookPassScenario:
    """Hook reports passing tests correctly."""

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_all_tests_pass(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="42 passed in 3.21s\n",
            stderr="",
        )
        hook = TestVerificationHook()
        data = _session_payload()
        _run(hook(data))
        mock_run.assert_called_once()
        results = data["test_results"]
        assert results["passed"] == 42
        assert results["failed"] == 0
        assert "42 passed" in results["output"]

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_uses_default_pytest_command(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="1 passed\n",
            stderr="",
        )
        hook = TestVerificationHook()
        _run(hook(_session_payload()))
        call_args = mock_run.call_args[0][0]
        assert call_args == _DEFAULT_CMD

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_stores_results_on_data_dict(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="10 passed\n",
            stderr="",
        )
        hook = TestVerificationHook()
        data = _session_payload()
        _run(hook(data))
        assert "test_results" in data
        assert isinstance(data["test_results"], dict)
        assert "passed" in data["test_results"]
        assert "failed" in data["test_results"]
        assert "output" in data["test_results"]


# ---------------------------------------------------------------------------
# Test fail scenario
# ---------------------------------------------------------------------------


class TestTestVerificationHookFailScenario:
    """Hook handles test failures gracefully — warn, never raise."""

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_some_tests_fail(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="3 failed, 39 passed in 4.56s\n",
            stderr="",
        )
        hook = TestVerificationHook()
        data = _session_payload()
        _run(hook(data))
        results = data["test_results"]
        assert results["passed"] == 39
        assert results["failed"] == 3

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_failure_does_not_raise(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="5 failed\n",
            stderr="",
        )
        hook = TestVerificationHook()
        # Must NOT raise
        _run(hook(_session_payload()))

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_failure_logs_warning(
        self,
        mock_run: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="2 failed, 10 passed\n",
            stderr="",
        )
        hook = TestVerificationHook()
        with caplog.at_level(logging.WARNING, logger="owlbear.core.test_hook"):
            _run(hook(_session_payload()))
        assert "2 failed" in caplog.text


# ---------------------------------------------------------------------------
# Subprocess timeout
# ---------------------------------------------------------------------------


class TestTestVerificationHookTimeout:
    """Hook handles subprocess timeout — warn, never raise."""

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_timeout_does_not_raise(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)
        hook = TestVerificationHook()
        # Must NOT raise
        _run(hook(_session_payload()))

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_timeout_stores_timeout_results(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)
        hook = TestVerificationHook()
        data = _session_payload()
        _run(hook(data))
        results = data["test_results"]
        assert results["passed"] == 0
        assert results["failed"] == 0
        assert "timeout" in results["output"].lower()

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_timeout_logs_warning(
        self,
        mock_run: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)
        hook = TestVerificationHook()
        with caplog.at_level(logging.WARNING, logger="owlbear.core.test_hook"):
            _run(hook(_session_payload()))
        assert "timeout" in caplog.text.lower()


# ---------------------------------------------------------------------------
# Subprocess error (e.g., binary not found)
# ---------------------------------------------------------------------------


class TestTestVerificationHookSubprocessError:
    """Hook handles subprocess errors — warn, never raise."""

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_os_error_does_not_raise(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("pytest not found")
        hook = TestVerificationHook()
        _run(hook(_session_payload()))

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_os_error_stores_error_results(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("pytest not found")
        hook = TestVerificationHook()
        data = _session_payload()
        _run(hook(data))
        results = data["test_results"]
        assert results["passed"] == 0
        assert results["failed"] == 0
        assert "error" in results["output"].lower()

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_os_error_logs_warning(
        self,
        mock_run: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.side_effect = OSError("pytest not found")
        hook = TestVerificationHook()
        with caplog.at_level(logging.WARNING, logger="owlbear.core.test_hook"):
            _run(hook(_session_payload()))
        assert "pytest not found" in caplog.text


# ---------------------------------------------------------------------------
# Configurable command
# ---------------------------------------------------------------------------


class TestTestVerificationHookConfigurable:
    """Hook accepts custom pytest command."""

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_custom_command(self, mock_run: MagicMock) -> None:
        custom = ["python", "-m", "pytest", "-x"]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="5 passed\n",
            stderr="",
        )
        hook = TestVerificationHook(pytest_cmd=custom)
        _run(hook(_session_payload()))
        call_args = mock_run.call_args[0][0]
        assert call_args == custom

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_custom_timeout(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="1 passed\n",
            stderr="",
        )
        hook = TestVerificationHook(timeout=60)
        _run(hook(_session_payload()))
        assert mock_run.call_args[1]["timeout"] == 60

    def test_default_timeout_is_120(self) -> None:
        hook = TestVerificationHook()
        assert hook._timeout == 120


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestTestVerificationHookEdgeCases:
    """Edge cases: unparseable output."""

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_unparseable_output_defaults_to_zero(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="some weird output\n",
            stderr="",
        )
        hook = TestVerificationHook()
        data = _session_payload()
        _run(hook(data))
        results = data["test_results"]
        assert results["passed"] == 0
        assert results["failed"] == 0
        assert results["output"] == "some weird output"


# ---------------------------------------------------------------------------
# HookRegistry integration
# ---------------------------------------------------------------------------


class TestTestVerificationHookIntegration:
    """Hook fires correctly through HookRegistry.emit."""

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_emit_triggers_test_run(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="10 passed\n",
            stderr="",
        )
        hook = TestVerificationHook()
        registry = HookRegistry()
        hook.register(registry)
        _run(registry.emit(HookEvent.SESSION_END, _session_payload()))
        mock_run.assert_called_once()

    @patch("owlbear.core.test_hook.subprocess.run")
    def test_emit_on_other_event_does_not_trigger(self, mock_run: MagicMock) -> None:
        hook = TestVerificationHook()
        registry = HookRegistry()
        hook.register(registry)
        _run(registry.emit(HookEvent.SESSION_START, _session_payload()))
        mock_run.assert_not_called()
