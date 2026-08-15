"""MegaLinter image configuration shared by workspace commands."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from owlbear_tools.quality_runtime import FixMode, _call, _finish, _parse_options, _require_development

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_CONFIG_PATH = _REPOSITORY_ROOT / ".mega-linter.yml"
_BASE_IMAGE_REPOSITORY = "ghcr.io/oxsecurity/megalinter"
_IMAGE_COMPONENT_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_IMAGE_TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass(frozen=True)
class MegaLinterImage:
    """Pinned MegaLinter runtime image."""

    reference: str

    @property
    def repository(self) -> str:
        """Return the image repository without its tag."""
        return self.reference.rsplit(":", 1)[0]

    @property
    def tag(self) -> str:
        """Return the image tag."""
        return self.reference.rsplit(":", 1)[1]


def load_megalinter_image(path: Path = _CONFIG_PATH) -> MegaLinterImage:
    """Derive and validate the MegaLinter image from native configuration."""
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        msg = f"{path} must contain a YAML mapping"
        raise TypeError(msg)

    flavor = content.get("MEGALINTER_FLAVOR", "all")
    version = content.get("MEGALINTER_VERSION")
    if not isinstance(flavor, str) or not _IMAGE_COMPONENT_RE.fullmatch(flavor):
        msg = f"{path} has an invalid MEGALINTER_FLAVOR"
        raise ValueError(msg)
    if not isinstance(version, str) or not _IMAGE_TAG_RE.fullmatch(version):
        msg = f"{path} has an invalid MEGALINTER_VERSION"
        raise ValueError(msg)

    repository = _BASE_IMAGE_REPOSITORY
    if flavor != "all":
        repository = f"{repository}-{flavor}"
    reference = f"{repository}:{version}"
    return MegaLinterImage(reference=reference)


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


def run_megalint(fix_mode: FixMode) -> int:
    """Run the configured MegaLinter image with one fix policy."""
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


def megalint() -> None:
    """Run MegaLinter across the workspace."""
    args = _parse_options("megalint", staged=False, fixes=True, allow_unsafe=True)
    _require_development("megalint")
    try:
        rc = run_megalint(args.fix_mode)
    except (OSError, RuntimeError, TypeError, ValueError, yaml.YAMLError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        rc = 2
    _finish(rc)


def _run(command: list[str]) -> int:
    return subprocess.run(command, check=False).returncode  # noqa: S603


def megalint_clean() -> None:
    """Preview and remove obsolete MegaLinter Docker images."""
    parser = argparse.ArgumentParser(prog="megalint-clean")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    _require_development("megalint-clean")
    try:
        image = load_megalinter_image()
        current = image.tag
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "docker",
                "image",
                "ls",
                "--filter",
                f"reference={_BASE_IMAGE_REPOSITORY}*:*",
                "--format",
                "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, RuntimeError, TypeError, ValueError, yaml.YAMLError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        _finish(2)
    if result.returncode:
        print(result.stderr, file=sys.stderr, end="")  # noqa: T201
        _finish(result.returncode)
    obsolete = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if fields[:2] != [image.repository, current]:
            obsolete.append(line)
    if not obsolete:
        print(f"No obsolete MegaLinter images found; preserving {current}.")  # noqa: T201
        _finish(0)
    print("Obsolete MegaLinter images:")  # noqa: T201
    for line in obsolete:
        print(f"  {line}")  # noqa: T201
    if not args.yes and (
        not sys.stdin.isatty() or input("Remove these images? [y/N] ").strip().lower() not in {"y", "yes"}
    ):
        print("No images removed.")  # noqa: T201
        _finish(0)
    image_ids = list(dict.fromkeys(line.split("\t")[2] for line in obsolete))
    _finish(_run(["docker", "image", "rm", *image_ids]))
