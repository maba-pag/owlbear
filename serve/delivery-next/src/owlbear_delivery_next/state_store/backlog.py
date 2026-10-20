"""Improvement backlog (TD-84, TD-103): what the owner, the watcher, the assistant, reviews and runs found.

Each entry is one GitHub issue in the shared repository (``backlog_issues``); this module is the view over them. A
finding names the project it was found in, none outside any; an entry names its triaged projects, else its origin. A
finding that repeats an entry naming the same projects counts it up; otherwise it is a new entry, linked at once to
every entry with the same finding (TD-345, TD-405, TD-406); links hold on both entries. The only limit on links is
the length of an issue body: a link that would not fit is refused with the full entries named, before anything is
written. Untriaged entries form the inbox. Saving is online-only: when GitHub cannot be reached the save fails with
GitHub's reason, nothing is kept locally. Reads are cached for a few seconds since the page refreshes often; every
write reads afresh under the shared repository's lock, and reads each issue it changes directly first, so an edit made
on GitHub meanwhile is kept.
"""

from __future__ import annotations

import re
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.state_store import backlog_issues
from owlbear_delivery_next.state_store.backlog_issues import Issues

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from owlbear_delivery_next.github.gh_client import Json
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.store import Store

ID = r"^[1-9]\d{0,8}$"  # the issue's number
EVIDENCE = 50  # references kept per entry, the newest
LINKS = backlog_issues.LONGEST // 10  # more than an issue body holds: each link takes 10 characters or more
PROBE = "9" * 9  # the longest id, for the room a new entry's link takes before GitHub numbers it
READ_SECONDS = 10.0  # how long a listing is reused
RECENT_SECONDS = 120.0  # GitHub lists a new or edited issue only seconds later; until then the write's answer counts
type Source = Literal["owner", "watcher", "assistant", "review", "run"]
type Kind = Literal["untriaged", "defect", "improvement", "idea", "question"]
type Status = Literal["inbox", "open", "in-change", "done", "dropped"]
type Folder = Annotated[str, Field(min_length=1, max_length=100)]  # a project's folder in the shared repository
type Ref = Annotated[str, Field(min_length=1, max_length=500)]
ORDER = {"inbox": 0, "open": 1, "in-change": 2, "done": 3, "dropped": 4}
NO_SHARED = "no shared repository is set up (`owlbear-next data PATH`); the backlog lives in its GitHub issues"
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
    projects: list[Folder] | None = Field(default=None, max_length=50)  # what it concerns: [] Global, None untriaged
    origin: str = Field(default="", max_length=100)  # the project it was found in, kept as attribution (TD-241)
    notes: str = Field(default="", max_length=4000)  # the owner's context
    links: list[Annotated[str, Field(pattern=ID)]] = Field(default_factory=list, max_length=LINKS)
    evidence: list[Ref] = Field(default_factory=list, max_length=EVIDENCE)
    change: str = ""  # the Change it went into: ``{clone id}/{slug}``, or an older entry's bare slug
    launch: str = ""  # the New Change launch that took the entry
    count: int = Field(default=1, ge=1)
    first_seen: datetime
    last_seen: datetime
    updated_at: datetime
    legacy: str = Field(default="", pattern=r"^(\d{8}-[0-9a-f]{6})?$")  # the file entry it was migrated from

    @model_validator(mode="before")
    @classmethod
    def _scoped(cls, data: Any) -> Any:  # noqa: ANN401 - pydantic's raw input
        """An entry written before TD-241: only what its scope states becomes ``projects``; its project, the origin."""
        if not isinstance(data, dict) or not {"scope", "project"} & data.keys():
            return data
        data = dict(data)
        scope, old = data.pop("scope", "unassigned"), data.pop("project", "")
        data.setdefault("origin", old)
        if "projects" not in data:
            data["projects"] = [old] if scope == "project" and old else [] if scope == "global" else None
        return data


def key(source: str, title: str) -> str:
    """What makes two findings the same: their source and their title's words, case and punctuation aside."""
    return f"{source}:{' '.join(re.findall(r'\w+', title.casefold()))}"


