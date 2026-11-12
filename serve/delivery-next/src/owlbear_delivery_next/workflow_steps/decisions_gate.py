"""The runner's decision gate at each step boundary (TD-419 slice 4, TD-456): the rules a step works by, or why not.

A Change with an approved brief runs a step only on decisions that load (`decision_store.load`), none of those pinned
conflicted or invalid; a difference since its baseline is adopted and logged, never asked after approval (#1062,
D-01M6RT4ADHEEH6FFAF6HVW55QZ), and the approved brief is never rewritten (TD-428). Pinned from a pick, the baseline
holds the picked decisions and the Change's own: a decision that came into force or changed since goes, with the others
new at that boundary, to the picker, joins the pinned set when picked and is recorded as considered when not; a failed
pick waits and tries again. Pinned without a pick, it holds every decision in force, and a new one is adopted with it.
Before judging, the gate catches the checkout up with its remote (`decision_store.refresh`); when it cannot, steps go on
with the local decisions but publication and merge, the irreversible ones, stop. A project without a shared data
repository runs as before until one of its Changes holds a baseline: Changes from before this gate have no rules to
compare with.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from owlbear_decisions import Scope, State
from owlbear_delivery_next.change_contracts.decision_records import DecisionBaseline, Said
from owlbear_delivery_next.change_contracts.decision_wording import problem
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, StepKind, Stop
from owlbear_delivery_next.change_flow import loop, picks
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.runtimes import step_decisions
from owlbear_delivery_next.state_store import decision_store, read_backs
from owlbear_delivery_next.state_store.decision_archive import whole
from owlbear_delivery_next.workflow_steps import before, check, pick, prepare, sessions

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from typing import Any

    from owlbear_decisions import Decision, Queued, Snapshot
    from owlbear_delivery_next.change_contracts.decision_records import PickedDecision
    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.state_store.decision_store import DataView
    from owlbear_delivery_next.state_store.store import Lock, Store

_log = logging.getLogger(__name__)
UNGATED = frozenset({StepKind.SHAPE, StepKind.CLEANUP})  # shaping waits for chat; an ending Change always cleans up
IRREVERSIBLE = frozenset({StepKind.PUBLISH, StepKind.MERGE})  # never on decisions another checkout may have changed
FAULTY = "Resolve the decision's conflict or finding in the shared data repository"
STALE = (
    "Let the shared data repository's checkout catch up with its remote (reach the network, commit or discard its "
    'local changes, or resolve what refused the rebase), then press "Done: run the step again" on the Changes page'
)
CHANGED = "Decisions this Change follows changed since its brief was approved:"
UNPINNED = (
    "The decisions could not be read when this Change's brief was approved. "
    "Decisions in force now (not pinned at approval) that it would follow:"
)
REPICK = "the decisions new since this Change's were picked could not be put to the picker"
SHOWN = 3  # read-backs a checkpoint shows; the rest wait on the Decisions page (TD-427)
WAITING = "Read-backs waiting that apply to this Change (optional: answer them on the Decisions page):"


@dataclass(frozen=True)
class Gate:
    """The gate's verdict: the Change (written when *pinned*), a stop or question, or the step's sections."""

    change: Change
    result: StepResult | None = None
    lines: list[str] | None = None
    others: list[str] | None = None  # the complete list a challenger reads besides *lines* (TD-452)
    pinned: bool = False
    refresh_error: str = ""
    adopted: list[str] = field(default_factory=list)  # what changed since approval, logged as adopted (#1062)


def stem(c: Change) -> str:
    """The Change's record stem, which its own Change decisions name (`change_record`)."""
    return f"{c.brief.approved_at:%Y%m%d-%H%M%S}-{c.slug}" if c.brief.approved_at else ""


def reaches(d: Decision, c: Change) -> bool:
    """Whether *d* is in force for *c*: a Global or project decision, or one of *c*'s own Change decisions."""
    return d.state is State.IN_FORCE and (d.scope is not Scope.CHANGE or d.change == stem(c))


def in_force(seen: Snapshot, c: Change) -> list[Decision]:
    """Every decision in force for *c*, in the view's order: the complete list a challenger checks (TD-452)."""
    return [e.decision for e in seen.entries if reaches(e.decision, c)]


def _attached(d: Decision, c: Change) -> bool:
    """One of *c*'s own, pinned without a pick: a Change decision, or one its approval published (TD-453).

    A published one counts only as its approval saved it: changed elsewhere since, the picker judges it like any other.
    """
    return d.scope is Scope.CHANGE or pick.published(c, d)


