"""Retro's proposal bars (#715, Improvement design §5): which findings and grades become proposals.

- A Delivery change: a finding Delivery owns (a tool's defect or Delivery's logic) with the steps that reproduce it
  and a cost; the bar is met once.
- A Spotter case: a real record graded ``wrong`` or ``missed``, with the call Retro says it should have made.
- A lesson (an agent's behaviour) or an agent change (an agent's, skill's or prompt's instructions): findings of one
  cause and target are sorted by one bounded **confirm** batch into mechanisms, the reasons they happened. Only a
  mechanism whose findings span at least two independent families opens a proposal (assumption
  ``retro-lesson-bar-1``); its counterexamples are the judged units exposed to the target that hold none of it, read
  from what each unit's capture showed, so they outlive the capture.
- A look reconsidered: when catchable findings are at least 30 % of the real findings over the last 20 judged units
  (assumption ``retro-catchable-1``), once while one is open.

Real and synthetic evidence never meet: each bar counts only findings of the run's provenance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement.retro_calls import paid

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from owlbear_delivery_next.improvement.retro_calls import Work

CAUSES = (
    "misread-task",
    "missing-context",
    "skipped-verification",
    "wrong-tool-use",
    "scope-drift",
    "poor-plan",
    "instruction-gap",
    "tool-defect",
    "delivery-logic",
    "other",
)
DELIVERY, AGENT = frozenset({"tool-defect", "delivery-logic"}), frozenset({"instruction-gap"})
CONFIRM = Path(__file__).with_name("retro_confirm_prompt.md")
ASSIGNED = "assignments.jsonl"
CANDIDATES, FAMILIES, SHOWN = 12, 2, 3  # findings one confirm batch sorts; families a mechanism needs; counterexamples
CATCHABLE, WINDOW = 0.3, 20  # the share of catchable findings over the last judged units that reconsiders a look


def kind(cause: str) -> str:
    """The proposal a finding of *cause* can lead to."""
    return "delivery-change" if cause in DELIVERY else "agent-change" if cause in AGENT else "lesson"


def _marks(w: Work, *more: str) -> list[str]:
    return [assumptions.RETRO_CAUSES, *more, *([assumptions.RETRO_SYNTHETIC] if w.provenance == "synthetic" else [])]


def _delivery(w: Work, mine: Iterable[Mapping[str, Any]]) -> list[str | None]:
    return [
        props.file(
            props.open_key(w.provenance, "delivery-change", f["cause"], f["target"]),
            [f["id"]],
            kind="delivery-change",
            cause=f["cause"],
            target=f["target"],
            mechanism=f.get("mechanism", ""),
            bar="a finding Delivery owns, with the steps that reproduce it and its cost",
            provenance=w.provenance,
            assumptions=_marks(w),
        )
        for f in mine
        if f["cause"] in DELIVERY and f.get("target") and str(f.get("steps") or "").strip() and f.get("cost")
    ]


def _cases(w: Work) -> list[str | None]:
    if w.provenance != "real":
        return []
    return [
        props.file(
            props.open_key("real", "spotter-case", g["record"]),
            [g["id"]],
            kind="spotter-case",
            record=g["record"],
            call=g.get("should", ""),
            cause="",
            target=f"look:{g.get('look', '')}",
            mechanism=f"the Spotter's {g.get('look')} look was {g['grade']}: it should have said "
            f"{g.get('should') or 'otherwise'}",
            bar="a record graded wrong or missed",
            provenance="real",
            assumptions=[assumptions.RETRO_GRADES],
        )
        for g in store.grades(unit=w.uid)
        if g["grade"] in {"wrong", "missed"} and g.get("rev") == w.rev.get("rev")
    ]


def assignments() -> dict[str, dict[str, Any]]:
    """Each sorted finding's mechanism (``none`` when it has none), by finding id; the first kept counts."""
    found: dict[str, dict[str, Any]] = {}
    for line in store.lines(ASSIGNED):
        found.setdefault(line["finding"], line)
    return found


def _assign(lines: Iterable[Mapping[str, Any]]) -> None:
    with store.locked():
        have = set(assignments())
        for line in lines:
            if line["finding"] not in have:
                store.append(ASSIGNED, line)
                have.add(line["finding"])


def _valid_sorting(said: Mapping[str, Any]) -> bool:
    return isinstance(said.get("assign"), dict) and isinstance(said.get("new") or {}, dict)


