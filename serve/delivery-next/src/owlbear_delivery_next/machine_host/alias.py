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
import logging
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import data_place, data_repo, local_home
from owlbear_delivery_next.machine_host import versions
from owlbear_delivery_next.state_store import registry

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)
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
    if not runtime.is_symlink() and runtime.exists():
        versions.keep_data(runtime)  # the legacy folder is put away under versions/, which never keeps the data
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
        if why := _kept(new):
            _log.warning("%s", why)  # left in place, the data with it; the host still starts
        else:
            legacy = home / local_home.VERSIONS / f"legacy-{_commit(new)}"
            legacy.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            new.rename(legacy)
    runtime = home / local_home.RUNTIME
    if runtime.is_symlink():
        with contextlib.suppress(OSError):
            (runtime.resolve() / versions.ACTIVATED).touch(exist_ok=True)
        _marked(runtime.resolve().name)


def _kept(new: Path) -> str:
    """Why the legacy folder at *new* stays, else '': it holds the shared data.

    That includes data the pointer names through ``runtime``, the folder's name before the update.
    """
    try:
        versions.keep_data(new)
        named = data_place.protected()
    except (versions.VersionError, data_repo.DataRepoError) as exc:
        return str(exc)
    runtime = local_home.root() / local_home.RUNTIME
    for path in named:
        if path.absolute() == runtime or runtime in path.absolute().parents:
            inside, place = new / path.absolute().relative_to(runtime), data_place.default()
            return (
                f"{new} is not put away: it holds the shared data at {inside}, which the pointer names as {path}; "
                f"move it to {place}, then run `owlbear data {place}`"
            )
    return ""


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