def named(entry: Entry) -> frozenset[str]:
    """The projects an entry names: its triaged ones, else its origin, else none (TD-406)."""
    return frozenset(entry.projects if entry.projects is not None else [entry.origin] if entry.origin else [])


def repeats(entry: Entry, project: str, source: str, title: str) -> bool:
    """Whether a finding in *project* (none: outside any) repeats *entry*: the same key, the same projects (TD-345)."""
    finding = frozenset([project] if project else [])
    return key(entry.source, entry.title) == key(source, title) and named(entry) == finding


def ordered(entries: Iterable[Entry]) -> list[Entry]:
    """The inbox, then open entries, then the rest; the most recently seen first in each."""
    return sorted(entries, key=lambda e: (ORDER[e.status], -e.last_seen.timestamp()))


def _valid(fields: dict[str, Any]) -> Entry:
    try:
        return Entry.model_validate(fields)
    except ValidationError as exc:
        error = exc.errors(include_url=False)[0]
        raise BacklogError(422, f"{'.'.join(map(str, error['loc']))}: {error['msg']}") from exc


def _linked(entry: Entry, other: str, now: datetime) -> Entry:
    return _valid(entry.model_dump() | {"links": [*entry.links, other], "updated_at": now})


class Backlog:
    """The backlog issues of the shared repository, seen from one project."""

    def __init__(self, shared: DataRepo, project: str = "", clock: Callable[[], datetime] | None = None) -> None:
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
            self.raw = dict(hit[2])
            return dict(hit[1]), list(hit[3])
        found, raw, bad = {}, {}, []
        for issue in self._overlaid(self._github("read", self.issues.issues)):
            try:
                entry = Entry.model_validate(backlog_issues.fields(issue))
            except ValidationError:
                bad.append(f"#{issue['number']}")
                continue
            found[entry.id], raw[entry.id] = entry, issue
        self.raw = dict(raw)
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
            match = key(source, title)
            listed = [e.id for e in found.values() if key(e.source, e.title) == match]  # read again: the listing lags
            fresh = [e for e in (self._fetch(found, i) for i in listed) if e and key(e.source, e.title) == match]
            same = next((e for e in fresh if repeats(e, self.project, source, title)), None)
            if same is None:  # TD-405: linked both ways at once, to every match
                alike = sorted(fresh, key=lambda e: int(e.id))
                self._room([_linked(e, PROBE, now) for e in alike])
                fields = {"id": "1", "title": title.strip(), "text": text.strip(), "source": source}
                fields |= {"evidence": refs[-EVIDENCE:], "origin": self.project, "links": [e.id for e in alike]}
                entry = self.put(_valid(fields | {"first_seen": now, "last_seen": now, "updated_at": now}))
                self._save(*(_linked(e, entry.id, now) for e in alike))
                return entry, True
            new = [r for r in refs if r not in same.evidence]
            seen = {"count": same.count + 1, "last_seen": now, "updated_at": now}
            entry = _valid(same.model_dump() | seen | {"evidence": (same.evidence + new)[-EVIDENCE:]})
            others = [self._fetch(found, i) for i in entry.links]  # a link a failed save left one-sided is completed
            lacking = [_linked(e, entry.id, now) for e in others if e and entry.id not in e.links]
            self._room(lacking)
            self._save(entry, *lacking)
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
            others = []
            if "links" in fields:
                new["links"] = links = list(dict.fromkeys(fields["links"]))
                if bad := [i for i in links if i == entry_id or (i not in found and self._fetch(found, i) is None)]:
                    raise BacklogError(422, f"links: {', '.join(bad)} is not another entry of this backlog")
                pointing = {i for i, e in found.items() if entry_id in e.links}  # a failed save's side is redone
                for other in sorted(((set(links) ^ set(old.links)) | (set(links) ^ pointing)) & found.keys(), key=int):
                    them = self._get(found, other)
                    theirs = [i for i in them.links if i != entry_id] + ([entry_id] if other in links else [])
                    if set(theirs) != set(them.links):
                        others.append(_valid(them.model_dump() | {"links": theirs, "updated_at": now}))
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

    def put(self, entry: Entry, made: Callable[[str], None] = lambda _number: None) -> Entry:
        """Open one issue holding ``entry`` as it is (its id aside), closed when it is done or dropped.

        ``made`` gets the issue's number as soon as GitHub confirms it, before the issue is closed.
        """
        fields = entry.model_dump()
        text, names = self._body(fields), backlog_issues.labels(fields)
        self._github("save", lambda: self.issues.ensure_labels(names))
        issue = self._remember(self._github("save", lambda: self.issues.create(entry.title, text, names)))
        made(str(issue["number"]))
        if (wanted := backlog_issues.state(entry.status))["state"] == "closed":
            self._remember(self._github("save", lambda: self.issues.edit(issue["number"], wanted)))
        return entry.model_copy(update={"id": str(issue["number"])})

    def _room(self, entries: list[Entry]) -> None:
        """Refuse the write when an entry's issue has no room for its new link, naming each full one."""
        if full := [f"#{e.id}" for e in entries if len(backlog_issues.body(e.model_dump())) > backlog_issues.LONGEST]:
            said = ", ".join(full)
            raise BacklogError(422, f"no room for another link in the GitHub issue of {said}: unlink or shorten it")

    def _save(self, *entries: Entry) -> None:
        """Write each entry over its issue, keeping the labels OwlBear does not own; none when one is too long."""
        bodies = [self._body(entry.model_dump()) for entry in entries]
        for entry, text in zip(entries, bodies, strict=True):
            fields = entry.model_dump()
            names = backlog_issues.labels(fields)
            change = {"title": entry.title, "body": text, **backlog_issues.state(entry.status)}
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
        for number, (_, issue) in kept.items():  # a tie is the listing's: an edit elsewhere may share the second
            if number not in out or out[number].get("updated_at", "") < issue.get("updated_at", ""):
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

    def current(self, entry_id: str) -> Entry | None:
        """The entry as its issue holds it now, read directly; None when there is no such issue."""
        return self._fetch({}, entry_id)

    def _get(self, found: dict[str, Entry], entry_id: str) -> Entry:
        if (entry := self._fetch(found, entry_id)) is None:
            raise BacklogError(404, f"no backlog entry #{entry_id}")
        return entry

    def _fetch(self, found: dict[str, Entry], entry_id: str) -> Entry | None:
        """The entry as its issue holds it now, read directly before it changes: the listing may be behind."""
        if not re.fullmatch(ID, entry_id):
            return None
        if (issue := self._github("read", lambda: self.issues.issue(int(entry_id)))) is None:
            return None
        try:
            entry = Entry.model_validate(backlog_issues.fields(issue))
        except ValidationError as exc:
            raise BacklogError(409, f"#{entry_id} holds no readable backlog entry; fix its issue first") from exc
        found[entry_id], self.raw[entry_id] = entry, issue
        return entry

    def _github[T](self, what: str, call: Callable[[], T]) -> T:
        """Run one GitHub call; its failure is the owner's error, saying whether a save may have happened."""
        try:
            return call()
        except ProviderError as exc:
            self._forget()
            if what == "read":
                text = f"the backlog could not be read from GitHub ({self.repository}): {exc}"
            elif exc.operation == backlog_issues.VISIBILITY:
                text = f"not saved to GitHub ({self.repository}): {exc}"
            elif exc.retry_safe:
                text = f"not saved: GitHub ({self.repository}) could not be reached: {exc}"
            else:
                text = f"GitHub ({self.repository}) did not confirm the save; check its issues before retrying: {exc}"
            raise BacklogError(503, text) from exc

    def _apply[T](self, work: Callable[[dict[str, Entry], datetime], T]) -> T:
        """Run ``work`` on a fresh reading under the shared repository's lock."""
        with self.shared.locked():
            return work(self.read(fresh=True)[0], self.clock())
