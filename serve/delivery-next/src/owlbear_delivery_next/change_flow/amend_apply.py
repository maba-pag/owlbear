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
    Criterion,
    ErrorKind,
    Exit,
    Outcome,
    PersonCheck,
    StepKind,
    VisualState,
)
from owlbear_delivery_next.change_contracts.round_records import FINAL
from owlbear_delivery_next.change_flow import budgets
from owlbear_delivery_next.change_flow.moves import go

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.amendment_records import Amendment, Level
    from owlbear_delivery_next.change_contracts.models import Brief, Change

STALE = 0  # a visual state version no brief has: its recorded result no longer holds


def snapshot(c: Change, version: int | None) -> Brief | None:
    """The retained approved version *version*, its person checks with it."""
    return next((b for b in c.brief.approved if b.version == version), None)


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
    out += [f"visual:{s.name} ({s.path}): {s.expect}" for s in b.visual]
    out += [f"check:{p.id}: {p.expect} (steps: {'; '.join(p.steps)})" for p in checks]
    out += [f"decision:{d.id} [{d.scope}]: {d.question} -> {d.answer}" for d in b.decisions]
    out += [f"outcome: {b.outcome}", *(f"non-goal: {n}" for n in b.non_goals)]
    return [f"{x}{' (the owner specified it)' if _ref(x) in b.specified else ''}" for x in out]


def _ref(line: str) -> str:
    """The ``specified`` entry of one of ``lines``: a bare criterion id, else ``screen:``/``check:`` and its key."""
    field, _, rest = line.partition(":")
    key = rest.split(":", 1)[0].split(" (", 1)[0]
    return {"criterion": key, "visual": f"screen:{key}", "check": f"check:{key}"}.get(field, "")


def specified(c: Change, item: AmendedItem) -> bool:
    """Whether *item* changes something the owner stated (TD-179's list), or adds to the brief."""
    if not item.key:
        return True  # a new item is never a replaced generated check
    return {"criterion": item.key, "visual": f"screen:{item.key}", "check": f"check:{item.key}"}.get(
        item.field, ""
    ) in c.brief.specified or item.field not in {"criterion", "visual", "check"}


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
    """The exact items that undo applied amendment *a*: each one back to its wording before it."""
    out = []
    for i in a.items:
        why = f"reverts {a.id}"
        if i.field == "ui":
            out.append(exact(c, "ui", "", i.old, why=why))
        elif i.remove:  # brought back as a new item
            out.append(exact(c, i.field, "", i.old, why=why, question=i.question, path=i.path, steps=i.steps))
        elif not i.old:  # added: removed again
            out.append(exact(c, i.field, i.key, "", remove=True, why=why))
        else:  # a scope line and a decision are known by their new key after a change
            out.append(exact(c, i.field, i.key, i.old, why=why))
    return out


def apply(c: Change, a: Amendment, level: Level, now: datetime) -> None:
    """Apply *a* as the next brief version at *level*, void its evidence, then resume the stopped step."""
    b, v = c.brief, c.brief.version + 1
    changed, removed = set(), set()
    for i in a.items:
        _item(c, i, v, level, now)
        if i.field == "criterion":
            (removed if i.remove else changed).add(i.key)
        if level != "autonomous" and not i.remove and i.field in {"criterion", "visual", "check"}:
            ref = {"criterion": i.key, "visual": f"screen:{i.key}", "check": f"check:{i.key}"}[i.field]
            b.specified = [*b.specified, ref] if ref not in b.specified else b.specified
    b.specified = [s for s in b.specified if s not in {*removed, *_gone(a)}]
    b.version = b.approved_version = b.challenged = a.version = v
    b.approved_at, a.level, a.state = now, level, "applied"
    if level in {"approved", "decided"}:
        b.reference = v
    b.approved.append(b.model_copy(deep=True, update={"approved": [], "checks": [p.model_copy() for p in c.checks]}))
    void(c, a, changed | removed)
    resume(c, a, level, now)
    c.amending = None


def _gone(a: Amendment) -> set[str]:
    return {f"screen:{i.key}" for i in a.items if i.remove and i.field == "visual"} | {
        f"check:{i.key}" for i in a.items if i.remove and i.field == "check"
    }


