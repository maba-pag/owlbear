"""An automatic change bound to the shared remote's state until the remote has it (R15, FND-01).

Some automatic changes stand only while the shared remote still holds what they were prepared against: the legacy
preference import fills the project config only under its own pending claim, and the role move only over the config it
read. Before such a change is written, its checkout records in its own Git folder what the remote must hold: the
upstream commit it just caught up with, after which no remote commit may change the file (one that changed and changed
back still did), that file's blob, and, when named, the fields another file must keep. While that record stands, nothing
in the checkout is pushed or rebased before the freshly fetched remote is checked against it, and a push runs only as
one non-forced refspec to that same upstream branch, so Git accepts it only as a fast-forward of the very revision that
was checked. Every push of the checkout runs so, held or not: an automatic publication that follows a retired record
never falls back to a configured forced push. A remote that no longer meets the record holds the checkout: nothing is
pushed or rebased, the refusal is kept in the record and reported, and nothing in Git is undone. The record lapses only
once the checkout itself holds no change of the file the remote lacks: no unpushed commit touches it and its copies are
the committed one. A record that cannot be read or is malformed is kept as it is and holds.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo

RECORD = "owlbear-held-publication.json"
ABSENT = "absent"
UPSTREAM = "@{upstream}"
_KEYS = ("watch", "base", "since", "file", "fields", "what")
_RECORD_KEYS = frozenset((*_KEYS, "refused"))
_EXPLICIT = 2  # an explicit push: one remote and one source:destination
_BLOB = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


@dataclass(frozen=True)
class Requires:
    """What the shared remote must still hold, described for the owner as *what*.

    The changed file's own remote blob is always bound. *path* and *fields*, both or neither, add the fields the
    remote's copy of another file must keep, such as a claim.
    """

    what: str
    path: Path | None = None
    fields: Mapping[str, str | None] | None = None

    def __post_init__(self) -> None:
        """A file and its fields are named together, and the fields are never empty."""
        if (self.path is None) != (self.fields is None) or self.fields == {}:
            msg = "a held change requires a file and non-empty fields together, or neither"
            raise ValueError(msg)


class _UnknownError(Exception):
    """Git could not say what the checkout or the remote holds: nothing is pushed or rebased."""


def _run(repo: DataRepo, until: float | None, *args: str) -> str:
    said = repo.git(*args, until=until)
    if said.returncode:
        raise _UnknownError(said.stderr.strip()[:200] or f"git {args[0]} failed")
    return said.stdout


def _lines(out: str, what: str) -> list[str]:
    """Git's newline-terminated values, each kept whole, spaces included; output Git did not terminate is unknown."""
    if not out.endswith("\n"):
        msg = f"git printed no complete {what}"
        raise _UnknownError(msg)
    return out[:-1].split("\n")


def _path(repo: DataRepo, until: float | None) -> Path:
    named = _run(repo, until, "rev-parse", "--git-path", RECORD).strip()
    if not named:
        msg = "git named no folder for the held publication record"
        raise _UnknownError(msg)
    return repo.root / named  # relative to the checkout, unless Git named it absolute


def _safe(rel: object) -> bool:
    """Whether *rel* names a file inside the checkout, outside its Git folder, the way a record writes it."""
    if not isinstance(rel, str) or any(c == "\\" or ord(c) < 0x20 for c in rel):  # noqa: PLR2004 - control chars
        return False
    parts = rel.split("/")  # split as written: a normalizing parser would drop empty and "." parts
    return parts[0] != ".git" and all(p not in ("", ".", "..") for p in parts)


def _malformed(data: object) -> str:
    """What makes *data* no record this module writes; nothing when it is one."""
    if not isinstance(data, dict) or set(data) != _RECORD_KEYS:
        return f"its keys are not exactly {', '.join(sorted(_RECORD_KEYS))}"
    bound = not (data["file"] is None and data["fields"] is None)  # a file and its fields, or neither
    if not _safe(data["watch"]) or (bound and not _safe(data["file"])):
        return "a file it names is not a plain path inside the checkout"
    base, since = data["base"], data["since"]
    if not (isinstance(base, str) and (base == ABSENT or _BLOB.fullmatch(base))):
        return "its base is not a Git blob or absent"
    if not (isinstance(since, str) and _BLOB.fullmatch(since)):
        return "its upstream commit is not a Git object name"
    fields = data["fields"]
    if bound and (
        not isinstance(fields, dict)
        or not fields
        or not all(isinstance(k, str) and (v is None or isinstance(v, str)) for k, v in fields.items())
    ):
        return "its fields are not a non-empty map of text"
    texts = isinstance(data["what"], str) and data["what"] and isinstance(data["refused"], str)
    return "" if texts else "its description or refusal is not text"


