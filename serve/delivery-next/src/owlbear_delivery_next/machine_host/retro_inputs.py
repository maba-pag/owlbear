"""What Retro's job reads around a run (#715): its settings, a unit's outcome, and what pruning may remove or keeps.

``Running`` is one run as the job holds it and as its ``opened`` line keeps it, so a restarted host takes it up.
"""

from __future__ import annotations

import contextlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import cases, retro_judge, retro_segments
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_synthetic as syn
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.retro_calls import Paid, Work, key
from owlbear_delivery_next.machine_host import cases_job
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import machine_settings, registry, spend_ledger

if TYPE_CHECKING:
    from collections.abc import Mapping

    from owlbear_delivery_next.change_contracts.profile_record import RoleModel
    from owlbear_delivery_next.improvement.credit_meter import Meter
    from owlbear_delivery_next.improvement.retro_segments import Prepared


def enrolled() -> list[str]:
    """The workspace folders whose chats Retro may read; none when the machine settings cannot be read."""
    try:
        return list(machine_settings.current().enrolled_chats or ())
    except registry.RegistryError:
        return []


def session(agent: str) -> tuple[RoleModel, float]:
    """The model and the time in seconds a session of role *agent* runs with.

    Raises:
        SettingsUnset: The role is unset.
    """
    minutes = cases_job.settings().agent(agent).minutes
    if minutes is None:
        msg = f"agents.{agent}.minutes"
        raise SettingsUnset(msg)
    return cases_job.role(agent), minutes * 60.0


def where(uid: str, projects: units.Projects) -> spend_ledger.Where:
    """Where a run of *uid* spends: its Change's project, else machine-wide."""
    if uid.startswith("chg:"):
        pid, slug = uid.split(":", 2)[1:]
        st, repo = projects[pid]
        return spend_ledger.Where.of(st, repo, change=slug, job="retro")
    return spend_ledger.Where(job="retro")


def outcome(uid: str, projects: units.Projects) -> str:
    """How a Change ended, as Retro judges its sessions against it: its exit and its reviews' verdicts."""
    pid, _, slug = uid.split(":", 2)[1:]
    try:
        change = projects[pid][0].read(slug)
    except (*units.UNREADABLE, KeyError):
        return ""
    said = []
    if change.outcome is not None:
        said.append(f"the Change ended {change.outcome.exit}" + (f": {r}" if (r := change.outcome.reason) else ""))
    said += [f"{r.task or 'final'} review, round {r.round}: {r.verdict}" for r in change.reviews]
    return "\n".join(said)


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
    return retro_segments.prepare(sessions, outcome(uid, projects))


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
    known = store.units().get(uid) or {}
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


def _at(text: str) -> datetime:
    at = datetime.fromisoformat(text)
    return at if at.tzinfo else at.replace(tzinfo=UTC)


def judged_sessions() -> dict[str, datetime]:
    """Each real session whose capture is judged as it is now, with its judgement time: what pruning may remove."""
    out: dict[str, datetime] = {}
    for unit in store.units().values():
        revs = unit.get("revisions") or []
        if unit.get("provenance") == "synthetic" or not unit.get("judged_at") or not revs:
            continue
        sessions = list(unit.get("sessions") or ())
        if unit.get("kind") == "chat" and (
            revs[-1].get("state") != "judged" or revs[-1].get("sha256") != units.fingerprint(sessions[0])["sha256"]
        ):
            continue  # a newer revision not judged yet, or a capture taken since
        out |= dict.fromkeys(sessions, _at(unit["judged_at"]))
    return out


def pinned() -> set[str]:
    """The sessions a finding, a Spotter case or an open proposal rests on: never pruned."""
    found = store.all_findings()
    pins = {s for f in found for s in f.get("sessions") or ()}
    for path in cases.place().glob("c-*.json"):
        with contextlib.suppress(OSError, ValueError, AttributeError):
            pins.add(json.loads(path.read_text())["provenance"]["record"]["session"])
    owner = {f["id"]: f.get("unit") for f in found} | {g["id"]: g.get("unit") for g in store.grades(synthetic=True)}
    known = store.units()
    for snap in props.folded().values():
        if snap.get("state") not in props.CLOSED:
            for fid in snap.get("findings") or ():
                pins |= set(known.get(owner.get(fid) or "", {}).get("sessions") or ())
    return pins - {""}


@dataclass
class Running:
    """One run: the unit revision it judges, how it was asked for, and its allowance."""

    uid: str
    trigger: str  # "button", "change" or "idle"
    by: str = ""
    rev: str = ""  # "" until its revision is taken
    provenance: str = "real"
    mode: str = "judge"  # or "grade-only"
    records: list[str] = field(default_factory=list)  # a grade-only run's records
    spec: str = ""  # a synthetic unit's name
    id: str = field(default_factory=lambda: f"rr-{uuid.uuid4().hex[:12]}")
    limit: float = 0.0
    spent: float = 0.0  # what it spent before this host took it up
    known: bool = True
    meter: Meter | None = None
    why: str = ""  # why it waits
    unended: bool = False  # a session's end was not confirmed: the run ends at its next call

    @classmethod
    def of(cls, snap: dict[str, Any]) -> Running:
        """A run as its kept snapshot has it, after a restart."""
        keep = ("trigger", "by", "rev", "provenance", "mode", "records", "spec", "id", "limit", "spent", "known")
        return cls(uid=snap.get("unit", ""), **{k: snap[k] for k in keep if k in snap})
