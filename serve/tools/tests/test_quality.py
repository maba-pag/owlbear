"""Behavioral tests for quality command wrappers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.quality import (
    _DIRECT_HOOKS,
    _PRECOMMIT_FIX_HOOKS,
    FixMode,
    _consumer_lint,
    _precommit_hook_names,
    _run_biome,
    _run_leaf,
    _run_named,
    format_commands,
    format_eof,
    format_whitespace,
    lint,
    lint_biome,
    lint_python,
    quality,
)
from owlbear_tools.quality_runtime import _call

_ROOT = Path(__file__).resolve().parents[3]
_UNCLAIMED = (
    "check-yaml",
    "check-merge-conflict",
    "check-added-large-files",
    "validate-skills",
    "validate-agents",
    "validate-prompts",
    "todo-check",
)


def _static_ci_hooks(monkeypatch: pytest.MonkeyPatch) -> tuple[set[str], set[str]]:
    """Return the hooks CI's Static suite passes to pre-commit and those it covers, fixers via check twins."""
    monkeypatch.chdir(_ROOT)
    with (
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
        patch("owlbear_tools.quality._check_text_files", return_value=0),
        patch("owlbear_tools.quality._run_leaf", wraps=_run_leaf) as leaf,
    ):
        for command in (lint, format_commands):
            with patch.object(sys, "argv", ["command", "--no-fix"]), pytest.raises(SystemExit, match="0"):
                command()

    passed = {item.args[0][2] for item in call.call_args_list if item.args[0][:2] == ["pre-commit", "run"]}
    leaves = {item.args[0] for item in leaf.call_args_list}
    covered = set(passed) | {hook for hook, owner in _DIRECT_HOOKS.items() if owner in leaves}
    for name, (fixer, check, _unsafe) in _PRECOMMIT_FIX_HOOKS.items():
        if (check in passed) or (not check and name in leaves):
            covered.add(fixer)
    return passed, covered


def test_static_ci_runs_every_precommit_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    """A hook added to the config runs in CI without a second list (TD-409); unsafe fixes never do."""
    _, covered = _static_ci_hooks(monkeypatch)

    assert set(_precommit_hook_names()) - covered == {"ruff-unsafe-fix"}


def test_static_ci_runs_only_hooks_the_config_defines(monkeypatch: pytest.MonkeyPatch) -> None:
    passed, _ = _static_ci_hooks(monkeypatch)

    assert passed <= set(_precommit_hook_names())
    assert set(_DIRECT_HOOKS) <= set(_precommit_hook_names())
    assert not passed & {fixer for fixer, _check, _unsafe in _PRECOMMIT_FIX_HOOKS.values()}


def test_lint_runs_the_normal_local_suite() -> None:
    with (
        patch.object(sys, "argv", ["lint"]),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    commands = [item.args[0] for item in call.call_args_list]
    manual = ["--hook-stage", "manual", "--all-files"]
    assert commands == [
        ["pre-commit", "run", "ruff-fix", *manual],
        ["pre-commit", "run", "markdownlint-fix", *manual],
        ["pre-commit", "run", "yamllint", *manual],
        ["pre-commit", "run", "shellcheck", *manual],
        ["pre-commit", "run", "actionlint", *manual],
        ["pre-commit", "run", "zizmor", *manual],
        ["pre-commit", "run", "editorconfig-checker", *manual],
        ["node", "node_modules/@biomejs/biome/bin/biome", "check", ".", "--write"],
        *(["pre-commit", "run", hook, *manual] for hook in _UNCLAIMED),
    ]


def test_call_bridges_node_ca_to_python_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ca_path = tmp_path / "atls-root.pem"
    ca_path.write_text("certificate", encoding="utf-8")
    monkeypatch.setenv("NODE_EXTRA_CA_CERTS", str(ca_path))
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)

    with patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call:
        assert _call(["editorconfig-checker"]) == 0

    environment = call.call_args.kwargs["env"]
    assert environment["SSL_CERT_FILE"] == str(ca_path)
    assert environment["REQUESTS_CA_BUNDLE"] == str(ca_path)
    assert environment["CURL_CA_BUNDLE"] == str(ca_path)
    assert environment["PIP_CERT"] == str(ca_path)


