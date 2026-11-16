"""Explicit repair of grades made with live callback counts or omitted Change repair evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import (
    retro_evidence,
    retro_grade_history,
    retro_judge,
    retro_segments,
    retro_units,
)
from owlbear_delivery_next.improvement import retro_store as store

if TYPE_CHECKING:
    from owlbear_delivery_next.improvement.retro_units import Projects


def plan(uid: str, projects: Projects) -> dict[str, Any]:
    """The exact historical correction cohort, without writing or paying."""
    if not uid.startswith("chg:"):
        msg = "grade evidence repair names a finished Change"
        raise store.RetroError(msg)
    if why := retro_units.eligible(uid, [], projects):
        raise store.RetroError(why)
    unit = store.known().get(uid)
    if not unit or not unit.get("revisions"):
        msg = f"{uid} has no saved Retro revision to correct"
        raise store.RetroError(msg)
    rev = unit["revisions"][-1]
    found = {r["id"]: r for r in retro_units.records() if retro_units.unit_of(r) == uid}
    prepared = retro_evidence.evidence(uid, unit, rev, projects)
    read = {p.session for p in prepared.parts}
    located = {r["id"]: retro_segments.locate(r, prepared)[0] for r in found.values() if r.get("session") in read}
    history = retro_grade_history.effective(store.lines("grades.jsonl"), ())
    corrections = {}
    for grade in history:
        if grade.get("unit") != uid or grade.get("evidence_contract") == retro_grade_history.CONTRACT:
            continue
        if grade["record"] not in found:
            msg = f"grade {grade['id']} cannot be corrected: its Spotter record {grade['record']} is missing"
            raise store.RetroError(msg)
        record = found[grade["record"]]
        if not retro_judge.assessable(record):
            continue
        resolved = located.get(record["id"])
        if record.get("session") not in unit.get("sessions", ()) or resolved is None or resolved != grade.get("cutoff"):
            corrections[record["id"]] = grade["id"]
    return {"unit": uid, "revision": rev["rev"], "records": len(corrections), "corrections": corrections}


def queue(by: str, uid: str, projects: Projects) -> str:
    """Register affected originals as pending and queue their correction through the normal host."""
    with store.locked():
        existing = next(
            (q["id"] for q in store.queued() if q.get("change") == uid.removeprefix("chg:") and q.get("corrections")),
            "",
        )
        if existing:
            return existing
        cohort = plan(uid, projects)
        if not cohort["corrections"]:
            msg = f"{uid} has no affected grades awaiting evidence correction"
            raise store.RetroError(msg)
        return store.request_correction(by, uid.removeprefix("chg:"), cohort["revision"], cohort["corrections"])
