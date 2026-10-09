"""Controller release integrity (N02 I6): the release tree digest that ``delivery-controller verify`` checks.

Integrity is defined against accidental and ordinary-tool modification (editor saves, Git or package-manager
writes, interrupted installs, restores), not against the same OS user or root. Install seals every release
entry read-only; ``pin``, ``switch`` and ``verify`` hash the full content and the interpreter binary against
``RELEASE.json`` and refuse a writable entry. Starts do not re-verify.
"""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

RELEASE_FILE = "RELEASE.json"
_MAX_RELEASE_BYTES = 1 << 20
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


class ReleaseIntegrityError(ValueError):
    """A file that a release names is not a regular file, or ``RELEASE.json`` is not bounded."""


def file_sha256(path: Path | str) -> str:
    """SHA-256 of one regular file, opened without following a final link or blocking on a FIFO."""
    descriptor = os.open(path, _READ_FLAGS)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        msg = f"{path} is not a regular file"
        raise ReleaseIntegrityError(msg)
    with open(descriptor, "rb") as handle:  # noqa: PTH123 - the descriptor is already opened and checked.
        return hashlib.file_digest(handle, "sha256").hexdigest()


def tree_digest(tree: Path) -> str:
    """SHA-256 over every entry's type, path, executable bit and content or link target (no mode bits)."""
    digest = hashlib.sha256()
    for directory, names, files in os.walk(tree):
        names.sort()
        base = Path(directory)
        relative = base.relative_to(tree).as_posix()
        for name in sorted([*files, *(name for name in names if (base / name).is_symlink())]):
            path = base / name
            locator = f"{relative}/{name}" if relative != "." else name
            if locator == RELEASE_FILE:
                continue
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                digest.update(f"l {locator} {path.readlink()}\n".encode())
            elif stat.S_ISREG(info.st_mode):
                executable = "x" if info.st_mode & stat.S_IXUSR else "-"
                digest.update(f"f {locator} {executable} {file_sha256(path)}\n".encode())
            else:
                digest.update(f"o {locator}\n".encode())
        digest.update(f"d {relative}\n".encode())
    return digest.hexdigest()


def read_release_record(release: Path) -> bytes:
    """Return the bounded ``RELEASE.json`` bytes of one release."""
    descriptor = os.open(release / RELEASE_FILE, _READ_FLAGS)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_RELEASE_BYTES:
            msg = f"{RELEASE_FILE} is not a bounded regular file"
            raise ReleaseIntegrityError(msg)
        return os.read(descriptor, _MAX_RELEASE_BYTES + 1)
    finally:
        os.close(descriptor)
