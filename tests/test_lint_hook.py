"""Tests for AutoLintHook — post-tool-use auto-lint for Python files.

Covers: registration on POST_TOOL_USE, firing on .py edits, skipping
non-.py files, ruff error isolation, and logging of lint results.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.lint_hook import AutoLintHook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> None:
    """Convenience wrapper around asyncio.run for coroutines."""
    asyncio.run(coro)  # type: ignore[arg-type]


def _edit_payload(file_path: str) -> dict[str, object]:
    """Build a POST_TOOL_USE payload for a file-edit operation."""
    return {"tool_name": "replace_string_in_file", "args": {"filePath": file_path}, "result": None}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestAutoLintHookRegistration:
    """AutoLintHook registers on HookRegistry POST_TOOL_USE."""

    def test_register_adds_to_post_tool_use(self) -> None:
        hook = AutoLintHook()
        registry = HookRegistry()
        hook.register(registry)
        handlers = registry.handlers.get(HookEvent.POST_TOOL_USE, [])
        assert hook in handlers

    def test_register_does_not_add_to_other_events(self) -> None:
        hook = AutoLintHook()
        registry = HookRegistry()
        hook.register(registry)
        for event in HookEvent:
            if event != HookEvent.POST_TOOL_USE:
                assert hook not in registry.handlers.get(event, [])


# ---------------------------------------------------------------------------
# Fire on .py edit
# ---------------------------------------------------------------------------


class TestAutoLintHookFiresOnPyEdit:
    """Hook invokes ruff when a .py file is edited."""

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_runs_ruff_on_py_file(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        hook = AutoLintHook()
        _run(hook(_edit_payload("src/owlbear/core/hooks.py")))
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "ruff" in call_args
        assert "--fix" in call_args
        assert "src/owlbear/core/hooks.py" in call_args

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_runs_ruff_with_check_fix_command(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        hook = AutoLintHook()
        _run(hook(_edit_payload("test.py")))
        call_args = mock_run.call_args[0][0]
        assert call_args == ["uv", "run", "ruff", "check", "--fix", "test.py"]

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_extracts_file_path_from_various_arg_keys(self, mock_run: MagicMock) -> None:
        """Finds .py path in any string value within args."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        hook = AutoLintHook()
        payload: dict[str, object] = {
            "tool_name": "create_file",
            "args": {"path": "new_module.py", "content": "print('hello')"},
            "result": None,
        }
        _run(hook(payload))
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "new_module.py" in call_args


# ---------------------------------------------------------------------------
# Skip non-.py files
# ---------------------------------------------------------------------------


class TestAutoLintHookSkipsNonPy:
    """Hook silently skips non-Python files."""

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_skips_js_file(self, mock_run: MagicMock) -> None:
        hook = AutoLintHook()
        _run(hook(_edit_payload("app.js")))
        mock_run.assert_not_called()

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_skips_md_file(self, mock_run: MagicMock) -> None:
        hook = AutoLintHook()
        _run(hook(_edit_payload("README.md")))
        mock_run.assert_not_called()

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_skips_toml_file(self, mock_run: MagicMock) -> None:
        hook = AutoLintHook()
        _run(hook(_edit_payload("pyproject.toml")))
        mock_run.assert_not_called()

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_skips_py_like_but_not_py(self, mock_run: MagicMock) -> None:
        """e.g. .pyx, .pyc — only exact .py suffix triggers lint."""
        hook = AutoLintHook()
        _run(hook(_edit_payload("module.pyx")))
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestAutoLintHookEdgeCases:
    """Edge cases: missing args, no file path."""

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_missing_args_key_ignored(self, mock_run: MagicMock) -> None:
        hook = AutoLintHook()
        _run(hook({"tool_name": "edit_file"}))
        mock_run.assert_not_called()

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_args_not_dict_ignored(self, mock_run: MagicMock) -> None:
        hook = AutoLintHook()
        _run(hook({"tool_name": "edit_file", "args": "not a dict"}))
        mock_run.assert_not_called()

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_no_py_file_in_args_ignored(self, mock_run: MagicMock) -> None:
        hook = AutoLintHook()
        payload: dict[str, object] = {
            "tool_name": "edit_file",
            "args": {"text": "hello world", "count": 5},
            "result": None,
        }
        _run(hook(payload))
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


class TestAutoLintHookErrorIsolation:
    """Lint failures are logged but never block the agent."""

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_subprocess_error_does_not_propagate(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("ruff not found")
        hook = AutoLintHook()
        # Should NOT raise — error is swallowed
        _run(hook(_edit_payload("module.py")))

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_subprocess_error_is_logged(
        self,
        mock_run: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.side_effect = OSError("ruff not found")
        hook = AutoLintHook()
        with caplog.at_level(logging.ERROR, logger="owlbear.core.lint_hook"):
            _run(hook(_edit_payload("module.py")))
        assert "module.py" in caplog.text

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_nonzero_return_code_does_not_raise(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="Found 3 errors",
            stderr="",
        )
        hook = AutoLintHook()
        # Non-zero return is fine — ruff found issues it couldn't fix
        _run(hook(_edit_payload("module.py")))


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class TestAutoLintHookLogging:
    """Lint results are logged."""

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_logs_clean_result(
        self,
        mock_run: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="All checks passed!",
            stderr="",
        )
        hook = AutoLintHook()
        with caplog.at_level(logging.DEBUG, logger="owlbear.core.lint_hook"):
            _run(hook(_edit_payload("clean.py")))
        assert "clean.py" in caplog.text

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_logs_warnings_found(
        self,
        mock_run: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="Found 2 errors (1 fixed, 1 remaining)",
            stderr="",
        )
        hook = AutoLintHook()
        with caplog.at_level(logging.WARNING, logger="owlbear.core.lint_hook"):
            _run(hook(_edit_payload("messy.py")))
        assert "messy.py" in caplog.text


# ---------------------------------------------------------------------------
# HookRegistry integration
# ---------------------------------------------------------------------------


class TestAutoLintHookIntegration:
    """Hook fires correctly through HookRegistry.emit."""

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_emit_triggers_lint_on_py_file(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        hook = AutoLintHook()
        registry = HookRegistry()
        hook.register(registry)
        _run(registry.emit(HookEvent.POST_TOOL_USE, _edit_payload("file.py")))
        mock_run.assert_called_once()

    @patch("owlbear.core.lint_hook.subprocess.run")
    def test_emit_skips_non_py_file(self, mock_run: MagicMock) -> None:
        hook = AutoLintHook()
        registry = HookRegistry()
        hook.register(registry)
        _run(registry.emit(HookEvent.POST_TOOL_USE, _edit_payload("file.js")))
        mock_run.assert_not_called()
