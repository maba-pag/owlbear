"""The owner's brief actions on the Changes page: one more challenge of a revision no challenger read (#966).

Like the shaping chat's request, it is checked and recorded under the Change's lock, and its round runs even while
Delivery is paused (TD-287); what follows the verdict waits for Resume as usual.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_flow import brief_rounds, picks
from owlbear_delivery_next.state_store.store import LockHeldError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store


class AgainBody(BaseModel):
    """The unreviewed brief version the owner wants challenged once more."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)


def router(store: Store, read: Callable[[str], Change], wake: Callable[[], None]) -> APIRouter:
    """POST /changes/{slug}/challenge-brief reopens the brief's ended loop for one more round on that version."""
    routes = APIRouter()

    @routes.post("/changes/{slug}/challenge-brief")
    def challenge(slug: str, body: AgainBody) -> dict[str, str]:
        read(slug)
        try:
            with store.lock(slug) as lock:
                c = store.read(slug)
                if why := brief_rounds.again(c, body.version):
                    raise HTTPException(409, why)
                if store.shared is not None:  # as a request's, the challenge owes a version without a pick its pick
                    picks.owe(c)
                store.write(lock, c)
        except (LockHeldError, StoreError) as exc:
            raise HTTPException(409, f"change: {exc}; try again") from exc
        wake()
        return {"accepted": "brief-challenge"}

    return routes
