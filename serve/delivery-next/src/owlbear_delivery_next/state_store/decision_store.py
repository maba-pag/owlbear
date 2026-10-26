"""Decisions in the shared data repository (TD-424, TD-419 slice 3): load, save with a receipt, refresh.

The files in ``owlbear-data`` are the authority. A repository or project folder that is missing or unreadable, or a
file in the project's view that is not a usable decision, raises `DecisionsUnavailable`, never an empty or partial
rule set. A save, under the repository-wide lock, catches up with the remote, writes with an expected revision,
commits and pushes its files alone (`decision_sync`), reloads and validates, and reads its receipt back before the
lock is released; a save of several files (a successor and what it retires) writes all of them or none, in one
commit. Neither a Git merge nor a timestamp decides authority: when the reloaded snapshot shows two
in-force successors of one decision (a widening promotion counts), every successor of it is flagged ``conflict`` and
published, and the owner resolves them.
"""

from __future__ import annotations

import stat
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionError, LinkType, Scope, check_write, decision_path, read, snapshot, write
from owlbear_decisions.snapshot import CONFLICT
from owlbear_decisions.storage import kind, serialize
from owlbear_decisions.validate import collect, layers, project_folders
from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.data_repo import SAVE_SECONDS, DataRepoError
from owlbear_delivery_next.state_store import decision_batch, decision_sync, decision_transaction
from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from owlbear_decisions import Decision, Entry, Finding, Snapshot
    from owlbear_delivery_next.local_system.data_repo import DataRepo

    type Placed = tuple[Decision, Path, str | None]  # a decision, its layer's folder and its expected revision

SET_UP = "Set the shared data repository: `owlbear-next data PATH`"
SET_UP_PROJECT = "Set up the project so the shared data repository holds its folder: `owlbear-next setup`"
REPAIR = "Repair the shared data repository's checkout so Git can read it"
READ = "Make the decision folders and files in the shared data repository readable and valid"
RECOVER = "Finish or abandon the interrupted decision batch by its generation (owner's explicit choice)"
ROUNDS = 3  # flag-and-publish rounds before a conflict is reported unresolved
SUCCEEDS = (LinkType.REPLACES, LinkType.PROMOTED_FROM)  # the links that make a successor (TD-426)


class DecisionsUnavailable(StoreError):  # noqa: N818 - the design's name for it
    """The decisions cannot be read, so no work may run as if there were none."""

    action = REPAIR
    resume = "The decisions load"

    def __init__(self, reason: str, action: str = REPAIR) -> None:
        super().__init__(reason)
        self.action = action


@dataclass(frozen=True)
class DataView:
    """A project's snapshot and the data commit (`HEAD`) it was read at."""

    snapshot: Snapshot
    commit: str


@dataclass(frozen=True)
class Receipt:
    """What became of one save: each step reported apart, read back from the files and Git."""

    id: str
    saved: bool
    commit: str
    committed: bool = False
    published: bool = False
    active: bool = False
    revision: str = ""
    conflict: bool = False
    notice: str = ""
    batch: bool = False  # the save's own commit holds what it wrote, whatever became of a later conflict flag


def _checkout(shared: DataRepo | None) -> DataRepo:
    if shared is None:
        msg = "there is no shared data repository, so there are no decisions to work by"
        raise DecisionsUnavailable(msg, SET_UP)
    try:
        mode = shared.root.stat().st_mode
    except FileNotFoundError, NotADirectoryError:
        mode = 0
    except OSError as exc:
        msg = f"the shared data repository {shared.root} cannot be read: {exc}"
        raise DecisionsUnavailable(msg, READ) from exc
    if not stat.S_ISDIR(mode):
        msg = f"the shared data repository {shared.root} is not a folder on this machine"
        raise DecisionsUnavailable(msg, SET_UP)
    return shared


def _head(shared: DataRepo) -> str:
    said = shared.git("rev-parse", "--show-toplevel", "HEAD")
    lines = said.stdout.splitlines()
    if said.returncode or len(lines) != 2 or lines[0] != str(shared.root.resolve()):  # noqa: PLR2004 - top, HEAD
        why = said.stderr.strip()[:200] or "it is not the top folder of a Git checkout with a commit"
        msg = f"Git cannot read the shared data repository {shared.root}: {why}"
        raise DecisionsUnavailable(msg)
    return lines[1]


