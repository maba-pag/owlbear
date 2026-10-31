"""A redirected proposal's redraft (#716, Improvement design §6): one ``retro-review`` call, then a new proposal.

The owner's redirect says what to change. The redraft keeps the prior's kind, findings and provenance; one paid call
redrafts its cause, target and mechanism as directed and challenges the redraft as a review would, so it comes back
``waiting`` with its publishable text, or ``rejected`` with the reason. No other proposal is reviewed or paid for. An
unusable answer or the run's limit stops the run before anything is filed; the redirected card offers it again.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import retro_bars, retro_judge
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement.retro_calls import StoppedError, paid, strings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from owlbear_delivery_next.improvement.retro_calls import Work

PROMPT = Path(__file__).with_name("retro_redraft_prompt.md")
ABOUT = 300  # characters of a redraft's cause, target and mechanism each


def render(snap: Mapping[str, Any]) -> str:
    """The redraft's message: the proposal as a review sees it, its last review, provenance, assumptions, direction."""
    more = {
        "prior_review": {k: snap.get(k) for k in ("verdict", "why", "publishable")},
        "provenance": snap.get("provenance"),
        "assumptions": list(snap.get("assumptions") or ()),
        "direction": snap.get("direction", ""),
    }
    if snap.get("kind") == "spotter-case":
        more |= {"record": snap.get("record", ""), "call": snap.get("call", "")}
    return retro_judge.render(snap, retro_judge.seen_findings(), prompt=PROMPT, more=more)


def _valid(said: Mapping[str, Any]) -> bool:
    about = [said.get(k) for k in ("cause", "target", "mechanism", "call")]
    return (
        retro_judge.valid_review(said)
        and all(isinstance(v or "", str) for v in about)
        and bool(str(said.get("mechanism") or "").strip())
        and strings(said.get("assumptions") or [])
    )


def run(w: Work, pid: str) -> dict[str, Any]:
    """Redraft the redirected proposal *pid* in one paid call; the redraft's id and how many reviews were made.

    Raises:
        StoppedError: *pid* is not redirected, the answer is unusable or the run's limit is reached; nothing filed.
    """
    snap = props.folded().get(pid)
    if snap is None or snap["state"] != "redirected":
        msg = f"refused: proposal {pid} is {'unknown' if snap is None else snap['state']}, not redirected"
        raise StoppedError(msg)
    if snap["redraft"]:
        return {"redraft": snap["redraft"], "reviews": 0}
    said = dict(paid(w, f"redraft:{pid}", render(snap), _valid, "retro-review"))
    said |= {k: str(said.get(k) or "")[:ABOUT] for k in ("cause", "target", "mechanism")}
    if said["cause"] not in retro_bars.CAUSES:
        said["cause"] = "other"
    read = [f"read the direction as: {a}" for a in said.get("assumptions") or ()]
    said["risks"] = [*(said.get("risks") or ()), *read]
    new = props.redrafted(pid, said, snap["direction"])
    fresh = props.folded()[new]
    props.reviewed(new, fresh["evidence"], retro_judge.settled(fresh, said))
    return {"redraft": new, "reviews": 1}
