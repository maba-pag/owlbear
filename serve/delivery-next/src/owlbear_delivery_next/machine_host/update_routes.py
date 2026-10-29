"""The update checks' routes (D-01M63CCVRK8ZKFENY9F4A2K11A): each update's state, and Search for updates by hand."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException

from owlbear_delivery_next.machine_host.update_checks import CHECKS

if TYPE_CHECKING:
    from owlbear_delivery_next.machine_host.machine import Machine


def router(machine: Machine) -> APIRouter:
    """``GET /updates`` and ``POST /updates/{name}/check``."""
    routes = APIRouter()

    @routes.get("/updates")
    def updates() -> dict[str, Any]:
        """OwlBear's, PDS's and Impeccable's state: newer, current, unknown or failed; and how many can be run."""
        return machine.checks.read()

    @routes.post("/updates/{name}/check")
    def check(name: str) -> dict[str, Any]:
        """Search for updates now, also while its interval is unset; it runs in the background, pages read GET."""
        if name not in CHECKS:
            raise HTTPException(404, f"no update named {name}")
        machine.checks.start(name)
        return machine.checks.read()

    return routes
