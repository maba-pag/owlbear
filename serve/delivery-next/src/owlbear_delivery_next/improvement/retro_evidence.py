"""What a Retro run reads about its unit (#715): a Change's outcome, a chat's last word, and what a run would ask.

``plan`` counts a run's judging batches with no paid call, for the ``retro --plan`` command and the job alike.
"""

from __future__ import annotations

import contextlib
import json
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import retro_judge, retro_segments
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_synthetic as syn
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.retro_calls import Paid, Work, key
from owlbear_delivery_next.improvement.retro_segments import dumps
from owlbear_delivery_next.local_system import mask

if TYPE_CHECKING:
    from collections.abc import Mapping

    from owlbear_delivery_next.improvement.retro_segments import Prepared

EVENTS, ACTIVITY = 200, 6_000  # a Change's activity events read; the characters they take in a message, newest kept


def outcome(uid: str, projects: units.Projects) -> str:
    """How a Change ended, as Retro judges its sessions against it: its exit, brief, plan, reviews and spend."""
    pid, slug = uid.split(":", 2)[1:]
    try:
        change = projects[pid][0].read(slug)
    except (*units.UNREADABLE, KeyError):
        return ""
    cut, said = retro_segments.cut, []
    if change.outcome is not None:
        said.append(f"the Change ended {change.outcome.exit}" + (f": {r}" if (r := change.outcome.reason) else ""))
    brief = change.brief
    said += [f"its brief: {cut(brief.outcome, retro_segments.SAID)}"] if brief.outcome else []
    said += [f"criterion {c.id}: {cut(c.text, retro_segments.BRIEF)}" for c in brief.criteria]
    said += [f"decision ({d.origin}): {cut(d.question, 120)} -> {cut(d.answer, 120)}" for d in brief.decisions]
    tasks = change.plan.tasks if change.plan else []
    said += [f"task {t.id} ({t.origin}{', done' if t.done else ''}): {cut(t.title, 120)}" for t in tasks]
    for r in change.reviews:
        said.append(f"{r.task or 'final'} review, round {r.round}: {r.verdict}")
        said += [f"  finding: {cut(f, retro_segments.BRIEF)}" for f in r.findings]
    lower = " at least" if change.spend.unread else ""
    said.append(f"it spent{lower} {change.spend.credits:g} credits")
    tools = [(n, t) for n, t in change.tool_use.tools.items() if t.rejected or t.retries]
    said += [f"tool {n}: {t.calls} calls, {t.rejected} refused, {t.retries} retried" for n, t in tools]
    return "\n".join(said)


def activity(uid: str, projects: units.Projects) -> str:
    """A Change's last ``EVENTS`` activity events, masked, one line each, within ``ACTIVITY`` with the newest kept."""
    pid, slug = uid.split(":", 2)[1:]
    try:
        events = projects[pid][0].events(slug)[-EVENTS:]
    except (*units.UNREADABLE, KeyError):
        return ""
    kept: list[str] = []
    for event in reversed(events):
        line = retro_segments.cut(mask.redact(json.dumps(event, sort_keys=True, default=str)), retro_segments.BRIEF)
        if len(dumps("\n".join([line, *kept]))) - 2 > ACTIVITY:
            break
        kept.insert(0, line)
    return "\n".join(kept)


def last_said(sid: str) -> str:
    """A chat's outcome: what its main agent said last in its capture."""
    said = ""
    with contextlib.suppress(OSError):
        for d in units.events(sid):
            data = d.get("data") if isinstance(d.get("data"), dict) else {}
            if d.get("type") == "assistant.message" and data.get("content") and not data.get("parentToolCallId"):
                said = str(data["content"])
    return said


def evidence(uid: str, unit: Mapping[str, Any], rev: Mapping[str, Any], projects: units.Projects) -> Prepared:
    """What a run of *uid*'s revision *rev* reads: a chat's events with its last word, else sessions and outcome."""
    sessions = list(unit.get("sessions") or ())
    if unit.get("kind") == "chat":
        low, high = int(rev.get("from_events") or 0), int(rev.get("cutoff_events") or 0)
        return retro_segments.prepare(sessions, last_said(sessions[0]), low=low, high=high, per_turn=True)
    prepared = retro_segments.prepare(sessions, outcome(uid, projects))
    prepared.activity = activity(uid, projects)
    return prepared


def _never(_batch: str, _message: str, _agent: str) -> Paid:
    msg = "a plan asks nothing"
    raise store.RetroError(msg)


def plan(uid: str, projects: units.Projects) -> dict[str, Any]:
    """What a run of *uid* would ask now, with no paid call: its judging batches and how many are saved already.

    A unit whose last revision is judged, or that has none, is counted as its next revision would be taken; a
    synthetic unit is installed first, as a run takes it; a chat only once taken, since taking it captures the chat.
    Proposals and reviews are not counted: they depend on what the judging finds.

    Raises:
        RetroError: The unit cannot be described.
    """
    known = store.known().get(uid) or {}
    revs, found = list(known.get("revisions") or []), {r["id"]: r for r in units.records()}
    taken = bool(revs) and revs[-1].get("state") != "judged"
    if uid.startswith(syn.PREFIX):
        spec = syn.specs(uid.removeprefix(syn.PREFIX))[0]
        w, taken = syn.work(spec, syn.install(spec), "plan", _never), True
    elif taken:
        unit, rev = known, revs[-1]
        held = [found[i] for i in rev.get("records") or () if i in found]
        w = Work("plan", uid, rev, unit, held, evidence(uid, unit, rev, projects), _never)
    elif uid.startswith("chat:"):
        return {"unit": uid, "taken": False, "why": "a chat is counted once its revision is taken (that captures it)"}
    else:
        unit, graded = units.describe_change(uid, *projects[uid.split(":", 2)[1]]), store.graded()
        held = [r for r in found.values() if units.unit_of(r) == uid and r.get("cutoff") and r["id"] not in graded]
        rev = {"rev": f"r{len(revs) + 1}", "records": [r["id"] for r in held]}
        w = Work("plan", uid, rev, unit, held, evidence(uid, unit, rev, projects), _never)
    keys = [key(w, "judge", message) for *_, message in retro_judge.judging(w)]
    return {
        "unit": uid,
        "rev": w.rev["rev"],
        "taken": taken,
        "records": len(w.records),
        "judge_batches": len(keys),
        "saved": sum(store.saved(k) is not None for k in keys),
        "attempts": sum(len(store.attempts(k)) for k in keys),
    }
