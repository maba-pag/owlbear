"""The Improvement page's machine routes (#716, design §6): read the Spotter, Retro, cases and proposals; act on them.

Every write is the owner's (``proposal_apply.BY``); nothing is written while OwlBear stops or updates. Errors carry
their full text: what was refused, where and why.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from owlbear_memory.engine import MemoryEngine
from pydantic import Field

from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.improvement import case_edits, cases, followups, improvement_view, proposal_apply
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.cases import CaseError, Stale
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store import machine_settings, registry
from owlbear_delivery_next.state_store.backlog import BacklogError
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.machine_host.machine import Machine

BY = proposal_apply.BY
ID = 200  # characters of an id or a Change name in a request
UNREACHABLE = (BacklogError, ProviderError, OSError)


class RetroBody(api.Body):
    """The finished Change to run Retro on, ``project:slug``."""

    change: str = Field(min_length=3, max_length=ID)


class DecideBody(api.Body):
    """The owner's decision on a proposal, the token of what he saw, and a redirect's direction."""

    state: str = Field(min_length=1, max_length=20)
    token: str = Field(min_length=1, max_length=64)
    direction: str = Field(default="", max_length=proposal_apply.DIRECTION * 2)


class FollowupBody(api.Body):
    """The Retro finding or Spotter record to follow up."""

    finding: str = Field(min_length=1, max_length=ID)


class MoveBody(api.Body):
    """A case's new stage, the version the owner saw and, into the examples, the example text."""

    stage: str = Field(min_length=1, max_length=20)
    parent: int = Field(ge=0)
    example: str = Field(default="", max_length=cases.EXAMPLE * 2)


def seams() -> proposal_apply.Seams:
    """Where an accepted proposal's artefacts are made on this machine."""
    return proposal_apply.Seams(
        backlog=followups.backlog,
        memory=MemoryEngine,
        issues=lambda: OwlbearIssues(targets.REPOSITORY, local_home.root()),
        case=proposal_apply.intake,
        check=lambda cid: case_edits.check_request([cid], proposal_apply.BY),
    )


def _redraft(pid: str) -> str:
    """Queue redirected proposal *pid*'s redraft, unless one is queued; the request's id."""
    snap = props.folded().get(pid)
    if snap is None or snap["state"] != "redirected":
        raise HTTPException(409, f"proposal {pid} is {snap['state'] if snap else 'unknown'}, not redirected")
    if snap["redraft"]:
        raise HTTPException(409, f"proposal {pid}'s redraft is filed already: {snap['redraft']}")
    if waiting := next((q["id"] for q in store.queued() if q.get("redraft") == pid), ""):
        return waiting
    return store.request(BY, redraft=pid)


def _switches() -> dict[str, Any]:
    try:
        s = machine_settings.current()
    except registry.RegistryError as exc:
        return {"error": f"the machine's settings cannot be read: {exc}"}
    return {"retro_after_change": s.retro_after_change, "retro_when_idle": s.retro_when_idle}


@dataclass(frozen=True)
class _Machine:
    """What the routes read of the machine: its loaded projects, whether it may be written, the shared repository."""

    machine: Machine
    shared: Callable[[], DataRepo | None]

    def projects(self) -> units.Projects:
        return self.machine.retro.seams.projects()

    def writable(self) -> None:
        if why := self.machine.updating or ("OwlBear is stopping" if self.machine.stopping.is_set() else ""):
            raise HTTPException(503, why)

    def registered(self, pid: str) -> None:
        if pid not in self.machine.projects:
            raise HTTPException(404, f"no registered project has the id {pid!r}")

    def root(self) -> Path | None:
        found = self.shared()
        return found.root if found else None


def router(machine: Machine, shared: Callable[[], DataRepo | None]) -> APIRouter:
    """The Improvement routes under ``/improvement``, reading the projects *machine* has loaded."""
    routes, m = APIRouter(prefix="/improvement"), _Machine(machine, shared)
    _reads(routes, m)
    _retro(routes, m)
    _proposals(routes, m)
    _cases(routes, m)
    return routes


