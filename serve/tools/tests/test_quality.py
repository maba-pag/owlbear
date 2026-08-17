"""Behavioral tests for quality command wrappers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.megalinter import MegaLinterImage, megalint
from owlbear_tools.quality import (
    FixMode,
    _consumer_lint,
    _run_cockpit_html,
    _run_named,
    format_eof,
    format_whitespace,
    lint,
    lint_full,
    lint_python,
    quality_full,
    typecheck_cockpit,
)

_TEST_IMAGE = MegaLinterImage(reference="registry.example/megalinter-main:v-current")


def test_lint_runs_the_normal_local_suite() -> None:
    with (
        patch.object(sys, "argv", ["lint"]),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    commands = [item.args[0] for item in call.call_args_list]
    assert commands == [
        ["pre-commit", "run", "ruff-fix", "--all-files"],
        ["pre-commit", "run", "markdownlint-fix", "--all-files"],
        ["pre-commit", "run", "eslint-json", "--all-files"],
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
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=staged),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
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
            patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
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
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
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
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
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

    with patch("owlbear_tools.quality._run_leaf", side_effect=record):
        assert _run_named("quality-full", staged=False, fix_mode=FixMode.SAFE) == 0

    assert executed[-1] == "todo"
    assert executed == [
        "format-python",
        "format-whitespace",
        "format-eof",
        "lint-python",
        "lint-markdown",
        "lint-json",
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
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=f"{path}\0".encode()),
        pytest.raises(SystemExit, match="1"),
    ):
        format_whitespace()


def test_no_fix_text_check_skips_precommit_excluded_paths(tmp_path: Path) -> None:
    path = tmp_path / ".owlbear/legacy/absent.md"
    path.parent.mkdir(parents=True)
    path.write_text("missing newline", encoding="utf-8")
    with (
        patch.object(sys, "argv", ["format-eof", "--no-fix"]),
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=f"{path}\0".encode()),
        pytest.raises(SystemExit, match="0"),
    ):
        format_eof()


def test_consumer_lint_accepts_staged_non_python_files_with_ruff_config(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")

    with (
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=b"README.md\0"),
        patch("owlbear_tools.quality_runtime.subprocess.call") as call,
    ):
        assert _consumer_lint(tmp_path, staged=True, fix_mode=FixMode.NONE) == 0

    call.assert_not_called()


def test_consumer_lint_skips_unscoped_npm_lint_in_staged_mode(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"scripts":{"lint":"eslint ."}}\n', encoding="utf-8")

    with (
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=b"src/App.tsx\0"),
        patch("owlbear_tools.quality_runtime.subprocess.call") as call,
    ):
        assert _consumer_lint(tmp_path, staged=True, fix_mode=FixMode.NONE) == 0

    call.assert_not_called()


def test_consumer_lint_resolves_staged_targets_from_git_root(tmp_path: Path) -> None:
    consumer_root = tmp_path / "consumer"
    nested = consumer_root / "packages/app"
    nested.mkdir(parents=True)
    (nested / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    staged_path = consumer_root / "packages/app/main.py"

    with (
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=b"packages/app/main.py\0"),
        patch("owlbear_tools.quality._git_root", return_value=consumer_root),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
    ):
        assert _consumer_lint(nested, staged=True, fix_mode=FixMode.NONE) == 0

    assert call.call_args.args[0] == ["ruff", "check", str(staged_path)]


def test_consumer_staged_lint_does_not_apply_fixes(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")

    with (
        patch("owlbear_tools.quality._git_paths", return_value=["main.py"]),
        patch("owlbear_tools.quality._git_root", return_value=tmp_path),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
    ):
        assert _consumer_lint(tmp_path, staged=True, fix_mode=FixMode.SAFE) == 0

    assert call.call_args.args[0] == ["ruff", "check", str(tmp_path / "main.py")]


def test_staged_cockpit_html_lints_any_html_file() -> None:
    with (
        patch("owlbear_tools.quality._git_paths", return_value=["serve/cockpit/web/src/other.html"]),
        patch("owlbear_tools.quality._call", return_value=0) as call,
    ):
        assert _run_cockpit_html(staged=True) == 0

    call.assert_called_once()


def test_no_fix_text_check_skips_deleted_tracked_paths() -> None:
    with (
        patch.object(sys, "argv", ["format-eof", "--no-fix"]),
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=b"deleted.md\0"),
        pytest.raises(SystemExit, match="0"),
    ):
        format_eof()


def test_format_eof_rejects_newline_only_files(tmp_path: Path) -> None:
    path = tmp_path / "newline-only.txt"
    path.write_bytes(b"\n")

    with (
        patch.object(sys, "argv", ["format-eof", "--no-fix"]),
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=f"{path}\0".encode()),
        pytest.raises(SystemExit, match="1"),
    ):
        format_eof()


def test_public_quality_leaf_reports_runtime_errors(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["format-eof"]),
        patch("owlbear_tools.quality._run_named", side_effect=RuntimeError("git unavailable")),
        pytest.raises(SystemExit, match="2"),
    ):
        format_eof()

    assert "Error: git unavailable" in capsys.readouterr().err


def test_lint_rejects_an_owlbear_development_subdirectory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "workspace"
    child = root / "serve/tools"
    child.mkdir(parents=True)
    (root / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.chdir(child)
    monkeypatch.setattr("owlbear_tools.quality_runtime._REPOSITORY_ROOT", root)

    with patch.object(sys, "argv", ["lint"]), pytest.raises(SystemExit, match="2"):
        lint()

    assert "must be run from the root" in capsys.readouterr().err


def test_lint_help_is_available_outside_development_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["lint-python", "--help"])

    with pytest.raises(SystemExit, match="0"):
        lint_python()


def test_text_check_reports_invalid_precommit_exclude(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["format-eof", "--no-fix"]),
        patch("owlbear_tools.quality.yaml.safe_load", return_value={"exclude": "["}),
        pytest.raises(SystemExit, match="2"),
    ):
        format_eof()

    assert "Error:" in capsys.readouterr().err


def test_typecheck_reports_missing_runtime(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["typecheck-cockpit"]),
        patch("owlbear_tools.quality._run_typecheck_cockpit", side_effect=OSError("npx unavailable")),
        pytest.raises(SystemExit, match="2"),
    ):
        typecheck_cockpit()

    assert "Error: npx unavailable" in capsys.readouterr().err


def test_megalint_reports_invalid_configuration(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["megalint", "--no-fix"]),
        patch("owlbear_tools.megalinter.load_megalinter_image", side_effect=ValueError("invalid image")),
        pytest.raises(SystemExit, match="2"),
    ):
        megalint()

    assert "Error: invalid image" in capsys.readouterr().err


def test_text_check_reports_malformed_precommit_config(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["format-eof", "--no-fix"]),
        patch("owlbear_tools.quality.yaml.safe_load", side_effect=ValueError("invalid YAML")),
        pytest.raises(SystemExit, match="2"),
    ):
        format_eof()

    assert "Error: invalid YAML" in capsys.readouterr().err


@pytest.mark.parametrize("command", [lint, megalint, lint_full, quality_full])
def test_unsafe_and_no_fix_are_mutually_exclusive(command: object) -> None:
    with (
        patch.object(sys, "argv", ["command", "--no-fix", "--unsafe-fix"]),
        pytest.raises(SystemExit, match="2"),
    ):
        command()
