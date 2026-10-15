"""One-time move of the file backlog into GitHub issues (TD-103), run by ``owlbear-next backlog migrate``.

Every ``<shared>/<project>/backlog/<id>.json`` becomes one issue scoped to its project, carrying the old id as its
marker. Each issue's number is noted in a journal at the shared checkout's root (kept out of git) as soon as GitHub
confirms it, so a later run, even in a fresh process, reads those issues directly instead of trusting a listing that
shows a new issue only seconds later. Only once every entry reads back from GitHub as it was are the files deleted,
with the journal, and that deletion is committed and pushed; a file changed meanwhile stays.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, NamedTuple

from pydantic import ValidationError

from owlbear_delivery_next.backlog import Backlog, BacklogError, Entry
from owlbear_delivery_next.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.common import Common

FOLDER = "backlog"
JOURNAL = ".backlog-migration.json"  # old id -> issue number; common.EXCLUDE keeps it out of git
COMPARED = ("title", "text", "source", "kind", "status", "scope", "project", "notes", "evidence", "change", "launch")
COMPARED += ("count", "first_seen", "last_seen")


class File(NamedTuple):
    """One file entry: where it is, its bytes as read, the entry it becomes, and its links by old id."""

    path: Path
    data: bytes
    entry: Entry
    links: list[str]


def _files(shared: Common, say: Callable[[str], None]) -> dict[str, File] | None:
    """Each file entry by its old id, as an entry of its project; None when one cannot be read."""
    found = {}
    for path in sorted(shared.root.glob(f"*/{FOLDER}/*.json")):
        data = path.read_bytes()
        try:
            old = json.loads(data)
            moved = {"id": "1", "legacy": old["id"], "scope": "project", "project": path.parent.parent.name}
            entry = Entry.model_validate(old | moved | {"links": []})
            links = [str(i) for i in old["links"]]
        except (ValueError, KeyError, TypeError, AttributeError, ValidationError) as exc:
            say(f"unreadable: {path.relative_to(shared.root)} ({exc}); fix or remove it, then run again")
            return None
        if entry.legacy != path.stem or entry.legacy in found:
            say(f"unreadable: {path.relative_to(shared.root)} does not hold the entry {path.stem} alone")
            return None
        found[entry.legacy] = File(path, data, entry, links)
    return found


class Journal:
    """The issue number of each file entry, noted as soon as GitHub confirmed the issue."""

    def __init__(self, shared: Common) -> None:
        """Read the journal an earlier run left, under the lock that also keeps it out of git."""
        self.path = shared.root / JOURNAL
        with shared.locked():
            try:
                self.numbers: dict[str, str] = json.loads(self.path.read_text()) if self.path.exists() else {}
            except ValueError as exc:
                raise BacklogError(409, f"{JOURNAL} is unreadable ({exc}); check the issues, then fix it") from exc

    def note(self, legacy: str, number: str) -> None:
        """Keep one confirmed number before anything else happens."""
        self.numbers[legacy] = number
        atomic_write(self.path, json.dumps(self.numbers, indent=1, sort_keys=True) + "\n")


def _created(backlog: Backlog, files: dict[str, File], journal: Journal, say: Callable[[str], None]) -> dict[str, str]:
    """Open an issue for each file entry that has none, then connect them as their files were; each one's number.

    A number the journal holds is read directly, so a listing that lags never makes a second issue.
    """
    listed = {e.legacy: e.id for e in backlog.read(fresh=True)[0].values() if e.legacy}
    have: dict[str, str] = {}
    for legacy, file in files.items():
        noted = journal.numbers.get(legacy)
        if noted and (issue := backlog.current(noted)) is not None:
            if issue.legacy != legacy:
                raise BacklogError(409, f"#{noted} holds no entry {legacy}, which {JOURNAL} gives it; check it")
            have[legacy] = noted
        elif legacy in listed:
            have[legacy] = listed[legacy]
        else:
            have[legacy] = backlog.put(file.entry, made=lambda n, legacy=legacy: journal.note(legacy, n)).id
            say(f"created #{have[legacy]}: {legacy} {file.entry.title}")
            continue
        say(f"already #{have[legacy]}: {legacy} {file.entry.title}")
    for legacy, file in files.items():
        wanted = [have[i] for i in file.links if i in have]
        if file.links and getattr(backlog.current(have[legacy]), "links", None) != wanted:
            backlog.update(have[legacy], {"links": wanted})
    return have


def _wrong(backlog: Backlog, files: dict[str, File], have: dict[str, str]) -> list[str]:
    """What differs between each file entry and its issue as GitHub returns it now, read directly."""
    wrong = []
    for legacy, file in files.items():
        if (issue := backlog.current(have[legacy])) is None or issue.legacy != legacy:
            wrong.append(f"{legacy}: no issue")
            continue
        fields = [f for f in COMPARED if getattr(issue, f) != getattr(file.entry, f)]
        if issue.links != [have.get(i, i) for i in file.links]:
            fields.append("links")
        wrong += [f"{legacy} (#{issue.id}): {', '.join(fields)} differ"] if fields else []
    return wrong


def migrate(shared: Common, say: Callable[[str], None]) -> int:
    """Move every file entry into an issue, verify them all, then delete and publish the files; 0 when done."""
    files = _files(shared, say)
    if files is None:
        return 1
    if not files:
        say("no file entries to migrate")
        return 0
    try:
        backlog = Backlog(shared)
        have = _created(backlog, files, Journal(shared), say)
        if wrong := _wrong(backlog, files, have):
            say("not verified, no file deleted: " + "; ".join(wrong))
            return 1
    except BacklogError as exc:
        say(f"stopped, no file deleted: {exc.text}")
        return 1
    gone, notice = _delete(shared, files, say)
    say(f"verified {len(files)} issues in {backlog.repository}; deleted {len(gone)} files")
    if notice:
        say(notice)
    return 1 if notice or len(gone) != len(files) else 0


def _delete(shared: Common, files: dict[str, File], say: Callable[[str], None]) -> tuple[list[Path], str]:
    """Delete the files still as they were read, then commit and push that; the deleted files and the notice."""
    with shared.locked():
        gone = [f.path for f in files.values() if f.path.exists() and f.path.read_bytes() == f.data]
        for path in [f.path for f in files.values() if f.path not in gone]:
            say(f"kept: {path.relative_to(shared.root)} changed while it was migrated")
        for path in gone:
            path.unlink()
        if len(gone) == len(files):  # every issue is verified: nothing more to reconcile
            (shared.root / JOURNAL).unlink(missing_ok=True)
        for folder in {path.parent for path in gone}:
            if not [p for p in folder.iterdir() if p.name != ".backlog.lock"]:
                (folder / ".backlog.lock").unlink(missing_ok=True)
                folder.rmdir()
        return gone, shared.publish(gone, f"backlog: {len(gone)} entries moved to GitHub issues (TD-103)")
