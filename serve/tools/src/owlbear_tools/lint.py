"""Lint and static-analysis shortcuts.

Commands
--------
uv run lint [--no-fix | --unsafe-fixes] [FILE ...]
                   OwlBear hooks in the dev checkout; otherwise discover
                   consumer-owned Ruff config and package lint scripts.
uv run lint --all [--no-fix | --unsafe-fixes]
                   All files, default hooks.
uv run megalint [--no-fix | --unsafe-fixes]
                   MegaLinter only.
uv run typecheck   TypeScript check only.
uv run lint-full [--no-fix | --unsafe-fixes]
                   All local and full-project lint checks.
uv run eslint-fix [--no-fix]
                   ESLint on Cockpit frontend (fixes by default).
uv run todo        Scan for ``> **TODO:**`` markers (warning only).

Default hooks (lint)
~~~~~~~~~~~~~~~~~~~~
Hook                       Auto-fix  Tool
─────────────────────────  ────────  ────
trailing-whitespace        yes       pre-commit-hooks
end-of-file-fixer          yes       pre-commit-hooks
check-yaml                 no        pre-commit-hooks
check-merge-conflict       no        pre-commit-hooks
check-added-large-files    no        pre-commit-hooks
ruff (lint)                yes       ruff
ruff-format                yes       ruff
yamllint                   no        yamllint
shellcheck                 no        shellcheck
actionlint                 no        actionlint
markdownlint-cli2          yes       markdownlint-cli2 --fix
editorconfig-checker       no        editorconfig-checker
eslint (Cockpit frontend)  yes       eslint --fix
validate-skills            no        custom (.owlbear/scripts)
validate-agents            no        custom (.owlbear/scripts)

Manual-stage hooks (megalint)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Hook                       Auto-fix  Tool
─────────────────────────  ────────  ────
megalinter                 yes       Selected safe fix-capable linters
typecheck-frontend         no        TypeScript check (tsc --noEmit, whole-project)
"""

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

from owlbear_tools.commands import command_footer
from owlbear_tools.megalinter import load_megalinter_image

COCKPIT_WEB = "serve/cockpit/web"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_NO_FIX_ENV = "OWLBEAR_LINT_NO_FIX"
_UNSAFE_FIX_ENV = "OWLBEAR_LINT_UNSAFE_FIXES"
_FIX_HOOK_ALIASES = (
    "trailing-whitespace-fix",
    "end-of-file-fix",
    "ruff-fix",
    "ruff-format-fix",
    "markdownlint-fix",
    "eslint-frontend-fix",
    "stylelint-frontend-fix",
)
_CHECK_HOOKS = (
    "text-hygiene-check",
    "ruff-check",
    "ruff-format-check",
    "markdownlint-check",
    "eslint-frontend-check",
    "stylelint-frontend-check",
)
_UNSAFE_REPLACED_HOOKS = ("ruff-fix", "stylelint-frontend-fix")
_UNSAFE_HOOKS = ("ruff-unsafe-fix", "stylelint-frontend-lax")
_PYTHON_SUFFIXES = frozenset({".py", ".pyi"})


class FixMode(StrEnum):
    """Supported lint mutation policies."""

    SAFE = "safe"
    NONE = "none"
    UNSAFE = "unsafe"