def _item(c: Change, i: AmendedItem, v: int, level: Level, now: datetime) -> None:  # noqa: C901, PLR0912 - per field
    """Apply one item; a new item's key is recorded on it, so a revert can name it."""
    b = c.brief
    match i.field:
        case "ui":
            b.ui = i.new.strip().lower() == "true"
        case "criterion":
            if i.remove:
                b.criteria = [k for k in b.criteria if k.id != i.key]
            elif i.key:
                b.criteria = [k.model_copy(update={"text": i.new, "version": k.version + 1}) if k.id == i.key else k
                              for k in b.criteria]  # fmt: skip
            else:
                i.key = _free("AC-", [k.id for k in b.criteria])
                b.criteria.append(Criterion(id=i.key, text=i.new))
        case "visual":
            if i.remove:
                b.visual = [s for s in b.visual if s.name != i.key]
            elif i.key:
                b.visual = [s.model_copy(update={"expect": i.new, "path": i.path or s.path, "version": v})
                            if s.name == i.key else s for s in b.visual]  # fmt: skip
            else:
                i.key = _free("amended-", [s.name for s in b.visual])
                b.visual.append(VisualState(name=i.key, path=i.path or "/", expect=i.new, version=v))
        case "check":
            if i.remove:
                c.checks = [p for p in c.checks if p.id != i.key]
            elif i.key:
                for p in c.checks:
                    if p.id == i.key:
                        p.expect, p.steps = i.new, i.steps or p.steps
                        p.procedure, p.answer = p.procedure + 1, None
            else:
                i.key = _free("check-", [p.id for p in c.checks])
                ids = [k.id for k in b.criteria]
                c.checks.append(PersonCheck(id=i.key, criteria=ids, steps=i.steps, expect=i.new, paths=coverage(c)))
        case "scope":
            kept = [s for s in b.scope if s != i.key] if i.key else list(b.scope)
            b.scope = kept if i.remove else [*kept, i.new]
            i.key = "" if i.remove else i.new
        case "decision":
            _decision(c, i, level, now)


def _decision(c: Change, i: AmendedItem, level: Level, now: datetime) -> None:
    """A Change-scoped brief decision: an approved answer is never edited, so a change is a successor."""
    b, old = c.brief, next((d for d in c.brief.decisions if d.id == i.key), None)
    b.decisions = [d for d in b.decisions if d.id != i.key] if i.key else b.decisions
    if i.remove:
        return
    origin = "autonomous" if level == "autonomous" else level or "approved"
    made = BriefDecision(
        id=new_id(now, seed=f"{c.slug}\n{i.key}\n{i.new}\n{now.isoformat()}"),
        question=old.question if old else i.question,
        answer=i.new,
        origin=origin,
        reason=i.why if origin == "autonomous" else "",
        scope="change",
        replaces=old.id if old else "",
    )
    b.decisions.append(made)
    i.key = made.id


def _free(prefix: str, taken: list[str]) -> str:
    return next(f"{prefix}{n}" for n in range(1, 1000) if f"{prefix}{n}" not in taken)


def void(c: Change, a: Amendment, criteria_changed: set[str]) -> None:
    """Void the evidence *a* touches; the rest keeps its result while its own inputs hold (TD-185 §3 step 6).

    The final review judged an earlier version: it is bound to its brief version (``Review.brief``), and the final
    loop's completion stands for that version only. A visual state or person check of a changed item, or one the
    challenger named, is redone; another drops the changed criteria from its recorded inputs.
    """
    if (lp := c.loops.get(FINAL)) is not None:
        lp.completion = None
    named = set(a.affected)
    checks = {i.key for i in a.items if i.field == "check"} | {n[6:] for n in named if n.startswith("check:")}
    for p in c.checks:
        if p.id in checks:
            p.answer = None
            continue
        p.criteria = [k for k in p.criteria if k not in criteria_changed]
        if p.answer and p.answer.inputs:
            p.answer.inputs.criteria = {k: n for k, n in p.answer.inputs.criteria.items() if k not in criteria_changed}
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
        r = StepResult(exit=Exit.BACK, back_to=StepKind.PLAN, cause=cause, reason=f"brief v{a.version}: {a.id}")
        c.outcome = Outcome(exit=Exit.BACK, cause=cause, reason=r.reason, at=now)
        budgets.back(c, r, now)
        return
    go(c, s.kind, s.task, s.mode)
    c.outcome = None