def test_lint_staged_passes_staged_files_to_every_local_leaf() -> None:
    staged = b"README.md\0package.json\0"
    with (
        patch.object(sys, "argv", ["lint", "--staged"]),
        patch("owlbear_tools.quality_runtime.subprocess.check_output", return_value=staged),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    precommit_commands = [item.args[0] for item in call.call_args_list if item.args[0][0] == "pre-commit"]
    assert all("--files" in command for command in precommit_commands)
    assert all("README.md" in command for command in precommit_commands)
    biome_command = next(item.args[0] for item in call.call_args_list if item.args[0][0] == "node")
    assert biome_command[2:] == ["check", "--staged", "--no-errors-on-unmatched", "--write"]


def test_lint_python_exposes_safe_no_fix_and_unsafe_modes() -> None:
    for option, hook in (([], "ruff-fix"), (["--no-fix"], "ruff-check"), (["--unsafe-fix"], "ruff-unsafe-fix")):
        with (
            patch.object(sys, "argv", ["lint-python", *option]),
            patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
            pytest.raises(SystemExit, match="0"),
        ):
            lint_python()

        assert call.call_args.args[0] == ["pre-commit", "run", hook, "--hook-stage", "manual", "--all-files"]


@pytest.mark.parametrize(
    ("options", "flags"),
    [([], ["--write"]), (["--no-fix"], []), (["--unsafe-fix"], ["--write", "--unsafe"])],
)
def test_lint_biome_forwards_fix_policy(options: list[str], flags: list[str]) -> None:
    with (
        patch.object(sys, "argv", ["lint-biome", *options]),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint_biome()

    assert call.call_args.args[0] == [
        "node",
        "node_modules/@biomejs/biome/bin/biome",
        "check",
        ".",
        *flags,
    ]


@pytest.mark.parametrize("staged", [False, True])
def test_biome_formatter_preserves_selection_without_lint_fixes(*, staged: bool) -> None:
    with patch("owlbear_tools.quality._call", return_value=0) as call:
        assert _run_biome(staged=staged, fix_mode=FixMode.SAFE, format_only=True) == 0
    selection = ["--staged", "--no-errors-on-unmatched"] if staged else ["."]
    assert call.call_args.args[0][2:] == ["format", *selection, "--write"]


def test_quality_runs_format_then_lint_checks() -> None:
    with (
        patch.object(sys, "argv", ["quality", "--no-fix"]),
        patch("owlbear_tools.quality_runtime.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        quality()

    commands = [item.args[0] for item in call.call_args_list]
    assert commands[0][:3] == ["pre-commit", "run", "ruff-format-check"]
    assert ["pre-commit", "run", "ruff-check"] in [command[:3] for command in commands]


def test_quality_executes_todo_last() -> None:
    executed: list[str] = []

    def record(name: str, **_: object) -> int:
        executed.append(name)
        return 0

    with patch("owlbear_tools.quality._run_leaf", side_effect=record):
        assert _run_named("quality", staged=False, fix_mode=FixMode.SAFE) == 0

    assert executed[-1] == "todo-check"
    assert executed == [
        "format-python",
        "format-biome",
        "format-whitespace",
        "format-eof",
        "lint-python",
        "lint-markdown",
        "lint-yaml",
        "lint-shell",
        "lint-actionlint",
        "lint-zizmor",
        "lint-editorconfig",
        "lint-biome",
        *_UNCLAIMED,
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


def test_text_check_reports_malformed_precommit_config(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["format-eof", "--no-fix"]),
        patch("owlbear_tools.quality.yaml.safe_load", side_effect=ValueError("invalid YAML")),
        pytest.raises(SystemExit, match="2"),
    ):
        format_eof()

    assert "Error: invalid YAML" in capsys.readouterr().err


@pytest.mark.parametrize("command", [lint, quality])
def test_unsafe_and_no_fix_are_mutually_exclusive(command: object) -> None:
    with (
        patch.object(sys, "argv", ["command", "--no-fix", "--unsafe-fix"]),
        pytest.raises(SystemExit, match="2"),
    ):
        command()
