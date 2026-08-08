"""Behavioral tests for lint command wrappers."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

from owlbear_tools.lint import lint, lint_full, megalint, megalint_hook, typecheck
from owlbear_tools.megalinter import MegaLinterImage

_TEST_IMAGE = MegaLinterImage(reference="registry.example/megalinter-main:v-current")


def test_lint_uses_staged_files_when_no_paths_are_given() -> None:
    with (
        patch.object(sys, "argv", ["lint"]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    call.assert_called_once_with(["pre-commit", "run"])


def test_lint_passes_explicit_paths_to_pre_commit() -> None:
    paths = ["share/skills/h-mcp-memory/SKILL.md", "share/skills/r-pipeline-protocol/SKILL.md"]
    with (
        patch.object(sys, "argv", ["lint", *paths]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    call.assert_called_once_with(["pre-commit", "run", "--files", *paths])


@pytest.mark.parametrize("option", ["--all", "-a"])
def test_lint_runs_all_files_for_all_option(option: str) -> None:
    with (
        patch.object(sys, "argv", ["lint", option]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    call.assert_called_once_with(["pre-commit", "run", "--all-files"])


def test_lint_rejects_all_with_explicit_paths() -> None:
    with patch.object(sys, "argv", ["lint", "--all", "README.md"]), pytest.raises(SystemExit, match="2"):
        lint()


def test_lint_no_fix_replaces_mutating_hooks_with_check_hooks() -> None:
    with (
        patch.object(sys, "argv", ["lint", "--no-fix", "README.md"]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    commands = [args[0][0] for args in call.call_args_list]
    assert commands == [
        ["pre-commit", "run", "--files", "README.md"],
        ["pre-commit", "run", "text-hygiene-check", "--hook-stage", "manual", "--files", "README.md"],
        ["pre-commit", "run", "ruff-check", "--hook-stage", "manual", "--files", "README.md"],
        ["pre-commit", "run", "ruff-format-check", "--hook-stage", "manual", "--files", "README.md"],
        ["pre-commit", "run", "markdownlint-check", "--hook-stage", "manual", "--files", "README.md"],
        ["pre-commit", "run", "eslint-frontend-check", "--hook-stage", "manual", "--files", "README.md"],
        ["pre-commit", "run", "stylelint-frontend-check", "--hook-stage", "manual", "--files", "README.md"],
    ]
    assert "trailing-whitespace-fix" in call.call_args_list[0].kwargs["env"]["SKIP"]


def test_lint_unsafe_fixes_replaces_safe_hooks_with_stronger_hooks() -> None:
    with (
        patch.object(sys, "argv", ["lint", "--unsafe-fixes", "serve/cockpit/web/src/styles.css"]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    commands = [args[0][0] for args in call.call_args_list]
    assert commands == [
        ["pre-commit", "run", "--files", "serve/cockpit/web/src/styles.css"],
        [
            "pre-commit",
            "run",
            "ruff-unsafe-fix",
            "--hook-stage",
            "manual",
            "--files",
            "serve/cockpit/web/src/styles.css",
        ],
        [
            "pre-commit",
            "run",
            "stylelint-frontend-lax",
            "--hook-stage",
            "manual",
            "--files",
            "serve/cockpit/web/src/styles.css",
        ],
    ]
    skip = call.call_args_list[0].kwargs["env"]["SKIP"]
    assert "ruff-fix" in skip
    assert "stylelint-frontend-fix" in skip


@pytest.mark.parametrize("command", [lint, megalint, lint_full])
def test_fix_modes_are_mutually_exclusive(command: object) -> None:
    with (
        patch.object(sys, "argv", ["lint", "--no-fix", "--unsafe-fixes"]),
        pytest.raises(SystemExit, match="2"),
    ):
        command()


@pytest.mark.parametrize(
    ("command", "hook"),
    [(megalint, "megalinter"), (typecheck, "typecheck-frontend")],
)
def test_manual_commands_run_only_their_named_hook(command: object, hook: str) -> None:
    with (
        patch.object(sys, "argv", [hook]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        command()

    call.assert_called_once_with(["pre-commit", "run", hook, "--all-files", "--hook-stage", "manual"])


def test_megalint_no_fix_disables_fixes_for_the_hook() -> None:
    with (
        patch.object(sys, "argv", ["megalint", "--no-fix"]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        megalint()

    assert call.call_args.args[0] == [
        "pre-commit",
        "run",
        "megalinter",
        "--all-files",
        "--hook-stage",
        "manual",
    ]
    assert call.call_args.kwargs["env"]["OWLBEAR_LINT_NO_FIX"] == "1"


def test_megalint_unsafe_fixes_enables_stronger_container_mode() -> None:
    with (
        patch.object(sys, "argv", ["megalint", "--unsafe-fixes"]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        megalint()

    assert call.call_args.kwargs["env"]["OWLBEAR_LINT_UNSAFE_FIXES"] == "1"


def test_lint_full_supports_all_fix_modes() -> None:
    for option, expected_env in (
        ([], {}),
        (["--no-fix"], {"OWLBEAR_LINT_NO_FIX": "1"}),
        (["--unsafe-fixes"], {"OWLBEAR_LINT_UNSAFE_FIXES": "1"}),
    ):
        with (
            patch.object(sys, "argv", ["lint-full", *option]),
            patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
            pytest.raises(SystemExit, match="0"),
        ):
            lint_full()

        megalint_call = next(
            item for item in call.call_args_list if item.args[0][0:3] == ["pre-commit", "run", "megalinter"]
        )
        env = megalint_call.kwargs.get("env", {})
        for key, value in expected_env.items():
            assert env[key] == value


def test_megalint_hook_runs_stronger_linter_modes() -> None:
    with (
        patch.dict(os.environ, {"OWLBEAR_LINT_UNSAFE_FIXES": "1"}),
        patch("owlbear_tools.lint.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        megalint_hook()

    command = call.call_args.args[0]
    assert "PYTHON_RUFF_ARGUMENTS=--unsafe-fixes" in command
    assert "CSS_STYLELINT_COMMAND_REMOVE_ARGUMENTS=--fix" in command
    assert "CSS_STYLELINT_ARGUMENTS=--fix=lax" in command
