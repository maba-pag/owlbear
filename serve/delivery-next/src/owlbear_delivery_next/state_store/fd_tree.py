"""Folder trees read, copied, flushed and removed by descriptor: no link is followed and no name is resolved twice.

Every operation takes the folder's descriptor and a bare name under it, so a path swapped for a link after it was
checked does not redirect the work. A link is copied as a link and never followed; anything that is not a plain
file, link or folder is refused.
"""

from __future__ import annotations

import errno
import hashlib
import os
import secrets
import stat
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store.database import FormatTooNewError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
CHUNK = 1 << 20
QUARANTINE = ".retired-"  # where an entry whose write or check failed is kept, under a name no one else chooses


def open_dir(dfd: int, name: str) -> int:
    """Open folder *name* under *dfd* without following a link; a link or a non-folder is refused."""
    try:
        return os.open(name, DIR_FLAGS, dir_fd=dfd)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            msg = f"{name} holds a link or is not a folder: refusing to move through it; nothing was moved"
            raise StoreError(msg) from exc
        raise


def stat_at(dfd: int, name: str) -> os.stat_result | None:
    """What *name* is under *dfd*, a link itself never followed; None when there is nothing."""
    try:
        return os.stat(name, dir_fd=dfd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def write_at(dfd: int, name: str, text: str, *, before_replace: Callable[[], None] | None = None) -> None:
    """Replace file *name* under *dfd* with *text*: a synced temporary entry renamed over it, then the folder synced.

    The temporary name is new and created exclusively, so no existing entry, link included, is written through.
    A failed write keeps whatever sits at the temporary name under a quarantine name and never unlinks it by name.
    *before_replace*, when supplied, must still admit the replacement after the temporary file is durable.

    Raises:
        StoreError: The file could not be written or renamed; the temporary entry is kept and named.
    """
    tmp = f".tmp-{name}-{secrets.token_hex(8)}"
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
    except OSError as exc:
        msg = f"{name} cannot be written ({exc.strerror}): nothing was moved"
        raise StoreError(msg) from exc
    try:
        try:
            with os.fdopen(fd, "wb", closefd=False) as fh:
                fh.write(text.encode())
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            os.close(fd)
        if before_replace is not None:
            before_replace()
        os.rename(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd)
    except (OSError, ValueError, StoreError) as exc:
        kept = keep_entry(dfd, tmp)
        detail = exc.strerror if isinstance(exc, OSError) else str(exc)
        msg = f"{name} could not be written ({detail}): {kept} was kept; move it away, then start again"
        error = FormatTooNewError if isinstance(exc, FormatTooNewError) else StoreError
        raise error(msg) from exc
    os.fsync(dfd)


def create_at(dfd: int, name: str, text: str) -> None:
    """Create file *name* under *dfd* exclusively with *text*, then sync the file and the folder.

    An existing entry, link included, is never followed or replaced: it raises FileExistsError and nothing is
    written. A write that fails after the name is created leaves that entry in place, never unlinked by name,
    and raises StoreError. The raw descriptor stays owned until finally, even if its file-object handover fails.

    Raises:
        FileExistsError: *name* already exists.
        StoreError: The file could not be created, or was not finished; what is there is kept.
    """
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
    except FileExistsError:
        raise
    except OSError as exc:
        msg = f"{name} cannot be created ({exc.strerror}): nothing was written"
        raise StoreError(msg) from exc
    try:
        try:
            with os.fdopen(fd, "wb", closefd=False) as fh:
                fh.write(text.encode())
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            os.close(fd)
        os.fsync(dfd)
    except OSError as exc:
        msg = f"{name} was not finished ({exc.strerror}): it was left in place; move it away, then start again"
        raise StoreError(msg) from exc


def keep_entry(dfd: int, name: str) -> str:
    """Rename entry *name* under *dfd* to a fresh quarantine name, synced in its folder, and return that name.

    Nothing is unlinked: whatever sits at *name*, owned or foreign, keeps its bytes under the quarantine name, where
    ``refuse_quarantined`` stops the next start until the owner moves it away.
    """
    held = f"{QUARANTINE}{secrets.token_hex(8)}"
    os.rename(name, held, src_dir_fd=dfd, dst_dir_fd=dfd)
    os.fsync(dfd)
    return held


def open_file(dfd: int, name: str) -> int:
    """Open regular file *name* under *dfd* for reading; a FIFO, device or other entry is refused, never waited on.

    The open is non-blocking and the type is checked on the descriptor, so an entry swapped to a FIFO after a
    stat still cannot block the open or be read.

    Raises:
        StoreError: The entry is not a regular file; nothing was read or removed.
    """
    fd = os.open(name, FILE_FLAGS | os.O_NONBLOCK, dir_fd=dfd)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        msg = f"{name} is not a regular file: refusing to read it; nothing was removed"
        raise StoreError(msg)
    return fd


def read_at(dfd: int, name: str) -> str | None:
    """The text of regular file *name* under *dfd*, or None when it is absent; a link or other entry is an OSError."""
    try:
        fd = os.open(name, FILE_FLAGS | os.O_NONBLOCK, dir_fd=dfd)
    except FileNotFoundError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, f"{name} is not a regular file")
        chunks = []
        while chunk := os.read(fd, 1 << 16):
            chunks.append(chunk)
        return b"".join(chunks).decode()
    finally:
        os.close(fd)


