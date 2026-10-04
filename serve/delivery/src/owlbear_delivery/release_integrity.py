"""Controller release integrity (N02 I6): the release tree digest, checked before a pinned controller starts.

Standard library only and free of Delivery imports: ``delivery-controller`` embeds this source in the
generated launchers, which run it with ``python -I -S`` so the release is verified before any of its code,
including ``.pth`` files, is imported. The loader repeats the check for callers that bypass a launcher,
unless a launcher in the same process already verified the same release record.

``pin`` and ``switch`` verify the full content digest and record, in ``pin.json``, the release record's
digest and a stat fingerprint of the verified tree and interpreter (type, mode, size, mtime, ctime and
inode of every entry). A start whose fingerprint still matches skips re-hashing: without root, no file
content, mode or entry can change without changing its ctime, inode or the entry set. Any other start
re-hashes the whole tree and the interpreter binary against the record.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

RELEASE_FILE = "RELEASE.json"
REFUSAL_CODE = "controller-release-invalid"
# Exit status of a launcher that refuses a release (EX_CONFIG): nothing of the release was imported.
REFUSAL_EXIT = 78
_MAX_RELEASE_BYTES = 1 << 20
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_ENTRY_POINTS = {"delivery-mcp": ("owlbear_delivery_mcp", None), "cockpit": ("owlbear_cockpit.main", "main")}
_verified: set[tuple[str, str, str]] = set()


class ReleaseIntegrityError(ValueError):
    """A release is not byte-identical to its install record, or a file it names is not a regular file."""


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


def interpreter_identity(executable: str | None = None) -> dict[str, str]:
    """Resolved path, version and binary digest of the interpreter running this process (or ``executable``)."""
    path = os.path.realpath(executable or sys.executable)
    return {"path": path, "version": sys.version.split()[0], "sha256": file_sha256(path)}


def stat_fingerprint(release: Path, interpreter: str) -> str:
    """SHA-256 over the metadata of every release entry and of the interpreter binary (no content reads)."""
    digest = hashlib.sha256()
    root = os.lstat(release)
    digest.update(f". {root.st_mode} {root.st_mtime_ns} {root.st_ctime_ns} {root.st_ino}\n".encode())
    for directory, names, files in os.walk(release):
        names.sort()
        relative = os.path.relpath(directory, release)
        for name in sorted([*files, *names]):
            info = os.lstat(os.path.join(directory, name))  # noqa: PTH118 - os.walk yields string paths.
            fields = f"{info.st_mode} {info.st_size} {info.st_mtime_ns} {info.st_ctime_ns} {info.st_ino}"
            digest.update(f"{relative}/{name} {fields}\n".encode())
    info = Path(interpreter).stat()
    digest.update(
        f"interpreter {interpreter} {info.st_size} {info.st_mtime_ns} {info.st_ctime_ns} {info.st_ino}\n".encode()
    )
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


def release_failures(release: Path, expected_sha256: str, expected_stat: str | None = None) -> list[str]:
    """Return why ``release`` does not match the pinned record digest; an empty list proves integrity.

    ``expected_stat`` is the pin's fingerprint of the tree verified at pin time; when it still matches
    and this process runs the recorded interpreter, the content is not hashed again.
    """
    try:
        content = read_release_record(release)
    except (OSError, ReleaseIntegrityError) as exc:
        return [f"{RELEASE_FILE} is unreadable ({exc})"]
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        return [f"{RELEASE_FILE} differs from the release record named by the pin"]
    try:
        record = json.loads(content)
        expected_tree, interpreter = record["tree_sha256"], record["interpreter"]
        recorded_path, recorded_version = interpreter["path"], interpreter["version"]
    except ValueError, KeyError, TypeError:
        return [f"{RELEASE_FILE} lacks the tree digest or the interpreter identity"]
    running = (os.path.realpath(sys.executable), sys.version.split()[0]) == (recorded_path, recorded_version)
    if expected_stat is not None and running and _fingerprint_matches(release, recorded_path, expected_stat):
        return []
    failures = []
    try:
        if tree_digest(release) != expected_tree:
            failures.append("the release tree was modified after install (tree digest differs)")
    except (OSError, ReleaseIntegrityError) as exc:
        failures.append(f"the release tree is unreadable ({exc})")
    try:
        actual = interpreter_identity()
    except (OSError, ReleaseIntegrityError) as exc:
        return [*failures, f"the interpreter is unreadable ({exc})"]
    if actual != interpreter:
        found = f"the interpreter {actual['path']} ({actual['version']})"
        failures.append(f"{found} is not the one recorded at install")
    return failures


def _fingerprint_matches(release: Path, interpreter: str, expected: str) -> bool:
    try:
        return stat_fingerprint(release, interpreter) == expected
    except OSError:
        return False


def require_release(release: Path, expected_sha256: str, expected_stat: str | None = None) -> None:
    """Verify one release once per process; raise ``ReleaseIntegrityError`` naming every failure."""
    key = (os.path.realpath(release), expected_sha256, expected_stat or "")
    if key in _verified:
        return
    failures = release_failures(Path(key[0]), expected_sha256, expected_stat)
    if failures:
        raise ReleaseIntegrityError("; ".join(failures))
    _verified.add(key)


def _launch(arguments: list[str]) -> None:
    """Launcher entry: verify the release, then enable its site-packages and run one controller entry point."""
    release, expected, expected_stat, entry, *rest = arguments
    try:
        require_release(Path(release), expected, expected_stat)
    except ReleaseIntegrityError as exc:
        sys.stderr.write(
            f"{REFUSAL_CODE}: controller release {release} is not intact: {exc}; nothing was started. "
            "Run delivery-controller verify, then install and switch to an intact release.\n"
        )
        raise SystemExit(REFUSAL_EXIT) from None
    import site  # noqa: PLC0415 - site-packages are enabled only after verification.

    site.main()
    try:
        from owlbear_delivery import release_integrity  # noqa: PLC0415, PLW0406 - the launcher runs this source.
    except ImportError:  # a release older than this check
        pass
    else:
        release_integrity._verified.add((os.path.realpath(release), expected, expected_stat))  # noqa: SLF001
    module, function = _ENTRY_POINTS[entry]
    sys.argv = [module, *rest]
    if function is None:
        import runpy  # noqa: PLC0415

        runpy.run_module(module, run_name="__main__", alter_sys=True)
        return
    import importlib  # noqa: PLC0415

    raise SystemExit(getattr(importlib.import_module(module), function)())


if __name__ == "__main__":
    _launch(sys.argv[1:])
