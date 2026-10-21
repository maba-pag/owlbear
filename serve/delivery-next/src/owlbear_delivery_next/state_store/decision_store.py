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
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionError, LinkType, Scope, check_write, decision_path, read, snapshot, write
from owlbear_decisions.snapshot import CONFLICT
from owlbear_decisions.storage import kind
from owlbear_delivery_next.local_system.data_repo import SAVE_SECONDS, DataRepoError
from owlbear_delivery_next.state_store import decision_sync
from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from owlbear_decisions import Decision, Entry, Snapshot
    from owlbear_delivery_next.local_system.data_repo import DataRepo

    type Placed = tuple[Decision, Path, str | None]  # a decision, its layer's folder and its expected revision

SET_UP = "Set the shared data repository: `owlbear-next data PATH`"
SET_UP_PROJECT = "Set up the project so the shared data repository holds its folder: `owlbear-next setup`"
REPAIR = "Repair the shared data repository's checkout so Git can read it"
READ = "Make the decision folders and files in the shared data repository readable and valid"
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


def _view(shared: DataRepo, project: str) -> DataView:
    commit = _head(shared)
    if project:
        _project(shared, project)
    try:
        seen = snapshot(shared.root, project)
    except OSError as exc:
        msg = f"the decisions in {shared.root} cannot be read: {exc}"
        raise DecisionsUnavailable(msg, READ) from exc
    return DataView(seen, commit)


def load(shared: DataRepo | None, project: str) -> DataView:
    """The Global layer and *project*'s layers as the checkout holds them, with its commit; never pulls.

    A file in those layers that is not a usable decision raises `DecisionsUnavailable`: the rules it holds are
    unknown, so nothing may run as if it were absent. Findings stay in the snapshot for the caller to judge.
    """
    view = _view(_checkout(shared), project)
    if bad := view.snapshot.unreadable:
        named = "; ".join(f"{f.path}: {f.message}" for f in bad[:3])
        msg = f"{len(bad)} file(s) among the decisions of {project or 'Global'} cannot be used: {named}"
        raise DecisionsUnavailable(msg[:600], READ)
    return view


def refresh(shared: DataRepo | None) -> str:
    """Rebase the checkout on its remote under the lock; why it did not, else nothing. Uncommitted work blocks it."""
    shared = _checkout(shared)
    try:
        with shared.locked():
            status = shared.git("status", "--porcelain", "--untracked-files=no")
            if status.returncode:
                msg = f"Git cannot read the shared data repository {shared.root}: {status.stderr.strip()[:200]}"
                raise DecisionsUnavailable(msg)
            if changed := status.stdout.splitlines():
                return f"not refreshed: {len(changed)} uncommitted file(s) in {shared.root}; the next save publishes"
            failed = decision_sync.catch_up(shared, time.monotonic() + SAVE_SECONDS)
    except DataRepoError as exc:
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
            return _save_all(shared, [(d, _layer(shared.root, d), expected) for d, expected in items], message)
    except DataRepoError as exc:
        raise DecisionsUnavailable(str(exc)) from exc
    except OSError as exc:
        msg = f"{', '.join(d.id for d, _ in items)} could not be written in {shared.root}: {exc}"
        raise DecisionsUnavailable(msg, READ) from exc


def _save_all(shared: DataRepo, items: list[Placed], message: str) -> list[Receipt]:
    until = time.monotonic() + SAVE_SECONDS
    behind = decision_sync.catch_up(shared, until)
    behind = f"not checked against the remote: {behind}" if behind else ""
    decisions = [d for d, _, _ in items]
    if refused := _refusals(items) or _write(shared, items):
        return _refused(shared, decisions, refused, behind)
    sent = decision_sync.publish(shared, [decision_path(d, folder) for d, folder, _ in items], message, until)
    if sent.stale:
        return [Receipt(d.id, saved=False, commit=_head(shared), notice=sent.notice[:300]) for d in decisions]
    said = [sent.notice]
    view = _reconcile(shared, decisions, said, until)
    return [_receipt(shared, view, d, _join(*said, behind), until) for d in decisions]


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


def _write(shared: DataRepo, items: list[Placed]) -> dict[str, str]:
    """Write the batch; a refused file puts back the files already written and says why."""
    done: list[tuple[Path, bool]] = []
    for decision, folder, expected in items:
        try:
            write(decision, folder, expected)
        except DecisionError as exc:
            for path, new in done:
                if new:
                    path.unlink(missing_ok=True)
                else:
                    shared.git("restore", "--source=HEAD", "--staged", "--worktree", "--", str(path))
            return {decision.id: str(exc)}
        done.append((decision_path(decision, folder), expected is None))
    return {}


def _refused(shared: DataRepo, decisions: list[Decision], refused: dict[str, str], behind: str) -> list[Receipt]:
    others = f"not saved: {', '.join(sorted(refused))} was refused, and these saves go together or not at all"
    commit = _head(shared)
    return [
        Receipt(d.id, saved=False, commit=commit, notice=_join(refused.get(d.id, others), behind)[:300])
        for d in decisions
    ]


def _reconcile(shared: DataRepo, decisions: list[Decision], said: list[str], until: float) -> DataView:
    """Flag competing successors and publish the flags, reloading until none is left unflagged (ROUNDS at most).

    A flag publication the remote overtook is taken back, and the next round reloads and flags again.
    """
    project = next((d.project for d in decisions if d.project), "")
    for _ in range(ROUNDS):
        view = _view(shared, project)
        competing = {e.decision.id: e for d in decisions for e in _competitors(view.snapshot, d)}
        if not competing:
            return view
        if flagged := [path for _, entry in sorted(competing.items()) if (path := _flag(entry))]:
            ids = ", ".join(sorted(p.stem for p in flagged))
            sent = decision_sync.publish(shared, flagged, f"decisions: conflict on {ids}", until)
            said.append("" if sent.stale else sent.notice)
    return _view(shared, project)


def _competitors(seen: Snapshot, written: Decision) -> list[Entry]:
    """The unflagged in-force successors competing with *written*, or with it for what it replaces or promotes."""
    touched = {written.id, *(link.target for link in written.links if link.type in SUCCEEDS)}
    ids = {f.involves[0] for f in seen.findings if f.rule == CONFLICT and touched.intersection(f.involves[1:])}
    return [e for i in sorted(ids) if (e := seen.get(i)) is not None and not e.decision.conflict]


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
    unresolved = bool(_competitors(view.snapshot, decision))  # still unflagged after every round
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
