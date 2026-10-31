"""Retro's runs that judge no unit (#716): a redirected proposal's redraft and a finding's follow-up.

Each is one run of the job, from the button: admitted, limited, leased and recorded as any Retro run, with one paid
call; it holds no unit revision, so its end settles none.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import followups, retro_redraft
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_synthetic as syn
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
    """The run a button *request* for a synthetic unit, a redraft or a follow-up asks for; None for a Change or chat."""
    if named := request.get("synthetic"):
        spec = syn.specs(named)[0]
        return Running(syn.unit_id(spec), "button", request.get("by", ""), provenance="synthetic", spec=spec["name"])
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
    places = {pid: targets.Place(st.name, repo) for pid, (st, repo) in projects.items()}
    unit = {"mode": ctx.mode, "subject": sid, "places": places}
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
