"""Validate the checked-in Python runtime against the workspace lower bound.

Mirrors ``check_node_runtime.py`` for the Python side of the workspace. The
``>=3.14.6`` floor is declared independently by every ``serve/*`` package, by
``.python-version``, and by the bootstrap guard in ``setup/init.py``; this
check keeps those declarations from drifting apart.
"""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path
from typing import NoReturn

_VERSION_PATTERN = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
_LOWER_BOUND_PATTERN = re.compile(r"^>=\s*(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
_GUARD_PATTERN = re.compile(
    r"^_MINIMUM_PYTHON\s*=\s*\((?P<major>\d+),\s*(?P<minor>\d+),\s*(?P<patch>\d+)\)", re.MULTILINE
)


def _raise_value_error(message: str) -> NoReturn:
    """Raise one named runtime-contract failure."""
    raise ValueError(message)


def _raise_type_error(message: str) -> NoReturn:
    """Raise one named runtime-input type failure."""
    raise TypeError(message)


def _format(version: tuple[int, int, int]) -> str:
    """Render one version tuple as a dotted string."""
    return ".".join(str(part) for part in version)


def _parse_version(value: str, source: str) -> tuple[int, int, int]:
    """Parse one complete CPython version."""
    match = _VERSION_PATTERN.fullmatch(value.strip())
    if match is None:
        _raise_value_error(f"{source} must contain a complete Python version")
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def _parse_lower_bound(value: str, source: str) -> tuple[int, int, int]:
    """Parse one ``>=major.minor.patch`` requires-python declaration."""
    match = _LOWER_BOUND_PATTERN.fullmatch(value.strip())
    if match is None:
        _raise_value_error(f"{source} requires-python must use >=major.minor.patch")
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def _read_member_lower_bounds(members_root: Path) -> dict[Path, tuple[int, int, int]]:
    """Read the requires-python lower bound declared by every workspace member."""
    manifests = sorted(members_root.glob("*/pyproject.toml"))
    if not manifests:
        _raise_value_error(f"{members_root} must contain at least one workspace member")
    bounds: dict[Path, tuple[int, int, int]] = {}
    for manifest in manifests:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
        project = document.get("project")
        if not isinstance(project, dict) or not isinstance(project.get("requires-python"), str):
            _raise_type_error(f"{manifest} must declare project.requires-python")
        bounds[manifest] = _parse_lower_bound(project["requires-python"], str(manifest))
    return bounds


def _read_guard_minimum(guard_file: Path) -> tuple[int, int, int]:
    """Read the bootstrap guard's hard-coded Python floor."""
    match = _GUARD_PATTERN.search(guard_file.read_text(encoding="utf-8"))
    if match is None:
        _raise_value_error(f"{guard_file} must declare _MINIMUM_PYTHON as a (major, minor, patch) tuple")
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def check_python_runtime(version_file: Path, members_root: Path, guard_file: Path) -> None:
    """Raise when the Python runtime declarations disagree or the pin is too low."""
    bounds = _read_member_lower_bounds(members_root)
    distinct = set(bounds.values())
    if len(distinct) > 1:
        detail = ", ".join(f"{manifest}: {_format(bound)}" for manifest, bound in sorted(bounds.items()))
        _raise_value_error(f"workspace members declare conflicting requires-python lower bounds ({detail})")
    minimum = distinct.pop()

    actual = _parse_version(version_file.read_text(encoding="utf-8"), str(version_file))
    if actual < minimum:
        _raise_value_error(
            f"{version_file} Python version {_format(actual)} is below the workspace "
            f"requires-python lower bound {_format(minimum)}"
        )

    guard = _read_guard_minimum(guard_file)
    if guard != minimum:
        _raise_value_error(
            f"{guard_file} _MINIMUM_PYTHON {_format(guard)} does not match the workspace "
            f"requires-python lower bound {_format(minimum)}"
        )


def main() -> int:
    """Run the Python runtime compatibility check."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-file", type=Path, required=True)
    parser.add_argument("--members-root", type=Path, required=True)
    parser.add_argument("--guard-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        check_python_runtime(args.version_file, args.members_root, args.guard_file)
    except (OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
