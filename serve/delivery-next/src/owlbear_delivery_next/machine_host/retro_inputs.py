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

from owlbear_delivery_next.improvement import cases
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.machine_host import cases_job
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import machine_settings, registry, spend_ledger

if TYPE_CHECKING:
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