def _project(shared: DataRepo, project: str) -> None:
    """The project's folder exists once the project is set up (it holds its claim); without it nothing is known."""
    folder = shared.root / project
    try:
        mode = kind(folder)
    except OSError as exc:
        msg = f"{folder} cannot be read: {exc}"
        raise DecisionsUnavailable(msg, READ) from exc
    if mode is None:
        msg = f"the project {project} has no folder in {shared.root}, so its decisions cannot be told from none"
        raise DecisionsUnavailable(msg, SET_UP_PROJECT)
    if not stat.S_ISDIR(mode):
        msg = f"{folder} is not a folder, so its decisions cannot be read"
        raise DecisionsUnavailable(msg, READ)


def _files(shared: DataRepo, project: str) -> Snapshot:
    if project:
        _project(shared, project)
    try:
        seen = snapshot(shared.root, project)
    except OSError as exc:
        msg = f"the decisions in {shared.root} cannot be read: {exc}"
        raise DecisionsUnavailable(msg, READ) from exc
    return seen


def _usable(seen: Snapshot, project: str) -> Snapshot:
    if bad := seen.unreadable:
        named = "; ".join(f"{f.path}: {f.message}" for f in bad[:3])
        msg = f"{len(bad)} file(s) among the decisions of {project or 'Global'} cannot be used: {named}"
        raise DecisionsUnavailable(msg[:600], READ)
    return seen


def _interrupted(shared: DataRepo) -> None:
    """Refuse every read and write while a batch is in flight: its files are not yet a settled rule set."""
    _head(shared)  # the journal lives in the checkout's Git folder, so the checkout is read first
    try:
        batch = decision_batch.pending(shared)
    except decision_batch.JournalError as exc:
        raise DecisionsUnavailable(str(exc)[:600], RECOVER) from exc
    if batch is not None:
        ids = ", ".join(batch.ids)
        msg = f"the interrupted decision batch {batch.generation} ({ids}) must be finished or abandoned"
        raise DecisionsUnavailable(msg[:600], RECOVER)


def _open(shared: DataRepo | None) -> DataRepo:
    root = _checkout(shared)
    _interrupted(root)
    return root


checkout = _checkout  # the owner's recovery reads the checkout while a batch is in flight
head = _head
files = _files
usable = _usable


def _stamp(shared: DataRepo) -> tuple[bytes | None, bytes | None]:
    try:
        return decision_batch.stamp(shared)
    except decision_batch.JournalError as exc:
        raise DecisionsUnavailable(str(exc)[:600], RECOVER) from exc


def _paired(shared: DataRepo, project: str) -> DataView:
    """HEAD and the snapshot read as one: a batch that began or completed while they were read is refused."""
    first = _stamp(shared)
    commit = _head(shared)
    seen = _files(shared, project)
    if _head(shared) != commit or _stamp(shared) != first:
        msg = "the decisions changed while they were read, so they are not a settled rule set; read them again"
        raise DecisionsUnavailable(msg, READ)
    return DataView(seen, commit)


def file_snapshot(shared: DataRepo | None, project: str) -> Snapshot:
    """A readable file-only view, with the same checkout, project and unreadable-file checks as `load`."""
    return _usable(_paired(_open(shared), project).snapshot, project)


def _view(shared: DataRepo, project: str) -> DataView:
    return _paired(shared, project)


def load(shared: DataRepo | None, project: str) -> DataView:
    """The Global layer and *project*'s layers as the checkout holds them, with its commit; never pulls.

    A file in those layers that is not a usable decision raises `DecisionsUnavailable`: the rules it holds are
    unknown, so nothing may run as if it were absent. Findings stay in the snapshot for the caller to judge.
    """
    view = _view(_open(shared), project)
    _usable(view.snapshot, project)
    return view


def refresh(shared: DataRepo | None) -> str:
    """Rebase the checkout on its remote under the lock; why it did not, else nothing. Uncommitted work blocks it."""
    shared = _checkout(shared)
    try:
        with shared.locked():
            _interrupted(shared)
            status = shared.git("status", "--porcelain", "--untracked-files=no")
            if status.returncode:
                msg = f"Git cannot read the shared data repository {shared.root}: {status.stderr.strip()[:200]}"
                raise DecisionsUnavailable(msg)
            if changed := status.stdout.splitlines():
                return f"not refreshed: {len(changed)} uncommitted file(s) in {shared.root}; the next save publishes"
            failed = decision_sync.catch_up(shared, time.monotonic() + SAVE_SECONDS)
    except (DataRepoError, OSError) as exc:  # a lock or attributes file that cannot be opened too
        raise DecisionsUnavailable(str(exc)) from exc
    return f"not refreshed from the remote: {failed}" if failed else ""


