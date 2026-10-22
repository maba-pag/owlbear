"""The decision lookup (TD-456, TD-459): a worker's or a lead chat's question, answered by the picker.

One SDK session on the picker's role reads the complete list of decisions in force (Global and the project's, and a
Change's own for its worker), the correction logs, the Change's brief and the question, and submits the ids that
govern the answer; the reply lists each whole. Decisions that do not load, or any other ending, give
``{"failed": reason}``, never an empty answer. A lookup answers and attaches nothing: the Change's pinned set changes
only at a step boundary. A worker's lookup counts its spend on the Change like a pick, once its step has settled;
a lead chat's has no Change. A step runs one lookup at a time and a host one lead chat's (TD-336).
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_decisions import Decision, Scope, State, new_id
from owlbear_delivery_next.change_contracts import pick_tools
from owlbear_delivery_next.change_contracts.decision_records import Pick
from owlbear_delivery_next.local_system import local_home, processes
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer, resolve
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, StoreError, read_layer
from owlbear_delivery_next.workflow_steps import decisions_gate, pick, sessions

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts import tools
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Lock, Store

LABEL = "decision-lookup"
ASKED = (
    "Someone doing work asks which decisions (rules) govern their question. Read the COMPLETE list. Select every "
    "decision that answers the question or constrains what the answer may be, including general rules for this kind "
    "of work. Leave out decisions on the same subject that place no constraint on it. When in doubt about a rule "
    "whose violation would cause a wrong result, include it."
)
NO_SHARED = "no shared data repository is set up, so no decision could be read"
NONE = "no decision is in force"
ENDED = "the step has ended"
BUSY = "another lookup is running; try again"
LEFT = "a previous lookup's processes are not confirmed gone"
SLOT_WAIT = 5.0  # seconds a lead chat's lookup waits for the host's running one


def worker(store: Store, lock: Lock, c: Change, question: str) -> tuple[dict[str, Any], Run | None]:
    """The picker's answer to a worker of *c* over every decision in force for it, and its run; *c* stays as it is."""
    if store.shared is None:
        return {"failed": NO_SHARED}, None
    try:
        view = decision_store.load(store.shared, store.name)
        log, settings = pick.corrections(view.snapshot.root, store.name), store.settings()
        found = decisions_gate.in_force(view.snapshot, c)
        found += _own(c, store.name, found)
    except (StoreError, OSError, ValueError) as exc:
        return {"failed": _one(str(exc))}, None
    if not found:
        return {"decisions": [], "note": NONE}, None
    journal = sdk_adapter.Journal(lambda e: store.log(lock, c.slug, e))
    done = _ran(settings, c.slug, pick.message(c, found, log, ASKED, question), journal)
    return answered(done, found), done


def _own(c: Change, project: str, found: list[Decision]) -> list[Decision]:
    """*c*'s approved brief decisions not on *found*, each whole: its Change ones stay in it until archival."""
    brief = c.brief.approved[-1] if c.brief.approved else c.brief
    at, held, stem = c.brief.approved_at or datetime.now(UTC), {d.id for d in found}, decisions_gate.stem(c)
    return [
        Decision(
            id=d.id or new_id(at, seed=f"{c.slug}\n{i}\n{d.question}"), title=_one(d.question), topic=brief.title,
            statement=d.answer, scope=Scope.CHANGE, project=project, change=stem or c.slug, origin=d.origin,
            actor="owner" if d.origin == "decided" else "shaper", state=State.IN_FORCE, created_at=at,
        )
        for i, d in enumerate(brief.decisions)
        if d.id not in held
    ]  # fmt: skip


def chat(
    shared: DataRepo | None, project: str, question: str, settings: Callable[[], Settings] | None
) -> tuple[dict[str, Any], Run | None]:
    """The picker's answer to a lead chat over the project's and Global decisions in force, and its run.

    *settings* are the project's; without them (OwlBear's own decisions on the machine host) this machine's.
    """
    if shared is None:
        return {"failed": NO_SHARED}, None
    try:
        view = decision_store.load(shared, project)
        log, resolved = pick.corrections(view.snapshot.root, project), settings() if settings else machine(shared)
    except (StoreError, OSError, ValueError) as exc:
        return {"failed": _one(str(exc))}, None
    found = [
        e.decision for e in view.snapshot.entries
        if e.decision.state is State.IN_FORCE and e.decision.scope is not Scope.CHANGE
    ]  # fmt: skip
    if not found:
        return {"decisions": [], "note": NONE}, None
    try:
        done = _ran(
            resolved, project or "global", pick.message(None, found, log, ASKED, question), sdk_adapter.Journal()
        )
    except Exception as exc:  # noqa: BLE001 - a lookup that cannot run is failed, never "none apply"
        return {"failed": _one(f"{type(exc).__name__}: {exc}")}, None
    return answered(done, found), done


