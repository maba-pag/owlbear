"""Each run's own share of its session's cumulative usage, split exclusively by agent and model (spend metrics).

The ledger's lines (``spend_ledger``) become runs: a live ``start`` and ``end`` pair by ``run``, or one line
``spend_reconcile`` imported: an ``event`` (a step's usage at a known time), a ``mark`` (a session's latest totals
a Change kept, time unknown), a ``residual`` (a Change's spend no session holds) or a ``look`` (a Spotter look before
the ledger). Every run names the ``session`` whose totals it reports; the totals only grow.

Shares are derived per session before anything is filtered or grouped, so a filter never hands a resumed run the
spend of earlier ones. The runs go in time order (unknown times last, as imported). Two kinds of high-water mark
start at zero: the session's totals per field (credits and each token count), which alone decide how much a run
spent, and each cell's (agent instance and model), which only decide whom that spend goes to. A report that splits
earlier spend anew (an unsplit legacy total, then the runtime's per-agent split) moves credits between cells but
never creates any: the growth the cells show is scaled down to the session's own growth. For each run:

1. Its ``before``, when known, is its session's totals when it started: what exceeds the marks was spent between
   the last run reported and this one. It goes to the latest earlier run whose usage is unknown (``recovered``, in
   that run's agent and time window, which is then no longer unknown), else stands as a ``gap``, its agent known and
   its time not.
2. Its usage, when read: what exceeds the marks is its own share (``run``). A run whose ``before`` was unread takes
   all growth since the last report, in the window from that report to its end. Unread: one ``unknown`` piece, its
   credits None; a ``start`` alone is ``open``. A run that spent nothing still keeps one piece, of zero credits (or
   None when its credits were not reported), so it counts as a run with its ending and its stop.
3. The marks rise to its usage.

A cell whose credits are unread has None credits; the session's growth the cells do not cover is ``unallocated``
within the run's role, and a run with subagents but no split marks its pieces uncertain in agent. A piece's time is
the window ``[lo, hi]`` it certainly lies in: one instant for a run, the run's end; wider or open-ended when
uncertain, never a made-up day.
"""

from __future__ import annotations

from typing import Any

FIELDS = ("credits", "input", "output", "cache_read", "cache_write")
EPS = 1e-9
LIVE = ("start", "end")


def _fields(m: dict[str, Any]) -> dict[str, float | None]:
    c = m.get("credits")
    return {"credits": None if c is None else float(c)} | {f: float(m.get(f) or 0) for f in FIELDS[1:]}


def cells(usage: dict[str, Any], model: str) -> dict[tuple[str, str], tuple[str, dict[str, float | None]]]:
    """A cumulative usage as cells: (agent instance, model) to (subagent name, "" for the main agent; fields)."""
    out: dict[tuple[str, str], tuple[str, dict[str, float | None]]] = {}
    if agents := usage.get("agents"):
        for key, a in agents.items():
            name = "" if key == "main" else (a.get("agent") or "subagent")
            for m, mm in (a.get("models") or {}).items():
                out[key, m] = (name, _fields(mm))
    else:
        for m, mm in (usage.get("models") or {}).items():
            out["main", m] = ("", _fields(mm))
    if not out and (total := usage.get("credits")) is not None:
        return {("main", model): ("", _fields({"credits": total}))}
    return out


def totals(
    usage: dict[str, Any], split: dict[tuple[str, str], tuple[str, dict[str, float | None]]]
) -> dict[str, float | None]:
    """The session's own cumulative totals: its reported credits (else the cells' when all are known) and tokens."""
    known = [f["credits"] for _, f in split.values()]
    spent = usage.get("credits")
    if spent is None and split and None not in known:
        spent = sum(known)  # type: ignore[arg-type]
    out: dict[str, float | None] = {"credits": None if spent is None else float(spent)}
    return out | {f: sum(v[f] or 0.0 for _, v in split.values()) for f in FIELDS[1:]}


