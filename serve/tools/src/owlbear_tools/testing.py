"""Maintained test commands for the OwlBear development checkout."""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_COCKPIT_WEB = _REPOSITORY_ROOT / "serve/cockpit/web"
_DOCS_ONLY_PREFIXES = ("share/", ".owlbear/")
_INVARIANT_TESTS = (
    "tests/test_deny_code_writes.py",
    "tests/test_package_boundary.py",
    "tests/test_sync_manifest.py",
    "tests/test_write_guard_hooks.py",
)


@dataclass(frozen=True, slots=True)
class _WorkspacePackage:
    directory: Path
    namespace: str
    project_name: str
    dependencies: tuple[str, ...]


class _ChangedScopeError(RuntimeError):
    """Raised when a changed-path scope cannot be established safely."""


def _require_development_checkout() -> None:
    if Path.cwd().resolve() != _REPOSITORY_ROOT or not (_REPOSITORY_ROOT / ".pre-commit-config.yaml").is_file():
        msg = "test commands are available only from the OwlBear development checkout root"
        raise RuntimeError(msg)


def _workspace_packages() -> tuple[_WorkspacePackage, ...]:
    packages: list[_WorkspacePackage] = []
    for manifest in sorted((_REPOSITORY_ROOT / "serve").glob("*/pyproject.toml")):
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
        project = document.get("project")
        if not isinstance(project, dict):
            continue
        project_name = project.get("name")
        dependencies = project.get("dependencies", ())
        if not isinstance(project_name, str) or not isinstance(dependencies, list):
            continue
        dependency_values = [dependency for dependency in dependencies if isinstance(dependency, str)]
        namespaces = sorted(path.name for path in (manifest.parent / "src").glob("owlbear_*") if path.is_dir())
        packages.extend(
            _WorkspacePackage(
                directory=manifest.parent,
                namespace=namespace,
                project_name=project_name,
                dependencies=tuple(dependency_values),
            )
            for namespace in namespaces
        )
    return tuple(packages)


