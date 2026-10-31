"""What Retro's job reads around a run (#715): its settings, where it spends, and what pruning may remove or keeps.

``Running`` is one run as the job holds it and as its ``opened`` line keeps it, so a restarted host takes it up.
"""

from __future__ import annotations

import contextlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions, cases, chatlogs, retro_judge
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_synthetic as syn
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.machine_host import cases_job
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import machine_settings, registry, spend_ledger

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.profile_record import RoleModel
    from owlbear_delivery_next.improvement.credit_meter import Meter


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


def _changes(uid: str) -> set[tuple[str, str]]:
    """The (project, Change) pairs run unit *uid* is about: a Change's, a proposal's or a finding's (or record's)."""
    kind, _, sid = uid.partition(":")
    if kind == "proposal":
        of = targets.units_of()
        about = [of.get(f, "") for f in (props.folded().get(sid) or {}).get("findings") or ()]
    elif kind == "finding":
        about = [str(f.get("unit") or "") for f in store.all_findings() if f["id"] == sid]
        about = about or [units.unit_of(r) for r in units.records() if r.get("id") == sid]
    else:
        about = [uid]
    return {(p, c) for u in about if u.startswith("chg:") for p, _, c in [u[4:].partition(":")] if c}


def where(uid: str, projects: units.Projects) -> spend_ledger.Where:
    """Where a run of *uid* spends: the one loaded project its Changes are in, with its Change if one; else machine."""
    pairs = _changes(uid)
    if len({pid for pid, _ in pairs}) != 1 or (pid := next(iter(pairs))[0]) not in projects:
        return spend_ledger.Where(job="retro")
    st, repo = projects[pid]
    more = {"change": next(iter(pairs))[1]} if len(pairs) == 1 else {}
    return spend_ledger.Where.of(st, repo, job="retro", **more)


def _at(text: str) -> datetime:
    at = datetime.fromisoformat(text)
    return at if at.tzinfo else at.replace(tzinfo=UTC)


def judged_sessions() -> dict[str, datetime]:
    """Each real session whose capture is judged as it is now, with its judgement time: what pruning may remove."""
    out: dict[str, datetime] = {}
    for unit in store.known().values():
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


def unfinished(uid: str) -> list[dict[str, Any]]:
    """*uid*'s grade-only work whose records are all graded but whose last run ended short of judged, review unsure.

    None once a later run of *uid* ended judged, since review takes every due proposal. The button finishes it with the
    saved answers replayed; records still ungraded are ``units.late``'s.
    """
    last: dict[tuple[str, tuple[str, ...]], str] = {}
    for r in store.run_states().values():
        if r.get("unit") != uid or r["state"] != "ended":
            continue
        if r["result"] == "judged":
            last.clear()
        if r.get("mode") == "grade-only":
            last[r.get("rev", ""), tuple(r.get("records") or ())] = r["result"]
    graded = store.graded()
    return [
        {"rev": rev, "records": list(ids)}
        for (rev, ids), result in last.items()
        if result != "judged" and rev and set(ids) <= graded
    ]


def failed_grading() -> set[tuple[str, str]]:
    """Each (unit, revision) whose last grade-only run ended short of judged: its late records wait for the button.

    A run its unset settings held before any work (#808) is not one: its records are offered again once they are set.
    """
    last: dict[tuple[str, str], str] = {}
    for r in store.run_states().values():  # in the order the runs opened
        if r.get("mode") == "grade-only" and r["state"] == "ended" and not r.get("held"):
            last[r.get("unit", ""), r.get("rev", "")] = r["result"]
    return {key for key, result in last.items() if result != "judged"}


