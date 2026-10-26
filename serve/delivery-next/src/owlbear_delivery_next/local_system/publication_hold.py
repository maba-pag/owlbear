"""An automatic change bound to the shared remote's state until the remote has it (R15, FND-01).

Some automatic changes stand only while the shared remote still holds what they were prepared against: the legacy
preference import fills the project config only under its own pending claim. Before such a change is written, its
checkout records in its own Git folder what the remote must hold: the changed file's blob on the remote it just caught
up with, and the fields another file must keep. While that record stands, nothing in the checkout is pushed or rebased
before the freshly fetched remote is checked against it, so a push, which Git accepts only as a fast-forward, lands on
the very revision that was checked. A remote that no longer meets the record holds the checkout: nothing is pushed or
rebased, the refusal is kept in the record and reported, and nothing in Git is undone. The record lapses once the remote
has the change or the checkout no longer does.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo

RECORD = "owlbear-held-publication.json"
ABSENT = "absent"
UPSTREAM = "@{upstream}"
_KEYS = ("watch", "base", "file", "fields", "what")


@dataclass(frozen=True)
class Requires:
    """The *fields* the shared remote's copy of *path* must still hold, described for the owner as *what*."""

    path: Path
    fields: Mapping[str, str | None]
    what: str


class _UnknownError(Exception):
    """Git could not say what the checkout or the remote holds: nothing is pushed or rebased."""


def _run(repo: DataRepo, until: float | None, *args: str) -> str:
    said = repo.git(*args, until=until)
    if said.returncode:
        raise _UnknownError(said.stderr.strip()[:200] or f"git {args[0]} failed")
    return said.stdout


def _path(repo: DataRepo, until: float | None) -> Path:
    named = _run(repo, until, "rev-parse", "--git-path", RECORD).strip()
    if not named:
        msg = "git named no folder for the held publication record"
        raise _UnknownError(msg)
    return repo.root / named  # relative to the checkout, unless Git named it absolute