def _load(path: Path) -> dict[str, object] | None:
    """The record as written; a record that cannot be read or is malformed stays, byte for byte, and holds."""
    try:
        data = json.loads(path.read_bytes())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        msg = f"the held publication record {path} cannot be read ({exc}); check it before removing it"
        raise _UnknownError(msg) from exc
    if why := _malformed(data):
        msg = f"the held publication record {path} is malformed: {why}; check it before removing it"
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
            "since": _run(repo, until, "rev-parse", "--verify", f"{UPSTREAM}^{{commit}}").strip(),
            "file": None if requires.path is None else _rel(repo, requires.path),
            "fields": None if requires.fields is None else dict(requires.fields),
            "what": requires.what,
        }
        held = _load(path)
    except _UnknownError as exc:
        msg = f"the automatic change was not written: {exc}"
        raise DataRepoError(msg) from exc
    if held is None:
        atomic_write(path, json.dumps({**want, "refused": ""}))
    elif {key: held[key] for key in _KEYS} != want:
        why = held["refused"] or "it is not pushed yet"
        msg = f"an earlier automatic change of {held['watch']} in {repo.root} is still held: {why}"
        raise DataRepoError(msg)


def _lapsed(repo: DataRepo, held: Mapping[str, object], until: float | None) -> bool:
    """Whether the checkout no longer holds any change of the watched file that the remote lacks.

    Only the checkout's own history and copies prove it: no commit the remote lacks changes the file, in the full
    history with every side of a merge, and its index and working copy are the committed one. Equal bytes on the remote
    prove nothing, and neither does a merge or revert that undoes the change: a rebase replays each commit, so the
    change could still be pushed after the remote changed the file again.
    """
    watch = str(held["watch"])
    if _changes(repo, watch, until):
        return False
    staged = repo.git("diff", "--cached", "--quiet", "HEAD", "--", watch, until=until)
    if staged.returncode not in (0, 1):
        raise _UnknownError(staged.stderr.strip()[:200] or "git could not compare the index")
    return staged.returncode == 0 and _blob(repo, watch, until) == _blob_at(repo, "HEAD", watch, until)


def _changes(repo: DataRepo, watch: str, until: float | None) -> list[str]:
    """The commits the remote lacks that change *watch*, merges included; history simplification hides none."""
    return _run(repo, until, "log", "--full-history", "--format=%h", f"{UPSTREAM}..HEAD", "--", watch).split()


def _unmet(repo: DataRepo, held: Mapping[str, object], until: float | None) -> str:
    """Why the fetched remote no longer meets the record; nothing when it does."""
    watch, rel, since = str(held["watch"]), held["file"], str(held["since"])
    kept = repo.git("merge-base", "--is-ancestor", since, UPSTREAM, until=until)
    if kept.returncode not in (0, 1):
        raise _UnknownError(kept.stderr.strip()[:200] or "git could not compare the remote's history")
    if kept.returncode:
        return f"the shared remote's history no longer holds {since[:12]}, where the change was prepared"
    # every commit since, merges included: a file that changed and changed back still changed (no bytes-only proof)
    if _run(repo, until, "log", "--full-history", "--format=%h", f"{since}..{UPSTREAM}", "--", watch).strip():
        return f"{watch} changed on the shared remote after the change was prepared"
    if _blob_at(repo, UPSTREAM, watch, until) != held["base"]:
        return f"{watch} changed on the shared remote after the change was prepared"
    return _kept(repo, rel, held["fields"], str(held["what"]), until) if isinstance(rel, str) else ""


def _kept(repo: DataRepo, rel: str, fields: object, what: str, until: float | None) -> str:
    """Why the remote's copy of *rel* no longer holds *fields*; nothing when it does."""
    if _blob_at(repo, UPSTREAM, rel, until) == ABSENT:
        return f"{rel} is gone from the shared remote"
    try:
        data = json.loads(_run(repo, until, "show", f"{UPSTREAM}:{rel}"))
    except UnicodeDecodeError:  # Git's text output of a blob that is not UTF-8: no field of it can be proven
        return f"{rel} on the shared remote is unreadable: it is not UTF-8"
    except ValueError:
        return f"{rel} on the shared remote is unreadable"
    if not isinstance(data, dict) or not isinstance(fields, dict) or any(data.get(k) != v for k, v in fields.items()):
        return f"{what} no longer stands on the shared remote"
    return ""