def _picked(c: Change) -> dict[str, PickedDecision] | None:
    """What *c*'s pick chose, by id; None for a Change approved without one (no data repository, or before picking)."""
    p = c.brief.picked
    return {d.id: d for d in p.decisions} if p is not None and p.status == "ok" else None


def _said(d: Decision) -> Said:
    return Said(title=d.title, statement=whole(d))


def baseline(view: DataView, c: Change, now: datetime) -> DecisionBaseline:
    """The decisions in force considered by rule revision, and the wording of those pinned.

    A first pin from a pick pins the picked decisions as the pick read them, in force or not, and the Change's own;
    it considers what the pick read at the revision it read, so a decision new or changed since stays for the
    picker (`_later`) and a picked one changed since asks the owner (`differences`). A pick saved before it recorded
    what it read counts only its picked ones as read. Without a pick a first pin considers and pins every decision in
    force. A later pin from a pick keeps the pinned set at its current revisions and every other considered one at
    the revision it was considered at.
    """
    found, prior = in_force(view.snapshot, c), c.decisions_baseline
    if prior is not None and prior.picked:
        said = {d.id: _said(d) for d in found if d.id in prior.said or _attached(d, c)}
        held = {d.id: prior.revisions[d.id] for d in found if d.id in prior.revisions}
        revisions = held | {d.id: d.rule_revision for d in found if d.id in said}
        return DecisionBaseline(commit=view.commit, at=now, revisions=revisions, said=said, picked=True)
    chosen = _picked(c) if prior is None else None  # a pin without a pick stays one
    if chosen is None:
        said, revisions = {d.id: _said(d) for d in found}, {d.id: d.rule_revision for d in found}
        return DecisionBaseline(commit=view.commit, at=now, revisions=revisions, said=said, picked=False)
    read, own = c.brief.picked.read, [d for d in found if _attached(d, c)]
    said = {k: Said(title=p.title, statement=p.statement) for k, p in chosen.items()} | {d.id: _said(d) for d in own}
    revisions = {k: p.revision for k, p in chosen.items()} | {d.id: read[d.id] for d in found if d.id in read}
    revisions |= {d.id: d.rule_revision for d in own}
    return DecisionBaseline(commit=view.commit, at=now, revisions=revisions, said=said, picked=True)


def loaded(store: Store) -> DataView | None:
    """The project's decisions as they load now; None without a data repository or when they do not load."""
    if store.shared is None:
        return None
    try:
        return decision_store.load(store.shared, store.name)
    except decision_store.DecisionsUnavailable:
        return None


def pinned(store: Store, c: Change, now: datetime, view: DataView | None) -> tuple[DecisionBaseline | None, bool]:
    """The baseline a brief approval pins from *view* (`loaded`), and whether one is owed.

    None is owed without a data repository; one is owed when the decisions did not load. An approval pins afresh,
    whatever an earlier approval pinned; a retried one of the approved version keeps its pin (`decision_baseline`).
    """
    if view is None:
        return None, store.shared is not None
    return baseline(view, c.model_copy(update={"decisions_baseline": None}), now), False


def _quoted(text: str) -> str:
    return '"' + " ".join(text.split()) + '"'


def differences(seen: Snapshot, pinned_at: DecisionBaseline, now: DecisionBaseline) -> list[str]:
    """One line per pinned decision changed or no longer in force and, for a pin without a pick, per new one.

    A decision new to a pin from a pick goes to the picker instead; one that is not pinned is irrelevant to the
    Change, whatever became of it.
    """
    keys = pinned_at.said.keys() if pinned_at.picked else pinned_at.said.keys() | now.said.keys()
    lines = []
    for key in sorted(keys):
        old, new = pinned_at.revisions.get(key), now.revisions.get(key)
        entry = seen.get(key)
        if old == new or (old is not None and new is not None and entry and old == entry.decision.revision):
            continue  # unchanged; a pin from before rule revisions holds the whole revision
        title = " ".join((entry.decision.title if entry else pinned_at.said[key].title).split())
        was = _quoted(pinned_at.said[key].statement) if key in pinned_at.said else "(its wording was not pinned)"
        if new is None:
            lines.append(f"- no longer in force: {key} {title}: was {was}")
        elif old is None:
            lines.append(f"- new: {key} {title}: {_quoted(now.said[key].statement)}")
        else:
            lines.append(f"- changed: {key} {title}: was {was}; now {_quoted(whole(entry.decision))}")
    return lines


