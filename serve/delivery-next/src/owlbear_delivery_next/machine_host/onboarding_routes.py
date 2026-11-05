"""Add project's routes (item 15): probe, preflight, the run, its answers and Resume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from owlbear_delivery_next.machine_host.onboarding import OnboardingError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.machine_host.machine import Machine


class Answer(BaseModel):
    """The owner's answer to what a run waits for: a shared folder name, or the profile's values."""

    kind: str
    value: Any = None


def router(machine: Machine) -> APIRouter:
    """The machine's Add project routes."""
    routes = APIRouter(prefix="/onboarding")
    jobs = machine.onboarding

    def answer(work: Callable[[], Any]) -> Any:  # noqa: ANN401 - each route's own answer
        try:
            return work()
        except OnboardingError as exc:
            raise HTTPException(exc.status, exc.text) from exc

    @routes.post("/probe")
    def probe(body: dict[str, Any]) -> dict[str, Any]:
        """What exists for the dialog's Start, the stages left, or the refusal."""
        return answer(lambda: jobs.probe(body))

    @routes.post("/preflight")
    def preflight(body: dict[str, Any]) -> dict[str, Any]:
        """What must hold before anything is created, for the chosen name and route."""
        return {"problems": jobs.preflight(body)}

    @routes.post("/jobs")
    def start(body: dict[str, Any]) -> dict[str, Any]:
        """Run the confirmed plan."""
        return answer(lambda: jobs.start(body))

    @routes.get("/jobs")
    def listed() -> dict[str, Any]:
        """Unfinished runs with Resume, and local-only ones with Publish."""
        return {"jobs": jobs.listed()}

    @routes.get("/jobs/{ident}")
    def read(ident: str) -> dict[str, Any]:
        """One run's stages, what it waits for and its ending."""
        return answer(lambda: jobs.get(ident).info())

    @routes.post("/jobs/{ident}/answer")
    def answered(ident: str, body: Answer) -> dict[str, Any]:
        """The owner's answer to what the run waits for."""
        return answer(lambda: jobs.answer(ident, body.kind, body.value))

    @routes.post("/jobs/{ident}/resume")
    def resume(ident: str) -> dict[str, Any]:
        """Resume or Retry."""
        return answer(lambda: jobs.resume(ident))

    return routes
