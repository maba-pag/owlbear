"""Tool use across Changes (C-28): each run's Delivery tool tallies and wrong tool choices, from the spend ledger.

A run is measured when its end line carries both ``tools`` and ``wrong``: SDK runs from this release on. Runs known
only from the runtime's logs or imported records carry none, nor do runs before it, so only measured runs are counted
and the answer says since when. Tool use belongs to the run's main agent (its role at the start), never to a subagent.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.tool_use import WRONG
from owlbear_delivery_next.state_store import spend_ledger, spend_metrics, spend_shares

if TYPE_CHECKING:
    from datetime import date
    from zoneinfo import ZoneInfo

FIELDS = ("calls", "accepted", "invalid", "checks", "order", "unsplit", "lint", "late", "retries")
_cache: dict[str, Any] = {"stamp": None, "runs": []}
_lock = threading.Lock()


def runs() -> list[dict[str, Any]]:
    """Every run the ledger holds, derived again only when a line was added."""
    stamp = spend_ledger.stamp()
    with _lock:
        if _cache["stamp"] != stamp:
            _cache["runs"], _cache["stamp"] = spend_shares.runs(spend_ledger.lines()), stamp
        return _cache["runs"]


def _time(run: dict[str, Any]) -> datetime | None:
    text = run.get("at") or run.get("started")
    if not text:
        return None
    t = datetime.fromisoformat(str(text))
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _row(tally: dict[str, int]) -> dict[str, Any]:
    """One tool's counts: accepted is what was neither refused, lint-held nor late; unsplit, refusals kept unsplit."""
    n = {k: int(tally.get(k) or 0) for k in ("calls", "rejected", "invalid", "checks", "order", "lint", "late")}
    accepted = max(n["calls"] - n["rejected"] - n["lint"] - n["late"], 0)
    unsplit = max(n["rejected"] - n["invalid"] - n["checks"] - n["order"], 0)
    return {k: n[k] for k in ("calls", "invalid", "checks", "order", "lint", "late")} | {
        "accepted": accepted, "unsplit": unsplit, "retries": int(tally.get("retries") or 0),
    }  # fmt: skip


def _rate(row: dict[str, Any]) -> dict[str, Any]:
    return row | {"success": round(100 * row["accepted"] / row["calls"]) if row["calls"] else None}


def query(  # noqa: PLR0913 - one value per filter the page offers
    found: list[dict[str, Any]], *, tz: ZoneInfo, start: date | None = None, end: date | None = None, project: str = "",
    agent: str = "", model: str = "", change: str = "", stopped: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """The measured runs' tool use for the filters: one row per tool, the totals and the wrong tool choices.

    Success is weighted: all accepted calls over all calls, so a tool called often counts as often as it was called.
    """
    since, until = spend_metrics.bounds(start, end, tz)
    measured = [r for r in found if not r.get("continued") and "tools" in r and "wrong" in r]

    def key(r: dict[str, Any], field: str) -> str:
        return str(r.get(field) or "") or spend_metrics.UNKNOWN

    def kept(r: dict[str, Any]) -> bool:
        t = _time(r)
        return (
            (not project or key(r, "project") == project)
            and (not agent or key(r, "agent") == agent)
            and (not model or key(r, "model") == model)
            and (not change or f"{r.get('project') or ''}/{r.get('change') or ''}" == change)
            and (not stopped or r.get("stopped") in {"reached", "credit-limit"})
            and (since is None or (t is not None and t >= since))
            and (until is None or (t is not None and t < until))
        )

    chosen = [r for r in measured if kept(r)]
    rows: dict[str, dict[str, Any]] = {}
    wrong = dict.fromkeys(WRONG, 0)
    for r in chosen:
        for tool, tally in (r.get("tools") or {}).items():
            row = _row(tally)
            rows[tool] = {k: rows.get(tool, {}).get(k, 0) + row[k] for k in FIELDS}
        for k, n in (r.get("wrong") or {}).items():
            wrong[k] = wrong.get(k, 0) + int(n or 0)
    totals = {k: sum(row[k] for row in rows.values()) for k in FIELDS}
    times = [t for r in measured if (t := _time(r)) is not None]
    choices = {f"{k}s": sorted({key(r, k) for r in measured}) for k in ("agent", "model")}
    return {
        "since": min(times).isoformat() if times else None,
        "runs": len(chosen),
        "choices": choices,
        "tools": sorted(({"tool": t} | _rate(row) for t, row in rows.items()), key=lambda x: (-x["calls"], x["tool"])),
        "totals": _rate(totals),
        "wrong": {"order": totals["order"]} | wrong,
    }
