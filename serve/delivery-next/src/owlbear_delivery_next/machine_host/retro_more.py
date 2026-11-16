"""Extra requested Retro runs: grade corrections, proposal redrafts and finding follow-ups.

Each is admitted, limited, leased and recorded as any Retro run. Redrafts and follow-ups need no unit evidence;
corrections use the normal judge with the request's exact cohort. None settles the original unit revision.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import followups, improvement_view, retro_redraft
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement.retro_calls import Work
from owlbear_delivery_next.improvement.retro_segments import Prepared
from owlbear_delivery_next.machine_host.retro_inputs import Running

if TYPE_CHECKING:
    from collections.abc import Mapping

    from owlbear_delivery_next.improvement import retro_units as units
    from owlbear_delivery_next.improvement.retro_calls import Ask

MODES = ("redraft", "followup")
UNIT = {"redraft": "proposal", "followup": "finding"}  # a run's unit id: ``<kind>:<subject id>``


def running(request: Mapping[str, Any]) -> Running | None:
    """An extra requested run; None for an ordinary Change or chat request."""
    if named := request.get("synthetic"):
        return Running(f"syn:{named}", "button", request.get("by", ""), provenance="synthetic")
    if request.get("corrections"):
        return Running(f"chg:{request['change']}", "button", request.get("by", ""), rev=request["revision"],
                       mode="correct-grades", records=list(request["corrections"]))  # fmt: skip
    mode = next((m for m in MODES if request.get(m)), "")
    if not mode:
        return None
    sid = str(request[mode])
    if mode == "redraft":
        about = props.folded().get(sid) or {}
    else:
        about = next((f for f in store.all_findings() if f["id"] == sid), {})
    provenance = str(about.get("provenance") or "real")
    return Running(f"{UNIT[mode]}:{sid}", "button", request.get("by", ""), provenance=provenance, mode=mode)


def work(ctx: Running, ask: Ask, projects: units.Projects) -> Work:
    """*ctx*'s work: its subject and the registered projects, no evidence to read."""
    sid = ctx.uid.split(":", 1)[1]
    unit = {"mode": ctx.mode, "subject": sid, "places": improvement_view.places(projects)}
    rev = {"rev": store.digest([ctx.mode, sid])}
    return Work(ctx.id, ctx.uid, rev, unit, [], Prepared(), ask, provenance=ctx.provenance)


def run(w: Work) -> dict[str, Any]:
    """Redraft or follow up *w*'s subject.

    Raises:
        StoppedError: The answer was unusable, the run's limit reached or the subject refused; nothing filed.
        WaitingError: No call may start now; the run waits.
    """
    if w.unit["mode"] == "redraft":
        return retro_redraft.run(w, w.unit["subject"])
    return followups.run(w, w.unit["subject"], w.unit["places"], followups.backlog)
