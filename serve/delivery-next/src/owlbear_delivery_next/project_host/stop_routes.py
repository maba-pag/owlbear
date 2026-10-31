"""The owner clears a stop he resolved, and Delivery reruns its step (#754); a chat can't.

The page sends the action the stop asked for; the host queues the matching recovery, which the fold applies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request

from owlbear_delivery_next.change_contracts.inbox import Recovery
from owlbear_delivery_next.change_contracts.models import Exit, Record
from owlbear_delivery_next.change_flow import delivery_target
from owlbear_delivery_next.project_host import runner_end

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.inbox import InboxItem
    from owlbear_delivery_next.change_contracts.models import Change

CHAT_REFUSED = "Only the owner clears a stop, on the Changes page"
STALE = "The stop changed since the page showed it; reload"


class RecoveryBody(Record):
    """The action of the stop the page showed."""

    action: str


def clearable(c: Change) -> str | None:
    """Why the owner can't clear *c*'s stop, or None when he can."""
    if c.finished_at:
        return "This Change has finished"
    if not (c.stop and c.outcome and c.outcome.exit == Exit.STOP):
        return "This Change is not stopped"
    if delivery_target.held(c):  # never on a real path today: a wrong merge is asked, and clearing it would deliver
        return "This stop ends only when you abandon or pause the Change; answer its question"
    if runner_end.unverified(c):
        return "This stop clears itself once the host sees none of the step's processes"
    return None


def _owner(request: Request) -> None:
    if request.headers.get("x-owlbear-use", "").lower() == "chat":
        raise HTTPException(403, CHAT_REFUSED)


def router(read: Callable[[str], Change], put: Callable[[str, InboxItem], dict[str, str]]) -> APIRouter:
    """The recovery route; *read* and *put* are the API's own Change reader and inbox writer."""
    routes = APIRouter()

    @routes.post("/changes/{slug}/recovery", dependencies=[Depends(_owner)])
    def recovery(slug: str, body: RecoveryBody) -> dict[str, str]:
        c = read(slug)
        if why := clearable(c):
            raise HTTPException(409, why)
        if c.stop.action != body.action:
            raise HTTPException(409, STALE)
        return put(slug, Recovery(at=datetime.now(UTC), action=c.stop.action))

    return routes
