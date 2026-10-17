"""Local text files written safely: never through a symbolic link, always by an atomic rename."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def linked_part(repo: Path, path: Path) -> Path | None:
    """The first of *path*'s components inside *repo*, itself included, that is a symbolic link."""
    at = repo
    for part in path.relative_to(repo).parts:
        at /= part
        if at.is_symlink():
            return at
    return None


def replace_text(path: Path, text: str) -> None:
    """Write *path* through a temporary file in its directory and an atomic rename, which never follows a link."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        Path(tmp).chmod(0o644)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
