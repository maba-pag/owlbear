"""The Metrics page's data (D-01M5XCDF6G60VG5GHTWF5QSSDE): every project's spend and tool use, from the spend ledger.

A read also starts a reconciling pass over OwlBear's other records when one is due; it runs on its own thread, so
the answer never waits for it, and says how far it got: "running" from the moment it is started, so the page reads
again until the pass is done, and the answer after that holds all it imported. Nothing here limits any work.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query

from owlbear_delivery_next.runtimes import compaction_report, spend_reconcile
from owlbear_delivery_next.state_store import spend_metrics, tool_metrics

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Store

type Projects = Callable[[], list[tuple[Store, Path | None]]]

_log = logging.getLogger(__name__)


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(422, f"unknown time zone {name!r}") from exc


def _date(text: str, what: str) -> date | None:
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(422, f"{what} must be a date as YYYY-MM-DD, got {text!r}") from exc


def router(projects: Projects) -> APIRouter:
    """``GET /metrics``: totals, one split, the runs, the coverage, the tool use and compaction for the filters."""
    routes = APIRouter()

    @routes.get("/metrics")
    def metrics(  # noqa: PLR0913, PLR0917 - one query parameter per filter
        start: Annotated[str, Query(alias="from", max_length=10)] = "",
        end: Annotated[str, Query(alias="to", max_length=10)] = "",
        tz: Annotated[str, Query(max_length=64)] = "UTC",
        project: Annotated[str, Query(max_length=200)] = "",
        agent: Annotated[str, Query(max_length=100)] = "",
        model: Annotated[str, Query(max_length=100)] = "",
        change: Annotated[str, Query(max_length=300)] = "",
        stopped: bool = False,  # noqa: FBT001, FBT002 - a query flag
        by: Annotated[str, Query(max_length=10)] = "agent",
        cursor: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        zone, since, until = _zone(tz), _date(start, "from"), _date(end, "to")
        if since and until and until <= since:
            raise HTTPException(422, "to must come after from: the range is [from, to)")
        if by not in spend_metrics.SPLITS:
            raise HTTPException(422, f"by must be one of {', '.join(spend_metrics.SPLITS)}")
        if spend_reconcile.due():
            spend_reconcile.start(projects())
        said = spend_reconcile.status()  # before the read: a pass said done has written all it found
        every = spend_metrics.pieces()
        found = spend_metrics.query(
            every, tz=zone, start=since, end=until, project=project, agent=agent, model=model,
            change=change, stopped=stopped, by=by, cursor=cursor,
        )  # fmt: skip
        found["coverage"]["reconcile"] = {k: said.get(k) for k in ("state", "started", "finished", "sources", "done",
                                                                   "imported", "errors")}  # fmt: skip
        used = tool_metrics.query(
            tool_metrics.runs(), tz=zone, start=since, end=until, project=project, agent=agent, model=model,
            change=change, stopped=stopped,
        )  # fmt: skip
        for k in ("agents", "models"):  # a main agent whose spend shows only as an unsplit subagent's is still chosen
            found["choices"][k] = sorted(set(found["choices"][k]) | set(used["choices"][k]))
        found["tool_use"] = used
        try:
            found["compaction"] = compaction_report.report(
                every, tz=zone, start=since, end=until, project=project, agent=agent, model=model, change=change,
                stopped=stopped,
            )  # fmt: skip
        except Exception as exc:
            _log.exception("compaction report failed")
            raise HTTPException(500, f"compaction report: {type(exc).__name__}: {exc}") from exc
        return found

    return routes
