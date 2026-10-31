"""What the Metrics page shows: the ledger's pieces of spend summed, split and filtered (D-01M5XCDF6G60VG5GHTWF5QSSDE).

Pieces come from ``spend_shares``, derived over every line before anything here filters them. A time range is
half-open, ``[from, to)`` in the page's time zone; a piece counts in it only when its window lies wholly inside, and
one whose window is unknown or crosses the range's edge is said apart (``undated``), never put on a made-up day.
Credits never read count as unknown runs, never as zero; credits whose time or agent is uncertain are said apart.
"""

from __future__ import annotations

import threading
from datetime import UTC, date, datetime, time
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.state_store import spend_ledger, spend_shares

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

SPLITS = ("project", "agent", "model", "day", "change", "step")
PAGE = 50
UNKNOWN = "?"  # the key of an unknown agent, model, project or day in a split or filter
_cache: dict[str, Any] = {"stamp": None, "pieces": []}
_lock = threading.Lock()


def pieces() -> list[dict[str, Any]]:
    """Every piece the ledger holds, derived again only when a line was added."""
    stamp = spend_ledger.stamp()
    with _lock:
        if _cache["stamp"] != stamp:
            _cache["pieces"], _cache["stamp"] = spend_shares.derive(spend_ledger.lines()), stamp
        return _cache["pieces"]


def bounds(start: date | None, end: date | None, tz: ZoneInfo) -> tuple[datetime | None, datetime | None]:
    """The UTC instants of local midnight at *start* and at *end*: the range ``[start, end)``."""

    def midnight(d: date | None) -> datetime | None:
        return None if d is None else datetime.combine(d, time(0), tzinfo=tz).astimezone(UTC)

    return midnight(start), midnight(end)


def _when(text: str | None) -> datetime | None:
    if not text:
        return None
    t = datetime.fromisoformat(text)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _day(p: dict[str, Any], tz: ZoneInfo) -> str:
    lo, hi = _when(p["lo"]), _when(p["hi"])
    if lo is None or hi is None or (d := lo.astimezone(tz).date()) != hi.astimezone(tz).date():
        return UNKNOWN
    return d.isoformat()


def _key(p: dict[str, Any], by: str, tz: ZoneInfo) -> str:
    if by == "day":
        return _day(p, tz)
    if by == "change":
        return f"{p['project']}/{p['change']}" if p["change"] else ""
    if by == "agent":
        return p["agent"] or UNKNOWN
    if by == "model":
        return p["model"] or UNKNOWN
    return p[by] or ""


def _label(p: dict[str, Any], by: str, key: str, names: dict[str, str]) -> str:
    if by == "project":
        return names.get(key) or key or "No project (this machine)"
    if by == "agent":
        return "Agent unknown" if key == UNKNOWN else f"{key} (subagent)" if p["under"] else key
    if by == "change":
        return f"{names.get(p['project']) or p['project']}: {p['change']}" if key else "Outside a Change"
    if by == "step":
        return key or "No step"
    return "Time unknown" if key == UNKNOWN and by == "day" else "Model unknown" if key == UNKNOWN else key


def reached(p: dict[str, Any]) -> bool:
    """Whether the run surely stopped at its credit limit: ``unknown`` is not, nor any other word."""
    return p["stopped"] in {
        "reached",
        "credit-limit",
    }  # the second: this ledger's first lines, before the meter's names


def keeps(  # noqa: PLR0913 - one value per filter the page offers
    p: dict[str, Any], *, project: str, agent: str, model: str, change: str, stopped: bool
) -> bool:
    """Whether the piece passes the page's filters other than its time range."""
    return (
        (not project or (p["project"] or UNKNOWN) == project)
        and (not agent or (p["agent"] or UNKNOWN) == agent)
        and (not model or (p["model"] or UNKNOWN) == model)
        and (not change or f"{p['project']}/{p['change']}" == change)
        and (not stopped or reached(p))
    )


def within(p: dict[str, Any], since: datetime | None, until: datetime | None) -> bool | None:
    """Whether the piece lies in the range: None when that is unknown (its window is open or crosses an edge)."""
    if since is None and until is None:
        return True
    lo, hi = _when(p["lo"]), _when(p["hi"])
    after = until is not None and lo is not None and lo >= until
    if after or (since is not None and hi is not None and hi < since):
        return False
    if lo is None or hi is None:
        return None
    return ((since is None or lo >= since) and (until is None or hi < until)) or None


