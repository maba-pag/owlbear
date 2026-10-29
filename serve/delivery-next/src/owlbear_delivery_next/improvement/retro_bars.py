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

from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement.retro_calls import StoppedError, paid, strings
from owlbear_delivery_next.improvement.retro_segments import QUOTE, dumps, fit, masked

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
BOUND, TEXT = 60_000, 1_000  # characters of one confirm message, as of a judging batch's; of one text it shows
CATCHABLE, WINDOW = 0.3, 20  # the share of catchable findings over the last judged units that reconsiders a look


def kind(cause: str) -> str:
    """The proposal a finding of *cause* can lead to."""
    return "delivery-change" if cause in DELIVERY else "agent-change" if cause in AGENT else "lesson"


def _synthetic(w: Work) -> list[str]:
    return [assumptions.RETRO_SYNTHETIC] if w.provenance == "synthetic" else []


def _marks(w: Work, *more: str) -> list[str]:
    return [assumptions.RETRO_CAUSES, *more, *_synthetic(w)]


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


def cases(w: Work) -> list[str | None]:
    """A Spotter case proposed for each record of this revision graded wrong or missed; a grade-only run's too.

    One of an earlier revision whose case was never filed, its run ended before, is filed now.
    """
    synthetic, held = w.provenance != "real", {f for p in props.folded().values() for f in p["findings"]}
    return [
        props.file(
            props.open_key(w.provenance, "spotter-case", g["record"]),
            [g["id"]],
            kind="spotter-case",
            record=g["record"],
            call=g.get("should", ""),
            cause="",
            target=f"look:{g.get('look', '')}",
            mechanism=f"the Spotter's {g.get('look')} look was {g['grade']}: it should have said "
            f"{g.get('should') or 'otherwise'}",
            bar="a record graded wrong or missed",
            provenance=w.provenance,
            assumptions=[assumptions.RETRO_GRADES, *_synthetic(w)],
        )
        for g in store.grades(unit=w.uid, synthetic=synthetic)
        if g["grade"] in {"wrong", "missed"} and (g.get("rev") == w.rev.get("rev") or g["id"] not in held)
    ]


def assignments() -> dict[str, dict[str, Any]]:
    """Each sorted finding's mechanism (``none`` when it has none), by finding id; the first kept counts."""
    found: dict[str, dict[str, Any]] = {}
    for line in store.lines(ASSIGNED):
        found.setdefault(line["finding"], line)
    return found


def _assign(lines: Iterable[Mapping[str, Any]]) -> None:
    """Keep a confirm batch's sorting whole, in one write: a finding sorted already keeps its first mechanism."""
    first: dict[str, Mapping[str, Any]] = {}
    for line in lines:
        first.setdefault(line["finding"], line)
    with store.locked():
        have = set(assignments())
        if rows := [line for f, line in first.items() if f not in have]:
            store.append(ASSIGNED, *rows)


def _valid_sorting(said: Mapping[str, Any], ids: Iterable[str], known: Mapping[str, str]) -> bool:
    """A sorting of every finding of *ids* into a *known* mechanism, a new one it states, or none."""
    assign, new = said.get("assign"), said.get("new") or {}
    if not (
        isinstance(assign, dict)
        and strings(list(assign.values()))
        and isinstance(new, dict)
        and strings(list(new.values()))
    ):
        return False
    made = {f"new:{k}" for k, v in new.items() if v.strip()}
    return all(assign.get(f) in {*known, *made, "none"} for f in ids)


def _shown(text: object, n: int = TEXT) -> str:
    return fit(masked(str(text or "")), n)


def _confirming(pair: tuple[str, str], pool: list[dict[str, Any]], known: dict[str, str]) -> tuple[list[str], str]:
    """The findings of *pool* one confirm message carries within ``BOUND``, newest first, and that message.

    Raises:
        StoppedError: Not even one finding fits beside the known mechanisms.
    """
    mechanisms = [{"id": k, "mechanism": _shown(v)} for k, v in known.items()]
    shown = [
        {"id": f["id"], "what": _shown(f.get("what")), "mechanism": _shown(f.get("mechanism"))}
        | {"quotes": [_shown(q, QUOTE) for q in (f.get("quotes") or ())[:3]]}
        for f in pool
    ]
    while shown:
        evidence = {"cause": _shown(pair[0]), "target": _shown(pair[1]), "mechanisms": mechanisms, "findings": shown}
        message = f"{CONFIRM.read_text()}\n\n## The evidence\n\n```json\n{dumps(evidence)}\n```\n"
        if len(message) <= BOUND:
            return [f["id"] for f in shown], message
        shown = shown[:-1]
    msg = "stopped: a confirm batch cannot fit its known mechanisms"
    raise StoppedError(msg)


def _confirm(w: Work, pair: tuple[str, str], pool: list[dict[str, Any]], known: dict[str, str]) -> None:
    """One confirm batch: sort *pool* into the *known* mechanisms of *pair*, new ones or none; keep the sorting.

    The findings that do not fit in the message stay unsorted for a later run.
    """
    ids, message = _confirming(pair, pool, known)
    pool = [f for f in pool if f["id"] in ids]
    said = paid(w, f"confirm:{pair[0]}|{pair[1]}", message, lambda s: _valid_sorting(s, ids, known))
    new = {str(k): str(v) for k, v in (said.get("new") or {}).items()}
    lines = []
    for f in pool:
        to = said["assign"][f["id"]]
        if to.startswith("new:"):
            text = new[to[4:]].strip()
            to = f"m-{store.digest([*pair, text])}"
            known[to] = text
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
        for uid, u in store.known().items()
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
    same = [p for p in props.folded().values() if p.get("provenance", "real") == w.provenance]
    if any(p["state"] not in props.CLOSED for p in same if p.get("kind") == "look-reconsider"):
        return []
    judged = sorted(  # the unit being judged is the newest; its judgement is settled only after this phase
        (
            u
            for uid, u in store.known().items()
            if uid != w.uid and u.get("judged_at") and u.get("provenance", "real") == w.provenance
        ),
        key=lambda u: u["judged_at"],
    )[-(WINDOW - 1) :]
    window = {u["family"] for u in judged} | {w.unit.get("family", w.uid)}
    inside = [f for f in every if f["family"] in window]
    caught = [f["id"] for f in inside if f.get("catchable")]
    if not inside or len(caught) / len(inside) < CATCHABLE:
        return []
    return [
        props.file(
            props.open_key(w.provenance, "look-reconsider"),
            caught,
            kind="look-reconsider",
            cause="",
            target="spotter:looks",
            provenance=w.provenance,
            assumptions=[assumptions.RETRO_CATCHABLE, *_synthetic(w)],
            mechanism=f"{len(caught)} of {len(inside)} findings over the last {len(judged) + 1} judged units "
            "were catchable at their moment",
            bar=f"at least {CATCHABLE:.0%} catchable findings",
        )
    ]


def propose(w: Work, found: list[str]) -> list[str]:
    """Phase 2: file what this run's evidence and what came before it carry; the proposals touched."""
    gone, synthetic = store.retired_ids(), w.provenance == "synthetic"
    every = [
        f
        for f in store.all_findings()
        if f.get("provenance") == w.provenance
        and f.get("status") == "known"
        and store.visible(f, gone, synthetic=synthetic)
    ]  # what rests on a retired assumption counts toward no bar
    mine = [f for f in every if f["id"] in set(found)]
    out = [*_delivery(w, mine), *cases(w), *_lessons(w, every), *_catchable(w, every)]
    return list(dict.fromkeys(p for p in out if p))
