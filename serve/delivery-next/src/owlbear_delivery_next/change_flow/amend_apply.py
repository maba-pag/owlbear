"""Applying a brief amendment (TD-185): the exact wording, the new version, the evidence it voids and the resume.

The version it makes counts as approved and challenged; it is appended to the retained versions with its person
checks, and earlier versions are never edited. Evidence of the changed items, and of those the challenger named, is
voided; the rest keeps its result while its own inputs hold. The stopped step then resumes by the amendment's level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_decisions import new_id
from owlbear_delivery_next.change_contracts.amendment_records import AmendedItem
from owlbear_delivery_next.change_contracts.decision_records import BriefDecision
from owlbear_delivery_next.change_contracts.evidence import coverage, criteria
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import (
    VISUAL,
    Criterion,
    ErrorKind,
    Exit,
    Outcome,
    PersonCheck,
    StepKind,
    VisualState,
    VisualStep,
)
from owlbear_delivery_next.change_contracts.round_records import FINAL
from owlbear_delivery_next.change_flow import budgets
from owlbear_delivery_next.change_flow.moves import go

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.amendment_records import Action, Amendment, Level
    from owlbear_delivery_next.change_contracts.models import Brief, Change

STALE = 0  # a visual state version no brief has: its recorded result no longer holds


def kept(c: Change) -> None:
    """Keep the current version as approved, its person checks with it, never edited again."""
    copied = [p.model_copy(deep=True) for p in c.checks]
    c.brief.approved.append(c.brief.model_copy(deep=True, update={"approved": [], "checks": copied}))


def reference(c: Change) -> int | None:
    """The version weakening is judged from: the owner's last, else the first approved one."""
    b = c.brief
    return b.reference if b.reference is not None else min((x.version for x in b.approved), default=b.approved_version)


def since(c: Change) -> list[Amendment]:
    """The amendments applied since the reference version: a candidate is judged together with them."""
    ref = reference(c) or 0
    return [a for a in c.amendments if a.state == "applied" and (a.version or 0) > ref]


def lines(b: Brief, checks: list[PersonCheck]) -> list[str]:
    """A brief version as ``field:key: wording`` lines, the way a candidate names its items."""
    out = [f"ui: {str(b.ui).lower()}", *(f"scope:{s}" for s in b.scope)]
    out += [f"criterion:{k.id}: {k.text}" for k in b.criteria]
    out += [f"visual:{s.name} ({s.path}{f'; actions: {_actions(s.steps)}' if s.steps else ''}): {s.expect}"
            for s in b.visual]  # fmt: skip
    out += [f"check:{p.id}: {p.expect} (steps: {'; '.join(p.steps)}; covers {', '.join(p.criteria)}"
            f"{'; judged by look' if p.visual else ''})" for p in checks]  # fmt: skip
    out += [f"decision:{d.id} [{d.scope}]: {d.question} -> {d.answer}" for d in b.decisions]
    out += [f"outcome: {b.outcome}", *(f"non-goal: {n}" for n in b.non_goals)]
    return [f"{x}{' (the owner specified it)' if _ref(x) in b.specified else ''}" for x in out]


def _ref(line: str) -> str:
    """The ``specified`` entry of one of ``lines``: a bare criterion id, else ``screen:``/``check:`` and its key."""
    field, _, rest = line.partition(":")
    key = rest.split(":", 1)[0].split(" (", 1)[0]
    return {"criterion": key, "visual": f"screen:{key}", "check": f"check:{key}"}.get(field, "")


def _actions(steps: Sequence[VisualStep | Action]) -> str:
    return "; ".join(f'type "{x.text}" into "{x.target}"' if x.do == "type" else f'click "{x.target}"' for x in steps)


def shape(i: AmendedItem) -> str:
    """What goes with an item's new wording: a state's path and actions, a check's steps, criteria and look."""
    parts = [
        f"path {i.path}" if i.path else "",
        f"actions: {_actions(i.actions) or 'none'}" if i.actions is not None else "",
        f"steps: {'; '.join(i.steps)}" if i.steps else "",
        f"covers {', '.join(i.covers)}" if i.covers else "",
        "" if i.visual is None else "judged by look" if i.visual else "not judged by look",
        f"question: {i.question}" if i.question else "",
    ]
    return "".join(f" ({p})" for p in parts if p)


