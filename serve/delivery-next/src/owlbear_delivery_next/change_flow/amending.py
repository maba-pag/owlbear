"""Brief amendments (TD-185): one path for every source, run before the step it stopped.

A worker's premise, the owner's answer classed as a brief change, his "Allow it" on a Spotter question and his revert
of an applied amendment each start one (``start``). The shaper prepares the exact candidate, an independent challenger
judges it in the brief's pinned challenge loop, the shaper revises it on findings, and then Delivery applies it alone,
his answer settles it, or he is asked. ``workflow_steps.amending`` runs its sessions; ``amend_apply`` applies it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.amendment_records import Amending, Amendment
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import Answer, ErrorKind, Exit, Option, Outcome, Question, StepKind
from owlbear_delivery_next.change_contracts.round_records import RoundLoop
from owlbear_delivery_next.change_flow import amend_apply
from owlbear_delivery_next.change_flow.moves import ask, go

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.amend_tools import CandidateItem, CandidateResult, VerdictResult
    from owlbear_delivery_next.change_contracts.amendment_records import AmendedItem, Choice, Objection, Source
    from owlbear_delivery_next.change_contracts.inbox import AnswerItem, ObjectionItem
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.round_records import RoundPolicy
    from owlbear_delivery_next.change_contracts.tools import WrongPremise

SUBJECT = "amend"  # a question's cause: scope:<step>:amend <id> <what>
OWNER = frozenset({"answer", "allow", "revert"})
YES = Option(id="yes", label="Yes: apply it")
UNREVIEWED = Option(id="accept-unreviewed", label="Apply this wording, which no challenge round reviewed")
WITHIN = Option(id="within", label="No: work on within the approved brief (your reason goes to the work)")
RESHAPE = Option(id="reshape", label="Reshape the brief with the shaper", next=StepKind.SHAPE)
STOP = Option(id="stop", label="Stop the Change", next="abandon")
FIX = Option(id="fix", label="The shaper revises the candidate for it")
RECONSIDER = Option(id="reconsider", label="Ask the challenger to reconsider", next="reconsider")
DROP = Option(id="drop", label="Drop the finding")
ANOTHER = Option(id="another", label="Another round")
NOW = Option(id="now", label="Decide on the candidate now")
REVERT = Option(id="revert", label="Revert it: a new brief version without it")
KEEP = Option(id="keep", label="Keep it and continue")
CHOICES: dict[str, Choice] = {YES.id: "yes", UNREVIEWED.id: "yes", WITHIN.id: "within", RESHAPE.id: "reshape",
                              STOP.id: "stop"}  # fmt: skip
OBJECTIONS: dict[str, Objection] = {REVERT.id: "revert", KEEP.id: "keep", RESHAPE.id: "reshape"}


def current(c: Change) -> Amendment | None:
    """The amendment the Change runs now."""
    return next((a for a in c.amendments if c.amending and a.id == c.amending.id), None)


def key(a: Amendment) -> str:
    """Its challenge loop's subject."""
    return f"amendment:{a.id}"


def start(  # noqa: PLR0913 - what each source states
    c: Change,
    source: Source,
    *,
    reason: str,
    now: datetime,
    items: Iterable[AmendedItem] = (),
    evidence: Iterable[str] = (),
    session: str = "",
    question: str = "",
    reverts: str = "",
) -> Amendment:
    """Start an amendment from *source*: the Change runs it before its current step, which it then resumes."""
    a = Amendment(
        id=f"A{len(c.amendments) + 1}", at=now, step=str(c.step.kind), session=session, source=source,
        base=c.brief.version, items=list(items), evidence=list(evidence), reason=" ".join(reason.split())[:2000],
        state="proposed", question=question, reverts=reverts,
    )  # fmt: skip
    c.amendments.append(a)
    c.amending, c.outcome = Amending(id=a.id), None  # a revert's exact items need no shaper: its loop opens first
    return a


def premised(c: Change, p: WrongPremise, session: str, now: datetime) -> Amendment:
    """A worker's brief premise: its amendment starts with the exact items it named, if any."""
    items = [amend_apply.exact(c, i.field, i.key, i.text, remove=i.remove, why=i.why) for i in p.amendment]
    return start(c, "worker", reason=p.reason, now=now, items=items, evidence=p.evidence, session=session)


