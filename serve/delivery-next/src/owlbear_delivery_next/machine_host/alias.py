"""The runtime alias (self-update build §3, §5.3): ``~/.owlbear/runtime`` names the active version.

Renaming it is the one point at which an update takes effect. On the first update the legacy runtime folder and a
new link to the version swap places in one atomic rename, so
``runtime`` is never missing; the legacy folder is then put away under ``versions/legacy-<commit>``. Every start
completes a migration a crash interrupted and raises ``machine.json``'s mark to the alias's version before any store
opens, so the machine never moves backwards.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import registry, versions

if TYPE_CHECKING:
    from pathlib import Path

NEW = "runtime.new"
RENAME_SWAP = 0x2  # macOS renamex_np: exchange the two names atomically (APFS; TD-262 Mac first)
RENAME_EXCHANGE, AT_FDCWD = 0x2, -100  # Linux renameat2, where CI runs the same exchange


def _swap(first: Path, second: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    a, b = os.fsencode(first), os.fsencode(second)
    if sys.platform == "darwin":
        done = libc.renamex_np(a, b, RENAME_SWAP)
    else:
        done = libc.renameat2(AT_FDCWD, a, AT_FDCWD, b, RENAME_EXCHANGE)
    if done != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), str(first))


def activate(folder: Path, tag: str) -> None:
    """Make *folder*, the installed version *tag*, the active one: the rename of the alias, then the mark.

    Raises only before the rename; what follows it (putting the legacy folder away, the mark) every start completes,
    so a failure there never sends the update back to the older version.
    """
    home = local_home.root()
    runtime, new = home / local_home.RUNTIME, home / NEW
    new.unlink(missing_ok=True)
    new.symlink_to(folder)
    if runtime.is_symlink() or not runtime.exists():
        new.replace(runtime)  # a link renamed over the alias
    else:
        _swap(new, runtime)  # the first update: the legacy folder now has the name runtime.new
    with contextlib.suppress(OSError, registry.RegistryError):
        (folder / versions.ACTIVATED).touch()
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
        with contextlib.suppress(OSError):
            (runtime.resolve() / versions.ACTIVATED).touch(exist_ok=True)
        _marked(runtime.resolve().name)


def _commit(folder: Path) -> str:
    command = ["git", "-C", str(folder), "rev-parse", "--short=12", "HEAD"]
    try:
        said = subprocess.run(  # noqa: S603 - fixed git arguments
            command, capture_output=True, text=True, check=True, timeout=30
        ).stdout.strip()
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
