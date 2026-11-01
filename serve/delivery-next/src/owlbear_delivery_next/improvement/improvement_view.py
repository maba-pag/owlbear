"""What the Improvement page reads (#716, design §6): the Spotter, Retro, the Spotter cases and Retro's proposals.

Each part is a read of the stores; the routes pass in the projects the machine has loaded (``units.Projects``).
Nothing here writes or spends.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import case_replay, cases, followups, proposal_apply
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.cases import CaseError
from owlbear_delivery_next.state_store import watch_reports
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Store

SETTINGS = "/config#spotter-title"  # where the Spotter's settings are changed: the Settings page's Spotter panel
WINDOW = 7  # days the Spotter's spend is summed over
LOOKS = 200  # looks and outside writes listed at most
RUNS = 50  # Retro's newest runs shown
FINDINGS = 50  # Retro's newest findings shown, each with its follow-up
ALL_RUNS = 10_000  # runs searched for a proposal's redraft or a finding's follow-up
CLOSED = 30  # closed proposals shown, newest first
VERSIONS = 20  # case versions and case runs shown, newest first
SEEN = 3  # a proposal's findings its card shows
OPEN = {"waiting": 0, "shown": 0, "later": 1, "drafted": 2}  # the order open proposals are listed in
UNREADABLE = (StoreError, OSError, ValueError)
NO_SHARED = {"error": "there is no shared repository: a proposal lands in or through it"}


def _when(text: object) -> datetime:
    try:
        at = datetime.fromisoformat(str(text))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return at if at.tzinfo else at.replace(tzinfo=UTC)


def _newest(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted((dict(r) for r in rows), key=lambda r: _when(r.get("at")), reverse=True)


def _graded(records: Iterable[Mapping[str, Any]], grades: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """*records*, newest first, each with its grades and how its look ended.

    ``stopped_step`` is a step the Spotter stopped for irreversible harm (``acted``, which live delivery writes);
    ``credit_stop`` why its credits stopped the look, which stops nothing else: its limit ``reached``, or its spend
    ``unknown``; else nothing.
    """
    by: dict[str, list[dict[str, Any]]] = {}
    for g in grades:
        by.setdefault(g["record"], []).append({k: g.get(k) for k in ("grade", "reason", "should", "preliminary")})
    return [
        r
        | {
            "grades": by.get(r["id"], []),
            "credit_stop": r.get("stopped") or "",
            "stopped_step": r.get("category") == "irreversible-harm" and r.get("acted") == "stopped",
        }
        for r in _newest(records)
    ]


# The Spotter


def _settings(st: Store) -> dict[str, Any]:
    try:
        s = st.settings()
    except UNREADABLE as exc:
        return {"error": f"the settings cannot be read: {type(exc).__name__}: {exc}", "link": SETTINGS}
    sources = {k: v for k, v in s.sources.items() if k.startswith(("spotter.", "agents.spotter."))}
    return {"spotter": s.spotter.model_dump(mode="json"), "model": s.roles.get("spotter"), "sources": sources,
            "link": SETTINGS}  # fmt: skip


def spotter(projects: units.Projects, records: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    """Each loaded project's Spotter settings and each project's spend over the last week."""
    spend: dict[str, dict[str, Any]] = {}
    for r in records:
        if _when(r.get("at")) >= now - timedelta(days=WINDOW):
            s = spend.setdefault(str(r.get("project") or ""), {"looks": 0, "credits": 0.0, "unknown": 0, "stopped": 0})
            s["looks"] += 1
            s["credits"] += float(r.get("credits") or 0.0)
            s["unknown"] += not r.get("credits_known")
            s["stopped"] += r.get("stopped") == "reached"
    return {
        "projects": {pid: {"name": repo.name} | _settings(st) for pid, (st, repo) in projects.items()},
        "window_days": WINDOW,
        "spend": spend,
    }


def looks(  # noqa: PLR0913 - what is read, and the filter
    projects: units.Projects,
    records: list[dict[str, Any]],
    grades: list[dict[str, Any]],
    *,
    project: str = "",
    change: str = "",
    limit: int = LOOKS,
) -> dict[str, Any]:
    """The Spotter's looks, each with its follow-up, and the outside writes the watcher saw, newest first.

    Of one project or Change if named. With no Change named, the outside writes of every Change of the project (of
    every loaded project with none named) are merged, each tagged with its project id and Change; a project whose
    writes cannot be read says why.
    """
    picked = [r for r in records if (not project or r.get("project") == project)
              and (not change or r.get("change") == change)]  # fmt: skip
    outside, unread = [], []
    for pid, (st, _repo) in projects.items():
        if project and pid != project:
            continue
        try:
            for slug in [change] if change else st.slugs():
                rows = watch_reports.reports(st.db, slug, limit)
                outside += [r | {"project": pid, "change": slug} for r in rows if r["targets"]]
        except UNREADABLE as exc:
            unread.append(f"{pid}: {type(exc).__name__}: {exc}")
    known = _followups()
    shown = [r | {"followup": followup(r["id"], *known)} for r in _graded(picked, grades)[:limit]]
    return {"looks": shown, "outside": _newest(outside)[:limit], "unread": unread}


# Retro


def _finished(projects: units.Projects) -> list[dict[str, Any]]:
    """Every finished Change of the loaded projects, newest first: what the Run Retro picker offers."""
    found = []
    for pid, (st, repo) in projects.items():
        with contextlib.suppress(*UNREADABLE):
            for slug in st.slugs():
                with contextlib.suppress(*UNREADABLE):
                    if (done := st.read(slug).finished_at) is not None:
                        found.append({"change": f"{pid}:{slug}", "project": repo.name, "slug": slug,
                                      "at": done.isoformat()})  # fmt: skip
    return _newest(found)


def retro(projects: units.Projects, switches: Mapping[str, Any]) -> dict[str, Any]:
    """Retro's queue, newest runs and findings, units by state, switches and the finished Changes it may run on.

    Each finding carries its follow-up, a chat's too: a chat has no Change page to follow it up on.
    """
    by_state: dict[str, int] = {}
    for u in store.units(synthetic=True).values():
        state = (u.get("revisions") or [{}])[-1].get("state") or "new"
        by_state[state] = by_state.get(state, 0) + 1
    known, newest = _followups(), store.findings(synthetic=True)[::-1][:FINDINGS]
    return {
        "queued": known[0],
        "findings": [f | {"followup": followup(f["id"], *known)} for f in newest],
        "runs": [{k: v for k, v in r.items() if k != "unsettled"} for r in store.runs(RUNS, synthetic=True)],
        "units": by_state,
        "switches": dict(switches),
        "finished": _finished(projects)[:LOOKS],
    }


# The Spotter cases


def prefill(cid: str) -> str:
    """The example text a move into the examples starts from: the card's task and its last action, cut to fit.

    The case's own example text is empty for a case checked the ordinary way, and its record's turn is an event id.
    """
    try:
        card = cases.card(cid)
    except CaseError:
        return ""
    parts = [str((card.get("intent") or {}).get("task") or "")]
    if recent := card.get("recent"):
        last = recent[-1]
        parts.append(str(last.get("text") or " ".join(str(last.get(k) or "") for k in ("tool", "args", "result"))))
    return "\n\n".join(p.strip() for p in parts if p.strip())[: cases.EXAMPLE]


def _case(cid: str, entry: Mapping[str, Any]) -> dict[str, Any]:
    try:
        fact = cases.fact(cid)
    except CaseError as exc:
        return {"id": cid, **entry, "marks": [], "error": str(exc)}
    marks = [m for m, on in (("reserve", fact.get("reserve")), ("synthetic", fact.get("source") == "synthetic"),
                             ("unscored", fact.get("unscored"))) if on]  # fmt: skip
    if fact.get("assumption"):
        marks.append(f"assumption {fact['assumption']}")
    return {"id": cid, **entry, "source": fact.get("source"), "marks": marks, "prefill": prefill(cid)}


def spotter_cases() -> dict[str, Any]:
    """The newest version's cases with marks, its versions and case runs (newest first), the queued and running runs."""
    cur = cases.current()
    shown = [{k: v for k, v in v.items() if k != "cases"} for v in cases.versions()]
    return {
        "n": cur["n"],
        "cases": [_case(cid, e) for cid, e in sorted(cur["cases"].items())],
        "versions": shown[::-1][:VERSIONS],
        "runs": case_replay.results()[::-1][:VERSIONS],
        "queued": [*case_replay.queued(), *({**r, "running": True} for r in case_replay.running())],
    }


