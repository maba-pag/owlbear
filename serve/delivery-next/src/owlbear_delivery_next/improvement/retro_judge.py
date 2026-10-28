"""Retro's run over one unit revision (#715, Improvement design §5): judge and grade, propose, review.

Each paid call is a batch kept before anything is derived from it (``retro_calls``).

Phases: (1) judge and grade, batches of the revision's parts with the records whose moment falls in them, each
bounded at ``BATCH`` characters; one answer gives the findings (each quote checked against the text it cites) and one
grade per record carried; (2) propose (``retro_bars``); (3) review, one ``retro-review`` batch per proposal whose
evidence has changed since its last review, bound to its evidence digest.
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions, case_review, retro_bars, retro_segments, spotter
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.retro_calls import Work, key, paid, strings
from owlbear_delivery_next.improvement.retro_segments import cut, dumps
from owlbear_delivery_next.local_system import mask

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from owlbear_delivery_next.improvement.retro_segments import Part

BATCH, REVIEW = 60_000, 20_000  # characters of one judging batch's and one review's message
CARD, NOTE, GAPS = 1_200, 600, 2_000  # characters of a record's card excerpt and note; of the gaps said
SAMPLES, SHOWN = 8, 3  # representative findings and counterexamples a review shows
JUDGE = Path(__file__).with_name("retro_judge_prompt.md")
REVIEWING = Path(__file__).with_name("retro_review_prompt.md")
UNASSESSABLE = frozenset({"failed", "insufficient-context", ""})
NEEDS = (assumptions.RETRO_SEGMENTS, assumptions.RETRO_CAUSES, assumptions.RETRO_GRADES)


# Phase 1: judge and grade


def assessable(record: Mapping[str, Any]) -> bool:
    """Whether a look can be graded: it was not skipped or failed, had the facts, and is no gap."""
    return bool(record.get("cutoff")) and not record.get("skipped") and record.get("category") not in UNASSESSABLE


def silence(record: Mapping[str, Any]) -> bool:
    """Whether *record* is a sampled look that stayed silent: the only one that can be ``missed``."""
    return record.get("look") == "sample" and record.get("category") == "none"


def _card(rid: str) -> str:
    try:
        with gzip.open(spotter.place() / "cards" / f"{rid}.json.gz", "rt") as fh:
            return cut(mask.redact(fh.read()), CARD)
    except (OSError, EOFError) as exc:
        return f"[card missing: {type(exc).__name__}]"


def _entry(r: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": r["id"],
        "look": r.get("look"),
        "category": r.get("category"),
        "at": f"e{r.get('cutoff')}",
        "session": r.get("session"),
        "note": cut(mask.redact(str(r.get("note") or "")), NOTE),
        "sampled_silence": silence(r),
        "card": cut(mask.redact(dumps(r["card"])), CARD) if "card" in r else _card(r["id"]),
    }


def _unassessable(record: Mapping[str, Any]) -> str:
    if not record.get("cutoff"):
        return str(record.get("skipped") or "a gap in what the Spotter could see")
    return str(record.get("skipped") or f"its look was {record.get('category') or 'skipped'}")


def _home(record: Mapping[str, Any], parts: list[Part]) -> int:
    """The part a record's moment falls in: its session's last part begun by then, else its first; else the last."""
    mine = [i for i, p in enumerate(parts) if p.session == record.get("session")]
    begun = [i for i in mine if parts[i].first <= int(record.get("cutoff") or 0)]
    return begun[-1] if begun else mine[0] if mine else len(parts) - 1


def _message(w: Work, parts: Iterable[Part], records: Iterable[Mapping[str, Any]]) -> str:
    evidence = {
        "unit": w.unit.get("kind", ""),
        "gaps": cut("; ".join(w.unit.get("gaps") or ()), GAPS),
        "earlier": w.prepared.earlier,
        "parts": [{"ref": p.ref, "text": p.text, "later": p.later} for p in parts],
        "records": [_entry(r) for r in records],
    }
    return f"{JUDGE.read_text()}\n\n## The evidence\n\n```json\n{dumps(evidence)}\n```\n"


def batches(w: Work, records: list[dict[str, Any]]) -> list[tuple[list[Part], list[dict[str, Any]]]]:
    """The judging batches: consecutive parts with their records, each message within ``BATCH``.

    A part whose records do not fit with it is carried again with the rest of them; a grade-only run carries only
    the parts that hold its records.
    """
    parts = w.prepared.parts
    held: dict[int, list[dict[str, Any]]] = {}
    for r in records:
        held.setdefault(_home(r, parts), []).append(r)
    room = BATCH - len(_message(w, (), ()))
    pieces: list[tuple[Part, list[dict[str, Any]]]] = []
    for i, part in enumerate(parts):
        mine, size = held.get(i, []), len(dumps({"ref": part.ref, "text": part.text, "later": part.later}))
        if w.grade_only and not mine:
            continue
        chunk: list[dict[str, Any]] = []
        for r in mine:
            if chunk and size + len(dumps([_entry(x) for x in [*chunk, r]])) > room:
                pieces.append((part, chunk))
                chunk = []
            chunk.append(r)
        pieces.append((part, chunk))
    out: list[tuple[list[Part], list[dict[str, Any]]]] = []
    for part, chunk in pieces:
        if out and len(_message(w, [*out[-1][0], part], [*out[-1][1], *chunk])) <= BATCH and part not in out[-1][0]:
            out[-1][0].append(part)
            out[-1][1].extend(chunk)
        else:
            out.append(([part], list(chunk)))
    return out


def _valid_finding(f: object) -> bool:
    texts = ("what", "mechanism", "cost", "cause", "target", "steps")
    return (
        isinstance(f, dict)
        and all(strings(f.get(k) or []) for k in ("refs", "quotes"))
        and all(isinstance(f.get(k) or "", str) for k in texts)
    )


def _valid_grade(g: object) -> bool:
    return isinstance(g, dict) and isinstance(g.get("record"), str) and isinstance(g.get("grade") or "", str)


def _valid_judgement(said: Mapping[str, Any]) -> bool:
    grades, found = said.get("grades"), said.get("findings")
    return (
        isinstance(found, list)
        and isinstance(grades, list)
        and all(_valid_finding(f) for f in found)
        and all(_valid_grade(g) for g in grades)
    )


def _finding(w: Work, key: str, n: int, raw: Mapping[str, Any], parts: list[Part]) -> dict[str, Any]:
    checked = retro_segments.verify(raw, parts)
    cited = {p.session for p in parts if set(checked.get("refs") or ()) & set(retro_segments.REF.findall(p.text))}
    keep = ("refs", "quotes", "what", "mechanism", "cost", "recovered", "catchable", "cause", "target", "steps")
    found = {k: checked.get(k) for k in keep} | {"rests_on_gap": bool(checked.get("rests_on_gap"))}
    if found["cause"] not in retro_bars.CAUSES:
        found["cause"] = "other"
    return found | {
        "id": f"rf-{key}-{n}",
        "status": checked["status"],
        "unit": w.uid,
        "family": w.unit.get("family", w.uid),
        "rev": w.rev.get("rev", ""),
        "change": w.uid.split(":", 1)[1] if w.uid.startswith("chg:") else "",
        "sessions": sorted(cited or {parts[0].session}),
        "provenance": w.provenance,
        "at": store.now(),
        "assumptions": [*NEEDS[:2], *([assumptions.RETRO_SYNTHETIC] if w.provenance == "synthetic" else [])],
    }


def _grade(w: Work, r: Mapping[str, Any], said: Mapping[str, Any] | None) -> dict[str, Any]:
    value, reason = (said or {}).get("grade"), str((said or {}).get("reason") or "")[:NOTE]
    if said is None:
        value, reason = "not-assessable", "not answered"
    elif value == "missed" and not silence(r):
        value, reason = "not-assessable", "missed is said only of a sampled silent look"
    elif value not in store.GRADES:
        value, reason = "not-assessable", f"not a grade: {str(value)[:40]}"
    should = str((said or {}).get("call") or "")[:60] if value in {"wrong", "missed"} else ""
    more: dict[str, Any] = {"should": should} if should else {}
    if w.provenance != "real":
        more |= {
            "provenance": w.provenance,
            "unit": w.uid,
            "family": w.unit.get("family", w.uid),
            "assumptions": [assumptions.RETRO_GRADES, assumptions.RETRO_SYNTHETIC],
        }
    return units.grade(r, w.rev.get("rev", ""), value, reason, **more)


def judging(w: Work) -> list[tuple[list[Part], list[dict[str, Any]], str]]:
    """The judging batches of *w*'s assessable records, each with its message; none when no evidence was read."""
    if not w.prepared.parts:
        return []
    return [(p, c, _message(w, p, c)) for p, c in batches(w, [r for r in w.records if assessable(r)])]