def _layer(root: Path, decision: Decision) -> Path:
    if decision.scope is Scope.GLOBAL:
        return root
    folder = root / decision.project
    return folder / "changes" / decision.change if decision.scope is Scope.CHANGE else folder


def _join(*parts: str) -> str:
    return "; ".join(filter(None, parts))


def save(shared: DataRepo | None, decision: Decision, *, expected_revision: str | None, message: str) -> Receipt:
    """Write *decision* if the remote's file is at *expected_revision* (None: a new file), publish it and validate.

    The receipt is read back before the repository's lock is released.
    """
    return save_all(shared, [(decision, expected_revision)], message=message)[0]


def save_all(shared: DataRepo | None, items: Sequence[tuple[Decision, str | None]], *, message: str) -> list[Receipt]:
    """Write every decision of *items* at its expected revision, or none; publish them as one commit and validate.

    Any file not at its expected revision refuses the whole batch before one is written, and a publication the remote
    overtook is taken back whole, so a transition never leaves half of it in force. The receipts are read back before
    the repository's lock is released.
    """
    shared = _checkout(shared)
    try:
        with shared.locked():
            _interrupted(shared)
            return _save_all(shared, [(d, _layer(shared.root, d), expected) for d, expected in items], message)
    except DataRepoError as exc:
        raise DecisionsUnavailable(str(exc)) from exc
    except OSError as exc:
        msg = f"{', '.join(d.id for d, _ in items)} could not be written in {shared.root}: {exc}"
        raise DecisionsUnavailable(msg, READ) from exc


def _save_all(shared: DataRepo, items: list[Placed], message: str) -> list[Receipt]:
    if not items:  # nothing to save: no remote work and no journal, which would name no file
        return []
    until = time.monotonic() + SAVE_SECONDS
    head, behind = decision_sync.prepare(shared, until)
    if not head:  # nothing is journalled or written until HEAD is proved on the remote
        return [Receipt(d.id, saved=False, commit="", notice=behind[:300]) for d, _, _ in items]
    return _journal(shared, items, message, head, behind)


def _journal(shared: DataRepo, items: list[Placed], message: str, head: str, behind: str) -> list[Receipt]:
    until = time.monotonic() + SAVE_SECONDS
    decisions, paths = [d for d, _, _ in items], [decision_path(d, folder) for d, folder, _ in items]
    before = {path: _content(path) for path in paths}
    images = {path: (before[path], serialize(d).encode("utf-8")) for d, path in zip(decisions, paths, strict=True)}
    if refused := _refusals(items):
        return _refused(shared, decisions, refused, behind)
    generation, rows = _begin(shared, items, before, message, head)
    try:
        refused = write_batch(items)
    except OSError:
        decision_transaction.settle(shared, images, head, generation)  # kept interrupted unless HEAD is proved
        raise
    if refused:
        why = "; ".join(f"{key}: {text}" for key, text in sorted(refused.items()))
        held = f"not saved ({why[:120]}), and the files are not proved put back on HEAD {head[:12]}"
        settled = decision_transaction.settle(shared, images, head, generation)
        return (
            _refused(shared, decisions, refused, behind) if settled else _held_back(shared, decisions, held, generation)
        )
    sent = decision_sync.publish(shared, paths, message, until, head)
    if sent.uncommitted or sent.ambiguous or sent.stale:  # only a known refusal on the proved head settles here
        put_back = sent.uncommitted and decision_transaction.settle(shared, images, head, generation)
        said = f"not saved, the files are put back: {sent.notice.removeprefix('saved, but ')}"
        return _unsaved(shared, decisions, said) if put_back else _held_back(shared, decisions, sent.notice, generation)
    if not decision_transaction.landed(shared, head, rows):  # a sent publication is not proof of landing
        notice = f"{sent.notice} (interrupted batch {generation}: not landed in Git; finish or abandon it in Decisions)"
        return _unsaved(shared, decisions, notice)
    decision_batch.complete(shared, generation)
    held = [decision_sync.revision_at(shared, "HEAD", p.relative_to(shared.root).as_posix(), until) for p in paths]
    said = [sent.notice]
    view = _reconcile(shared, decisions, said, until)
    if view is None:  # saved and published; only the conflict flags are interrupted
        return [Receipt(d.id, saved=True, commit=_head(shared), notice=_join(*said)[:300]) for d in decisions]
    return [
        replace(_receipt(shared, view, d, _join(*said, behind), until), batch=revision == d.revision)
        for d, revision in zip(decisions, held, strict=True)
    ]


