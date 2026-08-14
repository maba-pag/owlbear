"""Workspace lint, formatting, and quality commands."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from enum import StrEnum
from pathlib import Path

import yaml

from owlbear_tools.commands import command_footer
from owlbear_tools.megalinter import load_megalinter_image

COCKPIT_WEB = Path("serve/cockpit/web")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_NO_FIX_ENV = "OWLBEAR_LINT_NO_FIX"
_UNSAFE_FIX_ENV = "OWLBEAR_LINT_UNSAFE_FIXES"
_PYTHON_SUFFIXES = frozenset({".py", ".pyi"})


class FixMode(StrEnum):
    """Supported lint mutation policies."""

    SAFE = "safe"
    NONE = "none"
    UNSAFE = "unsafe"


_PRECOMMIT_FIX_HOOKS: dict[str, tuple[str, str, str | None]] = {
    "lint-python": ("ruff-fix", "ruff-check", "ruff-unsafe-fix"),
    "lint-markdown": ("markdownlint-fix", "markdownlint-check", None),
    "lint-cockpit-code": ("eslint-frontend-fix", "eslint-frontend-check", None),
    "lint-cockpit-style": ("stylelint-frontend-fix", "stylelint-frontend-check", "stylelint-frontend-lax"),
    "format-python": ("ruff-format-fix", "ruff-format-check", None),
    "format-whitespace": ("trailing-whitespace-fix", "", None),
    "format-eof": ("end-of-file-fix", "", None),
}
_PRECOMMIT_CHECK_HOOKS = {
    "lint-yaml": "yamllint",
    "lint-shell": "shellcheck",
    "lint-actions": "actionlint",
    "lint-editorconfig": "editorconfig-checker",
}
_AGGREGATES: dict[str, tuple[str, ...]] = {
    "lint": (
        "lint-python",
        "lint-markdown",
        "lint-yaml",
        "lint-shell",
        "lint-actions",
        "lint-editorconfig",
        "lint-cockpit",
    ),
    "lint-cockpit": ("lint-cockpit-code", "lint-cockpit-style", "lint-cockpit-html"),
    "lint-full": ("lint", "megalint"),
    "format-full": ("format-python", "format-whitespace", "format-eof"),
    "quality-full": ("format-full", "lint-full", "typecheck-cockpit", "todo"),
}
_SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "dist",
        "__pycache__",
        "build",
        ".egg-info",
        "megalinter-reports",
        "test-results",
        "scratch",
    }
)
_TODO_RE = re.compile(r"^> \*\*TODO:\*\*", re.MULTILINE)


def _call(command: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> int:
    kwargs: dict[str, object] = {}
    if env is not None:
        kwargs["env"] = env
    if cwd is not None:
        kwargs["cwd"] = cwd
    return subprocess.call(command, **kwargs)  # noqa: S603


def _git_paths(*, staged: bool) -> list[str]:
    command = (
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"] if staged else ["git", "ls-files", "-z"]
    )
    try:
        output = subprocess.check_output(command)  # noqa: S603
    except (OSError, subprocess.CalledProcessError) as exc:
        scope = "staged files" if staged else "workspace files"
        message = f"unable to discover {scope} from Git"
        raise RuntimeError(message) from exc
    return [value.decode("utf-8") for value in output.split(b"\0") if value]


def _add_fix_mode(parser: argparse.ArgumentParser, *, allow_unsafe: bool) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--no-fix", "-n", action="store_const", const=FixMode.NONE, dest="fix_mode")
    if allow_unsafe:
        group.add_argument("--unsafe-fix", "-u", action="store_const", const=FixMode.UNSAFE, dest="fix_mode")
    parser.set_defaults(fix_mode=FixMode.SAFE)


def _parse_options(
    prog: str,
    *,
    staged: bool,
    fixes: bool,
    allow_unsafe: bool = False,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=prog)
    if staged:
        parser.add_argument("--staged", "-s", action="store_true")
    if fixes:
        _add_fix_mode(parser, allow_unsafe=allow_unsafe)
    else:
        parser.set_defaults(fix_mode=FixMode.NONE)
    return parser.parse_args()


def _precommit_hook(hook: str, *, staged: bool, manual: bool = False) -> int:
    if staged:
        paths = _git_paths(staged=True)
        if not paths:
            return 0
    command = ["pre-commit", "run", hook]
    if manual:
        command.extend(["--hook-stage", "manual"])
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
        return _precommit_hook(check_hook, staged=staged, manual=True)
    if fix_mode is FixMode.UNSAFE and unsafe_hook is not None:
        return _precommit_hook(unsafe_hook, staged=staged, manual=True)
    return _precommit_hook(safe_hook, staged=staged)


def _precommit_excludes(hook: str) -> tuple[re.Pattern[str], ...]:
    """Return the exclude patterns pre-commit applies to one hook."""
    config = yaml.safe_load((Path.cwd() / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    top_level = config.get("exclude")
    scoped = [
        entry["exclude"]
        for repo in config.get("repos", [])
        for entry in repo.get("hooks", [])
        if hook in {entry.get("id"), entry.get("alias")} and isinstance(entry.get("exclude"), str)
    ]
    patterns = ([top_level] if isinstance(top_level, str) else []) + scoped
    return tuple(re.compile(pattern) for pattern in patterns)


def _check_text_files(name: str, *, staged: bool) -> int:
    excludes = _precommit_excludes(_PRECOMMIT_FIX_HOOKS[name][0])
    paths = [path for path in _git_paths(staged=staged) if not any(pattern.search(path) for pattern in excludes)]
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
            line_ending = data[len(data.rstrip(b"\r\n")) :]
            if line_ending not in (b"\n", b"\r\n"):
                print(f"{path}: expected exactly one final newline")  # noqa: T201
                failures += 1
    return int(bool(failures))


def _run_cockpit_html(*, staged: bool) -> int:
    if staged and "serve/cockpit/web/index.html" not in _git_paths(staged=True):
        return 0
    return _call(["npm", "run", "lint:html"], cwd=COCKPIT_WEB)


def _docker_command() -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "-v",
        f"{Path.cwd()}:/tmp/lint",
    ]


def _run_megalint(fix_mode: FixMode) -> int:
    image = load_megalinter_image()
    command = _docker_command()
    if fix_mode is FixMode.NONE:
        command.extend(["-e", "APPLY_FIXES=none"])
    if fix_mode is FixMode.UNSAFE:
        command.extend(
            [
                "-e",
                "PYTHON_RUFF_ARGUMENTS=--unsafe-fixes",
                "-e",
                "CSS_STYLELINT_COMMAND_REMOVE_ARGUMENTS=--fix",
                "-e",
                "CSS_STYLELINT_ARGUMENTS=--fix=lax",
            ]
        )
    command.extend(
        [
            "-e",
            "UPDATED_SOURCES_REPORTER=false",
            "-e",
            "LOG_LEVEL=INFO",
            "-e",
            "VALIDATE_ALL_CODEBASE=true",
            image.reference,
        ]
    )
    return _call(command)


def _run_typecheck_cockpit() -> int:
    return _call(
        [
            "npx",
            "--prefix",
            str(COCKPIT_WEB),
            "tsc",
            "--noEmit",
            "--project",
            str(COCKPIT_WEB / "tsconfig.json"),
        ]
    )


def _run_leaf(name: str, *, staged: bool, fix_mode: FixMode) -> int:
    if name in _PRECOMMIT_FIX_HOOKS:
        result = _run_precommit_fix_hook(name, staged=staged, fix_mode=fix_mode)
    elif name in _PRECOMMIT_CHECK_HOOKS:
        result = _precommit_hook(_PRECOMMIT_CHECK_HOOKS[name], staged=staged)
    elif name == "lint-cockpit-html":
        result = _run_cockpit_html(staged=staged)
    elif name == "megalint":
        result = _run_megalint(fix_mode)
    elif name == "typecheck-cockpit":
        result = _run_typecheck_cockpit()
    elif name == "todo":
        result = _run_todo()
    else:
        message = f"unknown quality command: {name}"
        raise ValueError(message)
    return result


def _run_named(name: str, *, staged: bool, fix_mode: FixMode) -> int:
    children = _AGGREGATES.get(name)
    if children is None:
        return _run_leaf(name, staged=staged, fix_mode=fix_mode)
    failures = 0
    for child in children:
        failures += int(bool(_run_named(child, staged=staged, fix_mode=fix_mode)))
    return int(bool(failures))


def _finish(rc: int) -> None:
    sys.stderr.write(command_footer() + "\n")
    raise SystemExit(rc)


def _require_development(prog: str) -> None:
    if not _is_owlbear_dev_checkout(Path.cwd()):
        message = f"{prog} is available only from the OwlBear development checkout"
        raise SystemExit(message)


def _is_owlbear_dev_checkout(root: Path) -> bool:
    return root.resolve() == _REPOSITORY_ROOT and (root / ".pre-commit-config.yaml").is_file()


def _has_ruff_config(root: Path) -> bool:
    if any((root / name).is_file() for name in ("ruff.toml", ".ruff.toml")):
        return True
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    tool = config.get("tool")
    return isinstance(tool, dict) and isinstance(tool.get("ruff"), dict)


def _consumer_lint(root: Path, *, staged: bool, fix_mode: FixMode) -> int:
    paths = _git_paths(staged=staged) if staged else ["."]
    has_ruff = _has_ruff_config(root)
    package = root / "package.json"
    package_command: list[str] | None = None
    if package.is_file():
        config = json.loads(package.read_text(encoding="utf-8"))
        scripts = config.get("scripts")
        if isinstance(scripts, dict) and isinstance(scripts.get("lint"), str):
            script = "lint:fix" if fix_mode is not FixMode.NONE and isinstance(scripts.get("lint:fix"), str) else "lint"
            package_command = ["npm", "run", script]
    commands: list[list[str]] = []
    if has_ruff:
        targets = [path for path in paths if Path(path).is_dir() or Path(path).suffix in _PYTHON_SUFFIXES]
        if targets:
            if fix_mode is FixMode.NONE:
                commands.append(["ruff", "check", *targets])
            else:
                command = ["ruff", "check", "--fix"]
                if fix_mode is FixMode.UNSAFE:
                    command.append("--unsafe-fixes")
                commands.append([*command, *targets])
    if package_command is not None:
        commands.append(package_command)
    if not commands:
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
        if _is_owlbear_dev_checkout(Path.cwd()):
            rc = _run_named("lint", staged=args.staged, fix_mode=args.fix_mode)
        else:
            rc = _consumer_lint(Path.cwd(), staged=args.staged, fix_mode=args.fix_mode)
    except (OSError, RuntimeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        rc = 2
    _finish(rc)


def _run_public_leaf(name: str, *, fixes: bool, allow_unsafe: bool, staged: bool) -> None:
    _require_development(name)
    args = _parse_options(name, staged=staged, fixes=fixes, allow_unsafe=allow_unsafe)
    rc = _run_named(name, staged=getattr(args, "staged", False), fix_mode=args.fix_mode)
    _finish(rc)


def lint_cockpit() -> None:
    """Run the Cockpit frontend lint suite."""
    _run_public_leaf("lint-cockpit", fixes=True, allow_unsafe=True, staged=True)


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
    """Run Actionlint on GitHub workflows."""
    _run_public_leaf("lint-actions", fixes=False, allow_unsafe=False, staged=True)


def lint_editorconfig() -> None:
    """Check repository files against EditorConfig policy."""
    _run_public_leaf("lint-editorconfig", fixes=False, allow_unsafe=False, staged=True)


def lint_cockpit_code() -> None:
    """Run Cockpit ESLint checks."""
    _run_public_leaf("lint-cockpit-code", fixes=True, allow_unsafe=False, staged=True)


def lint_cockpit_style() -> None:
    """Run Cockpit Stylelint checks."""
    _run_public_leaf("lint-cockpit-style", fixes=True, allow_unsafe=True, staged=True)


def lint_cockpit_html() -> None:
    """Run Cockpit HTMLHint checks."""
    _run_public_leaf("lint-cockpit-html", fixes=False, allow_unsafe=False, staged=True)


def megalint() -> None:
    """Run MegaLinter across the workspace."""
    _require_development("megalint")
    args = _parse_options("megalint", staged=False, fixes=True, allow_unsafe=True)
    _finish(_run_megalint(args.fix_mode))


def lint_full() -> None:
    """Run every configured lint engine, including MegaLinter."""
    _require_development("lint-full")
    args = _parse_options("lint-full", staged=False, fixes=True, allow_unsafe=True)
    _finish(_run_named("lint-full", staged=False, fix_mode=args.fix_mode))


def format_python() -> None:
    """Format Python with Ruff."""
    _run_public_leaf("format-python", fixes=True, allow_unsafe=False, staged=True)


def format_whitespace() -> None:
    """Remove trailing whitespace."""
    _run_public_leaf("format-whitespace", fixes=True, allow_unsafe=False, staged=True)


def format_eof() -> None:
    """Normalize final newlines."""
    _run_public_leaf("format-eof", fixes=True, allow_unsafe=False, staged=True)


def format_full() -> None:
    """Run all dedicated formatters and text normalizers."""
    _require_development("format-full")
    args = _parse_options("format-full", staged=True, fixes=True, allow_unsafe=False)
    _finish(_run_named("format-full", staged=args.staged, fix_mode=args.fix_mode))


def typecheck_cockpit() -> None:
    """Type-check the Cockpit frontend."""
    _require_development("typecheck-cockpit")
    parser = argparse.ArgumentParser(prog="typecheck-cockpit")
    parser.parse_args()
    _finish(_run_typecheck_cockpit())


def quality_full() -> None:
    """Run format, lint, typecheck, and advisory checks."""
    _require_development("quality-full")
    args = _parse_options("quality-full", staged=False, fixes=True, allow_unsafe=True)
    _finish(_run_named("quality-full", staged=False, fix_mode=args.fix_mode))


def _run_todo() -> int:
    hits: list[str] = []
    _walk_todo(".", hits)
    if hits:
        print(f"\033[1;33m\u26a0 {len(hits)} TODO marker(s):\033[0m")  # noqa: T201
        for hit in hits:
            print(f"  {hit}")  # noqa: T201
    else:
        print("\033[32m\u2713 No TODO markers found\033[0m")  # noqa: T201
    return 0


def todo_check() -> None:
    """Scan for TODO markers as an advisory check."""
    parser = argparse.ArgumentParser(prog="todo")
    parser.parse_args()
    rc = _run_todo()
    if not os.environ.get("PRE_COMMIT"):
        sys.stderr.write(command_footer() + "\n")
    raise SystemExit(rc)


def _walk_todo(root: str, hits: list[str]) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [directory for directory in dirnames if directory not in _SKIP_DIRS]
        for filename in filenames:
            _scan_todo(str(Path(dirpath) / filename), hits)


def _scan_todo(path: str, hits: list[str]) -> None:
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, 1):
                if _TODO_RE.search(line):
                    hits.append(f"{path}:{line_number}: {line.rstrip()}")
    except OSError:
        pass