def exact(c: Change, field: str, key: str, text: str, **more: object) -> AmendedItem:
    """One candidate item with the approved wording it replaces and that wording's version."""
    b, old, version = c.brief, "", 0
    match field:
        case "criterion":
            k = next((k for k in b.criteria if k.id == key), None)
            old, version = (k.text, k.version) if k else ("", 0)
        case "visual":
            s = next((s for s in b.visual if s.name == key), None)
            old, version = (s.expect, s.version) if s else ("", 0)
        case "check":
            p = next((p for p in c.checks if p.id == key), None)
            old, version = (p.expect, p.procedure) if p else ("", 0)
        case "scope":
            old = key if key in b.scope else ""
        case "decision":
            d = next((d for d in b.decisions if d.id == key), None)
            old = d.answer if d else ""
        case "ui":
            old = str(b.ui).lower()
    return AmendedItem.model_validate({"field": field, "key": key, "version": version, "old": old, "new": text} | more)


def reverted(c: Change, a: Amendment) -> list[AmendedItem]:
    """The exact items that undo applied amendment *a*: each one back to its wording and shape before it.

    A removed item comes back under its own key; a scope line and a decision are known by their new key.
    """
    out, before = [], max((x for x in c.brief.approved if x.version < (a.version or 0)), key=lambda x: x.version)
    for i in a.items:
        why = f"reverts {a.id}"
        if i.field == "ui":
            out.append(exact(c, "ui", "", i.old, why=why))
        elif not i.old:  # added: removed again
            out.append(exact(c, i.field, i.key, "", remove=True, why=why))
        else:
            out.append(exact(c, i.field, i.key, i.old, why=why, **_shape(before, i)))
    return out


def _shape(before: Brief, i: AmendedItem) -> dict[str, object]:
    """What item *i* had besides its wording before its amendment changed or removed it."""
    match i.field:
        case "visual":
            s = next((s for s in before.visual if s.name == i.key), None)
            return {"path": s.path, "actions": [x.model_dump() for x in s.steps]} if s else {}
        case "check":
            p = next((p for p in before.checks if p.id == i.key), None)
            return {"steps": p.steps, "covers": p.criteria, "visual": p.visual} if p else {}
        case "decision":
            return {"question": next((d.question for d in before.decisions if d.id == i.key), i.question)}
    return {}


def apply(c: Change, a: Amendment, level: Level, now: datetime) -> None:
    """Apply *a* as the next brief version at *level*, void its evidence, then resume the stopped step."""
    b, v = c.brief, c.brief.version + 1
    removed = set()
    for i in sorted(a.items, key=lambda i: i.field != "criterion"):  # a check covers the criteria it brings
        _item(c, i, v, level, now)
        if i.field == "criterion" and i.remove:
            removed.add(i.key)
        if level != "autonomous" and not i.remove and (ref := mark(i)):
            b.specified = [*b.specified, ref] if ref not in b.specified else b.specified
    gone = {f"{'screen' if i.field == 'visual' else 'check'}:{i.key}" for i in a.items
            if i.remove and i.field in {"visual", "check"}}  # fmt: skip
    b.specified = [s for s in b.specified if s not in removed | gone]
    b.version = b.approved_version = b.challenged = a.version = v
    b.approved_at, a.level, a.state = now, level, "applied"
    if level in {"approved", "decided"}:
        b.reference = v
    void(c, a, removed)
    kept(c)  # with the coverage the removed criteria left
    a.done = [f"{c.plan.version}:{t.id}" for t in c.plan.tasks if t.done] if c.plan else []
    resume(c, a, level, now)
    c.amending = None


def mark(i: AmendedItem) -> str:
    """The ``specified`` entry of a criterion, visual state or person check item: "" for the other fields."""
    return {"criterion": i.key, "visual": f"screen:{i.key}", "check": f"check:{i.key}"}.get(i.field, "")