def opened(c: Change, a: Amendment, policy: RoundPolicy) -> None:
    """Its challenge loop, anew for a new candidate: an earlier attempt is kept in its history."""
    old = c.loops.get(key(a))
    hist = [*old.history, old.model_copy(update={"history": []})] if old else []
    c.loops[key(a)] = RoundLoop(subject=key(a), attempt=len(hist) + 1, policy=policy, history=hist)
    if c.amending:
        c.amending.phase, c.amending.revision = "challenge", 0


def _exact(c: Change, items: Iterable[CandidateItem]) -> list[AmendedItem]:
    return [
        amend_apply.exact(c, i.field, i.key, i.text, remove=i.remove, why=i.why, path=i.path, steps=i.steps,
                          question=i.question, covers=i.covers, visual=i.visual,
                          actions=None if i.actions is None else [x.model_dump() for x in i.actions])
        for i in items
    ]  # fmt: skip


def prepared(c: Change, r: CandidateResult, policy: RoundPolicy, now: datetime) -> None:
    """The shaper's candidate against the current version, then its challenge; a refusal asks the owner."""
    a = current(c)
    if a is None:
        return
    if r.refuse.strip():
        _refused(c, a, r.refuse, now)
        return
    a.items, a.base, a.verdict, a.unreviewed = _exact(c, r.items), c.brief.version, "", False
    opened(c, a, policy)


def _refused(c: Change, a: Amendment, why: str, now: datetime) -> None:
    a.state, a.refused = "refused", " ".join(why.split())[:1000]
    text = (
        f"The amendment {a.id} ({a.reason[:300]}) needs the brief's outcome or non-goals, so it was refused for "
        f"reshaping: {a.refused}. Work on within the approved brief, reshape the brief, or stop the Change?"
    )
    _ask(c, a, "decide", text, WITHIN, RESHAPE, STOP, now=now)


def judged(c: Change, r: VerdictResult, session: str, now: datetime) -> None:
    """Count the challenger's verdict on the latest revision; a full round's verdict binds that wording."""
    a, am = current(c), c.amending
    if a is None or am is None:
        return
    lp, recheck = c.loops[key(a)], am.phase == "recheck"
    found = [" ".join(f"{f.place}: {f.problem} - fix: {f.fix}".split()) for f in r.findings]
    upheld = {x.finding: (bool(x.upheld), x.reason) for x in r.rechecked}
    lp.verdict(found, upheld, f"r{am.revision}", f"r{am.revision}", recheck=recheck)
    a.challenger = session
    if not recheck:
        a.verdict, a.judged, a.reference = r.verdict, " ".join(r.reasons.split()), amend_apply.reference(c)
        a.qualifies, a.build_only, a.tightening, a.widens = r.qualifies, r.build_only, r.tightening, r.widens
        a.affected = [x.item for x in r.affected]
        a.beyond, a.doubts = r.beyond, r.doubts
    proceed(c, now)


def proceed(c: Change, now: datetime) -> None:
    """After a verdict or the owner's decision: his finding, the shaper's revision, his round choice, or the end."""
    a, am = current(c), c.amending
    if a is None or am is None:
        return
    lp = c.loops[key(a)]
    if (f := next((f for f in lp.findings if f.state == "escalated" and f.reconsider != "due"), None)) is not None:
        text = f"The challenger upheld finding {f.id} of amendment {a.id} the shaper rejected: {f.text} Shaper: "
        text += f"{f.reason} Challenger: {f.judgement}"
        if f.reconsider == "unsure":  # reconsidered once already (TD-193): only his fix or drop is left
            said = f" Your note: {f.note} Reconsidering challenger, unsure: {f.clarified}"
            _ask(c, a, f"finding {f.id}", f"{text}{said}", FIX, DROP, now=now)
        else:
            _ask(c, a, f"finding {f.id}", text, FIX, RECONSIDER, DROP, now=now)
    elif any(f.reconsider == "due" for f in lp.findings):
        am.phase = "reconsider"
    elif any(f.state in {"open", "owner-fix"} for f in lp.findings):
        am.phase = "revise"
    elif lp.last and lp.many():
        said = "; ".join(f"{f.id}: {f.text}" for f in lp.findings if f.raised == lp.round)
        text = f"Amendment {a.id}'s challenge found {lp.found} new findings in its last allowed round: {said}."
        _ask(c, a, "round", text, ANOTHER, NOW, now=now)
    else:
        lp.ended = lp.ending() if lp.unreviewed else "clean"
        a.unreviewed = bool(lp.unreviewed)
        decide(c, now)


