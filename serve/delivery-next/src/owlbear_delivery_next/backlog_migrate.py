"""One-time move of the file backlog into GitHub issues (TD-103), run by ``owlbear-next backlog migrate``.

Every ``<shared>/<project>/backlog/<id>.json`` becomes one issue scoped to its project, carrying the old id as its
marker, so a second run skips what the first created. Only once every entry reads back from GitHub as it was are the
files deleted, and that deletion is committed and pushed; a file changed meanwhile stays.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, NamedTuple

from pydantic import ValidationError

from owlbear_delivery_next.backlog import Backlog, BacklogError, Entry

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.common import Common

FOLDER = "backlog"
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


def _created(backlog: Backlog, files: dict[str, File], say: Callable[[str], None]) -> None:
    """Open an issue for each file entry that has none, then connect them as their files were."""
    have = {e.legacy: e.id for e in backlog.read(fresh=True)[0].values() if e.legacy}
    for legacy, file in files.items():
        if legacy in have:
            say(f"already #{have[legacy]}: {legacy} {file.entry.title}")
            continue
        have[legacy] = backlog.put(file.entry).id
        say(f"created #{have[legacy]}: {legacy} {file.entry.title}")
    for legacy, file in files.items():
        wanted = [have[i] for i in file.links if i in have]
        if file.links and backlog.read(fresh=True)[0][have[legacy]].links != wanted:
            backlog.update(have[legacy], {"links": wanted})


def _wrong(backlog: Backlog, files: dict[str, File]) -> list[str]:
    """What differs between each file entry and its issue as GitHub returns it now."""
    issues = {e.legacy: e for e in backlog.read(fresh=True)[0].values() if e.legacy}
    numbers = {legacy: e.id for legacy, e in issues.items()}
    wrong = []
    for legacy, file in files.items():
        if (issue := issues.get(legacy)) is None:
            wrong.append(f"{legacy}: no issue")
            continue
        fields = [f for f in COMPARED if getattr(issue, f) != getattr(file.entry, f)]
        if issue.links != [numbers.get(i, i) for i in file.links]:
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
        _created(backlog, files, say)
        if wrong := _wrong(backlog, files):
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
        for folder in {path.parent for path in gone}:
            if not [p for p in folder.iterdir() if p.name != ".backlog.lock"]:
                (folder / ".backlog.lock").unlink(missing_ok=True)
                folder.rmdir()
        return gone, shared.publish(gone, f"backlog: {len(gone)} entries moved to GitHub issues (TD-103)")