# Retro's proposals


def places(projects: units.Projects) -> dict[str, targets.Place]:
    """The loaded projects as proposals and follow-ups see them: each one's folder and clone."""
    return {pid: targets.Place(st.name, repo) for pid, (st, repo) in projects.items()}


def _redrafts() -> dict[str, dict[str, Any]]:
    """Each redirected proposal's redraft as far as known, by its id: queued, else its newest run's state and result.

    One with neither (its request lost with the host that took it) may be asked for again.
    """
    found: dict[str, dict[str, Any]] = {}
    for r in store.runs(ALL_RUNS, synthetic=True):
        if (unit := str(r.get("unit") or "")).startswith("proposal:"):
            found.setdefault(unit.removeprefix("proposal:"), {k: r.get(k) for k in ("state", "result", "why")})
    return found | {q["redraft"]: {"state": "queued"} for q in store.queued() if q.get("redraft")}


def _found() -> dict[str, dict[str, Any]]:
    """What a proposal can rest on, by id: Retro's findings, and its grades, which a Spotter case rests on."""
    found = {f["id"]: f for f in store.findings(synthetic=True)}
    for g in store.grades(synthetic=True):
        unit, why = str(g.get("unit") or ""), f": {g['reason']}" if g.get("reason") else ""
        change = unit.removeprefix("chg:") if unit.startswith("chg:") else ""
        what = f"the {g.get('look') or 'Spotter'} look was graded {g.get('grade')}{why}"
        found.setdefault(g["id"], {"id": g["id"], "change": change, "unit": unit, "what": what, "cost": ""})
    return found


