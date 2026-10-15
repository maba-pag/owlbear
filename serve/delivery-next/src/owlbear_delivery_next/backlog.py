"""Improvement backlog (TD-84, TD-103): what the owner, the watcher, the assistant, reviews and runs found.

Each entry is one GitHub issue in the shared repository (``backlog_issues``); this module is the view over them. A
finding seen again counts up its entry instead of adding one; untriaged entries form the inbox. Saving is online-only:
when GitHub cannot be reached the save fails with GitHub's reason, nothing is kept locally. Reads are cached for a few
seconds since the page refreshes often; every write reads afresh under the shared repository's lock.
"""

from __future__ import annotations

import re
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery_next import backlog_issues
from owlbear_delivery_next.backlog_issues import Issues
from owlbear_delivery_next.github.provider import ProviderError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from owlbear_delivery_next.common import Common
    from owlbear_delivery_next.github.gh_client import Json
    from owlbear_delivery_next.store import Store

ID = r"^[1-9]\d{0,8}$"  # the issue's number
EVIDENCE = 50  # references kept per entry, the newest
READ_SECONDS = 10.0  # how long a listing is reused
RECENT_SECONDS = 120.0  # GitHub lists a new or edited issue only seconds later; until then the write's answer counts
type Source = Literal["owner", "watcher", "assistant", "review", "run"]
type Kind = Literal["untriaged", "defect", "improvement", "idea", "question"]
type Status = Literal["inbox", "open", "in-change", "done", "dropped"]
type Scope = Literal["project", "cross-project", "global", "unassigned"]
type Ref = Annotated[str, Field(min_length=1, max_length=500)]
ORDER = {"inbox": 0, "open": 1, "in-change": 2, "done": 3, "dropped": 4}
NO_SHARED = "no shared repository is set up (`owlbear-next common PATH`); the backlog lives in its GitHub issues"
_cache: dict[str, tuple[float, dict[str, Entry], dict[str, Json], list[str]]] = {}
_recent: dict[str, dict[int, tuple[float, Json]]] = {}  # repository -> issue number -> (when, GitHub's answer)
_cache_guard = threading.Lock()


class BacklogError(Exception):
    """An unknown entry, a refused field or an unreachable GitHub; ``status`` is the HTTP answer."""

    def __init__(self, status: int, text: str) -> None:
        """Keep the HTTP status and the owner's reason."""
        super().__init__(text)
        self.status, self.text = status, text