def _load(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        msg = f"the held publication record {path} cannot be read ({exc}); check it before removing it"
        raise _UnknownError(msg) from exc
    if not isinstance(data, dict) or any(key not in data for key in (*_KEYS, "filled", "refused")):
        msg = f"the held publication record {path} is incomplete; check it before removing it"
        raise _UnknownError(msg)
    return data


def _rel(repo: DataRepo, path: Path) -> str:
    return path.relative_to(repo.root).as_posix()


def _blob(repo: DataRepo, rel: str, until: float | None) -> str:
    """The blob the checkout's copy of *rel* would be; ``absent`` when there is none."""
    if not (repo.root / rel).exists():
        return ABSENT
    return _run(repo, until, "hash-object", "--", rel).strip()


def _blob_at(repo: DataRepo, rev: str, rel: str, until: float | None) -> str:
    """The blob *rel* is at *rev*; ``absent`` when *rev* lists none."""
    listed = _run(repo, until, "ls-tree", rev, "--", rel).split()
    if not listed:
        return ABSENT
    if len(listed) < 4 or listed[1] != "blob":  # noqa: PLR2004 - mode, type, object, path
        msg = f"{rel} at {rev[:12]} is no file"
        raise _UnknownError(msg)
    return listed[2]


def recorded(repo: DataRepo, until: float | None) -> bool:
    """Whether a held change is recorded here; a record Git cannot locate counts as one."""
    try:
        return _path(repo, until).exists()
    except _UnknownError:
        return True


def hold(repo: DataRepo, watch: Path, requires: Requires, until: float | None) -> None:
    """Record, before the automatic change of *watch* is written, what the remote must hold for it to be published.

    An earlier record of the same requirements stays; one of others is refused, so no requirement is ever dropped.
    """
    from owlbear_delivery_next.local_system.data_repo import DataRepoError  # noqa: PLC0415 - it imports this module

    try:
        path = _path(repo, until)
        want = {
            "watch": _rel(repo, watch),
            "base": _blob_at(repo, UPSTREAM, _rel(repo, watch), until),  # the remote's, just caught up with
            "file": _rel(repo, requires.path),
            "fields": dict(requires.fields),
            "what": requires.what,
        }
        held = _load(path)
    except _UnknownError as exc:
        msg = f"the automatic change was not written: {exc}"
        raise DataRepoError(msg) from exc
    if held is None:
        atomic_write(path, json.dumps({**want, "filled": "", "refused": ""}))
    elif {key: held[key] for key in _KEYS} != want:
        why = held["refused"] or "it is not pushed yet"
        msg = f"an earlier automatic change of {held['watch']} in {repo.root} is still held: {why}"
        raise DataRepoError(msg)


def filled(repo: DataRepo, watch: Path, until: float | None) -> None:
    """Note the blob the held change wrote to *watch*: once the remote has that blob, the change is published."""
    from owlbear_delivery_next.local_system.data_repo import DataRepoError  # noqa: PLC0415 - it imports this module

    try:
        path = _path(repo, until)
        held = _load(path)
        if held is not None and held["watch"] == _rel(repo, watch):
            atomic_write(path, json.dumps({**held, "filled": _blob(repo, _rel(repo, watch), until)}))
    except _UnknownError as exc:
        msg = f"the automatic change was written, but not noted as held: {exc}"
        raise DataRepoError(msg) from exc


def _lapsed(repo: DataRepo, held: Mapping[str, object], until: float | None) -> bool:
    """Whether the remote has the held change, or the checkout no longer has any change of its file the remote lacks."""
    watch = str(held["watch"])
    remote = _blob_at(repo, UPSTREAM, watch, until)
    if remote == held["filled"]:
        return True
    ahead = _run(repo, until, "log", "--format=%h", f"{UPSTREAM}..HEAD", "--", watch).strip()
    return not ahead and _blob(repo, watch, until) == remote


def _unmet(repo: DataRepo, held: Mapping[str, object], until: float | None) -> str:
    """Why the fetched remote no longer meets the record; nothing when it does."""
    watch, rel, fields = str(held["watch"]), str(held["file"]), held["fields"]
    if _blob_at(repo, UPSTREAM, watch, until) != held["base"]:
        return f"{watch} changed on the shared remote after the change was prepared"
    if _blob_at(repo, UPSTREAM, rel, until) == ABSENT:
        return f"{rel} is gone from the shared remote"
    try:
        data = json.loads(_run(repo, until, "show", f"{UPSTREAM}:{rel}"))
    except UnicodeDecodeError:  # Git's text output of a blob that is not UTF-8: no field of it can be proven
        return f"{rel} on the shared remote is unreadable: it is not UTF-8"
    except ValueError:
        return f"{rel} on the shared remote is unreadable"
    if not isinstance(data, dict) or not isinstance(fields, dict) or any(data.get(k) != v for k, v in fields.items()):
        return f"{held['what']} no longer stands on the shared remote"
    return ""


def check(repo: DataRepo, until: float | None, *, fetch: bool) -> str:
    """Why nothing may be pushed or rebased here; nothing when no change is held or the remote still meets the record.

    The remote is fetched first when *fetch*. A refusal is kept in the record; a lapsed record is removed.
    """
    try:
        path = _path(repo, until)
        held = _load(path)
        if held is None:
            return ""
        if fetch:
            _run(repo, until, "fetch", "-q")
        if _lapsed(repo, held, until):
            path.unlink(missing_ok=True)
            return ""
        why = _unmet(repo, held, until)
        ahead = _run(repo, until, "log", "--format=%h", f"{UPSTREAM}..HEAD", "--", str(held["watch"])).split()
    except _UnknownError as exc:
        return f"nothing was pushed or rebased in {repo.root}: a held automatic change cannot be checked: {exc}"
    if why != held["refused"]:
        atomic_write(path, json.dumps({**held, "refused": why}))
    if not why:
        return ""
    commits = ", ".join(ahead) or "none, the change is uncommitted"
    return (
        f"nothing was pushed or rebased in {repo.root}: its automatic change of {held['watch']} is held because {why}; "
        f"remove that change from the checkout (unpushed commits changing it: {commits}), then save again"
    )


def settled(repo: DataRepo, until: float | None) -> None:
    """Remove the record once a push gave the remote the held change, or left the checkout without one; never checks."""
    try:
        path = _path(repo, until)
        held = _load(path)
        if held is not None and _lapsed(repo, held, until):
            path.unlink(missing_ok=True)
    except _UnknownError:
        return  # the record stays, and the next push or rebase checks it again


def refusal(repo: DataRepo, until: float | None) -> str:
    """The kept refusal of a held change; nothing when none is held, it was not refused, or the record lapsed."""
    try:
        path = _path(repo, until)
        held = _load(path)
        if held is None or not held["refused"]:
            return ""
        if _lapsed(repo, held, until):
            path.unlink(missing_ok=True)
            return ""
    except _UnknownError as exc:
        return str(exc)
    return str(held["refused"])
