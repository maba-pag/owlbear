"""Project setup and diagnostic commands."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from owlbear_tools.commands import command_footer
from owlbear_tools.delivery_config import _delivery_config_status

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def _run(command: list[str], *, cwd: Path | None = None) -> int:
    return subprocess.run(command, cwd=cwd, check=False).returncode  # noqa: S603


def _finish(exit_code: int) -> None:
    print(command_footer(), file=sys.stderr)  # noqa: T201
    raise SystemExit(exit_code)


def hooks_install() -> None:
    """Install the Git hook and all configured hook environments."""
    install = _run(["pre-commit", "install"])
    environments = _run(["pre-commit", "install-hooks"]) if install == 0 else install
    _finish(environments)


def setup_project() -> None:
    """Run the repository initializer for a target project."""
    parser = argparse.ArgumentParser(prog="setup-project")
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--remote", default="origin", metavar="NAME")
    parser.add_argument("--target-branch", metavar="BRANCH")
    parser.add_argument("--github-repository", metavar="OWNER/NAME")
    parser.add_argument("--replace-hooks", action="store_true")
    args = parser.parse_args()
    target = args.path.expanduser().resolve()
    command = [sys.executable, str(_REPOSITORY_ROOT / "setup/init.py")]
    command.extend(["--remote", args.remote])
    if args.target_branch:
        command.extend(["--target-branch", args.target_branch])
    if args.github_repository:
        command.extend(["--github-repository", args.github_repository])
    if args.replace_hooks:
        command.append("--replace-hooks")
    _finish(_run(command, cwd=target))


def doctor() -> None:
    """Check the shallow prerequisites and tracked project policy."""
    parser = argparse.ArgumentParser(prog="doctor")
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.path.expanduser().resolve()
    failures: list[str] = []
    warnings: list[str] = []

    for executable in ("git", "uv"):
        if shutil.which(executable):
            print(f"PASS  {executable} is available")  # noqa: T201
        else:
            failures.append(f"{executable} is not available")
    config_failures, config_success = _delivery_config_status(root)
    failures.extend(config_failures)
    if config_success is not None:
        print(f"PASS  {config_success}")  # noqa: T201
    relative = Path(".vscode/mcp.json")
    if (root / relative).is_file():
        print(f"PASS  {relative}")  # noqa: T201
    else:
        failures.append(f"missing {relative}")
    if (root / "package-lock.json").is_file() and shutil.which("npm") is None:
        warnings.append("npm is unavailable for this Node project")

    for warning in warnings:
        print(f"WARN  {warning}")  # noqa: T201
    for failure in failures:
        print(f"FAIL  {failure}")  # noqa: T201
    _finish(1 if failures else 0)
