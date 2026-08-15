"""Project dependency and asset maintenance commands."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from owlbear_tools.commands import command_footer
from owlbear_tools.quality_runtime import _require_development


def _run(command: list[str], *, cwd: Path | None = None) -> int:
    try:
        return subprocess.run(command, cwd=cwd, check=False).returncode  # noqa: S603
    except OSError as exc:
        print(f"Error: unable to run {command[0]}: {exc}", file=sys.stderr)  # noqa: T201
        return 2


def _finish(exit_code: int) -> None:
    print(command_footer(), file=sys.stderr)  # noqa: T201
    raise SystemExit(exit_code)


def deps_status() -> None:
    """Check lock consistency and report available dependency updates."""
    parser = argparse.ArgumentParser(prog="deps-status")
    parser.parse_args()
    _require_development("deps-status")
    print("Dependency status is informational; manifests and lockfiles will not be changed.")  # noqa: T201
    lock_status = _run(["uv", "lock", "--check"])
    python_status = _run(["uv", "tree", "--outdated"])
    npm_status = 0
    web = Path("serve/cockpit/web")
    if (web / "package-lock.json").is_file():
        print(  # noqa: T201
            "npm: Current is installed, Wanted is the newest version allowed by package.json, "
            "and Latest is the newest published version."
        )
        npm_status = _run(["npm", "outdated"], cwd=web)
    if npm_status == 1:
        print(  # noqa: T201
            "Updates remain available. deps-sync may restore Current from the existing locks, "
            "but it does not update locks or manifest ranges."
        )
    if lock_status:
        _finish(lock_status)
    if python_status:
        _finish(python_status)
    if npm_status not in {0, 1}:
        _finish(npm_status)
    _finish(0)


def deps_sync() -> None:
    """Install the exact locked Python and npm dependency sets."""
    parser = argparse.ArgumentParser(prog="deps-sync")
    parser.parse_args()
    _require_development("deps-sync")
    print(  # noqa: T201
        "Installing existing Python and npm lockfiles exactly; versions and manifest ranges will not be updated."
    )
    python_status = _run(["uv", "sync", "--locked", "--all-extras"])
    if python_status:
        _finish(python_status)
    web = Path("serve/cockpit/web")
    npm_status = _run(["npm", "ci"], cwd=web) if (web / "package-lock.json").is_file() else 0
    if npm_status == 0:
        print(  # noqa: T201
            "Installed dependencies now match the existing locks. Any remaining deps-status entries "
            "require a lock or manifest update."
        )
    _finish(npm_status)


def pds_sync() -> None:
    """Refresh PDS assets in a temporary tree and replace only on success."""
    parser = argparse.ArgumentParser(prog="pds-sync")
    parser.parse_args()
    _require_development("pds-sync")
    web = Path("serve/cockpit/web").resolve()
    public = web / "public"
    target = public / "porsche-design-system"
    public.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=public, prefix=".pds-sync-") as temporary:
        temporary_path = Path(temporary)
        environment = {**os.environ, "PDS_OUTPUT_DIR": str(temporary_path)}
        try:
            result = subprocess.run(
                ["npm", "run", "sync:pds"],  # noqa: S607
                cwd=web,
                env=environment,
                check=False,
            )
        except OSError as exc:
            print(f"Error: unable to run npm: {exc}", file=sys.stderr)  # noqa: T201
            _finish(2)
        if result.returncode:
            _finish(result.returncode)
        temporary_path.chmod(0o755)
        backup = public / ".pds-sync-backup"
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.replace(backup)
        try:
            temporary_path.replace(target)
        except Exception:
            if backup.exists():
                backup.replace(target)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    _finish(0)
