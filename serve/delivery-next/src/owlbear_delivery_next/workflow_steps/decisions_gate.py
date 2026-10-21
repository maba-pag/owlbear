"""The runner's decision gate at each step boundary (TD-419 slice 4, §7): the rules a step works by, or why not.

A Change with an approved brief runs a step only on decisions that load (`decision_store.load`), none of those that
apply conflicted or invalid, and the applying ones unchanged since its baseline; a difference asks the owner, and the
approved brief is never rewritten (TD-428). A project without a shared data repository runs as before until one of
its Changes holds a baseline: Changes from before this gate have no rules to compare with.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_decisions import Scope, State, applies
from owlbear_delivery_next.change_contracts.decision_records import DecisionBaseline, Said
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, StepKind, Stop
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.decision_baseline import PREFIX
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.runtimes import step_decisions
from owlbear_delivery_next.state_store import decision_store, read_backs
from owlbear_delivery_next.workflow_steps import before, check, engine, prepare

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any

    from owlbear_decisions import Decision, Entry, Queued, Snapshot
    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.state_store.decision_store import DataView
    from owlbear_delivery_next.state_store.store import Lock, Store

UNGATED = frozenset({StepKind.SHAPE, StepKind.CLEANUP})  # shaping waits for chat; an ending Change always cleans up
ROLES: dict[StepKind, tuple[str, ...]] = {  # the sessions a step's inputs are built for
    StepKind.PLAN: ("planner", "challenger"),
    StepKind.TESTS: ("test-reviewer", "test-curator"),
    StepKind.BUILD: ("builder", "challenger", "test-curator"),
    StepKind.REVIEW: ("reviewer", "challenger"),
    StepKind.CHECK: ("preparer", "reviewer", "design-judge"),
    StepKind.INTEGRATE: ("builder",),
}
OPTIONS = [
    Option(id="continue", label="Continue with the current decisions", next="accept"),
    Option(id="pause", label="Pause", next="pause"),
]
FAULTY = "Resolve the decision's conflict or finding in the shared data repository"
SPLIT = "the decisions that apply do not fit into one step; split the Change"
CHANGED = "Decisions that apply to this Change changed since its brief was approved:"
UNPINNED = (
    "The decisions could not be read when this Change's brief was approved. "
    "Decisions in force now (not pinned at approval) that apply to it:"
)
SHOWN = 3  # read-backs a checkpoint shows; the rest wait on the Decisions page (TD-427)
WAITING = "Read-backs waiting that apply to this Change (optional: answer them on the Decisions page):"


@dataclass(frozen=True)
class Applied:
    """An in-force decision that applies to the Change; *resolved* is False when its scope cannot tell yet."""

    entry: Entry
    resolved: bool


@dataclass(frozen=True)
class Gate:
    """The gate's verdict: the Change (a baseline pinned when *pinned*), a stop or question, or the step's section."""

    change: Change
    result: StepResult | None = None
    lines: list[str] | None = None
    pinned: bool = False


def stem(c: Change) -> str:
    """The Change's record stem, which its own Change decisions name (`change_record`)."""
    return f"{c.brief.approved_at:%Y%m%d-%H%M%S}-{c.slug}" if c.brief.approved_at else ""


def scope(c: Change) -> list[str]:
    """The Change's scope paths: its brief's, then its plan tasks'."""
    tasks = c.plan.tasks if c.plan else []
    return list(dict.fromkeys([*c.brief.scope, *(p for t in tasks for p in t.scope)]))


def _own(d: Decision, c: Change) -> bool:
    return d.state is State.IN_FORCE and (d.scope is not Scope.CHANGE or d.change == stem(c))


def applying(seen: Snapshot, c: Change, role: str | None = None, step: str | None = None) -> list[Applied]:
    """The in-force decisions that apply to the Change, for any role and step unless named."""
    paths, own = scope(c), stem(c)
    found = [(e, applies(e.decision, paths=paths, role=role, step=step, change=own)) for e in seen.entries]
    return [Applied(e, resolved=said is True) for e, said in found if said is not False]


