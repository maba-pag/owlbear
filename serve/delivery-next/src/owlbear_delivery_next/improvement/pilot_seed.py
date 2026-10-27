"""Seeding the Spotter cases from the pilot (Improvement design §3, §4), once, from its saved cards only.

The pilot's 83 hindsight moments have saved cards (old shape); each is mapped to today's card. Nothing reads a chat log
again: enrolment comes before any read. What the saved card lacks is a gap in the card: the evidence outputs (the pilot
saved references only, with result excerpts in the recent actions), the decisions where none were given, the open work
where none was given. Hindsight's verdicts give the calls: ``could-not-should`` and ``no-issue`` are ``none``; each
``should`` takes the category the owner's or reviewer's calls file names (never guessed); ``unknown`` moments are left
out (b75e11 included: unknown is never a positive). wr-p-759028 is seeded unscored: TD-435, the decision it turns on,
is not in its card. Every seeded case is a candidate; a review of its frozen card makes it a test case.

Both pilot split assignments are kept (``split.json`` by session, ``eval-ids.json`` by moment); a family neither
assigns is assigned once by the pilot's rule and kept. The pilot's holdout is the reserve: its prompt experiments saw
it, so it is historically exposed, not unseen.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions, case_intake, cases
from owlbear_delivery_next.improvement.card import bounded
from owlbear_delivery_next.improvement.cases import CaseError
from owlbear_delivery_next.improvement.events import clean, clip

if TYPE_CHECKING:
    from collections.abc import Mapping

CARDS = (
    "moments-dev-v2p.jsonl",
    "moments-holdout-v2p.jsonl",
    "moments-fresh-cards.jsonl",
    "moments-fresh2-cards.jsonl",
)
UNSCORED = {"wr-p-759028": "TD-435, the decision it turns on, is not in its card"}
NONE = frozenset({"could-not-should", "no-issue"})
SYNTHETIC = Path(__file__).with_name("synthetic_cases.json")
MAPPED = "mapped from the pilot's saved card (2026-10-25): evidence outputs were not saved, only result excerpts"


def _cleaned(value: Any) -> Any:  # noqa: ANN401 - the card's JSON values
    if isinstance(value, str):
        return clean(value)
    if isinstance(value, list):
        return [_cleaned(v) for v in value]
    if isinstance(value, dict):
        return {k: _cleaned(v) for k, v in value.items()}
    return value


def _recent(a: dict[str, Any]) -> dict[str, Any]:
    if a.get("type") != "tool":
        return {"at": a.get("at"), "kind": "agent message" if a.get("type") == "assistant_message" else a.get("type")}
    out = {"at": a.get("at"), "tool": a.get("tool"), "args": clip(a.get("args", ""), 300)}
    if "result_excerpt" in a or "ok" in a:
        return out | {"ok": a.get("ok"), "result": clip(a.get("result_excerpt") or a.get("error") or "", 300)}
    return out | {"result": "not completed at this moment"}


def mapped(saved: dict[str, Any]) -> dict[str, Any]:
    """Today's card from a pilot moment's saved card; what it lacks named in its gaps."""
    intent, source = saved.get("intent") or {}, saved.get("source") or {}
    if "messages" in intent:
        said = [m.get("text", "") for m in intent["messages"]]
        task, later = (said[0] if said else ""), said[1:]
    else:
        task = intent.get("step_prompt", "")
        later = [m.get("text", "") if isinstance(m, dict) else str(m) for m in intent.get("later_harness_messages", [])]
    actions = saved.get("last_actions") or []
    last = actions[-1] if actions else {}
    moment: dict[str, Any] = {"at": source.get("cutoff_at"), "cutoff": source.get("cutoff_event_index")}
    if last.get("type") == "assistant_message" and last.get("event_index") == source.get("cutoff_event_index"):
        moment |= {"kind": "hand-off", "call": "", "result": clip(last.get("text", ""), 3000)}
    else:
        moment |= {"kind": "a completed action", "call": last.get("event_id", "")}
    timing = saved.get("timing") or {}
    work = saved.get("open_work") or {}
    open_work = list(work.get("plan_open_rows", [])) if isinstance(work, dict) else list(work)
    decisions = "\n".join(
        f"{d.get('id')} ({d.get('refs')}): {d.get('statement')}" for d in saved.get("decisions") or []
    )
    gaps = [*(saved.get("context_gaps") or []), MAPPED, "the moment's kind was read from the saved card"]
    gaps += [] if decisions else ["the decisions in force were not given at this moment"]
    gaps += [] if open_work else ["the open work was not given at this moment"]
    card = {
        "step": "",
        "intent": {"task": task, "later_requests": later, "answers": saved.get("owner_answers") or []},
        "plan": [{k: v for k, v in p.items() if k != "n"} for p in saved.get("agent_plan") or []],
        "moment": moment,
        "recent": [_recent(a) for a in actions[-15:]],
        "evidence": [],
        "timing": {
            "now": timing.get("now"),
            "minutes_since_request": timing.get("minutes_since_owner_message"),
            "minutes_since_edit": timing.get("minutes_since_agent_changed_a_file"),
            "minutes_waiting_in_last_30": timing.get("minutes_waiting_in_last_30"),
        },
        "open_work": open_work,
        "decisions": clip(decisions, 6000),
        "gaps": gaps,
    }
    return bounded(_cleaned(card))


def _read(folder: Path, name: str) -> Any:  # noqa: ANN401 - each file's JSON
    try:
        text = (folder / name).read_text()
    except OSError as exc:
        msg = f"the pilot's {name} cannot be read: {exc}"
        raise CaseError(msg) from exc
    try:
        return [json.loads(x) for x in text.splitlines() if x.strip()] if name.endswith(".jsonl") else json.loads(text)
    except ValueError as exc:
        msg = f"the pilot's {name} cannot be read: {exc}"
        raise CaseError(msg) from exc


def _sides(folder: Path, saved: Mapping[str, dict[str, Any]], ids: list[str]) -> dict[str, str]:
    """Each moment's family side: both pilot assignments kept, the rest hashed once; all persisted."""
    sessions = _read(folder, "split.json").get("sessions", {})
    evals = {m: k for k, ms in _read(folder, "eval-ids.json").items() for m in ms}
    given: dict[str, tuple[str, str]] = {}
    for mid in ids:
        family, sid = saved[mid]["family"], saved[mid]["source"]["session"]
        pilot = sessions.get(sid, {}).get("split") or evals.get(mid)
        if pilot:
            given.setdefault(family, ("dev" if pilot == "dev" else "reserve", "the pilot's split"))
    rest = sorted({saved[m]["family"] for m in ids} - set(given) - set(case_intake.families()))
    return case_intake.assign({**given, **case_intake.hashed(rest)})


