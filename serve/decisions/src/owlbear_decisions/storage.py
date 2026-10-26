"""Decision files: `<folder>/decisions/<id>.md`, YAML front matter plus the rationale as Markdown body."""

from __future__ import annotations

import contextlib
import fcntl
import os
import re
import secrets
import stat
import threading
from dataclasses import dataclass, field
from io import StringIO
from typing import TYPE_CHECKING

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from owlbear_decisions.errors import ConcurrencyError, DecisionFileError, ImmutableError
from owlbear_decisions.models import Decision, State

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

DECISIONS_DIR = "decisions"
_FENCE = "---\n"
_YAML_LOCAL = threading.local()
_TEMPORARY = re.compile(r"^\..+\.tmp$")  # `_replace`'s temporary files while a write is in flight
_IGNORED = frozenset({".DS_Store"})
# the lifecycle only moves forward; a retired decision stays retired and a successor carries any change
_NEXT = {
    State.DRAFT: {State.DRAFT, State.IN_FORCE, State.WITHDRAWN},
    State.IN_FORCE: {State.IN_FORCE, State.REPLACED, State.WITHDRAWN, State.SPENT},
    State.REPLACED: {State.REPLACED},
    State.WITHDRAWN: {State.WITHDRAWN},
    State.SPENT: {State.SPENT},
}


def _yaml() -> YAML:
    instance = getattr(_YAML_LOCAL, "instance", None)
    if instance is None:
        instance = _YAML_LOCAL.instance = YAML(typ="safe", pure=True)
        instance.default_flow_style = False
        instance.allow_unicode = True
        instance.width = 4096
        instance.sort_base_mapping_type_on_output = False
    return instance


@dataclass(frozen=True)
class FileError:
    """A file under a decisions folder that is not a valid decision; never skipped silently."""

    path: Path
    message: str
    locations: tuple[str, ...] = ()


@dataclass
class Loaded:
    """A folder's decisions by file, and the files that failed."""

    decisions: dict[Path, Decision] = field(default_factory=dict)
    errors: list[FileError] = field(default_factory=list)


def decision_path(decision: Decision, folder: Path) -> Path:
    """Where `decision` lives in the layer `folder`."""
    return folder / DECISIONS_DIR / f"{decision.id}.md"


def serialize(decision: Decision) -> str:
    """Deterministic file text: front matter in field order, then the rationale."""
    front = decision.content()
    rationale = str(front.pop("rationale"))
    stream = StringIO()
    _yaml().dump(front, stream)
    body = f"\n{rationale}\n" if rationale else ""
    return f"{_FENCE}{stream.getvalue()}{_FENCE}{body}"


def _schema_error(error: ValidationError) -> DecisionFileError:
    locations = tuple(".".join(str(p) for p in item["loc"]) or "decision" for item in error.errors())
    details = ", ".join(f"{loc}: {item['msg']}" for loc, item in zip(locations, error.errors(), strict=True))
    return DecisionFileError(f"schema: {details}", locations)


def parse(text: str) -> Decision:
    """Read decision file text; raises `DecisionFileError` with the failing field locations."""
    if not text.startswith(_FENCE) or (end := text.find(f"\n{_FENCE}", len(_FENCE) - 1)) < 0:
        msg = "front matter missing: the file must start with '---' and close it with a '---' line"
        raise DecisionFileError(msg)
    try:
        data = _yaml().load(text[len(_FENCE) : end + 1])
    except YAMLError as exc:
        msg = f"front matter is not valid YAML: {str(exc).splitlines()[0]}"
        raise DecisionFileError(msg) from exc
    if not isinstance(data, dict):
        msg = "front matter must be a mapping"
        raise DecisionFileError(msg)
    if "rationale" in data or "revision" in data:
        msg = "front matter must not hold rationale (the body) or revision (computed)"
        raise DecisionFileError(msg, tuple(k for k in ("rationale", "revision") if k in data))
    data["rationale"] = text[end + 1 + len(_FENCE) :]
    try:
        return Decision.model_validate(data)
    except ValidationError as exc:
        raise _schema_error(exc) from exc


def read(path: Path) -> Decision:
    """Read one decision file; its name must be `<id>.md`."""
    if path.is_symlink():
        msg = "symlinks are not decision files"
        raise DecisionFileError(msg)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        msg = f"unreadable: {type(exc).__name__}"
        raise DecisionFileError(msg) from exc
    decision = parse(text)
    if path.name != f"{decision.id}.md":
        msg = f"file name must be {decision.id}.md"
        raise DecisionFileError(msg, ("id",))
    return decision


def kind(path: Path) -> int | None:
    """The `lstat` mode of *path*, None when it does not exist; any other failure (a permission) raises `OSError`."""
    try:
        return path.lstat().st_mode
    except FileNotFoundError, NotADirectoryError:
        return None