def _call(command: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> int:
    if env is None:
        return subprocess.call(command, cwd=cwd) if cwd is not None else subprocess.call(command)  # noqa: S603
    if cwd is None:
        return subprocess.call(command, env=env)  # noqa: S603
    return subprocess.call(command, env=env, cwd=cwd)  # noqa: S603


def _run(args: list[str], *, hint: str = "", env: dict[str, str] | None = None) -> None:
    rc = _call(["pre-commit", *args], env=env)
    if hint:
        sys.stderr.write(hint + "\n")
    raise SystemExit(rc)


def _skip_hooks_environment(hooks: tuple[str, ...]) -> dict[str, str]:
    env = os.environ.copy()
    configured = [item for item in env.get("SKIP", "").split(",") if item]
    env["SKIP"] = ",".join(dict.fromkeys([*configured, *hooks]))
    return env


def _call_named_hooks(hooks: tuple[str, ...], selection: list[str]) -> int:
    failures = 0
    for hook in hooks:
        command = ["pre-commit", "run", hook, "--hook-stage", "manual", *selection]
        failures += int(bool(_call(command)))
    return int(bool(failures))


def _call_lint_hooks(args: list[str], *, fix_mode: FixMode) -> int:
    if fix_mode is FixMode.SAFE:
        return _call(["pre-commit", *args])
    selection = args[1:]
    if fix_mode is FixMode.NONE:
        env = _skip_hooks_environment(_FIX_HOOK_ALIASES)
        failures = int(bool(_call(["pre-commit", *args], env=env)))
        return int(bool(failures + _call_named_hooks(_CHECK_HOOKS, selection)))
    env = _skip_hooks_environment(_UNSAFE_REPLACED_HOOKS)
    failures = int(bool(_call(["pre-commit", *args], env=env)))
    return int(bool(failures + _call_named_hooks(_UNSAFE_HOOKS, selection)))


def _add_fix_mode(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--no-fix", action="store_const", const=FixMode.NONE, dest="fix_mode")
    group.add_argument("--unsafe-fixes", action="store_const", const=FixMode.UNSAFE, dest="fix_mode")
    parser.set_defaults(fix_mode=FixMode.SAFE)


def _parse_fix_mode(prog: str) -> FixMode:
    parser = argparse.ArgumentParser(prog=prog)
    _add_fix_mode(parser)
    return parser.parse_args().fix_mode


def _mode_environment(fix_mode: FixMode) -> dict[str, str] | None:
    if fix_mode is FixMode.NONE:
        return {**os.environ, _NO_FIX_ENV: "1"}
    if fix_mode is FixMode.UNSAFE:
        return {**os.environ, _UNSAFE_FIX_ENV: "1"}
    return None


def _is_owlbear_dev_checkout(root: Path) -> bool:
    return root.resolve() == _REPOSITORY_ROOT and (root / ".pre-commit-config.yaml").is_file()


def _consumer_paths(files: list[str], *, all_files: bool) -> list[str]:
    if all_files:
        return ["."]
    if files:
        return files
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],  # noqa: S607
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        msg = "lint needs explicit files or --all outside a Git working tree"
        raise RuntimeError(msg) from exc
    return [value.decode("utf-8") for value in output.split(b"\0") if value]


def _has_ruff_config(root: Path) -> bool:
    if any((root / name).is_file() for name in ("ruff.toml", ".ruff.toml")):
        return True
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    tool = config.get("tool")
    return isinstance(tool, dict) and isinstance(tool.get("ruff"), dict)


def _ruff_commands(targets: list[str], fix_mode: FixMode) -> tuple[list[str], list[str]]:
    if fix_mode is FixMode.NONE:
        return ["ruff", "check", *targets], ["ruff", "format", "--check", *targets]
    check = ["ruff", "check", "--fix"]
    if fix_mode is FixMode.UNSAFE:
        check.append("--unsafe-fixes")
    return [*check, *targets], ["ruff", "format", *targets]


def _package_lint_command(root: Path, fix_mode: FixMode) -> list[str] | None:
    manifest = root / "package.json"
    if not manifest.is_file():
        return None
    package = json.loads(manifest.read_text(encoding="utf-8"))
    scripts = package.get("scripts")
    if not isinstance(scripts, dict) or not isinstance(scripts.get("lint"), str):
        return None
    script = "lint:fix" if fix_mode is not FixMode.NONE and isinstance(scripts.get("lint:fix"), str) else "lint"
    package_manager = package.get("packageManager", "")
    if not isinstance(package_manager, str):
        package_manager = ""
    runner = next(
        (
            name
            for name, marker in (
                ("pnpm", "pnpm-lock.yaml"),
                ("yarn", "yarn.lock"),
                ("bun", "bun.lock"),
            )
            if package_manager.startswith(f"{name}@") or (root / marker).is_file()
        ),
        "npm",
    )
    return [runner, "run", script]


def _consumer_lint(root: Path, files: list[str], *, all_files: bool, fix_mode: FixMode) -> int:
    paths = _consumer_paths(files, all_files=all_files)
    has_ruff = _has_ruff_config(root)
    package_command = _package_lint_command(root, fix_mode)
    commands: list[list[str]] = []
    if has_ruff:
        ruff_targets = [path for path in paths if Path(path).is_dir() or Path(path).suffix in _PYTHON_SUFFIXES]
        if ruff_targets:
            commands.extend(_ruff_commands(ruff_targets, fix_mode))
    if package_command is not None and paths:
        commands.append(package_command)
    if not has_ruff and package_command is None:
        sys.stderr.write(
            "No consumer lint configuration found. Add [tool.ruff], ruff.toml, .ruff.toml, "
            "or a package.json lint script.\n"
        )
        return 2
    failures = sum(bool(_call(command, cwd=root)) for command in commands)
    return int(bool(failures))


def lint() -> None:
    """Run OwlBear hooks or discover consumer-owned lint tools."""
    parser = argparse.ArgumentParser(prog="lint")
    parser.add_argument("-a", "--all", action="store_true", dest="all_files")
    _add_fix_mode(parser)
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()
    if args.all_files and args.files:
        parser.error("--all cannot be combined with file names")
    root = Path.cwd()
    if not _is_owlbear_dev_checkout(root):
        try:
            rc = _consumer_lint(root, args.files, all_files=args.all_files, fix_mode=args.fix_mode)
        except (json.JSONDecodeError, RuntimeError, tomllib.TOMLDecodeError) as exc:
            sys.stderr.write(f"Error: {exc}\n")
            rc = 2
        sys.stderr.write(command_footer() + "\n")
        raise SystemExit(rc)
    pre_commit_args = ["run", "--all-files"] if args.all_files else ["run", "--files", *args.files]
    if not args.all_files and not args.files:
        pre_commit_args = ["run"]
    rc = _call_lint_hooks(pre_commit_args, fix_mode=args.fix_mode)
    sys.stderr.write(command_footer() + "\n")
    raise SystemExit(rc)


def megalint() -> None:
    """Run MegaLinter without the other manual-stage hooks."""
    fix_mode = _parse_fix_mode("megalint")
    _run(
        ["run", "megalinter", "--all-files", "--hook-stage", "manual"],
        hint=command_footer(),
        env=_mode_environment(fix_mode),
    )


def typecheck() -> None:
    """Run the Cockpit TypeScript project check."""
    _run(["run", "typecheck-frontend", "--all-files", "--hook-stage", "manual"], hint=command_footer())


def lint_full() -> None:
    """Run all local and full-project lint checks."""
    fix_mode = _parse_fix_mode("lint-full")
    failures = _call_lint_hooks(["run", "--all-files"], fix_mode=fix_mode)
    commands: tuple[tuple[list[str], dict[str, str] | None], ...] = (
        (["npm", "run", "lint:html"], None),
        (["pre-commit", "run", "typecheck-frontend", "--all-files", "--hook-stage", "manual"], None),
        (
            ["pre-commit", "run", "megalinter", "--all-files", "--hook-stage", "manual"],
            _mode_environment(fix_mode),
        ),
    )
    failures += sum(bool(_call(command, env=env)) for command, env in commands)
    sys.stderr.write(command_footer() + "\n")
    raise SystemExit(1 if failures else 0)


def eslint_fix() -> None:
    """Run ESLint on Cockpit frontend sources, fixing by default."""
    fix_mode = _parse_fix_mode("eslint-fix")
    web_dir = Path(COCKPIT_WEB)
    if not web_dir.is_dir():
        sys.stderr.write(f"Error: {COCKPIT_WEB} not found\n")
        raise SystemExit(1)
    command = ["npx", "eslint", "src/"]
    if fix_mode is not FixMode.NONE:
        command.append("--fix")
    rc = _call(command, cwd=web_dir)
    sys.stderr.write(command_footer() + "\n")
    raise SystemExit(rc)


def megalint_hook() -> None:
    """Run the pinned MegaLinter container for the manual pre-commit hook."""
    image = load_megalinter_image()
    unsafe_fixes = bool(os.environ.get(_UNSAFE_FIX_ENV))
    command = _docker_command()
    if os.environ.get(_NO_FIX_ENV):
        command.extend(["-e", "APPLY_FIXES=none"])
    if unsafe_fixes:
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
    raise SystemExit(_call(command))


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


def text_hygiene_check() -> None:
    """Check trailing whitespace and final newlines without modifying files."""
    failures = 0
    for raw_path in sys.argv[1:]:
        path = Path(raw_path)
        try:
            data = path.read_bytes()
        except OSError as exc:
            print(f"{path}: unable to read: {exc}")  # noqa: T201
            failures += 1
            continue
        if not data or b"\0" in data:
            continue
        trailing = any(line.rstrip(b"\r\n").endswith((b" ", b"\t")) for line in data.splitlines(keepends=True))
        line_ending = data[len(data.rstrip(b"\r\n")) :]
        if trailing:
            print(f"{path}: trailing whitespace")  # noqa: T201
            failures += 1
        if line_ending not in (b"\n", b"\r\n"):
            print(f"{path}: expected exactly one final newline")  # noqa: T201
            failures += 1
    raise SystemExit(1 if failures else 0)


# ── TODO marker scan ──────────────────────────────────────────

_TODO_RE = re.compile(r"^> \*\*TODO:\*\*", re.MULTILINE)
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


def todo_check() -> None:
    """Scan for ``> **TODO:**`` markers (warning only, exit 0)."""
    hits: list[str] = []
    _walk_todo(".", hits)
    if hits:
        print(  # noqa: T201
            f"\033[1;33m\u26a0 {len(hits)} TODO marker(s):\033[0m"
        )
        for h in hits:
            print(f"  {h}")  # noqa: T201
    else:
        print("\033[32m\u2713 No TODO markers found\033[0m")  # noqa: T201
    if not os.environ.get("PRE_COMMIT"):
        sys.stderr.write(command_footer() + "\n")


def _walk_todo(root: str, hits: list[str]) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for f in filenames:
            _scan_todo(str(Path(dirpath) / f), hits)


def _scan_todo(path: str, hits: list[str]) -> None:
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if _TODO_RE.search(line):
                    hits.append(f"{path}:{i}: {line.rstrip()}")
    except OSError:
        pass
