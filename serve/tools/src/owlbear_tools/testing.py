"""Maintained test commands for the OwlBear development checkout."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_COCKPIT_WEB = _REPOSITORY_ROOT / "serve/cockpit/web"
_DOCS_ONLY_PREFIXES = ("share/", ".owlbear/", "setup/")
_PYTHON_ROUTES = (
    ("serve/cockpit/", ("serve/cockpit/tests",), ("test_cockpit_*.py",)),
    ("serve/delivery-github/", ("serve/delivery-github/tests",), ()),
    ("serve/delivery-mcp/", ("serve/delivery-mcp/tests",), ()),
    ("serve/delivery/", ("serve/delivery/tests",), ("test_delivery_*.py", "test_engine_*.py")),
    ("serve/knowledge-mcp/", (), ("test_mcp_knowledge_*.py", "test_enrichment_tools_registry.py")),
    ("serve/knowledge/", ("serve/knowledge/tests",), ("test_knowledge_*.py", "test_enrichment_*.py")),
    (
        "serve/memory-mcp/",
        ("serve/memory-mcp/tests",),
        ("test_memory_*.py", "test_recall_memory.py", "test_assess_memories.py"),
    ),
    ("serve/memory/", (), ("test_memory_*.py", "test_recall_memory.py", "test_assess_memories.py")),
    ("serve/browser-mcp/", ("serve/browser-mcp/tests",), ()),
    ("serve/browser/", ("serve/browser/tests",), ()),
    ("serve/web-content/", ("serve/web-content/tests",), ()),
    ("serve/tools/", ("serve/tools/tests",), ()),
)


def _require_development_checkout() -> None:
    if Path.cwd().resolve() != _REPOSITORY_ROOT or not (_REPOSITORY_ROOT / ".pre-commit-config.yaml").is_file():
        msg = "test commands are available only from the OwlBear development checkout root"
        raise RuntimeError(msg)


def _existing_paths(paths: Iterable[Path]) -> list[str]:
    return [str(path.relative_to(_REPOSITORY_ROOT)) for path in paths if path.exists()]


def _matching_root_tests(*patterns: str) -> list[str]:
    tests_root = _REPOSITORY_ROOT / "tests"
    matches = {path for pattern in patterns for path in tests_root.glob(pattern)}
    return _existing_paths(sorted(matches))


def _python_scope(path: str) -> list[str] | None:
    normalized = path.removeprefix("./")
    route_path = normalized if normalized.endswith("/") else f"{normalized}/"
    if route_path.startswith("serve/cockpit/web/"):
        return []
    for prefix, directories, patterns in _PYTHON_ROUTES:
        if route_path.startswith(prefix):
            roots = [_REPOSITORY_ROOT / directory for directory in directories]
            return [*_existing_paths(roots), *_matching_root_tests(*patterns)]
    if normalized.startswith(_DOCS_ONLY_PREFIXES) or Path(normalized).suffix.lower() == ".md":
        return []
    if normalized.endswith(".py") and Path(normalized).name.startswith("test_"):
        return [normalized]
    return None


def _is_web_path(path: str) -> bool:
    return path.removeprefix("./").startswith("serve/cockpit/web/")


def _commands_for_paths(
    paths: list[str], *, all_tests: bool, python_only: bool, web_only: bool, coverage: bool
) -> list[tuple[list[str], Path]]:
    commands: list[tuple[list[str], Path]] = []
    if all_tests:
        python_targets = ["tests", "serve"]
        run_python = not web_only
        run_web = not python_only
    else:
        scopes: set[str] = set()
        fallback = False
        for path in paths:
            scope = _python_scope(path)
            if scope is None:
                fallback = True
            else:
                scopes.update(scope)
        python_targets = ["tests", "serve"] if fallback else sorted(scopes)
        run_python = bool(python_targets) and not web_only
        run_web = any(_is_web_path(path) for path in paths) and not python_only

    if run_python:
        command = ["uv", "run", "--locked", "pytest", *python_targets]
        if coverage:
            command.append("--cov")
        commands.append((command, _REPOSITORY_ROOT))
    if run_web:
        command = ["npm", "test"]
        if coverage:
            command.extend(("--", "--coverage"))
        commands.append((command, _COCKPIT_WEB))
    return commands


def _run_commands(commands: list[tuple[list[str], Path]]) -> int:
    failures = 0
    for command, cwd in commands:
        relative_cwd = cwd.relative_to(_REPOSITORY_ROOT)
        location = "." if relative_cwd == Path() else str(relative_cwd)
        print(f"[{location}] {' '.join(command)}")  # noqa: T201
        failures += int(bool(subprocess.call(command, cwd=cwd)))  # noqa: S603
    return int(bool(failures))


def test_main() -> None:
    """Run all maintained tests or suites selected by explicit paths."""
    _require_development_checkout()
    parser = argparse.ArgumentParser(prog="test")
    parser.add_argument("-a", "--all", action="store_true", dest="all_tests")
    toolchain = parser.add_mutually_exclusive_group()
    toolchain.add_argument("--py", action="store_true", dest="python_only")
    toolchain.add_argument("--web", action="store_true", dest="web_only")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if args.all_tests and args.paths:
        parser.error("--all cannot be combined with paths")

    all_tests = args.all_tests or not args.paths
    commands = _commands_for_paths(
        args.paths,
        all_tests=all_tests,
        python_only=args.python_only,
        web_only=args.web_only,
        coverage=args.coverage,
    )
    if not commands:
        print("No test scope matched the selected paths.")  # noqa: T201
        raise SystemExit(0)
    raise SystemExit(_run_commands(commands))


def test_e2e_main() -> None:
    """Run the maintained Cockpit Playwright gate."""
    _require_development_checkout()
    parser = argparse.ArgumentParser(prog="test-e2e")
    parser.add_argument("-a", "--all", action="store_true", dest="all_tests")
    parser.add_argument("specs", nargs="*")
    args = parser.parse_args()
    script = "test:e2e:all" if args.all_tests else "test:e2e"
    command = ["npm", "run", script]
    if args.specs:
        command.extend(("--", *args.specs))
    raise SystemExit(_run_commands([(command, _REPOSITORY_ROOT)]))
