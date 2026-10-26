"""Project setup commands."""

from __future__ import annotations

import subprocess
import sys

from owlbear_tools.commands import command_footer


def _run(command: list[str]) -> int:
    return subprocess.run(command, check=False).returncode  # noqa: S603


def _finish(exit_code: int) -> None:
    print(command_footer(), file=sys.stderr)  # noqa: T201
    raise SystemExit(exit_code)


def hooks_install() -> None:
    """Install the Git hook and all configured hook environments."""
    install = _run(["pre-commit", "install"])
    environments = _run(["pre-commit", "install-hooks"]) if install == 0 else install
    _finish(environments)
