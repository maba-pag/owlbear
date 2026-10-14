"""Improvement backlog (TD-84): what the owner, the watcher, the assistant, reviews and runs found, one file per entry.

Entries live in the project's folder of the shared repository (``<shared>/<project>/backlog/<id>.json``), else in the
clone's store. A finding seen again counts up its entry instead of adding one; untriaged entries form the inbox.
Every write holds the shared repository's lock, then commits and pushes the whole folder, so an entry whose
publication failed goes out with the next write.
"""

from __future__ import annotations

import contextlib
import os
import re
import secrets
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery_next import common
from owlbear_delivery_next.storage_io import atomic_write, open_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from owlbear_delivery_next.common import Common
    from owlbear_delivery_next.store import Store

BACKLOG = "backlog"
ID = r"^\d{8}-[0-9a-f]{6}$"  # the day it was first seen, then random: sortable and short
EVIDENCE = 50  # references kept per entry, the newest
type Source = Literal["owner", "watcher", "assistant", "review", "run"]
type Kind = Literal["untriaged", "defect", "improvement", "idea", "question"]
type Status = Literal["inbox", "open", "in-change", "done", "dropped"]
type Ref = Annotated[str, Field(min_length=1, max_length=500)]
ORDER = {"inbox": 0, "open": 1, "in-change": 2, "done": 3, "dropped": 4}


class BacklogError(Exception):
    """An unknown entry or a refused field; ``status`` is the HTTP answer."""

    def __init__(self, status: int, text: str) -> None:
        """Keep the HTTP status and the owner's reason."""
        super().__init__(text)
        self.status, self.text = status, text


class Entry(BaseModel):
    """One backlog entry as its file holds it."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID)
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(default="", max_length=4000)
    source: Source
    kind: Kind = "untriaged"
    status: Status = "inbox"
    notes: str = Field(default="", max_length=4000)  # the owner's context
    links: list[str] = Field(default_factory=list, max_length=50)
    evidence: list[Ref] = Field(default_factory=list, max_length=EVIDENCE)
    change: str = ""  # the Change's slug once the entry went into one
    launch: str = ""  # the New Change launch that took the entry
    count: int = Field(default=1, ge=1)
    first_seen: datetime
    last_seen: datetime
    updated_at: datetime


def key(source: str, title: str) -> str:
    """What makes two findings the same: their source and their title's words, case and punctuation aside."""
    return f"{source}:{' '.join(re.findall(r'\w+', title.casefold()))}"


def ordered(entries: Iterable[Entry]) -> list[Entry]:
    """The inbox, then open entries, then the rest; the most recently seen first in each."""
    return sorted(entries, key=lambda e: (ORDER[e.status], -e.last_seen.timestamp()))


def _valid(fields: dict[str, Any]) -> Entry:
    try:
        return Entry.model_validate(fields)
    except ValidationError as exc:
        error = exc.errors(include_url=False)[0]
        raise BacklogError(422, f"{'.'.join(map(str, error['loc']))}: {error['msg']}") from exc


