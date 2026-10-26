"""Maintained test commands for the OwlBear development checkout."""

from __future__ import annotations

import argparse
import ast
import contextlib
import fcntl
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_DOCS_ONLY_PREFIXES = ("share/", ".owlbear/")
_INVARIANT_TESTS = ("tests/test_package_boundary.py",)
# Packages whose own tests testmon selects for a Python source change; it needs the classic tracer on 3.14 and
# --testmon-forceselect, because the configured -m otherwise turns its selection off.
_TESTMON_NAMESPACES = frozenset({"owlbear_delivery_next"})
_TESTMON_DATA = ".owlbear/scratch"


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
    except OSError, SyntaxError:
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
    return _relative_paths([*_package_tests(package), *_neighbour_tests(package)])


def _neighbour_tests(package: _WorkspacePackage) -> list[Path]:
    """Root and consumer tests that import the package, and the invariant tests."""
    packages = _workspace_packages()
    targets = _tests_importing(package.namespace, _root_tests())
    for consumer in _direct_consumers(package, packages):
        targets.extend(_tests_importing(package.namespace, _package_tests(consumer)))
    targets.extend(_REPOSITORY_ROOT / path for path in _INVARIANT_TESTS)
    return targets


def _unseen_by_testmon(path: Path, namespace: str) -> bool:
    """Whether a test module depends on code testmon cannot trace: the package in a child process, or read as data."""
    try:
        nodes = list(ast.walk(ast.parse(path.read_text(encoding="utf-8"))))
    except OSError, SyntaxError:
        return True

    def attribute(owner: str, name: str) -> bool:
        return any(
            isinstance(node, ast.Attribute)
            and node.attr == name
            and isinstance(node.value, ast.Name)
            and node.value.id == owner
            for node in nodes
        )

    texts = [node.value for node in nodes if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    child = attribute("sys", "executable") and any(namespace in text for text in texts)
    return child or attribute("ast", "parse") or any(text.endswith("*.py") for text in texts)


def _monitored_package(path: str) -> _WorkspacePackage | None:
    """The testmon package of an existing Python source file; None for anything else."""
    normalized = path.removeprefix("./")
    package = _package_for_path(normalized)
    if package is None or package.namespace not in _TESTMON_NAMESPACES:
        return None
    source = normalized.startswith(f"serve/{package.directory.name}/src/") and normalized.endswith(".py")
    return package if source and (_REPOSITORY_ROOT / normalized).is_file() else None


def _testmon_commands(packages: Iterable[_WorkspacePackage], forced: set[str]) -> list[tuple[list[str], Path]]:
    """One testmon run per package over its tests, after adding to *forced* what must run regardless."""
    commands: list[tuple[list[str], Path]] = []
    for package in packages:
        tests = _package_tests(package)
        forced.update(_relative_paths(path for path in tests if _unseen_by_testmon(path, package.namespace)))
        forced.update(_relative_paths(_neighbour_tests(package)))
        selected = [path for path in _relative_paths(tests) if path not in forced]
        if selected:
            data = f"TESTMON_DATAFILE={_TESTMON_DATA}/testmon-{package.directory.name}.db"
            pytest = ["uv", "run", "--locked", "pytest", *selected, "--testmon", "--testmon-forceselect"]
            commands.append((["env", "COVERAGE_CORE=ctrace", data, *pytest], _REPOSITORY_ROOT))
    return commands


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
    package = _package_for_path(normalized)
    if package is not None:
        package_prefix = f"serve/{package.directory.name}/"
        if normalized.startswith(f"{package_prefix}src/") or normalized == f"{package_prefix}pyproject.toml":
            scope = _package_scope(package)
        elif normalized.startswith(f"{package_prefix}tests/"):
            candidate = _REPOSITORY_ROOT / normalized
            if candidate.exists():
                is_test_module = (
                    candidate.is_file() and candidate.name.startswith("test_") and candidate.suffix == ".py"
                )
                scope = [normalized] if is_test_module else _relative_paths(_package_tests(package))
    elif normalized.startswith(_DOCS_ONLY_PREFIXES) or Path(normalized).suffix.lower() == ".md":
        scope = []
    else:
        candidate = _REPOSITORY_ROOT / normalized
        if normalized.startswith("tests/") and candidate.is_file() and candidate.name.startswith("test_"):
            scope = [normalized]
    return scope


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


def _split_paths(paths: list[str], *, coverage: bool) -> tuple[set[str] | None, list[_WorkspacePackage]]:
    """The plain pytest scope (None: the full suite) and the packages whose changed sources testmon selects for."""
    scopes: set[str] = set()
    monitored: dict[str, _WorkspacePackage] = {}
    for path in paths:
        if not coverage and (package := _monitored_package(path)) is not None:
            monitored[package.namespace] = package
        elif (scope := _python_scope(path)) is None:
            return None, []
        else:
            scopes.update(scope)
    return scopes, list(monitored.values())


def _commands_for_paths(paths: list[str], *, all_tests: bool, coverage: bool) -> list[tuple[list[str], Path]]:
    commands: list[tuple[list[str], Path]] = []
    selected: list[tuple[list[str], Path]] = []
    if all_tests:
        python_targets = ["tests", "serve"]
    else:
        scopes, monitored = _split_paths(paths, coverage=coverage)
        if scopes is not None:
            selected = _testmon_commands(monitored, scopes)
        python_targets = ["tests", "serve"] if scopes is None else sorted(scopes)

    if python_targets:
        command = ["uv", "run", "--locked", "pytest", *python_targets]
        if coverage:
            command.append("--cov")
        commands.append((command, _REPOSITORY_ROOT))
    commands.extend(selected)
    return commands


@contextlib.contextmanager
def _testmon_lock(command: list[str]) -> Iterator[dict[str, tuple[int, ...]]]:
    """Serialize testmon runs sharing one data file: a first run deletes and recreates the database.

    The command inherits the locked descriptor, so the lock lasts as long as its process tree, Ctrl-C included.
    """
    data = next((arg.split("=", 1)[1] for arg in command if arg.startswith("TESTMON_DATAFILE=")), None)
    if data is None:
        yield {}
        return
    with (_REPOSITORY_ROOT / f"{data}.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Waiting for another testmon run of this checkout to end")  # noqa: T201
            fcntl.flock(handle, fcntl.LOCK_EX)
        yield {"pass_fds": (handle.fileno(),)}


def _run_commands(commands: list[tuple[list[str], Path]]) -> int:
    failures = 0
    for command, cwd in commands:
        relative_cwd = cwd.relative_to(_REPOSITORY_ROOT)
        location = "." if relative_cwd == Path() else str(relative_cwd)
        print(f"[{location}] {' '.join(command)}")  # noqa: T201
        with _testmon_lock(command) as inherited:
            failures += int(bool(subprocess.call(command, cwd=cwd, **inherited)))  # noqa: S603
    return int(bool(failures))


def test_main() -> None:
    """Run all maintained tests or suites selected by explicit paths."""
    _require_development_checkout()
    parser = argparse.ArgumentParser(prog="test")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-a", "--all", action="store_true", dest="all_tests")
    scope.add_argument("--changed", action="store_true")
    parser.add_argument("--base", help="Git ref used as the committed-change baseline for --changed")
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
    commands = _commands_for_paths(paths, all_tests=all_tests, coverage=args.coverage)
    if not commands:
        print("No test scope matched the selected paths.")  # noqa: T201
        raise SystemExit(0)
    raise SystemExit(_run_commands(commands))
