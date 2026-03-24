"""Tests for shared conftest.py helpers: MockChannel, make_mock_toolset, make_settings.

Verifies that the conftest extraction (task #808) delivers the correct
public API and that no duplicate definitions remain in individual test files.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from owlbear.config import OwlBearSettings

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Helper: run async coroutines in sync tests
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


# ===================================================================
# MockChannel
# ===================================================================


class TestFromAC_MockChannelInConftest:
    """AC: MockChannel class added to tests/conftest.py."""

    def test_import_mock_channel(self) -> None:
        """MockChannel is importable from conftest."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        assert MockChannel is not None

    def test_name_property_returns_mock(self) -> None:
        """MockChannel.name returns 'mock'."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        ch = MockChannel(messages=[])
        assert ch.name == "mock"

    def test_receive_returns_messages_in_order(self) -> None:
        """receive() yields messages sequentially."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        ch = MockChannel(messages=["hello", "world"])
        assert _run(ch.receive(prompt=None)) == "hello"
        assert _run(ch.receive(prompt=None)) == "world"

    def test_receive_returns_none_after_exhausted(self) -> None:
        """receive() returns None when all messages consumed."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        ch = MockChannel(messages=["only"])
        _run(ch.receive(prompt=None))
        assert _run(ch.receive(prompt=None)) is None

    def test_receive_empty_messages(self) -> None:
        """receive() returns None immediately for empty message list."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        ch = MockChannel(messages=[])
        assert _run(ch.receive(prompt=None)) is None

    def test_send_appends_to_sent(self) -> None:
        """send() records messages in .sent list."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        ch = MockChannel(messages=[])
        _run(ch.send("reply"))
        assert ch.sent == ["reply"]

    def test_receive_none_in_sequence(self) -> None:
        """None in message list is returned as-is (not treated as stop)."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        ch = MockChannel(messages=["a", None, "b"])
        assert _run(ch.receive(prompt=None)) == "a"
        assert _run(ch.receive(prompt=None)) is None
        assert _run(ch.receive(prompt=None)) == "b"


# ===================================================================
# make_mock_toolset
# ===================================================================


class TestFromAC_MakeMockToolset:
    """AC: make_mock_toolset() factory added to tests/conftest.py."""

    def test_import_make_mock_toolset(self) -> None:
        """make_mock_toolset is importable from conftest."""
        from conftest import make_mock_toolset  # type: ignore[import-untyped]

        assert callable(make_mock_toolset)

    def test_default_return_value_is_tool_result(self) -> None:
        """Default call_tool() returns 'tool_result'."""
        from conftest import make_mock_toolset  # type: ignore[import-untyped]

        ts = make_mock_toolset()
        result = _run(ts.call_tool())
        assert result == "tool_result"

    def test_custom_return_value(self) -> None:
        """Caller can override the default return_value."""
        from conftest import make_mock_toolset  # type: ignore[import-untyped]

        ts = make_mock_toolset(return_value="custom")
        result = _run(ts.call_tool())
        assert result == "custom"

    def test_call_tool_is_async(self) -> None:
        """call_tool is an AsyncMock (awaitable)."""
        from conftest import make_mock_toolset  # type: ignore[import-untyped]

        ts = make_mock_toolset()
        assert isinstance(ts.call_tool, AsyncMock)


# ===================================================================
# make_settings
# ===================================================================


class TestFromAC_MakeSettings:
    """AC: make_settings() factory added to tests/conftest.py."""

    def test_import_make_settings(self) -> None:
        """make_settings is importable from conftest."""
        from conftest import make_settings  # type: ignore[import-untyped]

        assert callable(make_settings)

    def test_returns_owlbear_settings(self, tmp_path: Path) -> None:
        """make_settings returns an OwlBearSettings instance."""
        from conftest import make_settings  # type: ignore[import-untyped]

        settings = make_settings(tmp_path)
        assert isinstance(settings, OwlBearSettings)

    def test_paths_use_tmp_path(self, tmp_path: Path) -> None:
        """Default paths are rooted in the provided tmp_path."""
        from conftest import make_settings  # type: ignore[import-untyped]

        settings = make_settings(tmp_path)
        token_path = settings.copilot_token_path
        assert tmp_path in token_path.parents or token_path.parent == tmp_path

    def test_overrides_applied(self, tmp_path: Path) -> None:
        """Keyword overrides replace defaults."""
        from conftest import make_settings  # type: ignore[import-untyped]

        custom_agents = tmp_path / "custom_agents"
        settings = make_settings(tmp_path, agents_dir=custom_agents)
        assert settings.agents_dir == custom_agents

    def test_signature_accepts_kwargs(self) -> None:
        """make_settings has (tmp_path, **overrides) signature."""
        from conftest import make_settings  # type: ignore[import-untyped]

        sig = inspect.signature(make_settings)
        params = list(sig.parameters.values())
        assert params[0].name == "tmp_path"
        # Second param should be **overrides (VAR_KEYWORD)
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)


# ===================================================================
# make_completed_process
# ===================================================================