def _begin(
    shared: DataRepo, items: list[Placed], before: dict[Path, bytes | None], message: str, head: str
) -> tuple[str, list[tuple[str, bytes | None, bytes]]]:
    """Journal the batch on *head*, with each file's bytes before and after, before its first file is written."""
    rows = []
    for decision, folder, _ in items:
        path = decision_path(decision, folder)
        rows.append((path.relative_to(shared.root).as_posix(), before[path], serialize(decision).encode("utf-8")))
    project = next((d.project for d, _, _ in items if d.project), "")
    generation = decision_batch.begin(shared, project, head, message, [d.id for d, _, _ in items], rows)
    return generation, rows


def _refusals(items: list[Placed]) -> dict[str, str]:
    """Why each file of the batch would be refused, checked before any is written."""
    found = {}
    for decision, folder, expected in items:
        path = decision_path(decision, folder)
        try:
            check_write(read(path) if path.exists() else None, decision, expected)
        except DecisionError as exc:
            found[decision.id] = str(exc)
    return found


def write_batch(items: Sequence[Placed]) -> dict[str, str]:
    """Write in order and stop at the first refused file; the caller settles the written files once HEAD is proved."""
    for decision, folder, expected in items:
        try:
            storage_io.make_dirs(decision_path(decision, folder).parent)  # ancestors are durable before the write
            write(decision, folder, expected)
        except DecisionError as exc:
            return {decision.id: str(exc)}
    return {}


