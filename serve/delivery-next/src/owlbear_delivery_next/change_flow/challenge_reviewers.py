"""First-round reviewers: kept verdicts, one shared allowance and an exact round-one gate."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import Exit, StepKind
from owlbear_delivery_next.change_contracts.round_records import BRIEF, PLAN, ReviewerVerdict

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.change_contracts.round_records import RoundLoop
    from owlbear_delivery_next.change_flow.loop import StepResult

ORDER = ("need", "build", "lean", "pipeline")
type Findings = tuple[list[str], dict[str, tuple[bool, str]]]


def at_once(c: Change, step: Step) -> int:
    """The sessions *step*'s runner may use at once: round one's reviewers when it runs them, else one.

    A planner's challenge follows in the planner's own runner, so planning before the plan's first verdict counts,
    and so does a plan step whose loop ended: its next challenge starts a new attempt at round one.
    """
    subject = {StepKind.SHAPE: BRIEF, StepKind.PLAN: PLAN}.get(step.kind)
    if subject is None:
        return 1
    planning = subject == PLAN and step.mode in {None, "challenge"}
    if (lp := c.loops.get(subject)) is None or (planning and lp.ended):
        return len(ORDER) if planning else 1
    return len(ORDER) if first(lp, "challenge" if planning else step.mode) else 1


def first(lp: RoundLoop, mode: str | None) -> bool:
    """Only a full first verdict with no rejected findings uses four reviewers; re-entry never does."""
    return (
        lp.round == 0 and not lp.reentry and mode == "challenge" and not any(f.state == "rejected" for f in lp.findings)
    )


def binding(change: Change, subject: str) -> ReviewerVerdict:
    """The current generation a reviewer judges, before it has any findings."""
    return ReviewerVerdict(
        brief=change.brief.version,
        plan=change.plan.version if subject == PLAN and change.plan else None,
        round=change.loops[subject].round,
        findings=[],
    )


def remaining(change: Change, subject: str) -> list[str]:
    """Drop stale results and return only the reviewers this generation still needs, in order."""
    lp, current = change.loops[subject], binding(change, subject)
    lp.reviewers = {
        name: kept
        for name, kept in lp.reviewers.items()
        if (kept.brief, kept.plan, kept.round) == (current.brief, current.plan, current.round)
    }
    return [name for name in ORDER if name not in lp.reviewers]


def keep(change: Change, subject: str, reviewer: str, found: list[str]) -> None:
    """Keep a complete result without counting any part of a round."""
    change.loops[subject].reviewers[reviewer] = binding(change, subject).model_copy(update={"findings": found})


def merged(lp: RoundLoop) -> list[str]:
    """Take one finding per reviewer in turn, up to the round's one allowance, and clear the kept results."""
    groups = [lp.reviewers[name].findings for name in ORDER]
    found = [
        f"{name}: {group[i]}"
        for i in range(max(map(len, groups)))
        for name, group in zip(ORDER, groups, strict=True)
        if i < len(group)
    ][: lp.policy.max_findings]
    lp.reviewers.clear()
    return found


def findings(verdict: StepResult, payload: object, *, brief: bool = False) -> Findings | None:
    """Today's complete verdicts as finding texts; None is a session failure, not a counted verdict."""
    if isinstance(payload, tools.ReviewResult) and verdict.cause is None and verdict.exit in {Exit.DONE, Exit.RETRY}:
        found = [" ".join(f"{f.place}: {f.problem} - fix: {f.fix}".split()) for f in payload.findings]
        return found, {r.finding: (bool(r.upheld), r.reason) for r in payload.rechecked}
    if isinstance(payload, tools.WrongPremise) and verdict.exit == Exit.BACK and (brief or not verdict.operational):
        return [" ".join(f"premise: {payload.reason} ({'; '.join(payload.evidence)})".split())], {}
    if brief and verdict.exit == Exit.BACK:
        return [" ".join(f"the brief {verdict.reason}".split())], {}
    return None


def named(change: Change, payload: object, judge: str, verdict: StepResult) -> list[dict[str, object]]:
    """Keep shaping names for its next pick and return their one activity event, announced after settlement."""
    accepted = verdict.cause is None and verdict.exit in {Exit.DONE, Exit.RETRY}
    if not accepted or not isinstance(payload, tools.ReviewResult) or not payload.unpicked:
        return []
    if change.step.kind == StepKind.SHAPE and change.brief.approved_version != change.brief.version:
        change.decisions_named.update({d.id: d.note for d in payload.unpicked})
    return [
        {
            "event": "decisions-named",
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "judge": judge,
            "decisions": [d.model_dump() for d in payload.unpicked],
            "reason": f"{judge}: " + "; ".join(f"{d.id}: {d.note}" for d in payload.unpicked),
        }
    ]


def failed(verdict: StepResult, reviewer: str) -> StepResult:
    """Name the reviewer whose failed or stopped session leaves the round incomplete."""
    reason = f"{reviewer}: {verdict.reason}"
    update: dict[str, object] = {"reason": reason}
    if verdict.stop is not None:
        update["stop"] = verdict.stop.model_copy(update={"reason": f"{reviewer}: {verdict.stop.reason}"})
    return verdict.model_copy(update=update)