class TestFromAC_MakeCompletedProcess:
    """AC: make_completed_process() factory added to tests/conftest.py.

    Verifies the helper returns real text-mode subprocess.CompletedProcess values
    and covers success, non-zero exit, malformed stdout, and malformed stderr.
    """

    def test_importable_from_conftest(self) -> None:
        """make_completed_process is importable from conftest."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        assert callable(make_completed_process)

    def test_returns_real_completed_process_not_mock(self) -> None:
        """Returns subprocess.CompletedProcess, not a MagicMock."""
        import subprocess

        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process()
        assert isinstance(result, subprocess.CompletedProcess)

    def test_default_returncode_is_zero(self) -> None:
        """Default returncode is 0 (success)."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process()
        assert result.returncode == 0

    def test_nonzero_returncode_round_trips(self) -> None:
        """Non-zero returncode is preserved."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process(returncode=1)
        assert result.returncode == 1

    def test_stdout_is_string_text_mode(self) -> None:
        """stdout is a str (text mode, not bytes)."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process()
        assert isinstance(result.stdout, str)

    def test_stderr_is_string_text_mode(self) -> None:
        """stderr is a str (text mode, not bytes)."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process()
        assert isinstance(result.stderr, str)

    def test_default_stdout_is_empty_string(self) -> None:
        """Default stdout is an empty string."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process()
        assert result.stdout == ""

    def test_default_stderr_is_empty_string(self) -> None:
        """Default stderr is an empty string."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process()
        assert result.stderr == ""

    def test_custom_stdout_payload_round_trips(self) -> None:
        """Custom stdout payload is preserved verbatim."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process(stdout="hello output")
        assert result.stdout == "hello output"

    def test_custom_stderr_payload_round_trips(self) -> None:
        """Custom stderr payload is preserved verbatim."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        result = make_completed_process(stderr="error message")
        assert result.stderr == "error message"

    def test_malformed_stdout_payload_accepted(self) -> None:
        """Accepts non-JSON malformed stdout without raising."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        malformed = "not valid json {{{"
        result = make_completed_process(stdout=malformed)
        assert result.stdout == malformed

    def test_malformed_stderr_payload_accepted(self) -> None:
        """Accepts non-JSON malformed stderr without raising."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        malformed = "fatal: not a git repo\n---\n{{"
        result = make_completed_process(stderr=malformed)
        assert result.stderr == malformed

    def test_success_with_json_stdout(self) -> None:
        """Success payload: returncode=0 with valid JSON stdout is preserved."""
        import json

        from conftest import make_completed_process  # type: ignore[import-untyped]

        payload = json.dumps([{"id": 1, "title": "task"}])
        result = make_completed_process(returncode=0, stdout=payload)
        assert result.returncode == 0
        assert result.stdout == payload

    def test_signature_has_returncode_stdout_stderr(self) -> None:
        """make_completed_process signature includes returncode, stdout, stderr."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        sig = inspect.signature(make_completed_process)
        params = set(sig.parameters.keys())
        assert "returncode" in params
        assert "stdout" in params
        assert "stderr" in params


# ===================================================================
# Zero duplicate definitions
# ===================================================================


def _has_class_def(filepath: Path, class_name: str) -> bool:
    """Return True if *filepath* contains a class definition named *class_name*."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    return any(
        isinstance(node, ast.ClassDef) and node.name == class_name for node in ast.walk(tree)
    )


def _has_func_def(filepath: Path, func_name: str) -> bool:
    """Return True if *filepath* has a top-level function definition named *func_name*."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name
        for node in ast.iter_child_nodes(tree)
    )


class TestFromAC_ZeroDuplicates:
    """AC: Zero duplicate definitions across test files."""

    @pytest.mark.parametrize(
        "filename",
        [
            "test_daemon.py",
            "test_daemon_coverage_gaps.py",
            "test_error_sanitization_callsites.py",
            "test_integration_e2e.py",
            "test_poll_dispatch.py",
        ],
    )
    def test_no_duplicate_mock_channel(self, filename: str) -> None:
        """MockChannel must not be defined in individual test files."""
        filepath = TESTS_DIR / filename
        if not filepath.exists():
            pytest.skip(f"{filename} does not exist")
        assert not _has_class_def(filepath, "MockChannel"), (
            f"MockChannel still defined in {filename}"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "test_approval_gate.py",
            "test_hooked_toolset.py",
            "test_slack_interactive.py",
        ],
    )
    def test_no_duplicate_make_mock_toolset(self, filename: str) -> None:
        """_make_mock_toolset must not be defined in individual test files."""
        filepath = TESTS_DIR / filename
        if not filepath.exists():
            pytest.skip(f"{filename} does not exist")
        assert not _has_func_def(filepath, "_make_mock_toolset"), (
            f"_make_mock_toolset still defined in {filename}"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "test_bootstrap_integration.py",
            "test_client_cleanup.py",
            "test_integration_e2e.py",
            "test_pipeline_e2e.py",
        ],
    )
    def test_no_duplicate_make_settings(self, filename: str) -> None:
        """_make_settings must not be defined in individual test files."""
        filepath = TESTS_DIR / filename
        if not filepath.exists():
            pytest.skip(f"{filename} does not exist")
        assert not _has_func_def(filepath, "_make_settings"), (
            f"_make_settings still defined in {filename}"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "test_cli_board.py",
            "test_cli_chat.py",
        ],
    )
    def test_no_duplicate_make_completed_process(self, filename: str) -> None:
        """make_completed_process must not be defined in individual test files."""
        filepath = TESTS_DIR / filename
        if not filepath.exists():
            pytest.skip(f"{filename} does not exist")
        assert not _has_func_def(filepath, "make_completed_process"), (
            f"make_completed_process still defined in {filename}"
        )
