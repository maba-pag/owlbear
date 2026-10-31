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

from owlbear_delivery_next.project_host.config_routes import resolved
from owlbear_delivery_next.runtimes import compaction_report, spend_reconcile
from owlbear_delivery_next.settings.config import ROLES, GlobalLayer, Layer, MachineLayer
from owlbear_delivery_next.state_store import spend_metrics, tool_metrics
from owlbear_delivery_next.state_store.layers import read_layer
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Store

type Projects = Callable[[], list[tuple[Store, Path | None]]]
type Served = Callable[[], list[tuple[str, Store]]]  # each loaded project's id on this machine and its store
type Read = tuple[Settings, Settings] | None  # a store's settings with its project layer and without; None unreadable
LAYERS = frozenset({"project", "machine", "global"})

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


def _read(pid: str, store: Store, errors: list[dict[str, str]]) -> Read:
    layers: list[Layer | None] = []
    for path, model in (
        (store.global_path, GlobalLayer),
        (store.machine_path, MachineLayer),
        (store.config_path, Layer),
    ):
        try:
            layers.append(read_layer(path, model) if path else None)
        except StoreError as exc:
            _log.exception("settings of %s unreadable", store.name or pid)
            cause = f": {type(exc.__cause__).__name__}: {exc.__cause__}" if exc.__cause__ else ""
            errors.append({"project": store.name or pid, "file": str(path), "error": f"{exc}{cause}"})
            return None
    glob, machine, project = layers
    return resolved(glob, project or Layer(), machine, []), resolved(glob, Layer(), machine, [])


def _entry(role: str, row: dict[str, Any], served: list[tuple[str, Store]], read: dict[str, Read]) -> dict[str, Any]:
    """Where the role's context setting that applies to the row is set: its project's page and layer, or why not."""
    wide = row["project"] == ""
    said = {"project": row["project"], "name": row["name"] or ("This machine" if wide else row["project"])}
    if role not in ROLES:
        return said | {"why": "no context setting"}
    found = served[:1] if wide else [
        (pid, s) for pid, s in served if s.root.name == row["clone"] or (s.name or s.root.name) == row["project"]
    ]  # fmt: skip
    if not found:
        return said | {"why": "no project served" if wide else "not served"}
    pid, store = found[0]
    if (settings := read[pid]) is None:
        return said | {"why": "settings unreadable"}
    source = settings[1 if wide else 0].sources.get(f"agents.{role}.context")
    if source in LAYERS:
        return said | {"clone": pid, "layer": source}
    return said | {"clone": pid, "layer": "global" if store.global_path else "machine", "unset": True}


def _attach(answer: dict[str, Any], served: list[tuple[str, Store]]) -> None:
    """Each row's links to its role's context setting (D-01M69C82SQMBHZ8FBKJBX42H3Y); a subagent's has none."""
    errors: list[dict[str, str]] = []
    read = {pid: _read(pid, store, errors) for pid, store in served}
    for row in answer["rows"]:
        row["settings"] = [] if row["subagent"] or row["project"] is None else [_entry(row["agent"], row, served, read)]
    for row in answer["rows"]:
        if row["project"] is None and not row["subagent"]:
            row["settings"] = [e for r in answer["rows"] if r["agent"] == row["agent"] and not r["subagent"]
                               for e in r["settings"]]  # fmt: skip
    answer["settings_errors"] = errors


def router(projects: Projects, served: Served = list) -> APIRouter:
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
            _attach(found["compaction"], served())
        except Exception as exc:
            _log.exception("compaction report failed")
            raise HTTPException(500, f"compaction report: {type(exc).__name__}: {exc}") from exc
        return found

    return routes