def _seen(snap: Mapping[str, Any], found: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Up to ``SEEN`` of *snap*'s findings as its card shows them: where, what was seen and what it cost."""
    picked = [found[f] for f in snap["findings"] if f in found][:SEEN]
    return [{k: f.get(k) for k in ("id", "change", "unit", "what", "cost")} for f in picked]


def _shown(
    snap: dict[str, Any], dest: dict[str, Any], redrafts: Mapping[str, Any], found: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    return snap | {"destination": dest, "token": props.token(snap, dest), "redraft_run": redrafts.get(snap["id"], {}),
                   "seen": _seen(snap, found)}  # fmt: skip


def proposals(projects: units.Projects, shared_root: Path | None) -> list[dict[str, Any]]:
    """The visible proposals: open ones first, then the newest closed ones and every closed one with work left.

    Open ones are waiting, later or under review. Work is left on an accepted one not made in full and on a redirected
    one whose redraft is not filed and reviewed. An open one carries where it would land, or why it cannot be
    accepted, and the token a decision on it names.
    """
    where, known, redrafts, found = places(projects), targets.units_of(), _redrafts(), _found()
    open_, closed = [], []
    for snap in props.proposals(synthetic=True):
        if snap["state"] in props.CLOSED:
            closed.append(_shown(snap, snap["accepted"].get("destination") or {}, redrafts, found))
        elif shared_root is None:
            open_.append(_shown(snap, NO_SHARED, redrafts, found))
        else:
            open_.append(_shown(snap, proposal_apply.destination(snap, where, shared_root, known), redrafts, found))
    open_.sort(key=lambda p: (OPEN.get(p["state"], len(OPEN)), -_when(p["history"][-1]["at"]).timestamp()))
    closed.sort(key=lambda p: _when(p["history"][-1]["at"]), reverse=True)
    return open_ + [p for i, p in enumerate(closed) if i < CLOSED or _unfinished(p)]


def _unfinished(p: Mapping[str, Any]) -> bool:
    if p["state"] == "accepted":
        return p["apply_state"] != "done"
    return p["state"] == "redirected" and (not p["redraft"] or p["redraft_state"] == "drafted")


# A Change's detail and a finding's follow-up


def _followups() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    return store.queued(), store.runs(ALL_RUNS, synthetic=True), followups.saved()


def followup(
    fid: str, queued: list[dict[str, Any]], runs: list[dict[str, Any]], saved: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    """What this machine knows of *fid*'s follow-up.

    Queued, its entry saved without a run, the newest run's entry or how it ended, else nothing.
    """
    if any(q.get("followup") == fid for q in queued):
        return {"state": "queued"}
    if fid in saved:
        return {"state": "saved", "entry": saved[fid]}
    run = next((r for r in runs if r.get("unit") == f"finding:{fid}"), None)
    if run is None:
        return {"state": ""}
    if run.get("followup"):
        return {"state": "saved", "entry": run["followup"]}
    return {"state": run.get("state") or "", "result": run.get("result") or "", "why": run.get("why") or ""}


def change_detail(pid: str, slug: str, records: list[dict[str, Any]], grades: list[dict[str, Any]]) -> dict[str, Any]:
    """Change *slug* of project *pid*: its looks with their grades and its Retro findings, each with its follow-up."""
    known = _followups()
    picked = [r for r in records if r.get("project") == pid and r.get("change") == slug]
    shown = [r | {"followup": followup(r["id"], *known)} for r in _graded(picked, grades)]
    found = store.findings(change=f"{pid}:{slug}", synthetic=True)
    return {"looks": shown, "findings": [f | {"followup": followup(f["id"], *known)} for f in found]}
