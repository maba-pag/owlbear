"""Workspace lint, formatting, and quality commands."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

import yaml

from owlbear_tools.quality_runtime import (
    FixMode,
    _add_fix_mode,
    _call,
    _finish,
    _git_paths,
    _git_root,
    _is_owlbear_dev_checkout,
    _is_owlbear_dev_subdirectory,
    _parse_options,
    _require_development,
)

BIOME = Path("node_modules/@biomejs/biome/bin/biome")
_PYTHON_SUFFIXES = frozenset({".py", ".pyi"})


_PRECOMMIT_FIX_HOOKS: dict[str, tuple[str, str, str | None]] = {
    "lint-python": ("ruff-fix", "ruff-check", "ruff-unsafe-fix"),
    "lint-markdown": ("markdownlint-fix", "markdownlint-check", None),
    "format-python": ("ruff-format-fix", "ruff-format-check", None),
    "format-whitespace": ("trailing-whitespace-fix", "", None),
    "format-eof": ("end-of-file-fix", "", None),
}
_PRECOMMIT_CHECK_HOOKS = {
    "lint-yaml": "yamllint",
    "lint-shell": "shellcheck",
    "lint-actionlint": "actionlint",
    "lint-zizmor": "zizmor",
    "lint-editorconfig": "editorconfig-checker",
}
# Config hooks whose tool a named leaf runs without pre-commit.
_DIRECT_HOOKS = {"biome-check": "lint-biome"}
# `lint` also runs every config hook no leaf claims, so the config is the one list (TD-409).
_AGGREGATES: dict[str, tuple[str, ...]] = {
    "lint": (
        "lint-python",
        "lint-markdown",
        "lint-yaml",
        "lint-shell",
        "lint-actions",
        "lint-editorconfig",
        "lint-biome",
    ),
    "lint-actions": ("lint-actionlint", "lint-zizmor"),
    "format": ("format-python", "format-biome", "format-whitespace", "format-eof"),
    "quality": ("format", "lint"),  # lint ends with the config's todo-check hook
}


def _precommit_hook(hook: str, *, staged: bool) -> int:
    if staged:
        paths = _git_paths(staged=True)
        if not paths:
            return 0
    command = ["pre-commit", "run", hook, "--hook-stage", "manual"]  # every hook is manual-only (TD-204)
    if staged:
        command.extend(["--files", *paths])
    else:
        command.append("--all-files")
    return _call(command)


def _run_precommit_fix_hook(name: str, *, staged: bool, fix_mode: FixMode) -> int:
    safe_hook, check_hook, unsafe_hook = _PRECOMMIT_FIX_HOOKS[name]
    if fix_mode is FixMode.NONE:
        if not check_hook:
            return _check_text_files(name, staged=staged)
        return _precommit_hook(check_hook, staged=staged)
    if fix_mode is FixMode.UNSAFE and unsafe_hook is not None:
        return _precommit_hook(unsafe_hook, staged=staged)
    return _precommit_hook(safe_hook, staged=staged)


def _precommit_config() -> tuple[object, list[dict[str, object]]]:
    """Return the top-level exclude and the hook entries of the workspace pre-commit config."""
    config_path = Path.cwd() / ".pre-commit-config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        message = f"{config_path} must contain a YAML mapping"
        raise TypeError(message)
    repos = config.get("repos", [])
    if not isinstance(repos, list):
        message = f"{config_path} repos must be a YAML sequence"
        raise TypeError(message)
    entries: list[dict[str, object]] = []
    for repo in repos:
        if not isinstance(repo, dict):
            message = f"{config_path} repository entries must be YAML mappings"
            raise TypeError(message)
        hooks = repo.get("hooks", [])
        if not isinstance(hooks, list):
            message = f"{config_path} hook lists must be YAML sequences"
            raise TypeError(message)
        entries.extend(entry for entry in hooks if isinstance(entry, dict))
    return config.get("exclude"), entries


def _precommit_excludes(hook: str) -> tuple[re.Pattern[str], ...]:
    """Return the exclude patterns pre-commit applies to one hook."""
    top_level, entries = _precommit_config()
    scoped = [
        entry["exclude"]
        for entry in entries
        if hook in {entry.get("id"), entry.get("alias")} and isinstance(entry.get("exclude"), str)
    ]
    patterns = ([top_level] if isinstance(top_level, str) else []) + scoped
    return tuple(re.compile(pattern) for pattern in patterns)


def _precommit_hook_names() -> tuple[str, ...]:
    """Return each config hook's `pre-commit run` name: its alias, else its id."""
    _, entries = _precommit_config()
    names = (entry.get("alias") or entry.get("id") for entry in entries)
    return tuple(dict.fromkeys(name for name in names if isinstance(name, str)))