def reconsidered(c: Change, verdicts: Mapping[str, tuple[str, str]], now: datetime) -> None:
    """Each finding he sent back: withdrawn settles it, clarified goes to the shaper, unsure back to him."""
    a = current(c)
    if a is None:
        return
    for f in (f for f in c.loops[key(a)].findings if f.reconsider == "due"):
        verdict, said = verdicts.get(f.id, ("unsure", "no verdict was given"))
        f.clarified = " ".join(said.split())[:1000]
        if verdict == "withdrawn":
            f.state, f.reconsider = "withdrawn", ""
        elif verdict == "clarified":
            f.state, f.reconsider = "owner-fix", ""
        else:
            f.reconsider = "unsure"
    proceed(c, now)


def revised(c: Change, r: CandidateResult, now: datetime) -> None:
    """The shaper's revision: each open finding fixed by a changed candidate, or rejected with its reason."""
    a, am = current(c), c.amending
    if a is None or am is None:
        return
    if r.refuse.strip():
        _refused(c, a, r.refuse, now)
        return
    lp, said = c.loops[key(a)], {x.finding: " ".join(x.reason.split())[:1000] for x in r.rejected}
    items = _exact(c, r.items)
    moved = [i.model_dump() for i in items] != [i.model_dump() for i in a.items]
    if moved:
        a.items, am.revision = items, am.revision + 1
    for f in lp.findings:
        if f.state == "open" and f.id in said:
            f.state, f.reason = "rejected", said[f.id]
        elif f.state in {"open", "owner-fix"}:
            f.state, f.repair = ("fixed", f"r{am.revision}") if moved else ("rejected", "the candidate is unchanged")
            f.reason = "" if moved else f.repair
    if not lp.last:
        am.phase = "challenge"
    elif any(f.state == "rejected" for f in lp.findings):
        am.phase = "recheck"  # the last round's rejections are judged before anything else
    else:
        if lp.head != f"r{am.revision}":  # no round judged this wording, unless he grants another
            lp.leave(f"r{am.revision}")
        proceed(c, now)


def alone(c: Change, a: Amendment) -> bool:
    """Delivery applies it alone only as an equivalent, independently shown replacement of generated checks."""
    return (
        a.verdict == "equivalent" and a.qualifies and not (a.build_only or a.tightening or a.unreviewed or a.widens)
        and bool(a.items) and all(i.key and (m := amend_apply.mark(i)) and m not in c.brief.specified for i in a.items)
    )  # fmt: skip


def decide(c: Change, now: datetime) -> None:
    """Apply it alone, as his answer settled it, or ask him; a candidate for an earlier version is prepared again."""
    a, am = current(c), c.amending
    if a is None or am is None:
        return
    if a.base != c.brief.version:  # never applied to a version it was not prepared against
        am.phase = "prepare"
        return
    if a.source in OWNER and not (a.beyond or a.doubts or a.unreviewed):
        amend_apply.apply(c, a, "approved" if a.source == "revert" else "decided", now)
    elif a.source not in OWNER and alone(c, a):
        amend_apply.apply(c, a, "autonomous", now)
    else:
        _ask(c, a, "decide", question_text(a), UNREVIEWED if a.unreviewed else YES, WITHIN, RESHAPE, STOP, now=now)