def _recovered(seen: Snapshot, pin: DecisionBaseline) -> DecisionBaseline:
    """*pin* with its pinned decisions as they stand now, for the owner to see and pin; withdrawn ones leave it."""
    now = {k: e.decision for k in pin.said if (e := seen.get(k)) and e.decision.state is State.IN_FORCE}
    revisions = {k: v for k, v in pin.revisions.items() if k not in pin.said} | {
        k: d.rule_revision for k, d in now.items()
    }
    return pin.model_copy(update={"said": {k: _said(d) for k, d in now.items()}, "revisions": revisions})


def unpinned(now: DecisionBaseline) -> list[str]:
    """The decisions in force now that would be pinned, each whole, then how many others the pick left out."""
    lines = [f"- {key} {' '.join(s.title.split())}: {_quoted(s.statement)}" for key, s in sorted(now.said.items())]
    if others := len(now.revisions.keys() - now.said.keys()):
        lines.append(f"{others} other decision(s) in force were not picked for this Change.")
    return lines or ["- none in force"]


def _faulty(seen: Snapshot, c: Change, keys: Iterable[str]) -> list[str]:
    """The decisions in force among *keys* flagged `conflict` or involved in a finding, each with why."""
    bad = []
    for key in sorted(keys):
        if (entry := seen.get(key)) is None or not reaches(d := entry.decision, c):
            continue
        why = ["flagged conflict"] if d.conflict else []
        why += [f"{f.rule}: {f.message}" for f in seen.findings_for(d.id)]
        if why:
            bad.append(f"{d.id} ({'; '.join(why)})")
    return bad


def _stopped(kind: ErrorKind, reason: str, action: str, resume: str, now: datetime) -> StepResult:
    stop = Stop(kind=kind, reason=reason, action=action, resume=resume, at=now)
    return StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)


def _faults(seen: Snapshot, c: Change, keys: Iterable[str], now: datetime) -> Gate | None:
    if not (bad := _faulty(seen, c, keys)):
        return None
    reason = f"decisions this Change follows are conflicted or invalid: {', '.join(bad)}"
    return Gate(c, _stopped(ErrorKind.STATE, reason, FAULTY, "The decisions it follows are valid", now))


def waiting(store: Store, view: DataView, c: Change) -> list[Queued]:
    """The read-backs waiting on decisions in force for the Change, in queue order; they never block it."""
    return [q for q in read_backs.waiting(store, view) if reaches(q.decision, c)]


def checkpoint(store: Store, c: Change) -> dict[str, Any] | None:
    """At most SHOWN read-backs that apply and how many more wait, while the brief awaits approval; else None."""
    if store.shared is None or c.step.kind is not StepKind.SHAPE or c.brief.approved_version == c.brief.version:
        return None
    try:
        view = decision_store.load(store.shared, store.name)
    except decision_store.DecisionsUnavailable:
        return None
    found, ignored = waiting(store, view, c), read_backs.marks(store)["ignored"]
    return {"items": [read_backs.item(q, ignored) for q in found[:SHOWN]], "more": max(0, len(found) - SHOWN)}


def _sections(found: Sequence[Decision], c: Change, keys: Iterable[str]) -> tuple[list[str], list[str]]:
    """Every role's section, the decisions of *keys* whole, and beside it the complete list of the others."""
    keys, replaced = set(keys), {d.replaces for d in c.brief.decisions if d.replaces}
    mine = [d for d in found if d.id in keys]
    return step_decisions.section(mine, replaced), step_decisions.complete([d for d in found if d.id not in keys])


def context(seen: Snapshot, c: Change) -> tuple[list[str], list[str]]:
    """The step's section, the same for every role, and the complete list for its challengers (TD-452, TD-457).

    The section is the pinned set: the decisions picked for the Change and its own; for a Change approved without a
    pick, every decision in force.
    """
    found, pin = in_force(seen, c), c.decisions_baseline
    return _sections(found, c, pin.said if pin is not None and pin.picked else (d.id for d in found))


def shaping(store: Store, c: Change) -> tuple[list[str], list[str]]:
    """A brief challenge's sections: the decisions picked for its version, and the complete list beside them."""
    if store.shared is None:
        return [step_decisions.HEAD, step_decisions.NONE], []
    try:
        view = decision_store.load(store.shared, store.name)
    except decision_store.DecisionsUnavailable as exc:
        return [step_decisions.HEAD, f"- the decisions could not be read: {' '.join(str(exc).split())[:300]}"], []
    p = picks.current(c)
    chosen = {d.id for d in p.decisions} if p is not None and p.status == "ok" else set()
    return _sections(in_force(view.snapshot, c), c, chosen)