def baseline(view: DataView, c: Change, now: datetime, found: list[Applied] | None = None) -> DecisionBaseline:
    """Every decision in force in the project's view by revision, and the wording of those that apply."""
    seen = view.snapshot
    found = applying(seen, c) if found is None else found
    said = {d.id: Said(title=d.title, statement=d.statement) for d in (a.entry.decision for a in found)}
    revisions = {e.decision.id: e.decision.rule_revision for e in seen.entries if _own(e.decision, c)}
    return DecisionBaseline(commit=view.commit, at=now, revisions=revisions, said=said)


def pinned(store: Store, c: Change, now: datetime) -> tuple[DecisionBaseline | None, bool]:
    """The baseline a brief approval pins, and whether one is owed: none without a data repository, owed unread."""
    if store.shared is None:
        return None, False
    try:
        return baseline(decision_store.load(store.shared, store.name), c, now), False
    except decision_store.DecisionsUnavailable:
        return None, True


def _quoted(text: str) -> str:
    return '"' + " ".join(text.split()) + '"'


def differences(seen: Snapshot, pinned_at: DecisionBaseline, now: DecisionBaseline) -> list[str]:
    """One line per decision that applies now or applied when pinned and is new, changed or no longer in force.

    A decision that applies to neither is irrelevant to the Change, whatever became of it.
    """
    lines = []
    for key in sorted(now.said.keys() | pinned_at.said.keys()):
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
            gone = "" if key in now.said else " (no longer applies to this Change)"
            lines.append(f"- changed: {key} {title}: was {was}; now {_quoted(entry.decision.statement)}{gone}")
    return lines


def unpinned(now: DecisionBaseline) -> list[str]:
    """The decisions in force now that apply, each whole, then how many others are in force."""
    lines = [f"- {key} {' '.join(s.title.split())}: {_quoted(s.statement)}" for key, s in sorted(now.said.items())]
    if others := len(now.revisions.keys() - now.said.keys()):
        lines.append(f"{others} other decision(s) in force do not apply to this Change.")
    return lines or ["- none in force applies to this Change"]


def _faulty(seen: Snapshot, found: list[Applied]) -> list[str]:
    """The applying decisions flagged `conflict` or involved in a finding, each with why."""
    bad = []
    for a in found:
        d = a.entry.decision
        why = ["flagged conflict"] if d.conflict else []
        why += [f"{f.rule}: {f.message}" for f in seen.findings_for(d.id)]
        if why:
            bad.append(f"{d.id} ({'; '.join(why)})")
    return bad


def _stopped(kind: ErrorKind, reason: str, action: str, resume: str, now: datetime) -> StepResult:
    stop = Stop(kind=kind, reason=reason[:600], action=action, resume=resume, at=now)
    return StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)


def _asked(c: Change, now: DecisionBaseline, head: str, lines: list[str], shown: Sequence[str] = ()) -> Gate:
    """The owner's question: Continue pins *now*, the set shown; Pause keeps what the Change holds.

    The read-backs waiting (*shown*) are listed after it, never part of what Continue accepts nor of its identity.
    """
    digest = hashlib.sha256("\n".join([head, *lines]).encode()).hexdigest()[:12]
    text = "\n".join([head, *lines])
    text += "\nContinue works by the decisions now in force; the approved brief stays as it is."
    text += "".join(f"\n{line}" for line in shown)
    asked = engine.ask(c.step.kind, text, f"{PREFIX}{c.step.kind}:{digest}", OPTIONS)
    return Gate(c.model_copy(update={"decisions_offered": now}), asked)


def waiting(store: Store, view: DataView, c: Change) -> list[Queued]:
    """The read-backs waiting that apply to the Change, in queue order; they never block it."""
    paths, own = scope(c), stem(c)
    found = read_backs.waiting(store, view)
    return [q for q in found if applies(q.decision, paths=paths, role=None, step=None, change=own) is not False]