def _target(repo: DataRepo, push: Sequence[str], until: float | None, *, held: bool) -> tuple[str, tuple[str, ...]]:
    """Why the git *push* may land elsewhere than the upstream branch the record was checked on, else the push to run.

    Git itself resolves where a plain push goes (``branch.<name>.pushRemote``, ``remote.pushDefault``,
    ``push.default``); an explicit push names one remote and one ``source:destination``. Any other form cannot be
    proven, and a remote whose push address differs from the one fetched from may be another repository. A plain push
    runs as the one non-forced refspec it was proven to be, ``HEAD:<upstream branch>``: configured push refspecs, a
    forced ``+`` one or ``push.default=matching``'s other branches, apply only to a plain push. With no change *held*,
    an explicit non-forced push may go to the branch its caller captured, such as a decision publication's own target,
    whatever branch is checked out by then; a held change's push must land on the upstream it was checked on.
    """
    branch = _run(repo, until, "symbolic-ref", "-q", "HEAD").strip()
    atoms = "%(upstream:remotename)%00%(upstream:remoteref)%00%(push:remotename)"
    said = _lines(_run(repo, until, "for-each-ref", f"--format={atoms}", branch), "branch")
    up_remote, up_ref, remote = [*said[0].split("\0"), "", "", ""][:3] if len(said) == 1 else ("", "", "")
    words = [a for a in push[1:] if a != "-q"]
    if words:  # an explicit push: exactly one remote and one source:destination, never forced
        if (
            len(words) != _EXPLICIT
            or words[0].startswith("-")
            or ":" not in words[1]
            or words[1].startswith(("-", "+"))
        ):
            return f"its push ({' '.join(push)}) names no single remote and branch to check", ()
        remote, ref = words[0], words[1].split(":", 1)[1]
        lands = (remote, ref) == (up_remote, up_ref) or (not held and bool(ref))
    else:  # Git's own resolution of where this branch pushes, as a remote-tracking branch like its upstream
        ref = _run(repo, until, "rev-parse", "--symbolic-full-name", "@{push}").strip()
        lands = remote == up_remote and ref == _run(repo, until, "rev-parse", "--symbolic-full-name", UPSTREAM).strip()
    captured = bool(words) and not held  # an explicit push with nothing held names its own destination
    if not (lands and (captured or (up_remote and up_ref))):
        goes = f"{remote or 'no remote'} ({ref or 'no branch'})"
        return f"would be pushed to {goes}, not to its upstream {up_remote} {up_ref} where it was checked", ()
    fetched = _lines(_run(repo, until, "remote", "get-url", remote), "remote address")
    pushed = _lines(_run(repo, until, "remote", "get-url", "--push", "--all", remote), "push address")
    if len(fetched) != 1 or not fetched[0] or pushed != fetched:  # whole values, compared exactly: one address
        return f"the push address of {remote} is not exactly the one address its state was read from", ()
    return "", tuple(push) if words else ("push", "-q", up_remote, f"HEAD:{up_ref}")


def check(repo: DataRepo, until: float | None, *, fetch: bool) -> str:
    """Why nothing may be pushed or rebased here; nothing when no change is held or the remote still meets the record.

    The remote is fetched first when *fetch*. A refusal is kept in the record; a lapsed record is removed.
    """
    return _checked(repo, until, fetch=fetch, push=())[0]


def pushing(repo: DataRepo, push: Sequence[str], until: float | None) -> tuple[str, tuple[str, ...]]:
    """Why the git *push* may not run, after fetching and checking as `check` does; else the push to run.

    Plain and held pushes must land on the checked upstream. With nothing held, an explicit non-forced push may
    name its caller's captured destination. A plain push still runs as one non-forced refspec after a hold retires:
    configured forced or matching pushes cannot overwrite another checkout's work.
    """
    return _checked(repo, until, fetch=True, push=tuple(push))


def _bound(repo: DataRepo, push: tuple[str, ...], until: float | None) -> tuple[str, tuple[str, ...]]:
    """The checked, non-forced push with nothing held: plain to the upstream, explicit to its captured destination."""
    if not push:
        return "", push
    try:
        why, run = _target(repo, push, until, held=False)
    except _UnknownError as exc:
        why, run = f"its destination cannot be told: {exc}", ()
    return (f"nothing was pushed from {repo.root}: this push {why}", ()) if why else ("", run)


def _checked(repo: DataRepo, until: float | None, *, fetch: bool, push: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    try:
        path = _path(repo, until)
        held = _load(path)
        if held is None:
            return _bound(repo, push, until)
        if fetch:
            _run(repo, until, "fetch", "-q")
        if _lapsed(repo, held, until):
            path.unlink(missing_ok=True)
            return _bound(repo, push, until)
        why = _unmet(repo, held, until)
        ahead = _changes(repo, str(held["watch"]), until)
        elsewhere, run = _target(repo, push, until, held=True) if push and not why else ("", push)
    except _UnknownError as exc:
        return f"nothing was pushed or rebased in {repo.root}: a held automatic change cannot be checked: {exc}", ()
    if why != held["refused"]:
        atomic_write(path, json.dumps({**held, "refused": why}))
    if elsewhere:
        return f"nothing was pushed from {repo.root}: its held automatic change of {held['watch']} {elsewhere}", ()
    if not why:
        return "", run
    commits = ", ".join(ahead) or "none, the change is uncommitted"
    return (
        f"nothing was pushed or rebased in {repo.root}: its automatic change of {held['watch']} is held because {why}; "
        f"remove that change from the checkout (unpushed commits changing it: {commits}), then save again"
    ), ()


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