def check_step(store: Store, c: Change, now: datetime, lock: Lock | None = None) -> Gate:
    """The decisions a step of *c* works by, or the stop or question that keeps it from starting.

    Only under the runner's *lock* do decisions new since the pick go to the picker; the host's launch leaves them
    to the runner's next step.
    """
    if c.brief.approved_version is None or c.step.kind in UNGATED:
        return Gate(c)
    if store.shared is None and c.decisions_baseline is None and c.decisions_unpinned_at is None:
        return Gate(c, lines=[step_decisions.HEAD, step_decisions.NONE])
    stale = _refresh(store) if store.shared is not None else ""
    if stale and c.step.kind in IRREVERSIBLE:
        reason = f"the decisions were not refreshed before {c.step.kind}, which cannot be undone: {stale}"
        return Gate(
            c,
            _stopped(ErrorKind.STATE, reason, STALE, "The decisions refresh from the remote", now),
            refresh_error=stale,
        )
    try:
        view = decision_store.load(store.shared, store.name)
    except decision_store.DecisionsUnavailable as exc:
        gate = Gate(c, StepResult(exit=Exit.STOP, reason=failure(exc), stop=exc.stop(now)))
    else:
        gate = _wording_faults(view, c, now) or _judged(view, c, now, store, lock)
    return replace(gate, refresh_error=stale)


def _refresh(store: Store) -> str:
    """Why the checkout did not catch up with its remote, else nothing: another checkout's change reaches it first."""
    try:
        return decision_store.refresh(store.shared)
    except decision_store.DecisionsUnavailable as exc:
        return f"not refreshed: {failure(exc)}"


def _faulty_wording(found: Iterable[Decision]) -> list[str]:
    return [why for d in found if (why := problem(d))]


def _wording_faults(view: DataView, c: Change, now: datetime) -> Gate | None:
    """Unrecoverable full wording blocks before baseline construction or any paid reassessment."""
    if faults := _faulty_wording(in_force(view.snapshot, c)):
        stopped = _stopped(ErrorKind.STATE, "; ".join(faults), FAULTY, "The full decision wording is resolved", now)
        return Gate(c, stopped)
    return None


def unworded(view: DataView | None, c: Change) -> str:
    """Why an approval may not pin *c*'s decisions yet: a full wording it pins cannot be read; "" otherwise.

    From a pick it pins the picked decisions and the Change's own; any other one waits for the next step's gate.
    """
    if view is None:
        return ""
    chosen = _picked(c)
    found = [d for d in in_force(view.snapshot, c) if chosen is None or d.id in chosen or _attached(d, c)]
    if not (faults := _faulty_wording(found)):
        return ""
    why = f"the full decision wording is unresolved: {'; '.join(faults)}"
    _log.warning("brief approval refused: %s", why)
    return why


def wording_stop(store: Store, c: Change, now: datetime) -> StepResult | None:
    """The stop a challenger must not start under: an in-force full wording that cannot be read (TD-452)."""
    if store.shared is None:
        return None
    try:
        view = decision_store.load(store.shared, store.name)
    except decision_store.DecisionsUnavailable:
        return None  # the shaping sections report the unreadable decisions themselves
    gate = _wording_faults(view, c, now)
    return gate.result if gate else None


def _judged(view: DataView, c: Change, now: datetime, store: Store, lock: Lock | None) -> Gate:
    """The loaded decisions against the Change: faults stop it, changes to its pinned ones ask, new ones are picked."""
    seen, current = view.snapshot, baseline(view, c, now)
    pin = c.decisions_baseline or current
    if stop := _faults(seen, c, pin.said.keys() | (set() if pin.picked else current.said.keys()), now):
        return stop
    adopted: list[str] = []
    pinning = c.decisions_baseline is None  # a Change approved before this gate, or one its approval could not pin
    if pinning and c.decisions_unpinned_at is not None:
        current = _recovered(seen, current)
        adopted = [UNPINNED, *unpinned(current)]
    elif not pinning and (lines := differences(seen, c.decisions_baseline, current)):
        adopted, pinning = [CHANGED, *lines], True  # #1062: adopted as his Continue did, never asked
    if pinning:
        update = {"decisions_baseline": current, "decisions_unpinned_at": None, "decisions_offered": None}
        c = c.model_copy(update=update)
    if lock is not None and (later := _later(seen, c)):
        if adopted:  # its picker checkpoints the new baseline: the record goes first, so no restart loses it
            _adopted(store, lock, c, adopted, now)
            adopted = []
        c, result = _reassessed(store, lock, view, c, later)
        if result is not None:
            return Gate(c, result, adopted=adopted)  # the adoption already holds: its record goes with it
        if stop := _faults(seen, c, c.decisions_baseline.said, now):
            return replace(stop, adopted=adopted)
        pinning = True
    lines, others = context(seen, c)
    return Gate(c, lines=lines, others=others, pinned=pinning, adopted=adopted)


