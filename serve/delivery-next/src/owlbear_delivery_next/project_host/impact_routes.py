"""A change of mind's impact on the Decisions page (TD-428, slice 5b part 2): the report, fixes and kept code.

``GET /decisions/{id}/impact`` reports each project the replaced (or withdrawn) rule reached; the owner schedules
fixes as backlog entries and keeps a project's existing code, each a separate click from activating the new rule.
A project host sees its own project; the machine host mounts the same routes over every project it serves, as it
lists the pinning Changes of every loaded project. A chat's call to the owner's actions is refused.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, StringConstraints

from owlbear_decisions.models import FOLDER_PATTERN
from owlbear_delivery_next.state_store import decision_fixes, decision_impact, decision_store
from owlbear_delivery_next.state_store.backlog import BacklogError
from owlbear_delivery_next.state_store.decision_actions import Refused

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.decision_impact import Place, Report

NO_SHARED = "No shared repository is set up, so there are no decisions; set one with `owlbear-next data PATH`"
Revision = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Folder = Annotated[str, Query(pattern=FOLDER_PATTERN)]  # the data folder whose view holds the decision


class ScheduleBody(BaseModel):
    """The revision of the new rule the page showed."""

    model_config = ConfigDict(extra="forbid")

    revision: Revision


class AcceptBody(ScheduleBody):
    """The project whose existing code stays as it is, and why."""

    project: Annotated[str, StringConstraints(pattern=FOLDER_PATTERN)]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""


def _answer[T](work: Callable[[], T]) -> T:
    try:
        return work()
    except Refused as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    except decision_store.DecisionsUnavailable as exc:
        raise HTTPException(409, f"{exc} ({exc.action})") from exc
    except BacklogError as exc:
        raise HTTPException(exc.status, exc.text) from exc


def router(shared: Callable[[], DataRepo | None], places: Callable[[], Sequence[Place]], mine: list[Any]) -> APIRouter:
    """The impact routes over *places*; *mine* refuses a chat's call to the owner's actions."""
    routes = APIRouter()

    def read(folder: str, decision_id: str) -> tuple[DataRepo, Report]:
        if (repo := shared()) is None:
            raise Refused(NO_SHARED)
        return repo, decision_impact.report(repo, folder, decision_id, places())

    @routes.get("/decisions/{decision_id}/impact")
    def impact(decision_id: str, folder: Folder) -> dict[str, Any]:
        return _answer(lambda: decision_impact.shown(read(folder, decision_id)[1]))

    @routes.post("/decisions/{decision_id}/schedule-fixes", dependencies=mine)
    def schedule(decision_id: str, body: ScheduleBody, folder: Folder) -> dict[str, Any]:
        def work() -> dict[str, Any]:
            repo, found = read(folder, decision_id)
            return {"entries": decision_fixes.schedule(repo, found, body.revision)}

        return _answer(work)

    @routes.post("/decisions/{decision_id}/accept-existing", dependencies=mine)
    def accept_existing(decision_id: str, body: AcceptBody, folder: Folder) -> dict[str, Any]:
        def work() -> dict[str, Any]:
            repo, found = read(folder, decision_id)
            done = decision_fixes.accept(repo, found, body.project, body.revision, body.reason)
            return {"receipts": [asdict(done)], "saved": done.saved}

        return _answer(work)

    return routes
