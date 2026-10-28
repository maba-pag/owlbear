"""Local Git binding paths, including aliases and control-file referents, retained through validation reads."""

from __future__ import annotations

import errno
import os
import stat
from collections import deque
from pathlib import Path

from owlbear_delivery_next.state_store import fd_tree
from owlbear_delivery_next.state_store.database import StoreError

POSIX_SYMLINK_LIMIT = 40


class GitImages:
    """Keep the original image of each resolution dependency; ordinary directory-content writes remain valid."""

    def __init__(self) -> None:
        self.images: dict[Path, os.stat_result | None] = {}

    @staticmethod
    def _same(before: os.stat_result | None, after: os.stat_result | None) -> bool:
        if before is None:
            return after is None
        if stat.S_ISDIR(before.st_mode):
            return after is not None and stat.S_ISDIR(after.st_mode) and os.path.samestat(before, after)
        return fd_tree.same_entry_image(before, after)

    def _observe(self, path: Path) -> os.stat_result | None:
        try:
            found = path.lstat()
        except FileNotFoundError:
            found = None
        before = self.images.setdefault(path, found)
        if not self._same(before, found):
            msg = f"{path} changed while its Git binding was checked: nothing was registered"
            raise StoreError(msg)
        return found

    def path(self, path: Path) -> Path:
        """Resolve component by component while retaining every link, referent and directory identity."""
        absolute = path.absolute()
        pending = deque(absolute.parts[1:])
        current, links = Path(absolute.anchor), 0
        self._observe(current)
        while pending:
            part = pending.popleft()
            if part == "..":
                current = current.parent
                continue
            current /= part
            found = self._observe(current)
            if found is None:
                return current.joinpath(*pending)
            if stat.S_ISLNK(found.st_mode):
                links += 1
                if links > POSIX_SYMLINK_LIMIT:
                    raise OSError(errno.ELOOP, "too many links in Git binding", str(path))
                referent = current.readlink()
                current = Path(referent.anchor) if referent.is_absolute() else current.parent
                pending.extendleft(reversed(referent.parts[1:] if referent.is_absolute() else referent.parts))
        return current

    def reference(self, base: Path, name: str, prefix: str = "") -> Path | None:
        """Capture a Git directory reference and the complete resolution chain its content selects."""
        control = self.path(base / name)
        found = self._observe(control)
        if found is None:
            return None
        if stat.S_ISDIR(found.st_mode):
            return control
        parent_fd = os.open(control.parent, fd_tree.DIR_FLAGS)
        try:
            text = fd_tree.read_at(parent_fd, control.name)
        finally:
            os.close(parent_fd)
        if text is None or not text.startswith(prefix):
            msg = f"{control} is not a readable Git directory reference: nothing was registered"
            raise StoreError(msg)
        value = text[len(prefix) :].rstrip("\r\n")
        return self.path(base / value)

    def confirm(self) -> None:
        """Verify resolution images without another Git command or control-file content read."""
        for path, before in self.images.items():
            try:
                after = path.lstat()
            except FileNotFoundError:
                after = None
            if not self._same(before, after):
                msg = f"{path}'s Git binding image changed during validation: nothing was registered"
                raise StoreError(msg)