def _item(c: Change, i: AmendedItem, v: int, level: Level, now: datetime) -> None:
    """Apply one item; a new item's key is recorded on it, so a revert can name it."""
    b = c.brief
    match i.field:
        case "ui":
            b.ui = i.new.strip().lower() == "true"
        case "criterion":
            _criterion(c, i)
        case "visual":
            _visual(b, i, v)
        case "check":
            _check(c, i)
        case "scope":
            kept = [s for s in b.scope if s != i.key] if i.key else list(b.scope)
            b.scope = kept if i.remove else [*kept, i.new]
            i.key = "" if i.remove else i.new
        case "decision":
            _decision(c, i, level, now)


def _criterion(c: Change, i: AmendedItem) -> None:
    b = c.brief
    if i.remove:
        b.criteria = [k for k in b.criteria if k.id != i.key]
    elif any(k.id == i.key for k in b.criteria):
        b.criteria = [k.model_copy(update={"text": i.new, "version": k.version + 1}) if k.id == i.key else k
                      for k in b.criteria]  # fmt: skip
    else:  # new, or a removed one brought back above every version its evidence was recorded at
        was = max((k.version for x in b.approved for k in x.criteria if k.id == i.key), default=0)
        i.key = i.key or _free("AC-", [k.id for k in b.criteria])
        b.criteria.append(Criterion(id=i.key, text=i.new, version=was + 1))
        _covered(c, i.key)


def _visual(b: Brief, i: AmendedItem, v: int) -> None:
    steps = None if i.actions is None else [VisualStep(**x.model_dump()) for x in i.actions]
    if i.remove:
        b.visual = [s for s in b.visual if s.name != i.key]
    elif any(s.name == i.key for s in b.visual):
        b.visual = [s.model_copy(update={"expect": i.new, "path": i.path or s.path, "version": v,
                                         "steps": s.steps if steps is None else steps})
                    if s.name == i.key else s for s in b.visual]  # fmt: skip
    elif was := [s for x in b.approved for s in x.visual if s.name == i.key]:  # back with its steps
        s = was[-1]
        b.visual.append(s.model_copy(update={"expect": i.new, "path": i.path or s.path, "version": v,
                                             "steps": s.steps if steps is None else steps}))  # fmt: skip
    else:
        i.key = i.key or _free("amended-", [s.name for s in b.visual])
        b.visual.append(VisualState(name=i.key, path=i.path or "/", expect=i.new, steps=steps or [], version=v))


def _check(c: Change, i: AmendedItem) -> None:
    """A person check changed, removed, added, or brought back as it was with a new procedure."""
    if i.remove:
        c.checks = [p for p in c.checks if p.id != i.key]
        return
    ids = [k.id for k in c.brief.criteria]
    covers = [k for k in i.covers if k in ids]
    for p in c.checks:
        if p.id == i.key:
            p.expect, p.steps, p.criteria = i.new, i.steps or p.steps, covers or p.criteria
            p.visual = p.visual if i.visual is None else i.visual
            p.procedure, p.answer = p.procedure + 1, None
            return
    if was := [p for x in c.brief.approved for p in x.checks if p.id == i.key]:  # back as it was, a new procedure
        p = was[-1]
        c.checks.append(p.model_copy(deep=True, update={
            "criteria": covers or [k for k in p.criteria if k in ids], "steps": i.steps or p.steps, "expect": i.new,
            "visual": p.visual if i.visual is None else i.visual, "paths": coverage(c), "procedure": p.procedure + 1,
            "answer": None}))  # fmt: skip
        return
    i.key = i.key or _free("check-", [p.id for p in c.checks])
    c.checks.append(PersonCheck(id=i.key, criteria=covers or ids, steps=i.steps, expect=i.new, visual=bool(i.visual),
                                paths=coverage(c)))  # fmt: skip


def _covered(c: Change, key: str) -> None:
    """A criterion brought back goes back into the checks that covered it when it was last approved, to be redone."""
    was = next((x for x in reversed(c.brief.approved) if any(k.id == key for k in x.criteria)), None)
    held = {p.id for p in was.checks if key in p.criteria} if was else set()
    for p in c.checks:
        if p.id in held and key not in p.criteria:
            p.criteria, p.answer = [*p.criteria, key], None