def holds_text_at(dfd: int, name: str, text: str) -> bool:
    """Whether *name* under *dfd* is a regular file whose bytes are exactly *text*.

    Opened without following links and without blocking, so a FIFO or other special entry answers False at once;
    the read stops one byte past *text*, so longer content is never read to the end.
    """
    want = text.encode()
    try:
        fd = os.open(name, FILE_FLAGS | os.O_NONBLOCK, dir_fd=dfd)
    except OSError:
        return False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return False
        got = b""
        while len(got) <= len(want) and (chunk := os.read(fd, len(want) + 1 - len(got))):
            got += chunk
        return got == want
    finally:
        os.close(fd)


def require_text_at(dfd: int, name: str, text: str) -> None:
    """Refuse publication unless the named regular entry still holds the exact admitted image."""
    if not holds_text_at(dfd, name, text):
        msg = f"{name} changed or could not be verified: refusing publication"
        raise StoreError(msg)


def create_verified_at(dfd: int, name: str, text: str) -> None:
    """Create *name* under *dfd* with exactly *text*, then raise unless it still holds *text* when read back."""
    create_at(dfd, name, text)
    if not holds_text_at(dfd, name, text):
        msg = f"{name} was replaced while it was written; what is there was kept"
        raise StoreError(msg)


def names_at(dfd: int) -> list[str]:
    """The entry names of the folder *dfd* pins, listed by descriptor."""
    return sorted(os.listdir(dfd))  # listed by descriptor, not by path


def ident(st: os.stat_result) -> list[int]:
    """A folder's identity: its device and inode."""
    return [st.st_dev, st.st_ino]


def digest_at(dfd: int, name: str) -> str:
    """What entry *name* holds under *dfd*: names, kinds, link targets and bytes."""
    digest = hashlib.sha256()
    _feed(digest, dfd, name, ".")  # the entry's own name is not hashed: an entry moved aside keeps its digest
    return digest.hexdigest()


def entry_ok(dfd: int, name: str, digest: str) -> bool:
    """Whether entry *name* under *dfd* still holds what *digest* recorded; a missing entry does not."""
    try:
        return digest_at(dfd, name) == digest
    except FileNotFoundError:
        return False


def _feed(digest: hashlib._Hash, dfd: int, name: str, rel: str) -> None:
    st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
    digest.update(f"{rel}\0".encode())
    if stat.S_ISLNK(st.st_mode):
        digest.update(b"link\0" + os.readlink(name, dir_fd=dfd).encode())
    elif stat.S_ISDIR(st.st_mode):
        digest.update(b"dir\0")
        fd = open_dir(dfd, name)
        try:
            for child in sorted(os.listdir(fd)):  # noqa: PTH208 - listed by descriptor, not by path
                _feed(digest, fd, child, f"{rel}/{child}")
        finally:
            os.close(fd)
    else:
        digest.update(b"file\0")
        fd = open_file(dfd, name)
        with os.fdopen(fd, "rb") as fh:
            for chunk in iter(lambda: fh.read(CHUNK), b""):
                digest.update(chunk)
    digest.update(b"\0")


