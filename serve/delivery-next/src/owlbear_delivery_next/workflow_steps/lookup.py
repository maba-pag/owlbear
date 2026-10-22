"""The decision lookup (TD-456, TD-459): a worker's or a lead chat's question, answered by the picker.

One SDK session on the picker's role reads the complete list of decisions in force (Global and the project's, and a
Change's own for its worker), the correction logs, the Change's brief and the question, and submits the ids that
govern the answer; the reply lists each whole. Decisions that do not load, or any other ending, give
``{"failed": reason}``, never an empty answer. A lookup answers and attaches nothing: the Change's pinned set changes
only at a step boundary. A worker's lookup counts its spend on the Change like a pick; a lead chat's has no Change.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import threading
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_decisions import Scope, State
from owlbear_delivery_next.change_contracts import pick_tools
from owlbear_delivery_next.change_contracts.decision_records import Pick
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer, resolve
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, StoreError, read_layer
from owlbear_delivery_next.workflow_steps import decisions_gate, pick, sessions

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_decisions import Decision
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


def worker(store: Store, lock: Lock, c: Change, question: str) -> dict[str, Any]:
    """The picker's answer to a worker of *c*, over every decision in force for it; its spend counts on *c*."""
    if store.shared is None:
        return {"failed": NO_SHARED}
    try:
        view = decision_store.load(store.shared, store.name)
        log, settings = pick.corrections(view.snapshot.root, store.name), store.settings()
    except (StoreError, OSError, ValueError) as exc:
        return {"failed": _one(str(exc))}
    found = decisions_gate.in_force(view.snapshot, c)
    if not found:
        return {"decisions": [], "note": NONE}
    journal = sdk_adapter.Journal(lambda e: store.log(lock, c.slug, e))
    done = _ran(settings, c.slug, pick.message(c, found, log, ASKED, question), journal)
    said = answered(done, found)
    sessions.logged(store, lock, c, done, {"kind": LABEL, "exit": "failed" if "failed" in said else "ok"})
    return said


def chat(
    shared: DataRepo | None, project: str, question: str, settings: Callable[[], Settings] | None
) -> dict[str, Any]:
    """The picker's answer to a lead chat over the project's and Global decisions in force.

    *settings* are the project's; without them (OwlBear's own decisions on the machine host) this machine's.
    """
    if shared is None:
        return {"failed": NO_SHARED}
    try:
        view = decision_store.load(shared, project)
        log, resolved = pick.corrections(view.snapshot.root, project), settings() if settings else machine(shared)
    except (StoreError, OSError, ValueError) as exc:
        return {"failed": _one(str(exc))}
    found = [
        e.decision for e in view.snapshot.entries
        if e.decision.state is State.IN_FORCE and e.decision.scope is not Scope.CHANGE
    ]  # fmt: skip
    if not found:
        return {"decisions": [], "note": NONE}
    try:
        done = _ran(
            resolved, project or "global", pick.message(None, found, log, ASKED, question), sdk_adapter.Journal()
        )
    except Exception as exc:  # noqa: BLE001 - a lookup that cannot run is failed, never "none apply"
        return {"failed": _one(f"{type(exc).__name__}: {exc}")}
    return answered(done, found)


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
    """A step's ``lookup_decisions``, answered within the worker's turn; the runner waits for one still running."""

    def __init__(self, store: Store, lock: Lock, current: Callable[[], Change]) -> None:
        """Bind the step's store and lock, and how to read the Change the runner holds now."""
        self.store, self.lock, self.current, self.busy = store, lock, current, threading.Lock()

    def __call__(self, args: tools.Args) -> str:
        """The answer as JSON; whatever goes wrong is a failed lookup, never the step's end."""
        question = args.question if isinstance(args, pick_tools.Question) else ""
        with self.busy:
            try:
                said = worker(self.store, self.lock, self.current(), question)
            except Exception as exc:  # noqa: BLE001 - a lookup that cannot run is failed, never "none apply"
                said = {"failed": _one(f"{type(exc).__name__}: {exc}")}
        return json.dumps(said)

    def helper(self) -> tuple[tools.Spec, Callable[[tools.Args], str]]:
        """The step's tool and its answer."""
        return pick_tools.LOOKUP, self

    def settled[T](self, done: T) -> T:
        """*done*, once no lookup runs: its spend is on the Change before the runner writes it."""
        with self.busy:
            return done
