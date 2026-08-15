"""Shared execution policy for quality commands."""

from __future__ import annotations

import argparse
import subprocess
import sys
from enum import StrEnum
from pathlib import Path

from owlbear_tools.commands import command_footer

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class FixMode(StrEnum):
    """Supported quality-command mutation policies."""

    SAFE = "safe"
    NONE = "none"
    UNSAFE = "unsafe"


def _call(command: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> int:
    kwargs: dict[str, object] = {}
    if env is not None:
        kwargs["env"] = env
    if cwd is not None:
        kwargs["cwd"] = cwd
    return subprocess.call(command, **kwargs)  # noqa: S603


def _git_paths(*, staged: bool) -> list[str]:
    command = (
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"] if staged else ["git", "ls-files", "-z"]
    )
    try:
        output = subprocess.check_output(command)  # noqa: S603
    except (OSError, subprocess.CalledProcessError) as exc:
        scope = "staged files" if staged else "workspace files"
        message = f"unable to discover {scope} from Git"
        raise RuntimeError(message) from exc
    return [value.decode("utf-8") for value in output.split(b"\0") if value]


def _git_root() -> Path:
    try:
        output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])  # noqa: S607
    except (OSError, subprocess.CalledProcessError) as exc:
        message = "unable to discover Git repository root"
        raise RuntimeError(message) from exc
    return Path(output.decode("utf-8").strip())


def _add_fix_mode(parser: argparse.ArgumentParser, *, allow_unsafe: bool) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--no-fix", "-n", action="store_const", const=FixMode.NONE, dest="fix_mode")
    if allow_unsafe:
        group.add_argument("--unsafe-fix", "-u", action="store_const", const=FixMode.UNSAFE, dest="fix_mode")
    parser.set_defaults(fix_mode=FixMode.SAFE)


def _parse_options(
    prog: str,
    *,
    staged: bool,
    fixes: bool,
    allow_unsafe: bool = False,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=prog)
    if staged:
        parser.add_argument("--staged", "-s", action="store_true")
    if fixes:
        _add_fix_mode(parser, allow_unsafe=allow_unsafe)
    else:
        parser.set_defaults(fix_mode=FixMode.NONE)
    return parser.parse_args()


def _finish(exit_code: int) -> None:
    sys.stderr.write(command_footer() + "\n")
    raise SystemExit(exit_code)


def _require_development(prog: str) -> None:
    if not _is_owlbear_dev_checkout(Path.cwd()):
        message = f"{prog} is available only from the OwlBear development checkout"
        raise SystemExit(message)


def _is_owlbear_dev_checkout(root: Path) -> bool:
    return root.resolve() == _REPOSITORY_ROOT and (root / ".pre-commit-config.yaml").is_file()


def _is_owlbear_dev_subdirectory(root: Path) -> bool:
    resolved = root.resolve()
    return _REPOSITORY_ROOT in resolved.parents and (_REPOSITORY_ROOT / ".pre-commit-config.yaml").is_file()