def _later(seen: Snapshot, c: Change) -> list[Decision]:
    """The decisions in force a pin from a pick has not considered at their rule revision: new or changed since."""
    pin = c.decisions_baseline
    if pin is None or not pin.picked:
        return []
    return [
        d
        for d in in_force(seen, c)
        if d.id not in pin.said and pin.revisions.get(d.id) not in {d.rule_revision, d.revision}
    ]


def _reassessed(
    store: Store, lock: Lock, view: DataView, c: Change, later: list[Decision]
) -> tuple[Change, StepResult | None]:
    """*c* with *later* reassessed: its own attached, the others put to the picker in one batch (TD-456).

    The picked ones join the pinned set; the rest are recorded as considered at their revision. A failed pick waits
    and tries again, never taken for "none apply".
    """
    c = c.model_copy(deep=True)
    others = [d for d in later if not _attached(d, c)]
    wait = timedelta(minutes=1)
    try:
        chosen, why = pick.reassessed(store, lock, c, others, view.snapshot.root) if others else ([], "")
    except sessions.SessionGrantError as exc:  # a step granted no session: the host grants the retry one
        chosen, why, wait = [], f"{exc}; it runs again with one", timedelta(0)
    now = datetime.now(UTC)
    if why:
        cause = cause_key(ErrorKind.NETWORK, c.step.kind, pick.LABEL)
        reason = f"{REPICK}: {why}"
        return c, StepResult(exit=Exit.RETRY, cause=cause, reason=reason, wake_at=now + wait)
    pin = c.decisions_baseline
    pin.revisions |= {d.id: d.rule_revision for d in later}
    pin.said |= {d.id: _said(d) for d in [*(d for d in later if _attached(d, c)), *chosen]}
    pin.commit, pin.at = view.commit, now
    return c, None


def _adopted(store: Store, lock: Lock, c: Change, lines: list[str], now: datetime) -> None:
    at = now.isoformat(timespec="milliseconds")
    store.log(lock, c.slug, {"event": "decisions-adopted", "at": at, "step": c.step.kind, "lines": lines})


def _record(store: Store, lock: Lock, gate: Gate, now: datetime) -> None:
    if gate.adopted:
        _adopted(store, lock, gate.change, gate.adopted, now)
    if gate.refresh_error:
        c = gate.change
        store.log(
            lock,
            c.slug,
            {
                "event": "decisions-refresh-failed",
                "at": now.isoformat(timespec="milliseconds"),
                "step": f"{c.step.kind}:{c.step.task}",
                "reason": gate.refresh_error,
            },
        )


def launch(store: Store, c: Change, now: datetime, *, lock: Lock) -> tuple[Change, bool]:
    """The gate before the host launches a check environment: the Change as it goes on, and whether it launches."""
    gate = check_step(store, c, now)
    _record(store, lock, gate, now)
    if gate.result is None:
        return gate.change, True
    if c.stop is not None and c.stop.reason == gate.result.reason:
        return c, False  # stopped for it already: nothing launches and nothing is recorded twice
    return loop.apply(gate.change, gate.result, now), False


@contextmanager
def gated(store: Store, lock: Lock, c: Change, step: Step | None) -> Iterator[Change | None]:
    """The runner's one gate before a step works: the Change to run with its section held, or None once stopped."""
    works = c.env is None or check.capturing(c) or before.due(c) or prepare.due(store, c)  # a test copy's restore
    if step is None or not works:
        yield c  # nothing works this pass: a host-owned check environment, or a test copy's end
        return
    now = datetime.now(UTC)
    gate = check_step(store, c, now, lock)
    _record(store, lock, gate, now)
    if gate.result is not None:
        event = {"event": "step", "at": now.isoformat(timespec="seconds"), "kind": step.kind}
        store.log(lock, c.slug, event | {"exit": gate.result.exit, "reason": gate.result.reason})
        store.write(lock, loop.apply(gate.change, gate.result, now))
        yield None
        return
    if gate.pinned:
        store.write(lock, gate.change)
    with step_decisions.using(step_decisions.own(gate.lines, gate.change.decisions), gate.others):
        yield gate.change
