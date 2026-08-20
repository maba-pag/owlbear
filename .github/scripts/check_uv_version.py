"""Validate the active uv runtime against the project lower bound."""

from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from pathlib import Path
from typing import NoReturn

_VERSION_PATTERN = re.compile(r"\buv\s+v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\b")
_LOWER_BOUND_PATTERN = re.compile(r"^>=\s*(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")


def _raise_value_error(message: str) -> NoReturn:
    """Raise one named uv runtime-contract failure."""
    raise ValueError(message)


def _raise_type_error(message: str) -> NoReturn:
    """Raise one named uv runtime-input type failure."""
    raise TypeError(message)


def _parse_version(value: str, source: str) -> tuple[int, int, int]:
    """Parse one complete uv version from command output."""
    match = _VERSION_PATTERN.search(value.strip())
    if match is None:
        _raise_value_error(f"{source} must report a complete uv version")
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def _read_uv_lower_bound(path: Path) -> tuple[int, int, int]:
    """Read the uv lower-bound grammar from the project manifest."""
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    if not isinstance(document, dict):
        _raise_type_error(f"{path} must contain a TOML table")
    tool = document.get("tool")
    if not isinstance(tool, dict):
        _raise_type_error(f"{path} must declare [tool.uv]")
    uv_settings = tool.get("uv")
    if not isinstance(uv_settings, dict):
        _raise_type_error(f"{path} must declare [tool.uv]")
    required_version = uv_settings.get("required-version")
    if not isinstance(required_version, str):
        _raise_type_error(f"{path} [tool.uv] must declare required-version")
    match = _LOWER_BOUND_PATTERN.fullmatch(required_version.strip())
    if match is None:
        _raise_value_error(f"{path} [tool.uv] required-version must use >=major.minor.patch")
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def _read_uv_version(uv_executable: str, root: Path) -> tuple[int, int, int]:
    """Read the version reported by one exact uv executable."""
    try:
        result = subprocess.run(  # noqa: S603
            [uv_executable, "--version"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        _raise_value_error(f"{uv_executable} could not be executed: {error}")
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown error"
        _raise_value_error(f"{uv_executable} --version failed: {details}")
    return _parse_version(result.stdout, f"{uv_executable} --version")


def check_uv_runtime(pyproject_file: Path, uv_executable: str) -> None:
    """Raise when the active uv version is below the project lower bound."""
    minimum = _read_uv_lower_bound(pyproject_file)
    actual = _read_uv_version(uv_executable, pyproject_file.parent)
    if actual < minimum:
        _raise_value_error(
            f"{uv_executable} version {actual[0]}.{actual[1]}.{actual[2]} is below "
            f"{pyproject_file} [tool.uv] required-version lower bound "
            f"{minimum[0]}.{minimum[1]}.{minimum[2]}"
        )


def main() -> int:
    """Run the uv runtime compatibility check."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pyproject-file", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--uv-executable", default="uv")
    args = parser.parse_args()
    try:
        check_uv_runtime(args.pyproject_file, args.uv_executable)
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
