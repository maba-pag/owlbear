"""The runtime alias (self-update build §3, §5.3): ``~/.owlbear/runtime`` names the active version.

Renaming it is the one point at which an update takes effect. On the first update the legacy runtime folder and a
new link to the version swap places in one atomic rename, so
``runtime`` is never missing; the legacy folder is then put away under ``versions/legacy-<commit>``. Every start
completes a migration a crash interrupted and raises ``machine.json``'s mark to the alias's version before any store
opens, so the machine never moves backwards.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import registry, versions

if TYPE_CHECKING:
    from pathlib import Path

NEW = "runtime.new"
RENAME_SWAP = 0x2  # macOS renamex_np: exchange the two names atomically (APFS; TD-262 Mac first)


def _swap(first: Path, second: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.renamex_np(os.fsencode(first), os.fsencode(second), RENAME_SWAP) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), str(first))


def activate(folder: Path, tag: str) -> None:
    """Make *folder*, the installed version *tag*, the active one: the rename of the alias, then the mark."""
    home = local_home.root()
    runtime, new = home / local_home.RUNTIME, home / NEW
    new.unlink(missing_ok=True)
    new.symlink_to(folder)
    if runtime.is_symlink() or not runtime.exists():
        new.replace(runtime)  # a link renamed over the alias
    else:
        _swap(new, runtime)  # the first update: the legacy folder now has the name runtime.new
    complete()
    _marked(tag)


def complete() -> None:
    """Finish a first migration a crash interrupted, and raise the mark to the alias's version; at every start."""
    home = local_home.root()
    new = home / NEW
    if new.is_symlink():
        new.unlink()  # made, never renamed: the old version stays
    elif new.is_dir():
        legacy = home / local_home.VERSIONS / f"legacy-{_commit(new)}"
        legacy.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        new.rename(legacy)
    runtime = home / local_home.RUNTIME
    if runtime.is_symlink():
        _marked(runtime.resolve().name)


def _commit(folder: Path) -> str:
    command = ["git", "-C", str(folder), "rev-parse", "--short=12", "HEAD"]
    try:
        said = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30).stdout.strip()  # noqa: S603
    except OSError, subprocess.SubprocessError:
        said = ""
    return said or "unknown"


def _marked(tag: str) -> None:
    """Raise ``machine.json``'s highest version ever active to *tag*; never lower it."""
    found = versions.number(tag)
    if found is None:
        return
    with registry.locked():
        saved = registry.load()
        if (versions.number(saved.active) or (-1, -1)) < found:
            saved.active = tag
            registry.save(saved)


def physical(executable: Path) -> Path:
    """*executable* named by its own version's folder rather than through the alias.

    So a later switch never changes the code a running process loads (§3); the file itself may be a link (a venv's
    python), so only its folder is resolved.
    """
    return executable.parent.resolve() / executable.name