def _unclaimed_hooks() -> tuple[str, ...]:
    claimed = {*_PRECOMMIT_CHECK_HOOKS.values(), *_DIRECT_HOOKS}
    claimed |= {hook for hooks in _PRECOMMIT_FIX_HOOKS.values() for hook in hooks if hook}
    return tuple(name for name in _precommit_hook_names() if name not in claimed)


def _check_text_files(name: str, *, staged: bool) -> int:
    excludes = _precommit_excludes(_PRECOMMIT_FIX_HOOKS[name][0])
    paths = [
        path
        for path in _git_paths(staged=staged)
        if Path(path).exists() and not any(pattern.search(path) for pattern in excludes)
    ]
    failures = 0
    for raw_path in paths:
        path = Path(raw_path)
        try:
            data = path.read_bytes()
        except OSError as exc:
            print(f"{path}: unable to read: {exc}")  # noqa: T201
            failures += 1
            continue
        if not data or b"\0" in data:
            continue
        if name == "format-whitespace" and any(
            line.rstrip(b"\r\n").endswith((b" ", b"\t")) for line in data.splitlines(keepends=True)
        ):
            print(f"{path}: trailing whitespace")  # noqa: T201
            failures += 1
        if name == "format-eof":
            content = data.rstrip(b"\r\n")
            line_ending = data[len(content) :]
            if not content or line_ending not in (b"\n", b"\r\n"):
                print(f"{path}: expected exactly one final newline")  # noqa: T201
                failures += 1
    return int(bool(failures))


def _run_biome(*, staged: bool, fix_mode: FixMode, format_only: bool = False) -> int:
    command = ["node", str(BIOME), "format" if format_only else "check"]
    command.extend(["--staged", "--no-errors-on-unmatched"] if staged else ["."])
    if fix_mode is not FixMode.NONE:
        command.append("--write")
    if fix_mode is FixMode.UNSAFE and not format_only:
        command.append("--unsafe")
    return _call(command)


def _run_leaf(name: str, *, staged: bool, fix_mode: FixMode) -> int:
    if name in _PRECOMMIT_FIX_HOOKS:
        result = _run_precommit_fix_hook(name, staged=staged, fix_mode=fix_mode)
    elif name in _PRECOMMIT_CHECK_HOOKS:
        result = _precommit_hook(_PRECOMMIT_CHECK_HOOKS[name], staged=staged)
    elif name in {"lint-biome", "format-biome"}:
        result = _run_biome(staged=staged, fix_mode=fix_mode, format_only=name == "format-biome")
    elif name in _unclaimed_hooks():
        result = _precommit_hook(name, staged=staged)
    else:
        message = f"unknown quality command: {name}"
        raise ValueError(message)
    return result


def _run_named(name: str, *, staged: bool, fix_mode: FixMode) -> int:
    children = _AGGREGATES.get(name)
    if children is None:
        return _run_leaf(name, staged=staged, fix_mode=fix_mode)
    if name == "lint":
        children = (*children, *_unclaimed_hooks())
    failures = 0
    for child in children:
        failures += int(bool(_run_named(child, staged=staged, fix_mode=fix_mode)))
    return int(bool(failures))