def _sum(group: list[dict[str, Any]]) -> dict[str, Any]:
    runs = {p["run"] for p in group}
    unknown = {p["run"] for p in group if p["credits"] is None}
    known = [p for p in group if p["credits"] is not None]
    return {
        "credits": round(sum(p["credits"] for p in known), 4),
        "runs": len(runs),
        "unknown": len(unknown),
        "open": len({p["run"] for p in group if p["kind"] == "open"}),
        "incomplete": len({p["run"] for p in group if p["incomplete"]}),  # a lower bound: read short or failed
        "failed": len({p["run"] for p in group if p["failed"]}),
        "stopped": len({p["run"] for p in group if reached(p)}),
        "stopped_unknown": len({p["run"] for p in group if p["stopped"] == "unknown"}),
        "tokens": int(sum(p["input"] + p["output"] for p in group)),
        "cache": int(sum(p["cache_read"] + p["cache_write"] for p in group)),
        "uncertain_time": round(sum(p["credits"] for p in known if "at" in p["uncertain"]), 4),
        "uncertain_agent": round(sum(p["credits"] for p in known if "agent" in p["uncertain"]), 4),
    }


def query(  # noqa: PLR0913 - one value per filter the page offers
    found: list[dict[str, Any]], *, tz: ZoneInfo, start: date | None = None, end: date | None = None, project: str = "",
    agent: str = "", model: str = "", change: str = "", stopped: bool = False, by: str = "agent", cursor: int = 0,
) -> dict[str, Any]:  # fmt: skip
    """Totals, one row per value of *by*, the runs page from *cursor*, the filters' choices and the coverage."""
    since, until = bounds(start, end, tz)
    names: dict[str, str] = {}
    for p in found:
        if p["name"]:
            names[p["project"]] = p["name"]

    chosen = [p for p in found if keeps(p, project=project, agent=agent, model=model, change=change, stopped=stopped)]
    inside = [p for p in chosen if within(p, since, until) is True]
    undated = [p for p in chosen if within(p, since, until) is None]
    rows: dict[str, dict[str, Any]] = {}
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in inside:
        key = _key(p, by, tz)
        groups.setdefault(key, []).append(p)
        rows.setdefault(key, {"key": key or UNKNOWN, "label": _label(p, by, key, names)})
    listed = [rows[k] | _sum(g) for k, g in groups.items()]
    listed.sort(key=(lambda r: r["key"]) if by == "day" else (lambda r: (-r["credits"], r["label"])))
    return {
        "totals": _sum(inside),
        "undated": _sum(undated) if undated else None,
        "rows": listed,
        "runs": _runs(inside, names, cursor),
        "choices": _choices(found, names, project),
        "coverage": _coverage(found),
    }


def _runs(inside: list[dict[str, Any]], names: dict[str, str], cursor: int) -> dict[str, Any]:
    by: dict[str, list[dict[str, Any]]] = {}
    for p in inside:
        by.setdefault(p["run"], []).append(p)
    items = []
    for rid, group in by.items():
        first, s = group[0], _sum(group)
        items.append({
            "run": rid, "at": max((p["hi"] or p["lo"] or "") for p in group), "project": first["project"],
            "name": names.get(first["project"]) or first["project"], "change": first["change"], "step": first["step"],
            "agent": first["role"], "job": first["job"], "models": sorted({p["model"] for p in group if p["model"]}),
            "subagents": sorted({p["agent"] for p in group if p["under"] and p["agent"]}), "credits": s["credits"],
            "unknown": bool(s["unknown"]), "open": bool(s["open"]), "incomplete": bool(s["incomplete"]),
            "ending": first["ending"],
            "stopped": "reached" if reached(first) else first["stopped"], "stopped_by": first["stopped_by"],
            "limit": first["limit"], "source": first["source"],
            "uncertain": sorted({u for p in group for u in p["uncertain"]}),
        })  # fmt: skip
    items.sort(key=lambda r: r["at"], reverse=True)
    page = items[cursor : cursor + PAGE]
    after = cursor + len(page)
    return {"items": page, "total": len(items), "next": after if after < len(items) else None}


def _choices(found: list[dict[str, Any]], names: dict[str, str], project: str) -> dict[str, Any]:
    keys = {p["project"] or UNKNOWN for p in found}
    projects = [[k, names.get(k) or ("No project (this machine)" if k == UNKNOWN else k)] for k in keys]
    return {
        "projects": sorted(projects, key=lambda kv: kv[1].lower()),
        "agents": sorted({p["agent"] or UNKNOWN for p in found}),
        "models": sorted({p["model"] or UNKNOWN for p in found}),
        "changes": sorted(
            {f"{p['project']}/{p['change']}" for p in found if p["change"] and (not project or p["project"] == project)}
        ),
        "clones": {p["clone"]: p["project"] for p in found if p["clone"]},
    }


def _coverage(found: list[dict[str, Any]]) -> dict[str, Any]:
    recorded = [p["lo"] or p["hi"] for p in found if p["source"] == "recorded" and (p["lo"] or p["hi"])]
    sources: dict[str, float] = {}
    for p in found:
        sources[p["source"]] = round(sources.get(p["source"], 0.0) + (p["credits"] or 0.0), 4)
    return {
        "recorded_since": min(recorded) if recorded else None,
        "sources": sources,
        "open": len({p["run"] for p in found if p["kind"] == "open"}),
        "unknown": len({p["run"] for p in found if p["credits"] is None}),
    }