def sync(dfd: int, name: str) -> None:
    """Flush entry *name* under *dfd* to disk, a folder with everything in it."""
    st = stat_at(dfd, name)
    if st is None or stat.S_ISLNK(st.st_mode):
        return
    if stat.S_ISDIR(st.st_mode):
        fd = open_dir(dfd, name)
        try:
            for child in os.listdir(fd):  # noqa: PTH208 - listed by descriptor, not by path
                sync(fd, child)
            os.fsync(fd)
        finally:
            os.close(fd)
        return
    fd = open_file(dfd, name)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def copy(sfd: int, name: str, dfd: int) -> None:
    """Copy entry *name* under *sfd* into *dfd* under the same name; the destination must not hold it yet."""
    st = os.stat(name, dir_fd=sfd, follow_symlinks=False)
    if stat.S_ISLNK(st.st_mode):
        os.symlink(os.readlink(name, dir_fd=sfd), name, dir_fd=dfd)
    elif stat.S_ISDIR(st.st_mode):
        os.mkdir(name, 0o700, dir_fd=dfd)
        src, dst = _open_pair_dirs(sfd, dfd, name)
        try:
            for child in os.listdir(src):  # noqa: PTH208 - listed by descriptor, not by path
                copy(src, child, dst)
        finally:
            os.close(src)
            os.close(dst)
    elif stat.S_ISREG(st.st_mode):
        src = open_file(sfd, name)
        try:
            dst = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
            try:
                with os.fdopen(src, "rb", closefd=False) as fin, os.fdopen(dst, "wb", closefd=False) as fout:
                    for chunk in iter(lambda: fin.read(CHUNK), b""):
                        fout.write(chunk)
                os.fchmod(dst, stat.S_IMODE(st.st_mode))
                os.fsync(dst)
            finally:
                os.close(dst)
        finally:
            os.close(src)
    else:
        msg = f"{name} is neither a file, a link nor a folder: refusing to copy it; nothing was removed"
        raise StoreError(msg)


def partial_of(sfd: int, dfd: int, name: str) -> bool:
    """Whether entry *name* under *dfd* is a prefix of the same-named entry under *sfd*: our own interrupted copy.

    Every name in it must exist in the source, each file's bytes must be a prefix of the source's, and each link
    must point where the source's does. Anything else, a foreign child included, is not ours.
    """
    try:
        st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
        src_st = stat_at(sfd, name)
    except FileNotFoundError:
        return False
    if src_st is None or stat.S_IFMT(st.st_mode) != stat.S_IFMT(src_st.st_mode):
        return False
    if stat.S_ISLNK(st.st_mode):
        return os.readlink(name, dir_fd=dfd) == os.readlink(name, dir_fd=sfd)
    if stat.S_ISDIR(st.st_mode):
        return _partial_dir(sfd, dfd, name)
    return stat.S_ISREG(st.st_mode) and _partial_bytes(sfd, dfd, name)


def _open_pair_dirs(sfd: int, dfd: int, name: str) -> tuple[int, int]:
    """Open the same-named folder under both descriptors; if the second open fails, the first is closed."""
    src = open_dir(sfd, name)
    try:
        return src, open_dir(dfd, name)
    except BaseException:
        os.close(src)
        raise


def _partial_dir(sfd: int, dfd: int, name: str) -> bool:
    src, dst = _open_pair_dirs(sfd, dfd, name)
    try:
        return all(partial_of(src, dst, child) for child in os.listdir(dst))  # noqa: PTH208 - listed by descriptor
    finally:
        os.close(src)
        os.close(dst)


def _partial_bytes(sfd: int, dfd: int, name: str) -> bool:
    dst = open_file(dfd, name)
    try:
        src = open_file(sfd, name)
    except BaseException:
        os.close(dst)
        raise
    try:
        with os.fdopen(dst, "rb", closefd=False) as fd_dst, os.fdopen(src, "rb", closefd=False) as fd_src:
            while chunk := fd_dst.read(CHUNK):
                if fd_src.read(len(chunk)) != chunk:
                    return False
        return True
    finally:
        os.close(dst)
        os.close(src)


def refuse_quarantined(dfd: int, folder: Path) -> None:
    """Refuse while *folder* holds ``.retired-*`` entries a failed operation kept: their owner is unknown.

    Such an entry is neither adopted into a move nor deleted; it is for the owner to move away.

    Raises:
        StoreError: Quarantined entries lie in the folder; nothing was moved.
    """
    kept = sorted(n for n in os.listdir(dfd) if n.startswith(QUARANTINE))
    if kept:
        msg = (
            f"{folder} holds entries kept by an earlier failed operation ({', '.join(kept)}): nothing was moved; "
            "move them away, then start again"
        )
        raise StoreError(msg)


def sync_names(pfd: int, target: Path, root: Path) -> None:
    """Sync the folder that holds the published name, then each folder above it up to *root*, before a switch."""
    os.fsync(pfd)
    folder = target.parent
    while folder != root and root in folder.parents:
        folder = folder.parent
        fd = os.open(folder, DIR_FLAGS)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