def _confirm(w: Work, pair: tuple[str, str], pool: list[dict[str, Any]], known: dict[str, str]) -> None:
    """One confirm batch: sort *pool* into the *known* mechanisms of *pair*, new ones or none; keep the sorting."""
    evidence = {
        "cause": pair[0],
        "target": pair[1],
        "mechanisms": [{"id": k, "mechanism": v} for k, v in known.items()],
        "findings": [{k: f.get(k) for k in ("id", "what", "mechanism", "quotes")} for f in pool],
    }
    message = f"{CONFIRM.read_text()}\n\n## The evidence\n\n```json\n{json.dumps(evidence)}\n```\n"
    said = paid(w, f"confirm:{pair[0]}|{pair[1]}", message, _valid_sorting)
    new = {str(k): str(v) for k, v in (said.get("new") or {}).items()}
    lines = []
    for f in pool:
        to = str(said["assign"].get(f["id"]) or "none")
        if to.startswith("new:") and (text := new.get(to[4:], "").strip()):
            to = f"m-{store.digest([*pair, text])}"
            known[to] = text
        elif to not in known:
            to = "none"
        lines.append(
            {
                "finding": f["id"],
                "mechanism": to,
                "text": known.get(to, ""),
                "cause": pair[0],
                "target": pair[1],
                "provenance": w.provenance,
                "at": store.now(),
            }
        )
    _assign(lines)


def counterexamples(provenance: str, target: str, holders: set[str]) -> dict[str, Any]:
    """The judged units of *provenance* exposed to *target* that hold none of a mechanism's findings."""
    found = sorted(
        uid
        for uid, u in store.units().items()
        if u.get("provenance", "real") == provenance
        and u.get("judged_at")
        and uid not in holders
        and target in (u.get("exposure") or ())
    )
    return {"count": len(found), "sample": found[:SHOWN]}


def _lessons(w: Work, every: list[dict[str, Any]]) -> list[str | None]:
    sorted_, out = assignments(), []
    pairs = sorted({(f["cause"], f["target"]) for f in every if f["cause"] not in DELIVERY and f.get("target")})
    live = {
        (p.get("cause"), p.get("target"))
        for p in props.folded().values()
        if p.get("provenance") == w.provenance and p["state"] not in props.CLOSED
    }
    for pair in pairs:
        same = [f for f in every if (f["cause"], f["target"]) == pair]
        pool = [f for f in same if f["id"] not in sorted_]
        if pool and (len({f["family"] for f in same}) >= FAMILIES or pair in live):
            known = {
                a["mechanism"]: a["text"]
                for a in sorted_.values()
                if (a["cause"], a["target"]) == pair and a["provenance"] == w.provenance and a["mechanism"] != "none"
            }
            _confirm(w, pair, sorted(pool, key=lambda f: f["at"], reverse=True)[:CANDIDATES], known)
            sorted_ = assignments()
        by_mechanism: dict[str, list[dict[str, Any]]] = {}
        for f in same:
            if (a := sorted_.get(f["id"])) and a["mechanism"] != "none":
                by_mechanism.setdefault(a["mechanism"], []).append(f)
        for mid, held in sorted(by_mechanism.items()):
            if len({f["family"] for f in held}) < FAMILIES:
                continue
            cause, target = pair
            out.append(
                props.file(
                    props.open_key(w.provenance, kind(cause), cause, target, mid),
                    [f["id"] for f in held],
                    counterexamples(w.provenance, target, {f["unit"] for f in held}),
                    kind=kind(cause),
                    cause=cause,
                    target=target,
                    mechanism=sorted_[held[0]["id"]]["text"],
                    mechanism_id=mid,
                    provenance=w.provenance,
                    bar=f"one confirmed mechanism in at least {FAMILIES} independent families",
                    assumptions=_marks(w, assumptions.RETRO_LESSON_BAR),
                )
            )
    return out


def _catchable(w: Work, every: list[dict[str, Any]]) -> list[str | None]:
    if w.provenance != "real" or any(
        p["state"] not in props.CLOSED for p in props.folded().values() if p.get("kind") == "look-reconsider"
    ):
        return []
    judged = sorted(
        (u for u in store.units().values() if u.get("judged_at") and u.get("provenance", "real") == "real"),
        key=lambda u: u["judged_at"],
    )[-WINDOW:]
    window = {u["family"] for u in judged}
    inside = [f for f in every if f["family"] in window]
    caught = [f["id"] for f in inside if f.get("catchable")]
    if not inside or len(caught) / len(inside) < CATCHABLE:
        return []
    return [
        props.file(
            props.open_key("real", "look-reconsider"),
            caught,
            kind="look-reconsider",
            cause="",
            target="spotter:looks",
            provenance="real",
            assumptions=[assumptions.RETRO_CATCHABLE],
            mechanism=f"{len(caught)} of {len(inside)} findings over the last {len(judged)} judged units "
            "were catchable at their moment",
            bar=f"at least {CATCHABLE:.0%} catchable findings",
        )
    ]


def propose(w: Work, found: list[str]) -> list[str]:
    """Phase 2: file what this run's evidence and what came before it carry; the proposals touched."""
    every = [f for f in store.all_findings() if f.get("provenance") == w.provenance and f.get("status") == "known"]
    mine = [f for f in every if f["id"] in set(found)]
    out = [*_delivery(w, mine), *_cases(w), *_lessons(w, every), *_catchable(w, every)]
    return list(dict.fromkeys(p for p in out if p))