def _reads(routes: APIRouter, m: _Machine) -> None:
    @routes.get("")
    def overview() -> dict[str, Any]:
        """The Spotter, Retro, the Spotter cases and the proposals."""
        loaded = m.projects()
        records, grades = units.records(), store.grades()
        return {
            "spotter": improvement_view.spotter(loaded, records, grades, datetime.now(UTC)),
            "retro": improvement_view.retro(loaded, _switches()),
            "cases": improvement_view.spotter_cases(),
            "proposals": improvement_view.proposals(loaded, m.root()),
        }

    @routes.get("/looks")
    def looks(
        project: Annotated[str, Query(max_length=ID)] = "",
        change: Annotated[str, Query(max_length=ID)] = "",
        limit: Annotated[int, Query(ge=1, le=improvement_view.LOOKS)] = improvement_view.LOOKS,
    ) -> dict[str, Any]:
        """The Spotter's looks and the outside writes, of one project or Change when named."""
        if project:
            m.registered(project)
        return improvement_view.looks(m.projects(), units.records(), store.grades(), project=project, change=change,
                                      limit=limit)  # fmt: skip

    @routes.get("/change")
    def change(
        project: Annotated[str, Query(min_length=1, max_length=ID)],
        slug: Annotated[str, Query(min_length=1, max_length=ID)],
    ) -> dict[str, Any]:
        """One Change's looks and Retro findings, each with its follow-up."""
        m.registered(project)
        loaded = m.projects().get(project)
        if loaded is not None and slug not in loaded[0].slugs():
            raise HTTPException(404, f"project {project} has no Change {slug!r}")
        return improvement_view.change_detail(project, slug, units.records(), store.grades())


def _retro(routes: APIRouter, m: _Machine) -> None:
    @routes.post("/retro")
    def run_retro(body: RetroBody) -> dict[str, Any]:
        """Queue a Retro run of one finished Change."""
        m.writable()
        pid, _, slug = body.change.partition(":")
        loaded = m.projects().get(pid)
        try:
            finished = loaded is not None and slug in loaded[0].slugs() and loaded[0].read(slug).finished_at
        except (StoreError, OSError, ValueError) as exc:
            raise HTTPException(409, f"Change {body.change} cannot be read: {exc}") from exc
        if not finished:
            raise HTTPException(409, f"{body.change} is not a finished Change of a loaded project: Retro runs on one")
        return {"queued": store.request(BY, change=body.change)}

    @routes.post("/followups")
    def followup(body: FollowupBody) -> dict[str, Any]:
        """Follow up a finding or record: its backlog entry, saved or found, or the run queued to write it."""
        m.writable()
        try:
            return followups.request(body.finding, BY, improvement_view.places(m.projects()), followups.backlog)
        except followups.Unknown as exc:
            raise HTTPException(404, str(exc)) from exc
        except store.RetroError as exc:
            raise HTTPException(409, str(exc)) from exc
        except UNREACHABLE as exc:
            raise HTTPException(409, f"the backlog could not be reached: {type(exc).__name__}: {exc}") from exc


def _proposals(routes: APIRouter, m: _Machine) -> None:
    @routes.post("/proposals/{pid}/decide")
    def decide(pid: str, body: DecideBody) -> dict[str, Any]:
        """The owner's decision on a proposal, given what he saw."""
        m.writable()
        if (where := m.root()) is None:
            raise HTTPException(409, "there is no shared repository: a proposal lands in or through it")
        try:
            return proposal_apply.decide(pid, body.state, body.token, BY, places=improvement_view.places(m.projects()),
                                         shared_root=where, direction=body.direction)  # fmt: skip
        except proposal_apply.Refused as exc:
            raise HTTPException(422, str(exc)) from exc
        except store.RetroError as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.post("/proposals/{pid}/apply")
    def apply(pid: str) -> dict[str, Any]:
        """Make an accepted proposal's artefacts, or those still missing after a failure."""
        m.writable()
        try:
            return proposal_apply.apply(pid, seams())
        except store.RetroError as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.post("/proposals/{pid}/redraft")
    def redraft(pid: str) -> dict[str, Any]:
        """Queue a redirected proposal's redraft again, after one that did not file it."""
        m.writable()
        return {"queued": _redraft(pid)}


def _cases(routes: APIRouter, m: _Machine) -> None:
    @routes.post("/cases/{cid}/move")
    def move(cid: str, body: MoveBody) -> dict[str, Any]:
        """Move a case to a stage, made of the version the owner saw; into the examples with its example text."""
        m.writable()
        if body.stage not in {*cases.STAGES, "removed"}:
            raise HTTPException(422, f"{body.stage!r} is not a stage: {', '.join(cases.STAGES)} or removed")
        example = body.example.strip()
        if body.stage == "example" and not 0 < len(example) <= cases.EXAMPLE:
            raise HTTPException(422, f"a case moved into the examples needs its example text, 1 to {cases.EXAMPLE} "
                                     "characters: nothing was written")  # fmt: skip
        fields = {"example": example} if body.stage == "example" else {}
        try:
            return case_edits.move(cid, body.stage, BY, body.parent, **fields)
        except Stale as exc:
            raise HTTPException(409, str(exc)) from exc
        except CaseError as exc:
            raise HTTPException(422, str(exc)) from exc