def _canonical_project_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _dependency_name(value: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", value)
    return _canonical_project_name(match.group(0)) if match is not None else ""


def _package_tests(package: _WorkspacePackage) -> list[Path]:
    tests_root = package.directory / "tests"
    return sorted(path for path in tests_root.rglob("test_*.py") if path.is_file()) if tests_root.is_dir() else []


def _root_tests() -> list[Path]:
    return sorted(path for path in (_REPOSITORY_ROOT / "tests").rglob("test_*.py") if path.is_file())


def _imported_namespaces(path: Path) -> frozenset[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return frozenset()
    namespaces: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            modules = (node.module,)
        else:
            continue
        namespaces.update(module.split(".", 1)[0] for module in modules if module.startswith("owlbear_"))
    return frozenset(namespaces)


def _tests_importing(namespace: str, paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if namespace in _imported_namespaces(path)]


def _direct_consumers(
    package: _WorkspacePackage,
    packages: tuple[_WorkspacePackage, ...],
) -> tuple[_WorkspacePackage, ...]:
    target = _canonical_project_name(package.project_name)
    return tuple(
        candidate
        for candidate in packages
        if any(_dependency_name(dependency) == target for dependency in candidate.dependencies)
    )


def _relative_paths(paths: Iterable[Path]) -> list[str]:
    return sorted({str(path.relative_to(_REPOSITORY_ROOT)) for path in paths if path.is_file()})


def _package_scope(package: _WorkspacePackage) -> list[str]:
    packages = _workspace_packages()
    targets = _package_tests(package)
    targets.extend(_tests_importing(package.namespace, _root_tests()))
    for consumer in _direct_consumers(package, packages):
        targets.extend(_tests_importing(package.namespace, _package_tests(consumer)))
    targets.extend(_REPOSITORY_ROOT / path for path in _INVARIANT_TESTS)
    return _relative_paths(targets)


def _package_for_path(normalized: str) -> _WorkspacePackage | None:
    for package in _workspace_packages():
        prefix = f"serve/{package.directory.name}/"
        if normalized.startswith((f"{prefix}src/", f"{prefix}tests/")):
            return package
        if normalized == f"{prefix}pyproject.toml":
            return package
    return None


def _python_scope(path: str) -> list[str] | None:
    normalized = path.removeprefix("./")
    scope: list[str] | None = None
    if normalized.startswith("serve/cockpit/web/"):
        scope = []
    elif normalized.startswith(".owlbear/hooks/"):
        scope = ["tests/test_deny_code_writes.py", "tests/test_write_guard_hooks.py"]
    elif normalized.startswith(".owlbear/scripts/diagrams/"):
        scope = ["tests/test_archify_diagrams.py", *_INVARIANT_TESTS]
    else:
        package = _package_for_path(normalized)
        if package is not None:
            package_prefix = f"serve/{package.directory.name}/"
            if normalized.startswith(f"{package_prefix}src/") or normalized == f"{package_prefix}pyproject.toml":
                scope = _package_scope(package)
            elif normalized.startswith(f"{package_prefix}tests/"):
                candidate = _REPOSITORY_ROOT / normalized
                if candidate.exists():
                    scope = [normalized] if candidate.is_file() else _relative_paths(_package_tests(package))
        elif normalized.startswith(_DOCS_ONLY_PREFIXES) or Path(normalized).suffix.lower() == ".md":
            scope = []
        else:
            candidate = _REPOSITORY_ROOT / normalized
            if normalized.startswith("tests/") and candidate.is_file() and candidate.name.startswith("test_"):
                scope = [normalized]
    return scope


def _is_web_path(path: str) -> bool:
    return path.removeprefix("./").startswith("serve/cockpit/web/")


def _git_executable() -> str:
    executable = shutil.which("git")
    if executable is None:
        message = "Git is unavailable"
        raise _ChangedScopeError(message)
    return executable


def _run_git(arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603
        [_git_executable(), *arguments],
        cwd=_REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )


def _git_paths(arguments: list[str]) -> set[str]:
    completed = _run_git(arguments)
    if completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip() or "unknown Git error"
        raise _ChangedScopeError(detail)
    return {path for path in completed.stdout.decode(errors="surrogateescape").split("\0") if path}


def _default_changed_base() -> str:
    completed = _run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    if completed.returncode:
        message = "no upstream branch is configured; pass --base explicitly"
        raise _ChangedScopeError(message)
    return completed.stdout.decode().strip()


def _changed_paths(base: str | None) -> list[str]:
    selected_base = base or _default_changed_base()
    merge_base = _run_git(["merge-base", selected_base, "HEAD"])
    if merge_base.returncode:
        detail = merge_base.stderr.decode(errors="replace").strip() or "unable to compute merge base"
        raise _ChangedScopeError(detail)
    common_ancestor = merge_base.stdout.decode().strip()
    paths = _git_paths(["diff", "--name-only", "-z", "--no-renames", f"{common_ancestor}...HEAD"])
    paths.update(_git_paths(["diff", "--name-only", "-z", "--no-renames", "HEAD"]))
    paths.update(_git_paths(["ls-files", "--others", "--exclude-standard", "-z"]))
    return sorted(paths)


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
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-a", "--all", action="store_true", dest="all_tests")
    scope.add_argument("--changed", action="store_true")
    parser.add_argument("--base", help="Git ref used as the committed-change baseline for --changed")
    toolchain = parser.add_mutually_exclusive_group()
    toolchain.add_argument("--py", action="store_true", dest="python_only")
    toolchain.add_argument("--web", action="store_true", dest="web_only")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if args.all_tests and args.paths:
        parser.error("--all cannot be combined with paths")
    if args.base and not args.changed:
        parser.error("--base requires --changed")
    if args.changed and args.paths:
        parser.error("--changed cannot be combined with paths")

    paths = args.paths
    all_tests = args.all_tests or not args.paths
    if args.changed:
        try:
            paths = _changed_paths(args.base)
            all_tests = False
        except _ChangedScopeError as error:
            print(f"Changed test scope unavailable; running the full suite: {error}")  # noqa: T201
            paths = []
            all_tests = True
    commands = _commands_for_paths(
        paths,
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