def runs(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The ledger's lines as runs, in the order their first line came."""
    by: dict[str, dict[str, Any]] = {}
    for line in lines:
        kind = line.get("type")
        rid = str(line.get("run") or line.get("id")) if kind in LIVE else str(line.get("id"))
        run = by.setdefault(rid, {"run": rid, "usage": None, "at": None, "started": None, "before": None})
        if kind == "start":
            run |= {k: v for k, v in line.items() if k not in {"id", "type", "at"}} | {"started": line.get("at")}
            run.setdefault("source", "recorded")
        else:
            keep = {k: v for k, v in line.items() if k not in {"id", "type"} and (v not in ("", None) or k not in run)}
            run |= keep | {"ended": True}
            run.setdefault("source", "recorded" if kind == "end" else f"import:{kind}")
    return list(by.values())


def _time(run: dict[str, Any]) -> str | None:
    return run.get("at") or run.get("started")


def _base(run: dict[str, Any]) -> dict[str, Any]:
    keys = ("run", "session", "project", "name", "clone", "change", "step", "job", "ending", "stopped", "stopped_by",
            "limit", "source")  # fmt: skip
    return {k: run.get(k) or ("" if k != "limit" else None) for k in keys} | {"role": run.get("agent") or ""}


def _piece(  # noqa: PLR0913, PLR0917 - the run and each part of its piece
    run: dict[str, Any], kind: str, name: str, model: str, share: dict[str, float | None],
           window: tuple[str | None, str | None], uncertain: list[str]) -> dict[str, Any]:  # fmt: skip
    role = run.get("agent") or ""
    agent, under = (role, "") if name == "" else ("", role) if name == "?" else (name, role)
    if name == "?" or (name == "" and run.get("subagents") and not (run.get("usage") or {}).get("agents")):
        uncertain = [*uncertain, "agent"]
    if not agent and "agent" not in uncertain:
        uncertain = [*uncertain, "agent"]
    return _base(run) | share | {"kind": kind, "agent": agent, "under": under, "model": model, "lo": window[0],
                                 "hi": window[1], "uncertain": sorted(set(uncertain))}  # fmt: skip


type Cell = tuple[str, str]
type Marks = dict[str, float]


def _grow(usage: dict[str, Any], model: str, session: Marks, marks: dict[Cell, Marks]) -> tuple[
        dict[Cell, tuple[str, dict[str, float | None]]], dict[str, float | None], bool]:  # fmt: skip
    """What *usage* adds: each cell's share, the unallocated rest, and whether the session's credits are known.

    The session's growth per field decides the amount; the cells' growth only splits it, scaled down when the cells
    re-split earlier spend. The marks rise to *usage*.
    """
    split = cells(usage, model)
    whole = totals(usage, split)
    shares: dict[Cell, tuple[str, dict[str, float | None]]] = {c: (n, {}) for c, (n, _) in split.items()}
    rest: dict[str, float | None] = {}
    for f in FIELDS:
        grew = {
            c: None if v[f] is None else max(0.0, v[f] - marks.get(c, {}).get(f, 0.0)) for c, (_, v) in split.items()
        }
        if (now := whole[f]) is None:
            for c in split:
                shares[c][1][f] = None
            rest[f] = None
            continue
        own = max(0.0, now - session.get(f, 0.0))
        seen = sum(g for g in grew.values() if g is not None)
        scale = own / seen if seen > own else 1.0
        for c, g in grew.items():
            shares[c][1][f] = 0.0 if g is None else g * scale
        rest[f] = max(0.0, own - seen)
        session[f] = max(session.get(f, 0.0), now)
    for c, (_, v) in split.items():
        mark = marks.setdefault(c, {})
        for f in FIELDS:
            if v[f] is not None:
                mark[f] = max(mark.get(f, 0.0), v[f])  # type: ignore[type-var]
    return shares, rest, whole["credits"] is not None


def _spent(share: dict[str, float | None]) -> bool:
    """Whether a share holds spend: credits or tokens, or tokens whose credits are unknown."""
    tokens = any((share.get(f) or 0.0) > EPS for f in FIELDS[1:])
    return (share.get("credits") or 0.0) > EPS or tokens


def _pieces(  # noqa: PLR0913, PLR0917 - the run, its kind and what grew, when and how sure
    owner: dict[str, Any], kind: str, model: str, grown: tuple[Any, dict[str, float | None], bool],
            window: tuple[str | None, str | None], uncertain: list[str]) -> list[dict[str, Any]]:  # fmt: skip
    shares, rest, _ = grown
    out = [_piece(owner, kind, name, cell[1], share, window, uncertain)
           for cell, (name, share) in shares.items() if _spent(share)]  # fmt: skip
    if _spent(rest):
        out.append(_piece(owner, kind, "?", "" if shares else model, rest, window, uncertain))
    return out


def derive(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every piece of spend the ledger holds: exclusive, additive, each in one run, agent and model."""
    sessions: dict[str, list[dict[str, Any]]] = {}
    for n, run in enumerate(runs(lines)):
        run["n"] = n
        sessions.setdefault(str(run.get("session") or run["run"]), []).append(run)
    pieces: list[dict[str, Any]] = []
    for group in sessions.values():
        group.sort(key=lambda r: (_time(r) is None, _time(r) or "", r["n"]))
        pieces += _session(group)
    return pieces


def _session(group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    session: Marks = {}
    marks: dict[Cell, Marks] = {}
    out: list[dict[str, Any]] = []
    lost: dict[str, Any] | None = None  # the latest run whose usage is unknown: later growth may be its own
    placeholder: dict[str, Any] = {}  # its unknown piece, dropped once its spend is recovered
    last: str | None = None  # the latest known time in this session: its last report
    for run in group:
        model = run.get("model") or ""
        if (before := run.get("before")) is not None and "error" not in before:
            grown = _grow(before, model, session, marks)
            if lost is not None:
                found = _pieces(lost, "recovered", model, grown, (lost.get("started") or last, run.get("started")),
                                ["at"])  # fmt: skip
                if found and placeholder in out:  # what it spent is known now: no longer unknown
                    out.remove(placeholder)
            else:
                found = _pieces(run, "gap", model, grown, (last, run.get("started")), ["at"])
            out += found
        usage = run.get("usage")
        if usage is None or "error" in usage:
            kind = "open" if usage is None else "unknown"
            window = (run.get("at"), run.get("at")) if run.get("at") else (run.get("started"), None)
            placeholder = _piece(run, kind, "", model, {f: None if f == "credits" else 0.0 for f in FIELDS}, window, [])
            out.append(placeholder)
            lost = run
            last = _time(run) or last
            continue
        timed = bool(run.get("at"))
        exact = timed and (before is not None or run.get("source") != "recorded")
        window = (run["at"], run["at"]) if exact else (last, run.get("at"))  # unread baseline: since the last report
        grown = _grow(usage, model, session, marks)
        found = _pieces(run, "run", model, grown, window, [] if exact else ["at"])
        if not found:  # nothing spent, or nothing known: still a run, with its ending and its stop
            zero = {f: (0.0 if grown[2] else None) if f == "credits" else 0.0 for f in FIELDS}
            found = [_piece(run, "run" if grown[2] else "unknown", "", model, zero, window, [] if exact else ["at"])]
        out += found
        lost = None
        last = run.get("at") or last
    return out