def _content(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _put_back(path: Path, text: bytes | None, fence: Callable[[], None] | None = None) -> None:
    if _content(path) != text:
        decision_batch.replace_file(path, text, fence)


def _unsaved(shared: DataRepo, decisions: list[Decision], notice: str) -> list[Receipt]:
    return [Receipt(d.id, saved=False, commit=_head(shared), notice=notice[:300]) for d in decisions]


def _held_back(shared: DataRepo, decisions: list[Decision], why: str, generation: str) -> list[Receipt]:
    """The receipts of a batch that stays interrupted: nothing is saved until the owner settles it."""
    return _unsaved(shared, decisions, f"{why} (interrupted batch {generation}: finish or abandon it in Decisions)")


def _refused(shared: DataRepo, decisions: list[Decision], refused: dict[str, str], behind: str) -> list[Receipt]:
    others = f"not saved: {', '.join(sorted(refused))} was refused, and these saves go together or not at all"
    return [
        Receipt(d.id, saved=False, commit=_head(shared), notice=_join(refused.get(d.id, others), behind)[:300])
        for d in decisions
    ]


def _reconcile(shared: DataRepo, decisions: list[Decision], said: list[str], until: float) -> DataView | None:
    """Flag competing successors and publish the flags, reloading until none is left unflagged (ROUNDS at most).

    The flags are one journaled batch: a refused flag commit puts them back, and an unknown one stops the loop as
    interrupted. Nothing is flagged unless `decision_sync.prepare` proved HEAD on the remote first.
    """
    project = next((d.project for d in decisions if d.project), "")
    for _ in range(ROUNDS):
        _interrupted(shared)  # before any remote work of this round, as every new writer
        head, behind = decision_sync.prepare(shared, until)
        if not head:  # the flags are not written: the competitors stay unflagged and none is active
            said.append(behind)
            return None
        found = whole(shared)
        competing = {e.decision.id: e for d in decisions for e in _competitors(found, d)}
        if not competing:
            return _view(shared, project)
        entries = [e for _, e in sorted(competing.items())]
        files = [(e.path, serialize(e.decision.model_copy(update={"conflict": True})).encode("utf-8")) for e in entries]

        def flag(head: str, entries: list[Entry] = entries) -> decision_transaction.Step:
            flagged = [path for e in entries if (path := _flag(e))]
            if not flagged:
                return decision_transaction.Step("", refused=True)
            ids = ", ".join(sorted(p.stem for p in flagged))
            sent = decision_sync.publish(shared, flagged, f"decisions: conflict on {ids}", until, head)
            unknown = sent.ambiguous or sent.stale
            return decision_transaction.Step(sent.notice, unknown=unknown, refused=sent.uncommitted)

        notice = decision_transaction.transaction(shared, project, "decisions: conflict flags", files, flag, head)
        said.append(notice)
        if decision_batch.pending(shared) is not None:  # the journal decides: a flag batch left pending halts the loop
            return None  # authority cannot be read until the owner settles it
    return _view(shared, project)


def whole(shared: DataRepo) -> tuple[dict[str, Entry], list[Finding]]:
    """Every decision of the data repository by id and every finding: competitors may lie outside a project's view."""
    try:
        entries, findings = collect(layers(shared.root, project_folders(shared.root)))
    except OSError as exc:
        msg = f"the decisions in {shared.root} cannot be read: {exc}"
        raise DecisionsUnavailable(msg, READ) from exc
    return {e.decision.id: e for e in entries}, findings


def _competitors(found: tuple[dict[str, Entry], list[Finding]], written: Decision) -> list[Entry]:
    """The unflagged in-force successors competing with *written*, or with it for what it replaces or promotes."""
    by_id, findings = found
    touched = {written.id, *(link.target for link in written.links if link.type in SUCCEEDS)}
    ids = {f.involves[0] for f in findings if f.rule == CONFLICT and touched.intersection(f.involves[1:])}
    return [e for i in sorted(ids) if (e := by_id.get(i)) is not None and not e.decision.conflict]


def _flag(entry: Entry) -> Path | None:
    """Mark *entry* `conflict`, in its state and at the revision just read; None when its file has moved on."""
    try:
        write(entry.decision.model_copy(update={"conflict": True}), entry.layer.folder, entry.decision.revision)
    except DecisionError:
        return None
    return entry.path


def _receipt(shared: DataRepo, view: DataView, decision: Decision, said: str, until: float) -> Receipt:
    """Each step read back for the revision this save wrote: *decision*, or it flagged `conflict`."""
    entry = view.snapshot.get(decision.id)
    if entry is None:  # written, then gone: the rebase removed it
        return Receipt(decision.id, saved=True, commit=view.commit, notice=_join(said, "the file is gone")[:300])
    rel = decision_path(decision, _layer(shared.root, decision)).relative_to(shared.root).as_posix()
    held = entry.decision.revision
    ours = held in {decision.revision, decision.model_copy(update={"conflict": True}).revision}
    committed = ours and decision_sync.revision_at(shared, "HEAD", rel, until) == held
    published = committed and decision_sync.revision_at(shared, decision_sync.UPSTREAM, rel, until) == held
    found = view.snapshot.findings_for(decision.id)
    unresolved = bool(_competitors(whole(shared), decision))  # still unflagged after every round
    conflict = not ours or unresolved or entry.decision.conflict or any(f.rule == CONFLICT for f in found)
    return Receipt(
        decision.id,
        saved=True,
        commit=decision_sync.last_commit(shared, rel, until) if committed else view.commit,
        committed=committed,
        published=published,
        active=not conflict and view.snapshot.complete and view.snapshot.active(decision.id),
        revision=held,
        conflict=conflict,
        notice=_join(said, _why(view.snapshot, decision.id, ours=ours, unresolved=unresolved, conflict=conflict))[:300],
    )


def _why(seen: Snapshot, decision_id: str, *, ours: bool, unresolved: bool, conflict: bool) -> str:
    if not ours:
        return f"{decision_id} holds another revision than this save wrote; the owner resolves it"
    if unresolved:
        return f"a successor competing with {decision_id} is still unflagged after {ROUNDS} rounds; none is active"
    if conflict:
        return "in conflict with another in-force successor; the owner resolves it"
    if found := seen.findings_for(decision_id):
        return f"not active: {found[0].rule}: {found[0].message}"
    if seen.unreadable:
        return f"not active: {seen.unreadable[0].path}: {seen.unreadable[0].message}"
    return ""