def _seeded(kind: str) -> set[str]:
    """The pilot moments or synthetic names already seeded: those of every case some version ever held.

    A case frozen by a seed that stopped before its version was written is in no version, so it is seeded again; one
    removed since stays seeded.
    """
    out = set()
    for cid in {cid for v in cases.versions() for cid in v["cases"]}:
        prov = cases.fact(cid).get("provenance", {})
        if kind in prov:
            out.add(prov[kind] if isinstance(prov[kind], str) else prov[kind].get("moment", ""))
    return out


def seed(folder: Path, calls: Mapping[str, str], by: str) -> dict[str, Any]:
    """Seed the pilot's hindsight moments as candidates; what was seeded and left out. A second seed adds nothing new.

    *calls* names each ``should`` moment's category.

    Raises:
        CaseError: A pilot file is unreadable, a moment's saved card is missing, or a ``should`` has no category.
    """
    rows = _read(folder, "hindsight.jsonl")
    saved = {r["id"]: r for name in CARDS for r in _read(folder, name) if r.get("id")}
    missing = sorted(r["id"] for r in rows if r["id"] not in saved)
    if missing:
        msg = f"no saved card for {', '.join(missing)}"
        raise CaseError(msg)
    should = [r["id"] for r in rows if r["verdict"] == "should"]
    if gaps := [m for m in should if calls.get(m) not in cases.CATEGORIES]:
        msg = f"name a finding category for each should moment: {', '.join(gaps)}"
        raise CaseError(msg)
    ids = [r["id"] for r in rows if r["verdict"] != "unknown"]
    sides, done = _sides(folder, saved, ids), _seeded("pilot")
    edits: dict[str, cases.Entry] = {}
    for r in rows:
        mid = r["id"]
        if r["verdict"] == "unknown" or mid in done:
            continue
        s = saved[mid]
        call = "none" if r["verdict"] in NONE else calls[mid]
        why = clip(f"{r.get('problem') or ''} {r.get('why') or ''}".strip(), cases.WHY)
        provenance = {
            "pilot": {
                "moment": mid,
                "session": s["source"].get("session"),
                "cutoff_event_index": s["source"].get("cutoff_event_index"),
                "cutoff_event_id": s["source"].get("cutoff_event_id"),
                "hindsight": {k: r.get(k) for k in ("verdict", "cost", "self_corrected", "channel")},
            }
        }
        cid = cases.freeze(
            mapped(s),
            {
                "source": "pilot",
                "provenance": provenance,
                "family": s["family"],
                "reserve": sides[s["family"]] == "reserve",
                "unscored": UNSCORED.get(mid, ""),
            },
        )
        edits[cid] = {"stage": "candidate", "call": call, "why": why, "example": "", "review": None}
    left_out = sorted(r["id"] for r in rows if r["verdict"] == "unknown")
    if edits:
        with cases.locked():
            cases.commit(cases.current()["n"], edits, by, "seeded from the pilot's hindsight moments")
    return {"seeded": len(edits), "already": len(done), "left_out": left_out}


def synthetic(by: str) -> dict[str, Any]:
    """Seed the synthetic cases (a marked assumption) as candidates; never in the reserve.

    Raises:
        CaseError: Their assumption was reset.
    """
    if not assumptions.ensure(assumptions.SYNTHETIC):
        msg = "the synthetic cases' assumption was reset: they are not seeded again"
        raise CaseError(msg)
    done, edits = _seeded("synthetic"), {}
    for case in json.loads(SYNTHETIC.read_text()):
        if case["name"] in done:
            continue
        the_card = {**case["card"], "gaps": [*case["card"].get("gaps", []), "synthetic: an invented moment"]}
        cid = cases.freeze(
            the_card,
            {
                "source": "synthetic",
                "provenance": {"synthetic": case["name"]},
                "family": f"synthetic:{case['name']}",
                "reserve": False,
                "assumption": assumptions.SYNTHETIC,
            },
        )
        edits[cid] = {"stage": "candidate", "call": case["call"], "why": case["why"], "example": "", "review": None}
    if edits:
        with cases.locked():
            cases.commit(cases.current()["n"], edits, by, "synthetic cases for categories no real moment shows yet")
    return {"seeded": len(edits), "already": len(done)}