def _decision(c: Change, i: AmendedItem, level: Level, now: datetime) -> None:
    """A Change-scoped brief decision: an approved answer is never edited, so a change is a successor."""
    b, old = c.brief, next((d for d in c.brief.decisions if d.id == i.key), None)
    b.decisions = [d for d in b.decisions if d.id != i.key] if i.key else b.decisions
    if i.remove:
        return
    made = BriefDecision(
        id=new_id(now, seed=f"{c.slug}\n{i.key}\n{i.new}\n{now.isoformat()}"),
        question=old.question if old else i.question,
        answer=i.new,
        origin=level or "approved",
        reason=i.why if level == "autonomous" else "",
        scope="change",
        replaces=old.id if old else "",
    )
    b.decisions.append(made)
    i.key = made.id


def _free(prefix: str, taken: list[str]) -> str:
    return next(f"{prefix}{n}" for n in range(1, 1000) if f"{prefix}{n}" not in taken)


def void(c: Change, a: Amendment, removed: set[str]) -> None:
    """Void the evidence *a* touches; the rest keeps its result while its own inputs hold (TD-185 §3 step 6).

    The final review judged an earlier version: it is bound to its brief version (``Review.brief``), and the final
    loop's completion stands for that version only. A visual state or person check of a changed item, or one the
    challenger named, is redone; a person check covering a changed criterion no longer holds by its version, and a
    removed criterion leaves the checks that covered it.
    """
    if (lp := c.loops.get(FINAL)) is not None:
        lp.completion = None
    named = set(a.affected)
    checks = {i.key for i in a.items if i.field == "check"} | {n[6:] for n in named if n.startswith("check:")}
    for p in c.checks:
        if p.id in checks:
            p.answer = None
            continue
        p.criteria = [k for k in p.criteria if k not in removed]
        if p.answer and p.answer.inputs:
            p.answer.inputs.criteria = {k: n for k, n in p.answer.inputs.criteria.items() if k not in removed}
    states = {i.key for i in a.items if i.field == "visual"} | {n[7:] for n in named if n.startswith("screen:")}
    if (r := c.visual) is not None:
        r.criteria = criteria(c)
        r.states = {s.name: STALE if s.name in states else r.states.get(s.name, STALE) for s in c.brief.visual}


def resume(c: Change, a: Amendment, level: Level, now: datetime) -> None:
    """The stopped step on the new version: approved by the owner, a plan task is replanned; else it reruns.

    A scope-widening amendment has the Change's governing decisions reassessed before work resumes: the pin forgets
    the revisions of those it did not pick, so the decisions gate puts them to the picker again.
    """
    s = c.step
    if a.widens and (pin := c.decisions_baseline) is not None:
        pin.revisions = {k: r for k, r in pin.revisions.items() if k in pin.said}
    tasks = {t.id for t in c.plan.tasks} if c.plan else set()
    if level != "autonomous" and s.kind in {StepKind.BUILD, StepKind.REVIEW} and s.task in tasks:
        from owlbear_delivery_next.change_flow.loop import StepResult  # noqa: PLC0415 - loop imports this module

        cause = cause_key(ErrorKind.SCOPE, s.kind, "amendment")
        done = ", ".join(f"{t.id} ({t.title})" for t in c.plan.tasks if t.done) or "none"
        why = f"brief v{a.version} ({a.id}) stopped task {s.task}; done before it, their work on the branch: {done}"
        r = StepResult(exit=Exit.BACK, back_to=StepKind.PLAN, cause=cause, reason=why)
        c.outcome = Outcome(exit=Exit.BACK, cause=cause, reason=r.reason, at=now)
        budgets.back(c, r, now)
        return
    if s.kind == StepKind.CHECK and s.task != VISUAL and all(p.id != s.task for p in c.checks):
        go(c, StepKind.FOLLOW)  # its person check is gone: the next one is chosen as after any follow
    else:
        go(c, s.kind, s.task, s.mode)
    c.outcome = None