class Entry(BaseModel):
    """One backlog entry as its issue holds it."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID)
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(default="", max_length=4000)
    source: Source
    kind: Kind = "untriaged"
    status: Status = "inbox"
    scope: Scope = "unassigned"
    project: str = Field(default="", max_length=100)  # where it was found; its label once the scope is a project
    notes: str = Field(default="", max_length=4000)  # the owner's context
    links: list[Annotated[str, Field(pattern=ID)]] = Field(default_factory=list, max_length=50)
    evidence: list[Ref] = Field(default_factory=list, max_length=EVIDENCE)
    change: str = ""  # the Change's slug once the entry went into one
    launch: str = ""  # the New Change launch that took the entry
    count: int = Field(default=1, ge=1)
    first_seen: datetime
    last_seen: datetime
    updated_at: datetime
    legacy: str = Field(default="", pattern=r"^(\d{8}-[0-9a-f]{6})?$")  # the file entry it was migrated from


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


class Backlog:
    """The backlog issues of the shared repository, seen from one project."""

    def __init__(self, shared: Common, project: str = "", clock: Callable[[], datetime] | None = None) -> None:
        """The issues of ``shared``'s GitHub remote; ``project`` is where new findings are found."""
        try:
            self.issues = Issues(shared)
        except ValueError as exc:
            raise BacklogError(409, str(exc)) from exc
        self.shared, self.project = shared, project
        self.clock = clock or (lambda: datetime.now(UTC))
        self.raw: dict[str, Json] = {}

    @property
    def repository(self) -> str:
        """The ``owner/name`` holding the issues."""
        return self.issues.repository

    @classmethod
    def of(cls, store: Store, clock: Callable[[], datetime] | None = None) -> Backlog:
        """The project's view of the shared repository's backlog; none without a shared repository."""
        if store.shared is None:
            raise BacklogError(409, NO_SHARED)
        return cls(store.shared, store.name, clock)

    def read(self, *, fresh: bool = False) -> tuple[dict[str, Entry], list[str]]:
        """Every readable entry by id, and the issues (``#n``) whose block is not one."""
        with _cache_guard:
            hit = _cache.get(self.repository)
        if not fresh and hit and time.monotonic() - hit[0] < READ_SECONDS:
            self.raw = hit[2]
            return dict(hit[1]), list(hit[3])
        found, raw, bad = {}, {}, []
        for issue in self._overlaid(self._github("read", self.issues.issues)):
            try:
                entry = Entry.model_validate(backlog_issues.fields(issue))
            except ValidationError:
                bad.append(f"#{issue['number']}")
                continue
            found[entry.id], raw[entry.id] = entry, issue
        self.raw = raw
        with _cache_guard:
            _cache[self.repository] = (time.monotonic(), found, raw, bad)
        return dict(found), list(bad)

    def entries(self) -> list[Entry]:
        """The readable entries in the page's order."""
        return ordered(self.read()[0].values())

    def add(
        self, title: str, text: str = "", source: Source = "owner", evidence: Iterable[str] = ()
    ) -> tuple[Entry, bool]:
        """Add a finding, or count up the entry it repeats; the entry and whether it is new."""
        refs = list(dict.fromkeys(r.strip() for r in evidence if r.strip()))

        def work(found: dict[str, Entry], now: datetime) -> tuple[Entry, bool]:
            same = next((e for e in found.values() if key(e.source, e.title) == key(source, title)), None)
            if same is None:
                fields = {"id": "1", "title": title.strip(), "text": text.strip(), "source": source}
                fields |= {"evidence": refs[-EVIDENCE:], "project": self.project}
                return self.put(_valid(fields | {"first_seen": now, "last_seen": now, "updated_at": now})), True
            new = [r for r in refs if r not in same.evidence]
            seen = {"count": same.count + 1, "last_seen": now, "updated_at": now}
            entry = _valid(same.model_dump() | seen | {"evidence": (same.evidence + new)[-EVIDENCE:]})
            self._save(entry)
            if new:
                said = "\n".join(f"- {' '.join(r.split())}" for r in new)
                self._github("save", lambda: self.issues.comment(int(entry.id), f"New evidence:\n\n{said}"))
            return entry, False

        return self._apply(work)

    def update(self, entry_id: str, fields: dict[str, Any]) -> Entry:
        """Set the owner's fields; classifying an inbox entry opens it, and a link holds on both entries."""

        def work(found: dict[str, Entry], now: datetime) -> Entry:
            old = self._get(found, entry_id)
            new = old.model_dump() | fields | {"updated_at": now}
            if fields.get("kind", "untriaged") != "untriaged" and old.status == "inbox" and "status" not in fields:
                new["status"] = "open"
            if fields.get("scope") == "project" and not new["project"]:
                new["project"] = self.project
            others = []
            if "links" in fields:
                new["links"] = links = list(dict.fromkeys(fields["links"]))
                if bad := [i for i in links if i not in found or i == entry_id]:
                    raise BacklogError(422, f"links: {', '.join(bad)} is not another entry of this backlog")
                for other in sorted((set(links) ^ set(old.links)) & found.keys(), key=int):
                    theirs = [i for i in found[other].links if i != entry_id] + ([entry_id] if other in links else [])
                    others.append(_valid(found[other].model_dump() | {"links": theirs, "updated_at": now}))
            entry = _valid(new)
            self._save(entry, *others)
            return entry

        return self._apply(work)

    def take(self, ids: list[str], launch: str) -> list[Entry]:
        """Mark the entries as going into the Change the launch shapes; each is checked before any is saved."""

        def work(found: dict[str, Entry], now: datetime) -> list[Entry]:
            moved = {"status": "in-change", "launch": launch, "updated_at": now}
            taken = [_valid(self._get(found, i).model_dump() | moved) for i in ids]
            self._save(*taken)
            return taken

        return self._apply(work)

    def put(self, entry: Entry) -> Entry:
        """Open one issue holding ``entry`` as it is (its id aside), closed when it is done or dropped."""
        fields = entry.model_dump()
        text, names = self._body(fields), backlog_issues.labels(fields)
        self._github("save", lambda: self.issues.ensure_labels(names))
        issue = self._remember(self._github("save", lambda: self.issues.create(entry.title, text, names)))
        if (wanted := backlog_issues.state(entry.status))["state"] == "closed":
            self._remember(self._github("save", lambda: self.issues.edit(issue["number"], wanted)))
        return entry.model_copy(update={"id": str(issue["number"])})

    def _save(self, *entries: Entry) -> None:
        """Write each entry over its issue, keeping the labels OwlBear does not own."""
        for entry in entries:
            fields = entry.model_dump()
            names = backlog_issues.labels(fields)
            change = {"title": entry.title, "body": self._body(fields), **backlog_issues.state(entry.status)}
            change["labels"] = backlog_issues.kept_labels(self.raw.get(entry.id, {})) + names
            self._github("save", lambda names=names: self.issues.ensure_labels(names))
            self._remember(self._github("save", lambda change=change, n=int(entry.id): self.issues.edit(n, change)))

    def _remember(self, issue: Json) -> Json:
        """Keep GitHub's answer to a write for the next reads, which may not list it yet."""
        with _cache_guard:
            _recent.setdefault(self.repository, {})[issue["number"]] = (time.monotonic(), issue)
            _cache.pop(self.repository, None)
        return issue

    def _overlaid(self, listed: list[Json]) -> list[Json]:
        """The listing, with the issues written lately where GitHub lists them older or not yet."""
        now = time.monotonic()
        with _cache_guard:
            kept = {n: v for n, v in _recent.get(self.repository, {}).items() if now - v[0] < RECENT_SECONDS}
            _recent[self.repository] = kept
        out = {i["number"]: i for i in listed}
        for number, (_, issue) in kept.items():
            if number not in out or out[number].get("updated_at", "") <= issue.get("updated_at", ""):
                out[number] = issue
        return sorted(out.values(), key=lambda i: -i["number"])

    @staticmethod
    def _body(fields: dict[str, Any]) -> str:
        text = backlog_issues.body(fields)
        if len(text) > backlog_issues.LONGEST:
            raise BacklogError(422, "the entry is too long for one GitHub issue: shorten its text, notes or evidence")
        return text

    def _forget(self) -> None:
        with _cache_guard:
            _cache.pop(self.repository, None)

    def _get(self, found: dict[str, Entry], entry_id: str) -> Entry:
        if entry_id not in found:
            raise BacklogError(404, f"no backlog entry #{entry_id}")
        return found[entry_id]

    def _github[T](self, what: str, call: Callable[[], T]) -> T:
        """Run one GitHub call; its failure is the owner's error, saying whether a save may have happened."""
        try:
            return call()
        except ProviderError as exc:
            self._forget()
            if what == "read":
                text = f"the backlog could not be read from GitHub ({self.repository}): {exc}"
            elif exc.retry_safe:
                text = f"not saved: GitHub ({self.repository}) could not be reached: {exc}"
            else:
                text = f"GitHub ({self.repository}) did not confirm the save; check its issues before retrying: {exc}"
            raise BacklogError(503, text) from exc

    def _apply[T](self, work: Callable[[dict[str, Entry], datetime], T]) -> T:
        """Run ``work`` on a fresh reading under the shared repository's lock."""
        with self.shared.locked():
            return work(self.read(fresh=True)[0], self.clock())