class Chats:
    """A host's lead-chat lookups: one at a time, none while an earlier one's processes may still run.

    A waiting call holds its request thread for `SLOT_WAIT` at most, so only the running lookup holds one for long.
    """

    def __init__(self) -> None:
        """No lookup runs yet and none was left."""
        self.slot = threading.BoundedSemaphore(1)
        self.left: dict[int, float | None] = {}  # an unconfirmed run's processes, until a rescan sees them gone

    def __call__(
        self, shared: DataRepo | None, project: str, question: str, settings: Callable[[], Settings] | None
    ) -> dict[str, Any]:
        """The lookup's answer, or why none could start."""
        if not self.slot.acquire(timeout=SLOT_WAIT):
            return {"failed": BUSY}
        try:
            if self.left and not processes.verdict(self.left, processes.alive).confirmed:
                return {"failed": LEFT}
            said, done = chat(shared, project, question, settings)
            t = done.termination if done else None
            gone = done is None or (t is not None and t.confirmed)
            left = dict.fromkeys((*t.survivors, *t.unknown) if t else ()) | (done.pids if done else {})
            self.left = {} if gone else left
            return said
        finally:
            self.slot.release()


def machine(shared: DataRepo) -> Settings:
    """This machine's settings outside any project: its layer over the global one over the defaults."""
    glob = read_layer(shared.global_path, GlobalLayer)
    return resolve(glob, Layer(), read_layer(local_home.root() / MACHINE_SETTINGS, MachineLayer))


def answered(done: Run, found: list[Decision]) -> dict[str, Any]:
    """The decisions the session picked, each whole with its scope and origin; else why the lookup failed."""
    said = pick.judged(done, found, Pick(version=0))
    if said.status != "ok":
        return {"failed": said.reason}
    by_id = {d.id: d for d in found}
    rows = [_row(by_id[p.id], p.note) for p in said.decisions]
    return {"decisions": rows} | ({"dropped": said.dropped} if said.dropped else {})


def _row(d: Decision, note: str) -> dict[str, str]:
    row = {"id": d.id, "title": d.title, "statement": d.statement, "scope": str(d.scope), "origin": str(d.origin)}
    return row | ({"note": note} if note else {})


def _ran(settings: Settings, prefix: str, said: str, journal: sdk_adapter.Journal) -> Run:
    """One picker session in an empty folder, no longer than a caller waits for it."""
    sessions.granted(LABEL)
    limit = min(roles.limit(settings, pick.LABEL), pick_tools.LIMIT)
    with tempfile.TemporaryDirectory(prefix="owlbear-lookup-") as folder:
        session = f"{prefix}-{LABEL}-{uuid.uuid4().hex[:8]}"
        return asyncio.run(sdk_adapter.run(pick.config(settings, Path(folder), session, said, journal, limit)))


def _one(text: str) -> str:
    return " ".join(text.split())[:300]


class Asked:
    """A step's ``lookup_decisions``, one at a time within the worker's turn.

    A lookup reads the Change the runner holds and never writes it: its run waits until `settled` closes admission,
    waits for every lookup admitted and counts their spend on the Change the runner holds then.
    """

    def __init__(self, store: Store, lock: Lock, current: Callable[[], Change]) -> None:
        """Bind the step's store and lock, and how to read the Change the runner holds now."""
        self.store, self.lock, self.current = store, lock, current
        self.turn, self.state = threading.Lock(), threading.Condition()  # one picker beside the step's own session
        self.open, self.admitted = True, 0
        self.runs: list[tuple[Run, str]] = []

    def __call__(self, args: tools.Args) -> str:
        """The answer as JSON; whatever goes wrong is a failed lookup, never the step's end."""
        question = args.question if isinstance(args, pick_tools.Question) else ""
        with self.state:
            if not self.open:
                return json.dumps({"failed": ENDED})
            self.admitted += 1
        try:
            with self.turn:
                return json.dumps(self._answer(question))
        finally:
            with self.state:
                self.admitted -= 1
                self.state.notify_all()

    def _answer(self, question: str) -> dict[str, Any]:
        with self.state:
            if not self.open:  # the step settled while this call waited its turn
                return {"failed": ENDED}
        try:
            said, done = worker(self.store, self.lock, self.current(), question)
        except Exception as exc:  # noqa: BLE001 - a lookup that cannot run is failed, never "none apply"
            return {"failed": _one(f"{type(exc).__name__}: {exc}")}
        if done is not None:
            with self.state:
                self.runs.append((done, "failed" if "failed" in said else "ok"))
        return said

    def helper(self) -> tuple[tools.Spec, Callable[[tools.Args], str]]:
        """The step's tool and its answer."""
        return pick_tools.LOOKUP, self

    def settled[T](self, step: Callable[[], T]) -> T:
        """*step*'s run; then no lookup starts, those admitted end and their spend is on the Change the runner holds."""
        try:
            return step()
        finally:
            with self.state:
                self.open = False
                self.state.wait_for(lambda: self.admitted == 0)
                runs, self.runs = self.runs, []
            for done, end in runs:
                sessions.logged(self.store, self.lock, self.current(), done, {"kind": LABEL, "exit": end})
