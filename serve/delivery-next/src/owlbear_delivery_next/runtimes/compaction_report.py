"""Metrics' compaction report: per role, how often its sessions compacted their context and how early.

A session belongs to the report when one of its pieces of spend passes the page's filters and lies in its time range,
as the spend split counts it (``spend_metrics``); its whole log counts then, once. A role's row counts its sessions:
those with a readable log, without one and with one unreadable, how many compacted and how often, and how early, as
the share of the main agent's model calls made before its first applied compaction, its median over the compacted
sessions and the earliest (D-01M69C82SQMBHZ8FBKJBX42H3Y). Each subagent invocation in those logs counts under its
role and name the same way. Data only: no advice (D-01M61V5F0J7SDJ6Q3TYFBKGYFZ).
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.runtimes import compaction_logs
from owlbear_delivery_next.state_store import spend_metrics

if TYPE_CHECKING:
    from datetime import date
    from zoneinfo import ZoneInfo

    from owlbear_delivery_next.runtimes.compaction_logs import Actor

type Key = tuple[str, str, str | None]  # role, subagent name ("" for the role itself), project (None: every project)


def report(  # noqa: PLR0913 - one value per filter the page offers
    found: list[dict[str, Any]], *, tz: ZoneInfo, start: date | None = None, end: date | None = None, project: str = "",
    agent: str = "", model: str = "", change: str = "", stopped: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """``{"rows": [...], "errors": [...]}`` for the sessions the filters and the range select."""
    since, until = spend_metrics.bounds(start, end, tz)
    sessions: dict[str, dict[str, Any]] = {}
    for p in found:
        chosen = spend_metrics.keeps(p, project=project, agent=agent, model=model, change=change, stopped=stopped)
        if p["session"] and chosen and spend_metrics.within(p, since, until) is True:
            sessions.setdefault(p["session"], p)
    rows: dict[Key, dict[str, Any]] = {}
    shares: dict[Key, list[float]] = {}
    errors = []
    for session, p in sessions.items():
        role, where = p["role"], p["project"]
        row = _row(rows, (role, "", where), p)
        row["sessions"] += 1
        log = compaction_logs.read(session)
        if log.state == "missing":
            row["missing"] += 1
            continue
        if log.state == "error":
            row["unreadable"] += 1
            errors.append({"session": session, "project": where, "role": role, "error": log.error})
            continue
        _count(row, shares.setdefault((role, "", where), []), log.main)
        for name, actor in log.subagents:
            sub = _row(rows, (role, name, where), p)
            sub["sessions"] += 1
            _count(sub, shares.setdefault((role, name, where), []), actor)
    if not project:
        _aggregate(rows, shares)
    for key, row in rows.items():
        got = shares.get(key) or []
        row["median"] = round(statistics.median(got), 4) if got else None
        row["earliest"] = round(min(got), 4) if got else None
    keep = [r for r in rows.values() if not agent or (r["subagent"] or r["agent"]) == agent]
    keep.sort(key=lambda r: (r["agent"], r["subagent"], r["project"] is not None, r["name"] or r["project"] or ""))
    return {"rows": keep, "errors": errors}


def _row(rows: dict[Key, dict[str, Any]], key: Key, p: dict[str, Any]) -> dict[str, Any]:
    return rows.setdefault(key, {
        "agent": key[0], "subagent": key[1], "project": key[2], "name": p["name"] if key[2] is not None else "",
        "clone": p["clone"] if key[2] is not None else "", "sessions": 0, "logs": 0, "missing": 0, "unreadable": 0,
        "compacted": 0, "compactions": 0,
    })  # fmt: skip


def _count(row: dict[str, Any], shares: list[float], actor: Actor) -> None:
    row["logs"] += 1
    row["compactions"] += actor.compactions
    if actor.compactions:
        row["compacted"] += 1
        if actor.calls and actor.before is not None:
            shares.append(actor.before / actor.calls)


def _aggregate(rows: dict[Key, dict[str, Any]], shares: dict[Key, list[float]]) -> None:
    """One row over every project for each role or subagent that ran in two or more projects."""
    spans: dict[tuple[str, str], list[Key]] = {}
    for key in rows:
        spans.setdefault(key[:2], []).append(key)
    for (role, name), keys in spans.items():
        if len(keys) < 2:  # noqa: PLR2004 - "two or more projects"
            continue
        total = {k: sum(rows[key][k] for key in keys) for k in ("sessions", "logs", "missing", "unreadable",
                                                                 "compacted", "compactions")}  # fmt: skip
        rows[role, name, None] = {"agent": role, "subagent": name, "project": None, "name": "", "clone": ""} | total
        shares[role, name, None] = [s for key in keys for s in shares.get(key, [])]
