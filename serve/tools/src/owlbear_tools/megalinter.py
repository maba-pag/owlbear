"""MegaLinter image configuration shared by workspace commands."""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from owlbear_tools.quality_runtime import FixMode, _call, _finish, _parse_options, _require_development

if TYPE_CHECKING:
    from collections.abc import Iterator

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_CONFIG_PATH = _REPOSITORY_ROOT / ".mega-linter.yml"
_BASE_IMAGE_REPOSITORY = "ghcr.io/oxsecurity/megalinter"
_IMAGE_COMPONENT_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_IMAGE_TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
_DOCKER_READY_TIMEOUT_SECONDS = 30.0
_DOCKER_READY_POLL_SECONDS = 0.5
_DOCKER_STOP_RUNTIME_ENV = "OWLBEAR_DOCKER_STOP_RUNTIME"
_DOCKER_CLI_CANDIDATES = (
    Path("/usr/local/bin/docker"),
    Path("/opt/homebrew/bin/docker"),
    Path.home() / ".orbstack/bin/docker",
    Path("/Applications/Docker.app/Contents/Resources/bin/docker"),
)


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


@dataclass(frozen=True)
class DockerRuntimeApp:
    """A supported macOS application that can provide a Docker engine."""

    name: str
    process_name: str


_DOCKER_RUNTIME_APPS = (
    DockerRuntimeApp(name="OrbStack", process_name="OrbStack"),
    DockerRuntimeApp(name="Docker", process_name="Docker Desktop"),
)


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


def _docker_command(binary: str = "docker") -> list[str]:
    return [
        binary,
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "-v",
        f"{Path.cwd()}:/tmp/lint",
    ]


def _run_host(command: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _find_docker_binary() -> str | None:
    if shutil.which("docker") is not None:
        return "docker"
    for candidate in _DOCKER_CLI_CANDIDATES:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _docker_is_ready(binary: str) -> bool:
    try:
        return _run_host([binary, "info"], timeout=5.0).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _app_is_installed(app: DockerRuntimeApp) -> bool:
    try:
        return _run_host(["open", "-Ra", app.name]).returncode == 0
    except OSError:
        return False


def _installed_docker_apps() -> tuple[DockerRuntimeApp, ...]:
    if sys.platform != "darwin":
        return ()
    return tuple(app for app in _DOCKER_RUNTIME_APPS if _app_is_installed(app))


def _app_is_running(app: DockerRuntimeApp) -> bool:
    try:
        return _run_host(["pgrep", "-x", app.process_name]).returncode == 0
    except OSError:
        return False


def _start_docker_app(app: DockerRuntimeApp) -> None:
    result = _run_host(["open", "-a", app.name])
    if result.returncode:
        message = result.stderr.strip() or f"unable to start {app.name}"
        raise RuntimeError(message)


def _stop_docker_app(app: DockerRuntimeApp) -> None:
    result = _run_host(["osascript", "-e", f'tell application "{app.name}" to quit'])
    if result.returncode:
        message = result.stderr.strip() or f"unable to stop {app.name}"
        raise RuntimeError(message)


def _wait_for_docker() -> str | None:
    deadline = time.monotonic() + _DOCKER_READY_TIMEOUT_SECONDS
    while True:
        binary = _find_docker_binary()
        if binary is not None and _docker_is_ready(binary):
            return binary
        if time.monotonic() >= deadline:
            return None
        time.sleep(_DOCKER_READY_POLL_SECONDS)


def _stop_runtime_requested() -> bool:
    return os.environ.get(_DOCKER_STOP_RUNTIME_ENV, "").strip().lower() in {"1", "true", "yes"}


def _acquire_docker_runtime() -> tuple[str, DockerRuntimeApp | None]:
    binary = _find_docker_binary()
    if binary is not None and _docker_is_ready(binary):
        return binary, None

    if sys.platform != "darwin":
        message = "Docker CLI or engine is unavailable on this platform"
        raise RuntimeError(message)

    installed_apps = _installed_docker_apps()
    if not installed_apps:
        message = "Docker is unavailable and no supported runtime app was found (OrbStack or Docker)"
        raise RuntimeError(message)

    failures: list[str] = []
    for app in installed_apps:
        started_by_us = False
        try:
            if not _app_is_running(app):
                _start_docker_app(app)
                started_by_us = True
            binary = _wait_for_docker()
            if binary is not None:
                return binary, app if started_by_us else None
            failures.append(f"{app.name} did not make Docker ready within {_DOCKER_READY_TIMEOUT_SECONDS:.0f}s")
        except (OSError, RuntimeError) as exc:
            failures.append(f"{app.name}: {exc}")
        if started_by_us:
            try:
                _stop_docker_app(app)
            except (OSError, RuntimeError) as exc:
                failures.append(f"{app.name} cleanup: {exc}")

    details = "; ".join(failures)
    message = f"Docker remained unavailable after trying supported runtime apps: {details}"
    raise RuntimeError(message)


@contextlib.contextmanager
def _docker_runtime() -> Iterator[str]:
    binary, started_app = _acquire_docker_runtime()
    try:
        yield binary
    finally:
        if started_app is not None and _stop_runtime_requested():
            try:
                _stop_docker_app(started_app)
            except (OSError, RuntimeError) as exc:
                sys.stderr.write(f"Warning: Docker runtime cleanup failed: {exc}\n")


def run_megalint(fix_mode: FixMode) -> int:
    """Run the configured MegaLinter image with one fix policy."""
    image = load_megalinter_image()
    with _docker_runtime() as docker_binary:
        command = _docker_command(docker_binary)
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
