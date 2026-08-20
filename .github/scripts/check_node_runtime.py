"""Validate the checked-in Node runtime against the Cockpit lower bound."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import NoReturn

_VERSION_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
_LOWER_BOUND_PATTERN = re.compile(r"^>=\s*(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")


def _raise_value_error(message: str) -> NoReturn:
    """Raise one named runtime-contract failure."""
    raise ValueError(message)


def _raise_type_error(message: str) -> NoReturn:
    """Raise one named runtime-input type failure."""
    raise TypeError(message)


def _parse_version(value: str, source: str) -> tuple[int, int, int]:
    """Parse one complete semantic Node version."""
    match = _VERSION_PATTERN.fullmatch(value.strip())
    if match is None:
        _raise_value_error(f"{source} must contain a complete Node version")
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def _read_node_lower_bound(path: Path) -> tuple[int, int, int]:
    """Read the supported lower-bound grammar from a package manifest."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        _raise_type_error(f"{path} must contain a JSON object")
    engines = document.get("engines")
    if not isinstance(engines, dict) or not isinstance(engines.get("node"), str):
        _raise_type_error(f"{path} must declare engines.node")
    match = _LOWER_BOUND_PATTERN.fullmatch(engines["node"].strip())
    if match is None:
        _raise_value_error(f"{path} engines.node must use >=major.minor.patch")
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def check_node_declaration(version_file: Path, engines_file: Path) -> None:
    """Raise when the development Node version is below the declared lower bound."""
    actual = _parse_version(version_file.read_text(encoding="utf-8"), str(version_file))
    minimum = _read_node_lower_bound(engines_file)
    if actual < minimum:
        _raise_value_error(
            f"{version_file} Node version {actual[0]}.{actual[1]}.{actual[2]} is below "
            f"{engines_file} engines.node lower bound {minimum[0]}.{minimum[1]}.{minimum[2]}"
        )


def check_installed_node(expected_version: str, node_executable: str = "node") -> None:
    """Raise when the installed Node executable does not match the expected version."""
    completed = subprocess.run(  # noqa: S603
        [node_executable, "--version"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        _raise_value_error(
            f"{node_executable} --version exited with status {completed.returncode}: {completed.stderr.strip()}"
        )

    actual = _parse_version(completed.stdout, f"{node_executable} --version")
    expected = _parse_version(expected_version, "expected Node version")
    if actual != expected:
        _raise_value_error(
            f"installed Node version {actual[0]}.{actual[1]}.{actual[2]} does not match "
            f"expected version {expected[0]}.{expected[1]}.{expected[2]}"
        )


def check_node_runtime(
    version_file: Path,
    engines_file: Path,
    *,
    expected_version: str | None = None,
    node_executable: str = "node",
) -> None:
    """Validate the declaration and, when requested, the installed Node executable."""
    check_node_declaration(version_file, engines_file)
    if expected_version is not None:
        check_installed_node(expected_version, node_executable)


def main() -> int:
    """Run Node declaration and installed-runtime compatibility checks."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-file", type=Path, required=True)
    parser.add_argument("--engines-file", type=Path, required=True)
    parser.add_argument("--expected-version")
    parser.add_argument("--node-executable", default="node")
    args = parser.parse_args()
    try:
        check_node_runtime(
            args.version_file,
            args.engines_file,
            expected_version=args.expected_version,
            node_executable=args.node_executable,
        )
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
