"""The PDS routes (#777): the hand audit of the installed pages, started and read from the Updates page."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException

from owlbear_delivery_next.pds_runs import hand_audit

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager


def router(
    hand: hand_audit.Hand, admitted: Callable[[], AbstractContextManager[None]] = contextlib.nullcontext
) -> APIRouter:
    """The hand audit's routes; *admitted* refuses a start once OwlBear stops, and the caller adds the token check."""
    routes = APIRouter()

    @routes.get("/pds/audit")
    def audit_state() -> dict[str, Any]:
        return hand.read()

    @routes.post("/pds/audit")
    def audit() -> dict[str, Any]:
        try:
            with admitted():
                return hand.start()
        except hand_audit.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    return routes