def question_text(a: Amendment) -> str:
    """The owner's question: old and new, the reason, the verdict, a tightening's cost and the evidence redone."""
    items = "; ".join(_item_line(i) for i in a.items)
    parts = [f"Amend the approved brief v{a.base} ({a.id}, from {_SOURCES[a.source]})? {items}.",
             f"Reason: {a.reason[:500]}", f"Challenger: {a.verdict or 'unsure'} - {a.judged[:800]}"]  # fmt: skip
    parts += [f"Tightening, its scope and cost: {a.tightening}"] if a.tightening else []
    parts += [f"Beyond your answer: {a.beyond}"] if a.beyond else []
    parts += [f"Open doubt: {a.doubts}"] if a.doubts else []
    parts += ["Its final wording was revised after the last challenge round: no round reviewed it."] * a.unreviewed
    redo = ["the final review", *a.affected, *(f"{i.field}:{i.key}" for i in a.items if i.field in {"visual", "check"})]
    parts.append(f"Redone after it: {', '.join(dict.fromkeys(redo))}.")
    return " ".join(parts)


_SOURCES = {"worker": "a worker", "answer": "your answer", "allow": "your Allow it", "revert": "your revert"}


def _item_line(i: AmendedItem) -> str:
    name = f"{i.field} {i.key}".strip()
    if i.remove:
        return f"remove {name} ({i.old})"
    shape = amend_apply.shape(i)
    return f"{name}: {i.old!r} -> {i.new!r}{shape}" if i.old else f"add {name}: {i.new!r}{shape}"


def _ask(c: Change, a: Amendment, what: str, text: str, *options: Option, now: datetime) -> None:
    if c.amending is not None and what != "objection":
        c.amending.phase = "ask"
    cause = cause_key(ErrorKind.SCOPE, c.step.kind, f"{SUBJECT} {a.id} {what}")
    ask(c, Question(step=c.step.kind, text=text, options=[o.model_copy() for o in options], cause=cause), now)


def owned(q: Question) -> tuple[str, str] | None:
    """The amendment id and what *q* asks about, when it is an amendment's question."""
    kind, _, rest = (q.cause or "").partition(":")
    said = rest.partition(":")[2]
    if kind != ErrorKind.SCOPE or not said.startswith(f"{SUBJECT} "):
        return None
    _, ident, what = said.split(" ", 2)
    return ident, what


def answered(c: Change, item: AnswerItem, now: datetime, dropped: list[tuple[AnswerItem, str]] | None) -> bool:
    """Whether *item* answers an amendment's question; then it is recorded and acted on, or dropped with why."""
    q = next((q for q in c.questions if q.id == item.question), None)
    if q is None or (own := owned(q)) is None:
        return False
    if why := _unsettled(c, q, own, item):
        if dropped is not None:
            dropped.append((item, f"question {q.id}: {why}"))
        return True
    q.answer = Answer(option=item.option, text=item.text, channel=item.channel, at=item.at)
    q.effect_observed_at = item.at  # an engine decision: never delivered to a worker
    if c.outcome and c.outcome.question == q.id:
        c.outcome = None
    a = next(a for a in c.amendments if a.id == own[0])
    if own[1] == "objection":
        _objection(c, a, item, now)
    elif own[1] == "decide":
        _decided(c, a, item, now)
    elif own[1] == "round":
        _round(c, a, now, another=item.option == ANOTHER.id)
    else:
        f = next(f for f in c.loops[key(a)].findings if f.id == own[1].removeprefix("finding "))
        if item.option == RECONSIDER.id:
            f.reconsider, f.note = "due", " ".join(item.text.split())[:2000]
        else:
            f.state, f.reconsider = ("owner-fix" if item.option == FIX.id else "owner-drop"), ""
            f.note = item.text or item.option or ""
        proceed(c, now)
    return True


def _unsettled(c: Change, q: Question, own: tuple[str, str], item: AnswerItem) -> str:
    if q.answer is not None:
        return "it is answered already"
    if item.option not in {o.id for o in q.options}:
        return "it is settled only by one of its options"
    if item.option in {WITHIN.id, "reshape"} and not item.text.strip():
        return "say why: the work, or the shaper, goes on from your reason"
    if own[1] == "objection":
        return "another amendment runs; answer after it ends" if c.amending else ""
    return "" if c.amending and c.amending.id == own[0] else "the amendment it asks about has ended"