def judge(w: Work) -> list[str]:
    """Phase 1: grade every record of the revision once and keep the findings; the ids of the findings."""
    open_ = [r for r in w.records if assessable(r)]
    unseen = {"grade": "not-assessable", "reason": "no evidence of the unit could be read"}
    without = [(r, {"grade": "not-assessable", "reason": _unassessable(r)}) for r in w.records if not assessable(r)]
    without += [(r, unseen) for r in open_] if not w.prepared.parts else []
    w.found["grades"] += len(store.add_grades(_grade(w, r, said) for r, said in without))
    ids: list[str] = []
    seen: set[str] = set()  # the parts judged by an earlier batch: a part carried again yields no finding twice
    for parts, carried, message in judging(w):
        said = paid(w, "judge", message, _valid_judgement)
        fresh = {ref for p in parts if p.ref not in seen for ref in retro_segments.REF.findall(p.text)}
        seen |= {p.ref for p in parts}
        if not w.grade_only:
            cites = [(n, f, set(f.get("refs") or ())) for n, f in enumerate(said["findings"])]
            raw = [(n, f) for n, f, refs in cites if fresh & refs or (fresh and not refs)]
            found = [_finding(w, key(w, "judge", message), n, f, parts) for n, f in raw]
            w.found["findings"] += len(store.add_findings(found))
            ids += [f["id"] for f in found]
        by_id = {g.get("record"): g for g in said["grades"] if isinstance(g, dict)}
        w.found["grades"] += len(store.add_grades(_grade(w, r, by_id.get(r["id"])) for r in carried))
    return ids