def settle_open(live: set[tuple[str, str]]) -> None:
    """On restore, settle each open revision no *live* run holds: as its run ended when that end was kept, else stopped.

    A host that stopped between a run's end and its revision's settling left the revision open; its run says how.
    """
    runs = store.run_states()
    for uid, unit in store.known().items():
        for rev in unit.get("revisions") or ():
            if rev.get("state") not in units.OPEN or (uid, rev["rev"]) in live:
                continue
            if (run := runs.get(rev.get("run") or "", {})).get("state") == "ended":
                units.settle(uid, rev["rev"], run["result"].split(":", 1)[0], run=rev["run"], result=run["result"])
            else:
                units.settle(uid, rev["rev"], "stopped", result="stopped: its run was interrupted")


def pinned() -> set[str]:
    """The sessions a finding, a Spotter or pilot case or an open proposal rests on: never pruned."""
    found = store.all_findings()
    pins = {s for f in found for s in f.get("sessions") or ()}
    for path in cases.place().glob("c-*.json"):
        with contextlib.suppress(OSError, ValueError, AttributeError):
            prov = json.loads(path.read_text()).get("provenance") or {}  # a synthetic case has no session
            pins |= {str(p["session"]) for p in (prov.get("record"), prov.get("pilot")) if p and p.get("session")}
    owner = {f["id"]: f.get("unit") for f in found} | {g["id"]: g.get("unit") for g in store.grades(synthetic=True)}
    known = store.known()
    for snap in props.folded().values():
        if snap.get("state") not in props.CLOSED:
            for fid in snap.get("findings") or ():
                pins |= set(known.get(owner.get(fid) or "", {}).get("sessions") or ())
    return pins - {""}


def prune(say: Callable[[str], None]) -> None:
    """Remove the captures of judged chats nothing pins, saying how many or why it could not."""
    try:
        gone = chatlogs.prune(datetime.now(UTC), judged_sessions(), pinned())
    except (store.RetroError, OSError, ValueError) as exc:
        say(f"Retro could not prune judged captures: {type(exc).__name__}: {exc}")
        return
    if gone:
        say(f"Retro pruned the captures of {len(gone)} judged sessions")


NEEDS = (*retro_judge.NEEDS, assumptions.RETRO_LESSON_BAR, assumptions.RETRO_CATCHABLE)  # what every run rests on


@dataclass
class Running:
    """One run: the unit revision it judges, how it was asked for, and its allowance."""

    uid: str
    trigger: str  # "button", "change" or "idle"
    by: str = ""
    rev: str = ""  # "" until its revision is taken
    provenance: str = "real"
    mode: str = "judge"  # or "grade-only", or retro_more's "redraft" or "followup"
    records: list[str] = field(default_factory=list)  # a grade-only run's records
    spec: str = ""  # a synthetic unit's name
    id: str = field(default_factory=lambda: f"rr-{uuid.uuid4().hex[:12]}")
    limit: float = 0.0
    spent: float = 0.0  # what it spent before this host took it up
    known: bool = True
    meter: Meter | None = None
    why: str = ""  # why it waits
    unended: bool = False  # a session's end was not confirmed: the run ends at its next call
    new: bool = False  # opened by this host and not yet admitted: its first admission rechecks its settings

    @classmethod
    def of(cls, snap: dict[str, Any]) -> Running:
        """A run as its kept snapshot has it, after a restart."""
        keep = ("trigger", "by", "rev", "provenance", "mode", "records", "spec", "id", "limit", "spent", "known")
        return cls(uid=snap.get("unit", ""), **{k: snap[k] for k in keep if k in snap})

    @property
    def reads_real(self) -> bool:
        """Whether this run reads a real unit, its eligibility checked: not synthetic, a redraft or a follow-up."""
        return self.provenance == "real" and self.mode in {"judge", "grade-only"}

    @property
    def needs(self) -> tuple[str, ...]:
        """The assumptions this run rests on."""
        return (*NEEDS, *(syn.NEEDS if self.provenance == "synthetic" else ()))

    def retired(self) -> str:
        """Why this run may not go on: the assumptions it rests on retired now; "" while none is."""
        gone = [n for n in self.needs if not assumptions.ensure(n)]
        return f"refused: it rests on retired assumptions ({', '.join(gone)})" if gone else ""