def _run_named_checked(name: str, *, staged: bool, fix_mode: FixMode) -> int:
    try:
        return _run_named(name, staged=staged, fix_mode=fix_mode)
    except (OSError, RuntimeError, TypeError, ValueError, re.error, yaml.YAMLError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2


def _has_ruff_config(root: Path) -> bool:
    if any((root / name).is_file() for name in ("ruff.toml", ".ruff.toml")):
        return True
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    tool = config.get("tool")
    return isinstance(tool, dict) and isinstance(tool.get("ruff"), dict)


def _consumer_package_command(root: Path, fix_mode: FixMode) -> list[str] | None:
    package = root / "package.json"
    if not package.is_file():
        return None
    config = json.loads(package.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        message = f"{package} must contain a JSON object"
        raise TypeError(message)
    scripts = config.get("scripts")
    if not isinstance(scripts, dict) or not isinstance(scripts.get("lint"), str):
        return None
    script = "lint:fix" if fix_mode is not FixMode.NONE and isinstance(scripts.get("lint:fix"), str) else "lint"
    return ["npm", "run", script]


def _consumer_lint(root: Path, *, staged: bool, fix_mode: FixMode) -> int:
    paths = _git_paths(staged=staged) if staged else ["."]
    has_ruff = _has_ruff_config(root)
    package_command = _consumer_package_command(root, fix_mode)
    commands: list[list[str]] = []
    if has_ruff:
        git_root = _git_root() if staged else root
        targets = [
            str(git_root / path)
            for path in paths
            if (git_root / path).is_dir() or Path(path).suffix in _PYTHON_SUFFIXES
        ]
        if targets:
            if staged or fix_mode is FixMode.NONE:
                commands.append(["ruff", "check", *targets])
            else:
                command = ["ruff", "check", "--fix"]
                if fix_mode is FixMode.UNSAFE:
                    command.append("--unsafe-fixes")
                commands.append([*command, *targets])
    if package_command is not None and not staged:
        commands.append(package_command)
    if not commands:
        if has_ruff or package_command is not None:
            return 0
        sys.stderr.write(
            "No consumer lint configuration found. Add [tool.ruff], ruff.toml, .ruff.toml, "
            "or a package.json lint script.\n"
        )
        return 2
    failures = sum(bool(_call(command, cwd=root)) for command in commands)
    return int(bool(failures))


def lint() -> None:
    """Run the normal local lint suite or discover consumer-owned lint tools."""
    parser = argparse.ArgumentParser(prog="lint")
    parser.add_argument("--staged", "-s", action="store_true")
    _add_fix_mode(parser, allow_unsafe=True)
    args = parser.parse_args()
    try:
        cwd = Path.cwd()
        if _is_owlbear_dev_checkout(cwd):
            rc = _run_named_checked("lint", staged=args.staged, fix_mode=args.fix_mode)
        elif _is_owlbear_dev_subdirectory(cwd):
            sys.stderr.write("lint must be run from the root of the OwlBear development checkout\n")
            rc = 2
        else:
            rc = _consumer_lint(cwd, staged=args.staged, fix_mode=args.fix_mode)
    except (OSError, RuntimeError, TypeError, ValueError, re.error, yaml.YAMLError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        rc = 2
    _finish(rc)


def _run_public_leaf(name: str, *, fixes: bool, allow_unsafe: bool, staged: bool) -> None:
    args = _parse_options(name, staged=staged, fixes=fixes, allow_unsafe=allow_unsafe)
    _require_development(name)
    rc = _run_named_checked(name, staged=getattr(args, "staged", False), fix_mode=args.fix_mode)
    _finish(rc)


def lint_python() -> None:
    """Run Ruff's Python lint checks."""
    _run_public_leaf("lint-python", fixes=True, allow_unsafe=True, staged=True)


def lint_markdown() -> None:
    """Run Markdown lint checks."""
    _run_public_leaf("lint-markdown", fixes=True, allow_unsafe=False, staged=True)


def lint_yaml() -> None:
    """Run strict YAML lint checks."""
    _run_public_leaf("lint-yaml", fixes=False, allow_unsafe=False, staged=True)


def lint_shell() -> None:
    """Run ShellCheck on shell sources."""
    _run_public_leaf("lint-shell", fixes=False, allow_unsafe=False, staged=True)


def lint_actions() -> None:
    """Run Actionlint and zizmor on GitHub workflows."""
    _run_public_leaf("lint-actions", fixes=False, allow_unsafe=False, staged=True)


def lint_editorconfig() -> None:
    """Check repository files against EditorConfig policy."""
    _run_public_leaf("lint-editorconfig", fixes=False, allow_unsafe=False, staged=True)


def lint_biome() -> None:
    """Run Biome checks for repository JSON files."""
    _run_public_leaf("lint-biome", fixes=True, allow_unsafe=True, staged=True)


def format_python() -> None:
    """Format Python with Ruff."""
    _run_public_leaf("format-python", fixes=True, allow_unsafe=False, staged=True)


def format_biome() -> None:
    """Format repository JSON files with Biome."""
    _run_public_leaf("format-biome", fixes=True, allow_unsafe=False, staged=True)


def format_whitespace() -> None:
    """Remove trailing whitespace."""
    _run_public_leaf("format-whitespace", fixes=True, allow_unsafe=False, staged=True)


def format_eof() -> None:
    """Normalize final newlines."""
    _run_public_leaf("format-eof", fixes=True, allow_unsafe=False, staged=True)


def format_commands() -> None:
    """Run all dedicated formatters and text normalizers."""
    args = _parse_options("format", staged=True, fixes=True, allow_unsafe=False)
    _require_development("format")
    _finish(_run_named_checked("format", staged=args.staged, fix_mode=args.fix_mode))


def quality() -> None:
    """Run format, lint, and advisory checks."""
    args = _parse_options("quality", staged=False, fixes=True, allow_unsafe=True)
    _require_development("quality")
    _finish(_run_named_checked("quality", staged=False, fix_mode=args.fix_mode))