def is_folder(path: Path) -> bool:
    """*path* is a real folder, not a symlink; raises `OSError` when that cannot be told."""
    return stat.S_ISDIR(kind(path) or 0)


def load_folder(folder: Path) -> Loaded:
    """Every entry of `<folder>/decisions/`; anything that is not a valid decision file is an error.

    A missing `decisions/` is an empty layer; a folder that cannot be listed raises `OSError`, never loads as empty.
    """
    loaded = Loaded()
    directory = folder / DECISIONS_DIR
    if (mode := kind(directory)) is None:
        return loaded
    if not stat.S_ISDIR(mode):
        loaded.errors.append(FileError(directory, "not a folder: decisions must be a real folder"))
        return loaded
    for path in sorted(directory.iterdir()):
        if path.name in _IGNORED or _TEMPORARY.match(path.name):
            continue
        mode = path.lstat().st_mode
        if path.suffix != ".md" or not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
            loaded.errors.append(FileError(path, "not a decision file (expected <id>.md)"))
            continue
        try:
            loaded.decisions[path] = read(path)
        except DecisionFileError as exc:
            loaded.errors.append(FileError(path, str(exc), exc.locations))
    return loaded


@contextlib.contextmanager
def _locked(directory: Path) -> Iterator[None]:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def check_write(current: Decision | None, decision: Decision, expected_revision: str | None) -> None:
    """Raise what `write` would refuse for *decision* over *current*; a batch checks every file before writing any."""
    if expected_revision is None and current is not None:
        msg = f"{decision.id} exists at revision {current.revision}; pass it as expected_revision"
        raise ConcurrencyError(msg)
    if expected_revision is not None and (current is None or current.revision != expected_revision):
        found = current.revision if current else "no file"
        msg = f"{decision.id} is at {found}, not the expected {expected_revision}"
        raise ConcurrencyError(msg)
    if current is None:
        return
    if decision.state not in _NEXT[current.state]:
        msg = f"{decision.id} cannot go from {current.state} to {decision.state}; record a successor instead"
        raise ImmutableError(msg)
    accepted = current.state is not State.DRAFT
    if accepted and (current.statement, current.origin) != (decision.statement, decision.origin):
        msg = f"{decision.id} was accepted: its statement and origin never change; record a successor that replaces it"
        raise ImmutableError(msg)


def own_temporary(folder: int, data: bytes) -> tuple[str, tuple[int, int]]:
    """Create a new temporary file in the folder open as *folder*, holding *data* durably; its name and identity.

    The file is made exclusively, never through a link, mode 0600, and named relative to *folder*, so a cleanup reaches
    this very file even when the folder's path is moved meanwhile. The identity is its device and inode.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    while True:
        name = f".{secrets.token_hex(8)}.tmp"
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=folder)
        except FileExistsError:
            continue
        break
    found = os.fstat(descriptor)
    identity = (found.st_dev, found.st_ino)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        discard_temporary(folder, name, identity)
        raise
    return name, identity


def discard_temporary(folder: int, name: str, identity: tuple[int, int]) -> None:
    """Remove the temporary file *name* in *folder*, only while it is still the one `own_temporary` made.

    A name now holding another file (someone else's) is left as it is, and a missing one needs nothing; any other error
    is raised, since whether the file is gone is then unknown.
    """
    try:
        found = os.stat(name, dir_fd=folder, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (found.st_dev, found.st_ino) == identity:
        os.unlink(name, dir_fd=folder)


def _replace(path: Path, text: str, fence: Callable[[], None] | None = None) -> None:
    folder = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        name, identity = own_temporary(folder, text.encode("utf-8"))
        try:
            if fence is not None:  # last, once the new bytes are durable: the caller's proof the file is its to change
                fence()
            os.replace(name, path.name, src_dir_fd=folder, dst_dir_fd=folder)
        except BaseException:
            discard_temporary(folder, name, identity)
            raise
        os.fsync(folder)
    finally:
        os.close(folder)


def write(
    decision: Decision, folder: Path, expected_revision: str | None = None, *, fence: Callable[[], None] | None = None
) -> str:
    """Write `decision` atomically into the layer `folder` and return its revision.

    `expected_revision=None` creates a new file and refuses an existing one; otherwise the file's
    current revision must equal it. An in-force decision's statement never changes. *fence*, when given, runs after
    the new bytes are durable and immediately before the rename; when it raises, only this write's own temporary file is
    removed, through the folder it was made in.
    """
    path = decision_path(decision, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        msg = f"{path} is a symlink"
        raise DecisionFileError(msg)
    text = serialize(decision)
    if parse(text) != decision:
        msg = f"{decision.id} does not round-trip through its file format"
        raise DecisionFileError(msg)
    with _locked(path.parent):
        current = read(path) if path.exists() else None
        check_write(current, decision, expected_revision)
        _replace(path, text, fence)
    return decision.revision