def _staged(folder: Path, content: str) -> Path:
    """A fsynced ``.tmp-*`` file in ``folder`` holding ``content``, ready to be renamed into place."""
    fd, name = tempfile.mkstemp(dir=folder, prefix=".tmp-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name)


def _sync(folder: Path) -> None:
    fd = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Backlog:
    """The project's backlog folder."""

    def __init__(self, folder: Path, shared: Common | None = None, clock: Callable[[], datetime] | None = None) -> None:
        """Entries in ``folder``, published to ``shared`` when the folder is in it."""
        self.folder, self.shared = folder, shared
        self.clock = clock or (lambda: datetime.now(UTC))

    @classmethod
    def of(cls, store: Store, clock: Callable[[], datetime] | None = None) -> Backlog:
        """The backlog in the project's shared folder, else in the clone's store."""
        folder = store.shared.root / store.name / BACKLOG if store.shared else store.root / BACKLOG
        return cls(folder, store.shared, clock)

    def read(self) -> tuple[dict[str, Entry], list[str]]:
        """Every readable entry by id, and the names of the files that are not one."""
        found, bad = {}, []
        for path in sorted(self.folder.glob("*.json")) if self.folder.is_dir() else []:
            try:
                entry = Entry.model_validate_json(path.read_bytes())
            except OSError, ValidationError:
                bad.append(path.name)
                continue
            if entry.id != path.stem:
                bad.append(path.name)
                continue
            found[entry.id] = entry
        return found, bad

    def entries(self) -> list[Entry]:
        """The readable entries in the page's order."""
        return ordered(self.read()[0].values())

    def add(
        self, title: str, text: str = "", source: Source = "owner", evidence: Iterable[str] = ()
    ) -> tuple[Entry, bool, str]:
        """Add a finding, or count up the entry it repeats; the entry, whether it is new, the publication notice."""
        refs = list(dict.fromkeys(r.strip() for r in evidence if r.strip()))

        def work(found: dict[str, Entry], now: datetime) -> tuple[tuple[Entry, bool], str]:
            same = next((e for e in found.values() if key(e.source, e.title) == key(source, title)), None)
            if same is None:
                fields = {"id": self._new_id(found, now), "title": title.strip(), "text": text.strip()}
                fields |= {"source": source, "evidence": refs[-EVIDENCE:]}
                entry = _valid(fields | {"first_seen": now, "last_seen": now, "updated_at": now})
            else:
                more = same.evidence + [r for r in refs if r not in same.evidence]
                seen = {"count": same.count + 1, "last_seen": now, "updated_at": now, "evidence": more[-EVIDENCE:]}
                entry = _valid(same.model_dump() | seen)
            self._write(entry)
            return (entry, same is None), f"{'add' if same is None else 'seen again'} {entry.id} {entry.title}"

        (entry, new), notice = self._apply(work)
        return entry, new, notice

    def update(self, entry_id: str, fields: dict[str, Any]) -> tuple[Entry, str]:
        """Set the owner's fields; classifying an inbox entry opens it, and a link holds on both entries."""

        def work(found: dict[str, Entry], now: datetime) -> tuple[Entry, str]:
            old = self._get(found, entry_id)
            new = old.model_dump() | fields | {"updated_at": now}
            if fields.get("kind", "untriaged") != "untriaged" and old.status == "inbox" and "status" not in fields:
                new["status"] = "open"
            others = []
            if "links" in fields:
                new["links"] = links = list(dict.fromkeys(fields["links"]))
                if bad := [i for i in links if i not in found or i == entry_id]:
                    raise BacklogError(422, f"links: {', '.join(bad)} is not another entry of this backlog")
                for other in sorted((set(links) ^ set(old.links)) & found.keys()):
                    theirs = [i for i in found[other].links if i != entry_id] + ([entry_id] if other in links else [])
                    others.append(_valid(found[other].model_dump() | {"links": theirs, "updated_at": now}))
            entry = _valid(new)
            self._write(entry, *others)
            return entry, f"update {entry.id} {entry.title}"

        return self._apply(work)

    def take(self, ids: list[str], launch: str) -> tuple[list[Entry], str]:
        """Mark the entries as going into the Change the launch shapes; all of them or none."""

        def work(found: dict[str, Entry], now: datetime) -> tuple[list[Entry], str]:
            moved = {"status": "in-change", "launch": launch, "updated_at": now}
            taken = [_valid(self._get(found, i).model_dump() | moved) for i in ids]
            self._write(*taken)
            return taken, f"{', '.join(ids)} into a new Change (launch {launch})"

        return self._apply(work)

    def _get(self, found: dict[str, Entry], entry_id: str) -> Entry:
        if entry_id not in found:
            raise BacklogError(404, f"no backlog entry {entry_id}")
        return found[entry_id]

    def _new_id(self, found: dict[str, Entry], now: datetime) -> str:
        made = f"{now:%Y%m%d}-{secrets.token_hex(3)}"
        while made in found:
            made = f"{now:%Y%m%d}-{secrets.token_hex(3)}"
        return made

    def _write(self, *entries: Entry) -> None:
        """Write every entry or none: all new files first, then the renames; a failed rename puts back the old files."""
        targets = [self.folder / f"{e.id}.json" for e in entries]
        kept = {t: t.read_text(encoding="utf-8") if t.exists() else None for t in targets}
        staged: list[Path] = []
        renamed: list[Path] = []
        try:
            for e in entries:
                text = e.model_dump_json(indent=1) + "\n"
                staged.append(_staged(self.folder, text))
            for tmp, target in zip(staged, targets, strict=True):
                tmp.replace(target)
                renamed.append(target)
        except BaseException:
            for tmp in staged[len(renamed) :]:
                tmp.unlink(missing_ok=True)
            for target in renamed:
                if (old := kept[target]) is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write(target, old)
            raise
        _sync(self.folder)

    def _apply[T](self, work: Callable[[dict[str, Entry], datetime], tuple[T, str]]) -> tuple[T, str]:
        """Run ``work`` under the locks, then publish the folder; its result and the publication notice."""
        until = time.monotonic() + common.SAVE_SECONDS
        with self._locked():
            out, what = work(self.read()[0], self.clock())
            if self.shared is None:
                return out, ""
            return out, self.shared.publish(self.folder, f"backlog {self.folder.parent.name}: {what}"[:200], until)

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        """The shared repository's lock, when there is one, and the folder's own."""
        with self.shared.locked() if self.shared else contextlib.nullcontext():
            self.folder.mkdir(parents=True, exist_ok=True)
            dir_fd = os.open(self.folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                fd = open_lock(dir_fd, blocking=True, name=".backlog.lock")
            finally:
                os.close(dir_fd)
            try:
                yield
            finally:
                os.close(fd)
