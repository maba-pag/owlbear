"""Tests for the _cli_error() helper in bearclaw.commands.

TDD RED phase: tests define the contract for _cli_error(msg: str) -> NoReturn.
The function should echo 'Error: {msg}' to stderr and raise typer.Exit(code=1).

Covers #532 AC (extraction + migration) and #805 AC (function contract).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NoReturn, get_type_hints

import pytest
import typer

from bearclaw.commands import _cli_error


class TestFromAC_CliErrorBehavior:  # noqa: N801
    """AC: _cli_error(msg) writes 'Error: {msg}' to stderr and raises typer.Exit(code=1)."""

    def test_raises_typer_exit(self) -> None:
        """_cli_error must raise typer.Exit."""
        with pytest.raises(typer.Exit):
            _cli_error("something went wrong")

    def test_exit_code_is_1(self) -> None:
        """The raised typer.Exit must have code=1."""
        with pytest.raises(typer.Exit) as exc_info:
            _cli_error("something went wrong")
        assert exc_info.value.exit_code == 1

    def test_writes_error_prefix_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Output must start with 'Error: ' and include the message on stderr."""
        with pytest.raises(typer.Exit):
            _cli_error("disk full")
        captured = capsys.readouterr()
        assert "Error: disk full" in captured.err

    def test_no_stdout_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Error message goes to stderr, not stdout."""
        with pytest.raises(typer.Exit):
            _cli_error("oops")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_stderr_format_exact(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Stderr line must be exactly 'Error: {msg}' followed by newline."""
        with pytest.raises(typer.Exit):
            _cli_error("connection refused")
        captured = capsys.readouterr()
        assert captured.err.rstrip("\n") == "Error: connection refused"


class TestFromAC_CliErrorNoReturnAnnotation:  # noqa: N801
    """AC: NoReturn annotation is present (inspect check)."""

    def test_return_annotation_is_noreturn(self) -> None:
        """_cli_error must declare -> NoReturn in its type hints."""
        hints = get_type_hints(_cli_error)
        assert hints.get("return") is NoReturn


class TestFromAC_CliErrorMessageFormats:  # noqa: N801
    """AC: Parametrize message arg with >=3 formats (plain, f-string result, empty)."""

    @pytest.mark.parametrize(
        ("msg", "expected_stderr"),
        [
            pytest.param("file not found", "Error: file not found", id="plain-string"),
            pytest.param(
                f"No source named '{'my-source'}'",
                "Error: No source named 'my-source'",
                id="f-string-interpolation",
            ),
            pytest.param("", "Error: ", id="empty-string"),
            pytest.param(
                "Slack API request failed: timeout after 30s",
                "Error: Slack API request failed: timeout after 30s",
                id="long-descriptive-message",
            ),
        ],
    )
    def test_message_format(
        self,
        msg: str,
        expected_stderr: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Each message variant must appear correctly in stderr."""
        with pytest.raises(typer.Exit) as exc_info:
            _cli_error(msg)
        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr()
        assert captured.err.rstrip("\n") == expected_stderr


# ---------------------------------------------------------------------------
# Migration tests — AC 3 & 4 from #532
# ---------------------------------------------------------------------------

# Root of src/bearclaw/commands/ resolved once at import time.
_COMMANDS_DIR = Path(__file__).resolve().parent.parent / "src" / "bearclaw" / "commands"

# The 7 command modules that must be migrated per #532 AC.
_AFFECTED_MODULES = [
    "auth",
    "browser",
    "decisions",
    "knowledge_source",
    "project",
    "slack",
    "voice",
]


def _find_raw_exit_code_1(source: str) -> list[int]:
    """Return line numbers of ``raise typer.Exit(code=1)`` in *source* via AST.

    Matches ``typer.Exit(code=1)`` in any ``raise`` statement. Does NOT report
    occurrences inside a function named ``_cli_error`` (since that is the
    canonical wrapper).
    """
    tree = ast.parse(source)
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        call = node.exc
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "Exit"
            and isinstance(func.value, ast.Name)
            and func.value.id == "typer"
        ):
            continue
        has_code_1 = any(
            kw.arg == "code" and isinstance(kw.value, ast.Constant) and kw.value.value == 1
            for kw in call.keywords
        )
        if has_code_1:
            hits.append(node.lineno)
    return hits


class TestFromAC_ZeroRawExitCode1:  # noqa: N801
    """AC 3: Zero raw typer.Exit(code=1) anywhere in src/bearclaw/.

    The only allowed typer.Exit(code=1) is inside _cli_error() in __init__.py.
    """

    @pytest.mark.parametrize("module", _AFFECTED_MODULES)
    def test_no_raw_exit_code_1_in_module(self, module: str) -> None:
        """Command module must not contain bare typer.Exit(code=1)."""
        source = (_COMMANDS_DIR / f"{module}.py").read_text(encoding="utf-8")
        hits = _find_raw_exit_code_1(source)
        assert hits == [], f"{module}.py still has raw typer.Exit(code=1) on lines {hits}"

    def test_no_raw_exit_code_1_anywhere_in_bearclaw(self) -> None:
        """Scan ALL .py files under src/bearclaw/ — only __init__.py may have it."""
        bearclaw_root = _COMMANDS_DIR.parent
        violations: list[str] = []
        for py_file in sorted(bearclaw_root.rglob("*.py")):
            # The _cli_error definition itself is allowed in __init__.py
            if py_file.name == "__init__.py" and py_file.parent == _COMMANDS_DIR:
                continue
            source = py_file.read_text(encoding="utf-8")
            hits = _find_raw_exit_code_1(source)
            if hits:
                rel = py_file.relative_to(bearclaw_root)
                violations.append(f"{rel}: lines {hits}")
        assert violations == [], "Raw typer.Exit(code=1) found:\n" + "\n".join(violations)


class TestFromAC_AllModulesUseCliError:  # noqa: N801
    """AC 4: All 7 affected command modules import and call _cli_error."""

    @pytest.mark.parametrize("module", _AFFECTED_MODULES)
    def test_module_imports_cli_error(self, module: str) -> None:
        """Each affected module must import _cli_error from the commands package."""
        source = (_COMMANDS_DIR / f"{module}.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "_cli_error":
                        imported = True
                        break
        assert imported, f"{module}.py does not import _cli_error"

    @pytest.mark.parametrize("module", _AFFECTED_MODULES)
    def test_module_calls_cli_error(self, module: str) -> None:
        """Each affected module must actually call _cli_error (not just import it)."""
        source = (_COMMANDS_DIR / f"{module}.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        called = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_cli_error"
            ):
                called = True
                break
        assert called, f"{module}.py imports _cli_error but never calls it"