def _waiting_lines(store: Store, view: DataView, c: Change) -> list[str]:
    found = waiting(store, view, c)
    if not found:
        return []
    lines = [WAITING, *(f"- {q.kind}: {q.decision.id} {_quoted(q.decision.title)}: {q.why}" for q in found[:SHOWN])]
    return lines + ([f"{len(found) - SHOWN} more wait on the Decisions page."] if len(found) > SHOWN else [])


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


def context(c: Change, found: list[Applied], in_force: int) -> list[str]:
    """The step's section: the decisions that apply to one of its sessions' roles, whole, and how many do not."""
    roles: tuple[str | None, ...] = ROLES.get(c.step.kind, (None,))
    step, listed = str(c.step.kind), []
    for a in found:
        said = {applies(a.entry.decision, paths=scope(c), role=r, step=step, change=stem(c)) for r in roles}
        if said - {False}:
            listed.append((a.entry.decision, True in said))
    replaced = {d.replaces for d in c.brief.decisions if d.replaces}
    return step_decisions.section(listed, in_force - len(listed), replaced)


def check_step(store: Store, c: Change, now: datetime) -> Gate:
    """The decisions a step of *c* works by, or the stop or question that keeps it from starting."""
    if c.brief.approved_version is None or c.step.kind in UNGATED:
        return Gate(c)
    if store.shared is None and c.decisions_baseline is None and c.decisions_unpinned_at is None:
        return Gate(c, lines=[step_decisions.HEAD, step_decisions.NONE])
    try:
        view = decision_store.load(store.shared, store.name)
    except decision_store.DecisionsUnavailable as exc:
        return Gate(c, StepResult(exit=Exit.STOP, reason=str(exc)[:600], stop=exc.stop(now)))
    return _judged(view, c, now, store)


def _judged(view: DataView, c: Change, now: datetime, store: Store) -> Gate:
    """The loaded decisions against the Change: faults stop it, differences ask, the rest is its section."""
    found = applying(view.snapshot, c)
    if bad := _faulty(view.snapshot, found):
        reason = f"decisions that apply to this Change are conflicted or invalid: {', '.join(bad)}"
        return Gate(c, _stopped(ErrorKind.STATE, reason, FAULTY, "The decisions that apply are valid", now))
    current = baseline(view, c, now, found)
    if c.decisions_baseline is None and c.decisions_unpinned_at is not None:  # its approval could not pin them
        return _asked(c, current, UNPINNED, unpinned(current), _waiting_lines(store, view, c))
    pinning = c.decisions_baseline is None  # a Change approved before this gate
    if pinning:
        c = c.model_copy(update={"decisions_baseline": current})
    elif lines := differences(view.snapshot, c.decisions_baseline, current):
        return _asked(c, current, CHANGED, lines, _waiting_lines(store, view, c))
    lines = context(c, found, len(current.revisions))
    if step_decisions.size(lines) > step_decisions.BUDGET:
        return Gate(c, _stopped(ErrorKind.STATE, SPLIT, "Split the Change", "The decisions that apply fit", now))
    return Gate(c, lines=lines, pinned=pinning)


def launch(store: Store, c: Change, now: datetime) -> tuple[Change, bool]:
    """The gate before the host launches a check environment: the Change as it goes on, and whether it launches."""
    gate = check_step(store, c, now)
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
    gate = check_step(store, c, now)
    if gate.result is not None:
        event = {"event": "step", "at": now.isoformat(timespec="seconds"), "kind": step.kind}
        store.log(lock, c.slug, event | {"exit": gate.result.exit, "reason": gate.result.reason[:300]})
        store.write(lock, loop.apply(gate.change, gate.result, now))
        yield None
        return
    if gate.pinned:
        store.write(lock, gate.change)
    with step_decisions.using(gate.lines):
        yield gate.change
