"""Each run's own share of its session's cumulative usage, split exclusively by agent and model (spend metrics).

The ledger's lines (``spend_ledger``) become runs: a live ``start`` and ``end`` pair by ``run``, or one line
``spend_reconcile`` imported: an ``event`` (a step's usage at a known time), a ``mark`` (a session's latest totals
a Change kept, time unknown), a ``residual`` (a Change's spend no session holds) or a ``look`` (a Spotter look before
the ledger). Every run names the ``session`` whose totals it reports; the totals only grow.

Shares are derived per session before anything is filtered or grouped, so a filter never hands a resumed run the
spend of earlier ones. The runs go in time order (unknown times last, as imported), with high-water marks per cell
(agent instance and model) and field (credits and each token count) starting at zero. For each run:

1. Its ``before``, when known, is its session's totals when it started: what exceeds the marks was spent between
   the last run reported and this one. It goes to the latest earlier run whose usage is unknown (``recovered``, in
   that run's agent and time window, which is then no longer unknown), else stands as a ``gap``, its agent known and
   its time not.
2. Its usage, when read: what exceeds the marks and ``before`` is its own share (``run``). A resumed run whose
   ``before`` was unread takes all growth since the marks, its time then uncertain. Unread: one ``unknown`` piece,
   its credits None; a ``start`` alone is ``open``.
3. The marks rise to its usage.

A cell whose credits are unread has None credits. The runtime splits a session's usage between its main agent and
each subagent instance; the total beyond those cells is ``unallocated`` within the run's role, and a run with
subagents but no split marks its pieces uncertain in agent. A piece's time is the window ``[lo, hi]`` it certainly
lies in: one instant for a run, the run's end; wider or open-ended when uncertain, never a made-up day.
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
    total = usage.get("credits")
    if total is None:
        return out
    if not out:
        return {("main", model): ("", _fields({"credits": total}))}
    known = [f["credits"] for _, f in out.values()]
    if None not in known and (rest := float(total) - sum(known)) > EPS:  # type: ignore[arg-type]
        out["?", ""] = ("?", _fields({"credits": rest}))
    return out


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
    keys = ("run", "session", "project", "name", "clone", "change", "step", "job", "ending", "stopped", "limit",
            "source")  # fmt: skip
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


def _over(now: dict[str, float | None], mark: dict[str, float]) -> dict[str, float | None] | None:
    """What *now* adds over *mark*, per field; None when it adds nothing."""
    out: dict[str, float | None] = {}
    for f in FIELDS:
        v = now.get(f)
        out[f] = None if v is None else max(0.0, v - mark.get(f, 0.0))
    return out if any((v or 0) > EPS for v in out.values()) else None


def _raise(mark: dict[str, float], now: dict[str, float | None]) -> None:
    for f in FIELDS:
        if (v := now.get(f)) is not None:
            mark[f] = max(mark.get(f, 0.0), v)


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
    marks: dict[tuple[str, str], dict[str, float]] = {}
    out: list[dict[str, Any]] = []
    lost: dict[str, Any] | None = None  # the latest run whose usage is unknown: later growth may be its own
    placeholder: dict[str, Any] = {}  # its unknown piece, dropped once its spend is recovered
    last: str | None = None  # the latest known time in this session
    for run in group:
        model = run.get("model") or ""
        if (before := run.get("before")) is not None and "error" not in before:
            for key, (name, now) in cells(before, model).items():
                if (share := _over(now, marks.setdefault(key, {}))) is None:
                    continue
                if lost is not None:
                    if placeholder in out:  # what it spent is known now: no longer unknown
                        out.remove(placeholder)
                    window = (lost.get("started") or last, run.get("started"))
                    out.append(_piece(lost, "recovered", name, key[1], share, window, ["at"]))
                else:
                    out.append(_piece(run, "gap", name, key[1], share, (last, run.get("started")), ["at"]))
                _raise(marks[key], now)
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
        window = (run["at"], run["at"]) if timed else (last, None)
        uncertain = [] if timed and (before is not None or run.get("source") != "recorded") else ["at"]
        for key, (name, now) in cells(usage, model).items():
            if (share := _over(now, marks.setdefault(key, {}))) is not None:
                out.append(_piece(run, "run", name, key[1], share, window, uncertain))
            _raise(marks[key], now)
        lost = None
        last = run.get("at") or last
    return out
