"""Compose one task's affected checks and explicitly required test targets."""

from __future__ import annotations

from pathlib import Path

from owlbear_tools import task_scope
from owlbear_tools.testing import (
    _CONFIG_TESTS,
    _INVARIANT_TESTS,
    _PAGES,
    _REPOSITORY_ROOT,
    _git_paths,
    _neighbour_tests,
    _package_for_path,
    _package_tests,
    _Packages,
    _page_scope,
    _python_scope,
    _relative_paths,
    _root_tests,
    _unseen_by_testmon,
    _workspace_packages,
    _WorkspacePackage,
)


def _targets(
    paths: list[str], workspace: _Packages, explicit: set[str] | None = None
) -> tuple[set[str], list[str], list[_WorkspacePackage], set[str], list[str]]:
    forced: set[str] = set()
    required = set(_INVARIANT_TESTS)
    python: list[str] = []
    packages: dict[str, _WorkspacePackage] = {}
    resources: list[str] = []
    for path in paths:
        package = _package_for_path(path, workspace)
        named = explicit is not None and path in explicit
        if path in _CONFIG_TESTS:
            required.update(_CONFIG_TESTS[path])
        elif package and path.startswith(_PAGES):
            forced.update(_page_scope(package, workspace))
        elif path.endswith(".py") and (package or path.startswith("tests/") or named):
            current_test = "/tests/" in path or path.startswith("tests/") or named
            if current_test and Path(path).name.startswith("test_") and (_REPOSITORY_ROOT / path).is_file():
                required.add(path)
            python.append(path)
            if package:
                packages[package.namespace] = package
        elif "/tests/" in path or path.startswith("tests/"):
            forced.update(_relative_paths(_package_tests(package) if package else _root_tests()))
        elif (
            path.endswith((".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs"))
            or (scope := _python_scope(path, workspace)) is None
        ):
            msg = f"Task test scope unsupported for {path}; use repair to establish its consumers, not the full suite"
            raise task_scope.ScopeError(msg)
        elif package and "/src/" in path:
            forced.update(scope)
            resources.append(path)
        else:
            required.update(scope)
    return forced | required, python, list(packages.values()), required, resources


def commands_for_task(
    paths: list[str], context: task_scope.Context, targets: list[str], *, coverage: bool
) -> list[tuple[list[str], Path]]:
    """Union affected consumers and required targets, never bootstrap the full suite."""
    workspace = _workspace_packages()
    recorded = (
        _git_paths(["ls-tree", "-r", "--name-only", "-z", f"{context.base}^{{commit}}"])
        if targets and context.measurement
        else set()
    )
    explicit = task_scope.explicit_targets(_REPOSITORY_ROOT, targets, sorted(recorded))
    forced, python, packages, required, resources = _targets(paths, workspace, explicit)
    required.update(test for test in explicit if (_REPOSITORY_ROOT / test.split("::", 1)[0]).is_file())
    for package in packages:
        forced.update(_relative_paths(_neighbour_tests(package, workspace)))
        forced.update(
            _relative_paths(path for path in _package_tests(package) if _unseen_by_testmon(path, package.namespace))
        )
    selected = sorted(forced | required) if paths or targets else []
    if python or resources or any(path.startswith((_PAGES, "tests/")) or "/tests/" in path for path in paths):
        from owlbear_tools import test_impact  # noqa: PLC0415 - task evidence only, never ordinary test startup.

        consumer_paths = [
            path
            for path in paths
            if path in python or path.startswith("tests/") or "/tests/" in path or _python_scope(path, workspace) != []
        ]
        selected = test_impact.select(
            _REPOSITORY_ROOT,
            python,
            context,
            selected,
            test_impact.RequiredScope(consumer_paths, sorted(required), resources, sorted(explicit)),
        )
    print(f"Task paths: {', '.join(paths) or 'none'}")  # noqa: T201
    if not selected:
        return []
    command = ["uv", "run", "--locked", "pytest", *selected]
    if coverage:
        command.append("--cov")
    return [(command, _REPOSITORY_ROOT)]