def _round(c: Change, a: Amendment, now: datetime, *, another: bool) -> None:
    lp, am = c.loops[key(a)], c.amending
    if another and am is not None:
        lp.extra, lp.last, am.phase = lp.extra + 1, False, "challenge"
        return
    lp.ended = lp.ending()
    a.unreviewed = a.unreviewed or bool(lp.unreviewed)
    decide(c, now)


def _decided(c: Change, a: Amendment, item: AnswerItem, now: datetime) -> None:
    """His choice: apply it, work on within the brief, reshape, or stop the Change."""
    a.choice = CHOICES[item.option or ""]
    if a.choice == "yes":
        amend_apply.apply(c, a, "approved", now)
        return
    a.state, a.declined = "refused" if a.state == "refused" else "declined", " ".join(item.text.split())[:1000]
    c.amending = None  # the work goes on without it: within the approved brief, reshaped, or stopped
    if a.choice == "reshape":
        c.intent.words, c.intent.hold = a.declined or a.reason, True
    elif a.choice == "stop":
        c.intent.abandoned_at = now
    else:
        _within(c, a, now)


def _within(c: Change, a: Amendment, now: datetime) -> None:
    """The worker's question opens again for an answer within the brief; any other stopped step runs again."""
    asked = next((q for q in c.questions if q.id == a.question), None)
    if a.source == "answer" and asked is not None and asked.delivered_at is None:
        asked.answer = None
        c.outcome = Outcome(exit=Exit.ASK, reason=asked.text, who="you", question=asked.id, at=now)
        return
    s = c.step
    go(c, s.kind, s.task, s.mode)
    c.outcome = None


def left(c: Change, why: str) -> None:
    """The Change stopped or finished before the amendment ended: it is declined, its work gone with the Change."""
    if (a := current(c)) is not None:
        a.state, a.declined = "declined", why
    c.amending = None


def objectable(c: Change, ident: str) -> str:
    """Why the owner may not object to amendment *ident* now, or ""."""
    a = next((a for a in c.amendments if a.id == ident), None)
    if a is None or a.state != "applied":
        return f"{ident} is no applied amendment of this Change"
    if c.finished_at or c.intent.abandoned_at:
        return "the Change has ended"
    if c.amending is not None:
        return "an amendment runs now; object after it ends"
    if c.outcome is not None and c.outcome.exit == Exit.ASK:
        return "the Change waits on another question; answer it first"
    return "you objected to it already; answer that question" if a.objected_at and not a.objection else ""


def objected(c: Change, item: ObjectionItem, now: datetime) -> None:
    """His objection: dependent work waits on his choice, and he sees what was built and judged on it.

    Folded between steps, so the step that ran when he objected has ended: work pauses after it.
    """
    a = next((a for a in c.amendments if a.id == item.amendment), None)
    if a is None or objectable(c, item.amendment):
        return
    a.objected_at = item.at
    later = [x.id for x in c.amendments if x.state == "applied" and (x.version or 0) > (a.version or 0)]
    done = [t.id for t in c.plan.tasks if t.done and f"{c.plan.version}:{t.id}" not in a.done] if c.plan else []
    text = (
        f"You objected to amendment {a.id} (brief v{a.version}: {'; '.join(_item_line(i) for i in a.items)})"
        f"{f': {item.text}' if item.text else ''}. Built and judged on it since: tasks {', '.join(done) or 'none'}, "
        f"the reviews and checks after v{a.version}; later amendments {', '.join(later) or 'none'}. Merged or "
        "published work can't be undone. Revert it as a new version, keep it, or reshape the brief?"
    )
    _ask(c, a, "objection", text, REVERT, KEEP, RESHAPE, now=now)


def _objection(c: Change, a: Amendment, item: AnswerItem, now: datetime) -> None:
    a.objection = OBJECTIONS[item.option or ""]
    if item.option == REVERT.id:
        start(c, "revert", reason=item.text or f"you reverted {a.id}", now=now, reverts=a.id,
              items=amend_apply.reverted(c, a))  # fmt: skip
    elif item.option == RESHAPE.id:
        c.intent.words, c.intent.hold = item.text, True
