"""Context at start per Delivery role, from the spend ledger's ``context`` lines (``spend_ledger.context``).

Each line belongs to the run that opened its session; that run's place, agent, model, time and stop decide whether
it passes the page's filters, with the same meaning as tool use's (``tool_metrics.keeps``). Sessions are counted by
their id, so a session's continuations and its resumed or repeated runs count once; a session passes when one of its
runs does. A Change's residual spend is no session; a look imported from its Spotter record names its SDK sessions,
counted with its own lines' (``look:<id>`` only when it names none and no own lines have its look). A session with a
measured line is measured; any other is not: one that ran before measuring began, or whose read failed, with that
read's error.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.state_store import spend_ledger, spend_shares, tool_metrics

if TYPE_CHECKING:
    from datetime import date
    from zoneinfo import ZoneInfo

LATEST = ("session", "run", "project", "name", "change", "model", "tier", "window", "total", "parts", "kept", "at")
SPOTTER = "import:spotter"  # a Spotter record's look: its sessions are its ``sdk_sessions``
_cache: dict[str, Any] = {"stamp": None, "lines": []}
_lock = threading.Lock()


def lines() -> list[dict[str, Any]]:
    """Every ``context`` line the ledger holds, read again only when a line was added."""
    stamp = spend_ledger.stamp()
    with _lock:
        if _cache["stamp"] != stamp:
            _cache["lines"] = [x for x in spend_ledger.lines() if x.get("type") == spend_shares.CONTEXT]
            _cache["stamp"] = stamp
        return _cache["lines"]


def query(  # noqa: PLR0913 - one value per filter the page offers
    found: list[dict[str, Any]], measures: list[dict[str, Any]], *, tz: ZoneInfo, start: date | None = None,
    end: date | None = None, project: str = "", agent: str = "", model: str = "", change: str = "",
    stopped: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """Per role: its latest measured session in the filters, its sessions without a measurement and their errors.

    *found* are the ledger's runs (``spend_shares.runs``), *measures* its ``context`` lines.
    """
    kept = tool_metrics.keeps(tz=tz, start=start, end=end, project=project, agent=agent, model=model, change=change,
                              stopped=stopped)  # fmt: skip
    by_run = {str(r["run"]): r for r in found if not r.get("continued")}
    sessions: dict[str, str] = {}  # each session in the filters to its role
    looks = {str(r["look"]) for r in by_run.values() if r.get("look") and r.get("source") != SPOTTER}
    for r in by_run.values():
        if kept(r):
            for sid in _sessions(r, looks):
                sessions.setdefault(sid, tool_metrics.key(r, "agent"))
    best, errors = _read(measures, by_run, sessions)
    roles: dict[str, dict[str, Any]] = {}
    for sid, role in sessions.items():
        row = roles.setdefault(role, {"role": role, "latest": None, "unmeasured": 0, "errors": []})
        if (m := best.get(sid)) is None:
            row["unmeasured"] += 1
            row["errors"] += errors.get(sid, [])
        elif row["latest"] is None or str(m.get("at") or "") > row["latest"]["at"]:
            row["latest"] = {k: m.get(k) for k in LATEST} | {"at": str(m.get("at") or "")}
    for row in roles.values():
        row["errors"].sort(key=lambda e: str(e["at"] or ""), reverse=True)
    rows = sorted(roles.values(), key=lambda x: x["role"])
    return {"roles": rows, "measured": sum(r["latest"] is not None for r in rows),
            "unmeasured": sum(r["unmeasured"] for r in rows)}  # fmt: skip


def _read(
    measures: list[dict[str, Any]], by_run: dict[str, dict[str, Any]], sessions: dict[str, str]
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Each session's latest measurement, joined to its run, and each of its failed reads' errors."""
    best: dict[str, dict[str, Any]] = {}
    errors: dict[str, list[dict[str, Any]]] = {}
    for line in measures:
        run = by_run.get(str(line.get("run") or ""), {})
        sid = str(run.get("session") or line.get("session") or "")
        if sid not in sessions:
            continue
        if line.get("measured"):
            if str(line.get("at") or "") >= str(best.get(sid, {}).get("at") or ""):
                best[sid] = run | line
        else:
            errors.setdefault(sid, []).append({"session": sid, "at": line.get("at"), "error": line.get("error") or ""})
    return best, errors


def _sessions(run: dict[str, Any], looks: set[str]) -> list[str]:
    """The SDK sessions *run* stands for; none for a residual or a look whose own lines are counted."""
    if run.get("line") == "residual":
        return []
    if run.get("source") == SPOTTER:
        named = [str(x) for x in run.get("sdk_sessions") or () if x]
        return named or ([] if str(run.get("look") or "") in looks else [str(run.get("session") or "")])
    return [sid] if (sid := str(run.get("session") or "")) else []