# Phase 3: review


def render(snap: Mapping[str, Any], findings: Mapping[str, Mapping[str, Any]]) -> str:
    """One proposal's review message, at most ``REVIEW`` characters, deterministic for its evidence."""
    mine = [findings[f] for f in snap["findings"] if f in findings]
    newest = sorted(mine, key=lambda f: (str(f.get("at")), f["id"]), reverse=True)
    shown = sorted(newest, key=lambda f: bool(f.get("recovered")))[:SAMPLES]  # the costliest: unrecovered, then newest
    proposal = {
        "id": snap["id"],
        "kind": snap.get("kind"),
        "cause": snap.get("cause"),
        "target": snap.get("target"),
        "mechanism": snap.get("mechanism"),
        "bar": snap.get("bar"),
        "counts": {
            "findings": len(snap["findings"]),
            "families": len({f.get("family") for f in mine}),
            "counterexamples": snap["counterexamples"].get("count", 0),
        },
        "findings": [{k: f.get(k) for k in ("id", "what", "mechanism", "cost", "steps", "quotes")} for f in shown],
        "counterexamples": list(snap["counterexamples"].get("sample") or ())[:SHOWN],
        "omitted": f"[{max(0, len(snap['findings']) - len(shown))} more findings omitted]",
        "evidence": snap["evidence"],
    }
    proposal = retro_segments.masked(proposal)
    head = f"{REVIEWING.read_text()}\n\n## The proposal\n\n```json\n"
    text = dumps(proposal)
    while len(head) + len(text) + 5 > REVIEW and proposal["findings"]:
        proposal["findings"].pop()
        proposal["omitted"] = f"[{len(snap['findings']) - len(proposal['findings'])} more findings omitted]"
        text = dumps(proposal)
    return f"{head}{cut(text, REVIEW - len(head) - 5)}\n```\n"


def _valid_review(said: Mapping[str, Any]) -> bool:
    shown = said.get("publishable") or {}
    return (
        isinstance(said.get("verdict"), str)
        and said["verdict"] in {"survive", "reject"}
        and isinstance(said.get("why") or "", str)
        and strings(said.get("risks") or [])
        and isinstance(shown, dict)
        and strings(list(shown.values()))
    )


def _graded(g: Mapping[str, Any]) -> dict[str, Any]:
    """A grade as a review reads it: the look, its moment and call, the grade with its reason and the right call."""
    moment = f"at event {g.get('cutoff')} of session {g.get('session')}"
    said = f"record {g['record']} ({g.get('look')} look {moment}, it said {g.get('category') or 'nothing'})"
    should = f"; it should have said {s}" if (s := g.get("should")) else ""
    what, why = f"{said} graded {g['grade']}", f"{g.get('reason', '')}{should}"
    return {"id": g["id"], "what": what, "mechanism": why, "family": g.get("family"), "at": g.get("at")}


def review(w: Work) -> int:
    """Phase 3: review each proposal of this run's provenance whose evidence has changed; how many were reviewed."""
    findings = {f["id"]: f for f in store.all_findings()}
    findings |= {g["id"]: _graded(g) for g in store.grades(synthetic=True)}
    n = 0
    for snap in props.due_reviews():
        if snap.get("provenance") != w.provenance:
            continue
        said = dict(paid(w, f"review:{snap['evidence']}", render(snap, findings), _valid_review, "retro-review"))
        if leaked := case_review.leaks(said.get("publishable") or {}):
            said |= {"verdict": "reject", "why": f"leak: {', '.join(leaked)}", "publishable": {}}
        props.reviewed(snap["id"], snap["evidence"], said)
        n += 1
    return n


def run(w: Work) -> dict[str, Any]:
    """The three phases over *w*; what it found, proposed and reviewed.

    Raises:
        StoppedError: An answer was unusable or the run's meter closed.
        WaitingError: No call may start now; the run waits at its cursor.
    """
    found = judge(w)
    proposed = [p for p in retro_bars.cases(w) if p] if w.grade_only else retro_bars.propose(w, found)
    return {**w.found, "proposals": proposed, "reviews": review(w)}
