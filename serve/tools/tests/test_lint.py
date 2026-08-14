"""Behavioral tests for lint, formatting, and quality command wrappers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.lint import (
    FixMode,
    _run_named,
    format_eof,
    format_whitespace,
    lint,
    lint_full,
    lint_python,
    megalint,
    quality_full,
)
from owlbear_tools.megalinter import MegaLinterImage

_TEST_IMAGE = MegaLinterImage(reference="registry.example/megalinter-main:v-current")


def test_lint_runs_the_normal_local_suite() -> None:
    with (
        patch.object(sys, "argv", ["lint"]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    commands = [item.args[0] for item in call.call_args_list]
    assert commands == [
        ["pre-commit", "run", "ruff-fix", "--all-files"],
        ["pre-commit", "run", "markdownlint-fix", "--all-files"],
        ["pre-commit", "run", "yamllint", "--all-files"],
        ["pre-commit", "run", "shellcheck", "--all-files"],
        ["pre-commit", "run", "actionlint", "--all-files"],
        ["pre-commit", "run", "editorconfig-checker", "--all-files"],
        ["pre-commit", "run", "eslint-frontend-fix", "--all-files"],
        ["pre-commit", "run", "stylelint-frontend-fix", "--all-files"],
        ["npm", "run", "lint:html"],
    ]
    assert call.call_args_list[-1].kwargs["cwd"] == Path("serve/cockpit/web")


def test_lint_staged_passes_staged_files_to_every_local_leaf() -> None:
    staged = b"README.md\0serve/cockpit/web/src/App.tsx\0"
    with (
        patch.object(sys, "argv", ["lint", "--staged"]),
        patch("owlbear_tools.lint.subprocess.check_output", return_value=staged),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    assert all("--files" in item.args[0] for item in call.call_args_list)
    assert all("README.md" in item.args[0] for item in call.call_args_list)


def test_lint_python_exposes_safe_no_fix_and_unsafe_modes() -> None:
    for option, hook, manual in (
        ([], "ruff-fix", False),
        (["--no-fix"], "ruff-check", True),
        (["--unsafe-fix"], "ruff-unsafe-fix", True),
    ):
        with (
            patch.object(sys, "argv", ["lint-python", *option]),
            patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
            pytest.raises(SystemExit, match="0"),
        ):
            lint_python()

        command = call.call_args.args[0]
        assert command[:3] == ["pre-commit", "run", hook]
        if manual:
            assert "--hook-stage" in command
            assert "manual" in command
        else:
            assert "--all-files" in command


def test_megalint_runs_as_a_direct_workspace_engine() -> None:
    with (
        patch.object(sys, "argv", ["megalint", "--unsafe-fix"]),
        patch("owlbear_tools.lint.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        megalint()

    command = call.call_args.args[0]
    assert command[:6] == ["docker", "run", "--rm", "--platform", "linux/amd64", "-v"]
    assert "registry.example/megalinter-main:v-current" in command
    assert "PYTHON_RUFF_ARGUMENTS=--unsafe-fixes" in command


def test_lint_full_runs_local_lint_then_megalint() -> None:
    with (
        patch.object(sys, "argv", ["lint-full", "--no-fix"]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        patch("owlbear_tools.lint.load_megalinter_image", return_value=_TEST_IMAGE),
        pytest.raises(SystemExit, match="0"),
    ):
        lint_full()

    commands = [item.args[0] for item in call.call_args_list]
    assert commands[0][:3] == ["pre-commit", "run", "ruff-check"]
    assert commands[-1][-1] == _TEST_IMAGE.reference
    assert "APPLY_FIXES=none" in commands[-1]


def test_quality_full_executes_todo_last() -> None:
    executed: list[str] = []

    def record(name: str, **_: object) -> int:
        executed.append(name)
        return 0

    with patch("owlbear_tools.lint._run_leaf", side_effect=record):
        assert _run_named("quality-full", staged=False, fix_mode=FixMode.SAFE) == 0

    assert executed[-1] == "todo"
    assert executed == [
        "format-python",
        "format-whitespace",
        "format-eof",
        "lint-python",
        "lint-markdown",
        "lint-yaml",
        "lint-shell",
        "lint-actions",
        "lint-editorconfig",
        "lint-cockpit-code",
        "lint-cockpit-style",
        "lint-cockpit-html",
        "megalint",
        "typecheck-cockpit",
        "todo",
    ]


def test_format_whitespace_no_fix_reports_trailing_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "example.txt"
    path.write_bytes(b"value  \n")

    with (
        patch.object(sys, "argv", ["format-whitespace", "--no-fix"]),
        patch("owlbear_tools.lint.subprocess.check_output", return_value=f"{path}\0".encode()),
        pytest.raises(SystemExit, match="1"),
    ):
        format_whitespace()


def test_no_fix_text_check_skips_precommit_excluded_paths() -> None:
    with (
        patch.object(sys, "argv", ["format-eof", "--no-fix"]),
        patch("owlbear_tools.lint.subprocess.check_output", return_value=b".owlbear/legacy/absent.md\0"),
        pytest.raises(SystemExit, match="0"),
    ):
        format_eof()


@pytest.mark.parametrize("command", [lint, megalint, lint_full, quality_full])
def test_unsafe_and_no_fix_are_mutually_exclusive(command: object) -> None:
    with (
        patch.object(sys, "argv", ["command", "--no-fix", "--unsafe-fix"]),
        pytest.raises(SystemExit, match="2"),
    ):
        command()
