"""Tests for SubagentVerificationHook — SUBAGENT_COMPLETE verification hook.

Covers: registration on SUBAGENT_COMPLETE, file existence checking,
test execution checking, graceful failure (never raises), and result
storage on the data dict.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.subagent_hook import SubagentVerificationHook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload(
    *,
    task_id: str | int = "42",
    created_files: list[str] | None = None,
    test_files: list[str] | None = None,
    result: str = "done",
) -> dict[str, object]:
    """Build a SUBAGENT_COMPLETE payload."""
    return {
        "task_id": task_id,
        "created_files": created_files or [],
        "test_files": test_files or [],
        "result": result,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestSubagentVerificationHookRegistration:
    """SubagentVerificationHook registers on SUBAGENT_COMPLETE."""

    def test_register_adds_to_subagent_complete(self) -> None:
        hook = SubagentVerificationHook()
        registry = HookRegistry()
        hook.register(registry)
        handlers = registry.handlers.get(HookEvent.SUBAGENT_COMPLETE, [])
        assert hook in handlers

    def test_register_does_not_add_to_other_events(self) -> None:
        hook = SubagentVerificationHook()
        registry = HookRegistry()
        hook.register(registry)
        for event in HookEvent:
            if event != HookEvent.SUBAGENT_COMPLETE:
                assert hook not in registry.handlers.get(event, [])


# ---------------------------------------------------------------------------
# File existence verification
# ---------------------------------------------------------------------------


class TestFileExistenceCheck:
    """Hook verifies that created_files actually exist on disk."""

    @patch("owlbear.core.subagent_hook.Path.exists")
    @pytest.mark.asyncio
    async def test_all_files_exist(self, mock_exists: MagicMock) -> None:
        mock_exists.return_value = True
        hook = SubagentVerificationHook()
        data = _payload(created_files=["src/foo.py", "src/bar.py"])
        await (hook(data))
        verification = data["verification"]
        assert verification["files_ok"] is True

    @patch("owlbear.core.subagent_hook.Path.exists")
    @pytest.mark.asyncio
    async def test_missing_file_sets_files_ok_false(self, mock_exists: MagicMock) -> None:
        mock_exists.side_effect = [True, False]
        hook = SubagentVerificationHook()
        data = _payload(created_files=["src/exists.py", "src/missing.py"])
        await (hook(data))
        verification = data["verification"]
        assert verification["files_ok"] is False

    @patch("owlbear.core.subagent_hook.Path.exists")
    @pytest.mark.asyncio
    async def test_missing_file_noted_in_details(self, mock_exists: MagicMock) -> None:
        mock_exists.side_effect = [True, False]
        hook = SubagentVerificationHook()
        data = _payload(created_files=["src/exists.py", "src/missing.py"])
        await (hook(data))
        verification = data["verification"]
        assert "src/missing.py" in verification["details"]

    @pytest.mark.asyncio
    async def test_empty_created_files_is_ok(self) -> None:
        hook = SubagentVerificationHook()
        data = _payload(created_files=[])
        await (hook(data))
        verification = data["verification"]
        assert verification["files_ok"] is True


# ---------------------------------------------------------------------------
# Test execution verification
# ---------------------------------------------------------------------------


class TestTestExecutionCheck:
    """Hook runs pytest on test_files when provided."""

    @patch("owlbear.core.subagent_hook.subprocess.run")
    @pytest.mark.asyncio
    async def test_tests_pass(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="1 passed",
            stderr="",
        )
        hook = SubagentVerificationHook()
        data = _payload(test_files=["tests/test_foo.py"])
        await (hook(data))
        verification = data["verification"]
        assert verification["tests_ok"] is True

    @patch("owlbear.core.subagent_hook.subprocess.run")
    @pytest.mark.asyncio
    async def test_tests_fail(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="1 failed",
            stderr="",
        )
        hook = SubagentVerificationHook()
        data = _payload(test_files=["tests/test_foo.py"])
        await (hook(data))
        verification = data["verification"]
        assert verification["tests_ok"] is False

    @patch("owlbear.core.subagent_hook.subprocess.run")
    @pytest.mark.asyncio
    async def test_test_failure_noted_in_details(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="FAILED test_foo",
            stderr="",
        )
        hook = SubagentVerificationHook()
        data = _payload(test_files=["tests/test_foo.py"])
        await (hook(data))
        verification = data["verification"]
        assert "FAILED" in verification["details"]

    @patch("owlbear.core.subagent_hook.subprocess.run")
    @pytest.mark.asyncio
    async def test_pytest_cmd_default(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        hook = SubagentVerificationHook()
        data = _payload(test_files=["tests/test_foo.py"])
        await (hook(data))
        call_args = mock_run.call_args[0][0]
        assert call_args[:3] == ["uv", "run", "pytest"]
        assert "tests/test_foo.py" in call_args

    @patch("owlbear.core.subagent_hook.subprocess.run")
    @pytest.mark.asyncio
    async def test_pytest_cmd_custom(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        hook = SubagentVerificationHook(pytest_cmd=["python", "-m", "pytest"])
        data = _payload(test_files=["tests/test_foo.py"])
        await (hook(data))
        call_args = mock_run.call_args[0][0]
        assert call_args[:3] == ["python", "-m", "pytest"]

    @pytest.mark.asyncio
    async def test_empty_test_files_is_ok(self) -> None:
        hook = SubagentVerificationHook()
        data = _payload(test_files=[])
        await (hook(data))
        verification = data["verification"]
        assert verification["tests_ok"] is True


# ---------------------------------------------------------------------------
# Graceful failure (never raises)
# ---------------------------------------------------------------------------


class TestGracefulFailure:
    """Hook never raises — logs warnings instead."""

    @pytest.mark.asyncio
    async def test_missing_keys_does_not_raise(self) -> None:
        hook = SubagentVerificationHook()
        await (hook({}))
        # No exception, no crash

    @patch("owlbear.core.subagent_hook.subprocess.run", side_effect=OSError("no pytest"))
    @pytest.mark.asyncio
    async def test_subprocess_error_does_not_raise(self, _mock_run: MagicMock) -> None:
        hook = SubagentVerificationHook()
        data = _payload(test_files=["tests/test_foo.py"])
        await (hook(data))
        verification = data["verification"]
        assert verification["tests_ok"] is False

    @patch("owlbear.core.subagent_hook.Path.exists", side_effect=OSError("perm denied"))
    @pytest.mark.asyncio
    async def test_file_check_error_does_not_raise(self, _mock_exists: MagicMock) -> None:
        hook = SubagentVerificationHook()
        data = _payload(created_files=["src/foo.py"])
        await (hook(data))
        verification = data["verification"]
        assert verification["files_ok"] is False

    @patch("owlbear.core.subagent_hook.Path.exists")
    @pytest.mark.asyncio
    async def test_failure_logs_warning(
        self,
        mock_exists: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_exists.return_value = False
        hook = SubagentVerificationHook()
        data = _payload(created_files=["src/missing.py"])
        with caplog.at_level(logging.WARNING):
            await (hook(data))
        assert any("missing" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Integration with HookRegistry (emit path)
# ---------------------------------------------------------------------------


class TestEmitIntegration:
    """Hook works when invoked through HookRegistry.emit."""

    @patch("owlbear.core.subagent_hook.Path.exists", return_value=True)
    def test_emit_invokes_hook(self, _mock_exists: MagicMock) -> None:
        registry = HookRegistry()
        hook = SubagentVerificationHook()
        hook.register(registry)
        data = _payload(created_files=["src/a.py"])
        asyncio.run(registry.emit(HookEvent.SUBAGENT_COMPLETE, data))
        assert "verification" in data
        assert data["verification"]["files_ok"] is True
