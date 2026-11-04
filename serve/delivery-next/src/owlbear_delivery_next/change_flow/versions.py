"""The brief's and the plan's versions on the Change page: each one's state and the challenges that read it.

A version is blue while its challenge runs, red while a finding of its challenge waits for the owner, orange when its
latest full challenge raised findings or did not accept a rejection, green when that challenge was clean, and grey
when no challenge read it. A rejections-only check is no challenge: it shows under the version and changes no colour.
Rounds counted before the loop recorded versions are said as such, and the versions they may have read are "not
recorded", never guessed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.round_records import BRIEF, PLAN, RECHECK
from owlbear_delivery_next.change_flow import brief_rounds, plan_rounds

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.round_records import RoundLoop, Verdict

WORDS = {
    "running": "challenge running",
    "waits": "waits for you",
    "findings": "findings",
    "clean": "clean",
    "unreviewed": "not challenged",
    "unknown": "not recorded",
}
_PLAN_MODES = frozenset({plan_rounds.CHALLENGE, plan_rounds.RECONSIDER, RECHECK})


def _attempts(lp: RoundLoop | None, subject: str) -> list[RoundLoop]:
    """The loop's attempts of *subject* in order: replaced task loops in a plan's history are no plan challenges."""
    return [*(x for x in lp.history if x.subject == subject), lp] if lp else []


def _legacy(attempts: list[RoundLoop]) -> tuple[str, bool]:
    """The line on rounds counted before versions were recorded, and whether there were any."""
    lines = []
    for x in attempts:
        k = x.round - sum(not v.recheck for v in x.verdicts)
        if k <= 0:
            continue
        said = "Challenge 1 ran" if k == 1 else f"Challenges 1 to {k} ran"
        lead = f"Attempt {x.attempt}: " if len(attempts) > 1 else ""
        lines.append(f"{lead}{said} before versions were recorded per challenge")
    return "; ".join(lines), bool(lines)


def _label(v: Verdict, attempt: int, *, many: bool) -> str:
    of = f" of attempt {attempt}" if many else ""
    return f"Rejections checked after challenge {v.round}{of}" if v.recheck else f"Challenge {v.round}{of}"


def _versions(attempts: list[RoundLoop], current: int, *, running: int, waits: int) -> list[dict]:
    """Versions 1 to *current*; *running* and *waits* name the version a challenge runs on or waits for you on."""
    legacy = _legacy(attempts)[1]
    read = [(x, v) for x in attempts for v in x.verdicts]
    earliest = min((v.version for _, v in read), default=current + 1)
    lp = attempts[-1] if attempts else None
    out = []
    for n in range(1, current + 1):
        mine = [(x, v) for x, v in read if v.version == n]
        full = [(x, v) for x, v in mine if not v.recheck]
        if n == running:
            state = "running"
        elif n == waits:
            state = "waits"
        elif full:
            x, v = full[-1]
            state = "findings" if v.upheld or any(f.raised == v.round for f in x.findings) else "clean"
        elif legacy and n < earliest and not (n == current and lp and f"v{n}" in lp.unreviewed):
            state = "unknown"
        else:
            state = "unreviewed"
        many = len(attempts) > 1
        out.append({
            "n": n, "state": state, "word": WORDS[state], "current": n == current, "approved": False, "actions": [],
            "challenges": [{"round": v.round, "label": _label(v, x.attempt, many=many), "recheck": v.recheck}
                           for x, v in mine],
        })  # fmt: skip
    return out


def brief(c: Change) -> dict:
    """The brief's versions, each with its state, the challenges that read it, and the current one's actions."""
    b, lp = c.brief, c.loops.get(BRIEF)
    attempts = _attempts(lp, BRIEF)
    live = brief_rounds.current(c)
    asks = brief_rounds.first(c) or brief_rounds.due(c) or brief_rounds.owned_open(c)
    waits = int(live.head) if live and live.head and asks else 0
    on = c.step.kind == StepKind.SHAPE and c.step.mode in brief_rounds.MODES
    versions = _versions(attempts, b.version, running=(b.requested or b.version) if on else 0, waits=waits)
    approved = {b.approved_version, *(a.version for a in b.approved)}
    for v in versions:
        v["approved"] = v["n"] in approved
        if v["current"] and not v["approved"] and c.step.kind == StepKind.SHAPE:
            v["actions"] = ["approve"]  # off while brief_rounds.approvable says why
    return {"versions": versions, "legacy": _legacy(attempts)[0]}


def plan(c: Change) -> dict:
    """The plan's versions, each with its state and the challenges that read it; the page offers no action on them."""
    if c.plan is None:
        return {"versions": [], "legacy": ""}
    attempts = _attempts(c.loops.get(PLAN), PLAN)
    live = plan_rounds.current(c)
    n = c.plan.version if live else 0
    running = n if c.step.kind == StepKind.PLAN and c.step.mode in _PLAN_MODES else 0
    waits = n if plan_rounds.first(c) or plan_rounds.due(c) or plan_rounds.owned_open(c) else 0
    return {
        "versions": _versions(attempts, c.plan.version, running=running, waits=waits),
        "legacy": _legacy(attempts)[0],
    }
