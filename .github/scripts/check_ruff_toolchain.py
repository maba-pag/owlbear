"""Verify exact Ruff version parity across repository tooling and MegaLinter declarations."""

from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from pathlib import Path
from typing import NoReturn

import yaml

from owlbear_tools.megalinter import load_megalinter_image

_VERSION_PATTERN = re.compile(r"^(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$")
_RUFF_REQUIREMENT_PATTERN = re.compile(r"^ruff==(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$")
_RUFF_PRE_COMMIT_REPOSITORY = "https://github.com/astral-sh/ruff-pre-commit"
_ACTION_PATTERN = re.compile(
    r"uses:\s*oxsecurity/megalinter(?:/flavors/(?P<flavor>[a-z0-9-]+))?@[^\s]+\s+#\s*"
    r"v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)",
)


def _raise_type_error(message: str) -> NoReturn:
    raise TypeError(message)


def _raise_value_error(message: str) -> NoReturn:
    raise ValueError(message)


def _raise_runtime_error(message: str) -> NoReturn:
    raise RuntimeError(message)


def _normalise_version(value: object, source: str) -> str:
    if not isinstance(value, str):
        _raise_type_error(f"{source} must contain a version")
    normalised = value.strip().removeprefix("v")
    if _VERSION_PATTERN.fullmatch(normalised) is None:
        _raise_value_error(f"{source} must contain a complete semantic version")
    return normalised


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        _raise_type_error(f"{path} must contain a YAML mapping")
    return document


def _read_standalone_ruff_version(root: Path) -> str:
    path = root / "pyproject.toml"
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    groups = document.get("dependency-groups")
    if not isinstance(groups, dict):
        _raise_type_error(f"{path} must declare dependency-groups")

    requirements = [
        requirement
        for dependencies in groups.values()
        if isinstance(dependencies, list)
        for requirement in dependencies
        if isinstance(requirement, str)
    ]
    matches = [_RUFF_REQUIREMENT_PATTERN.fullmatch(requirement.strip()) for requirement in requirements]
    versions = [match.group("version") for match in matches if match is not None]
    if len(versions) != 1:
        _raise_value_error(f"{path} must declare exactly one exact ruff dependency")
    return versions[0]


def _read_pre_commit_ruff_version(root: Path) -> str:
    path = root / ".pre-commit-config.yaml"
    document = _load_yaml_mapping(path)
    repositories = document.get("repos")
    if not isinstance(repositories, list):
        _raise_type_error(f"{path} must declare repos")

    matches = [
        repository
        for repository in repositories
        if isinstance(repository, dict) and repository.get("repo") == _RUFF_PRE_COMMIT_REPOSITORY
    ]
    if len(matches) != 1:
        _raise_value_error(f"{path} must declare exactly one Ruff pre-commit repository")
    return _normalise_version(matches[0].get("rev"), f"{path} Ruff pre-commit revision")


def _read_megalinter_action_version(root: Path) -> tuple[str, str]:
    path = root / ".github/workflows/megalinter.yml"
    match = _ACTION_PATTERN.search(path.read_text(encoding="utf-8"))
    if match is None:
        _raise_value_error(f"{path} must declare a pinned MegaLinter action with a version comment")
    return match.group("flavor") or "all", match.group("version")


def _read_ruff_command_version(command: list[str], source: str) -> str:
    completed = subprocess.run(command, capture_output=True, check=False, text=True)  # noqa: S603
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
        _raise_runtime_error(f"{source} exited with status {completed.returncode}: {detail}")
    match = re.search(r"\bruff\s+(?P<version>[0-9]+\.[0-9]+\.[0-9]+)\b", completed.stdout)
    if match is None:
        _raise_value_error(f"{source} did not report a Ruff version")
    return _normalise_version(match.group("version"), source)


def check_ruff_toolchain(
    root: Path,
    *,
    ruff_executable: str = "ruff",
) -> None:
    """Raise when repository Ruff declarations or MegaLinter declarations diverge."""
    standalone_version = _read_standalone_ruff_version(root)
    pre_commit_version = _read_pre_commit_ruff_version(root)
    image = load_megalinter_image(root / ".mega-linter.yml")
    native_flavor = image.flavor
    action_flavor, action_version = _read_megalinter_action_version(root)
    if native_flavor != action_flavor:
        _raise_value_error(f"MegaLinter flavors diverge: native={native_flavor}, action={action_flavor}")
    native_version = image.tag.removeprefix("v")
    if native_version != action_version:
        _raise_value_error(f"MegaLinter versions diverge: native={native_version}, action={action_version}")

    installed_version = _read_ruff_command_version(
        [ruff_executable, "--version"],
        f"{ruff_executable} --version",
    )
    versions = {
        "pyproject.toml": standalone_version,
        "ruff-pre-commit": pre_commit_version,
        "installed Ruff": installed_version,
    }
    if len(set(versions.values())) != 1:
        details = ", ".join(f"{name}={version}" for name, version in versions.items())
        _raise_value_error(f"Ruff toolchain versions diverge: {details}")
    print(f"Repository Ruff toolchain versions aligned at {standalone_version}.")


def main() -> int:
    """Run the Ruff toolchain parity proof."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--ruff-executable", default="ruff")
    args = parser.parse_args()
    try:
        check_ruff_toolchain(
            args.root,
            ruff_executable=args.ruff_executable,
        )
    except (OSError, TypeError, ValueError, RuntimeError, yaml.YAMLError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
