"""The owner clears a stop he resolved, and Delivery reruns its step (#754); a chat can't."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from owlbear_delivery_next.change_contracts.inbox import Recovery
from owlbear_delivery_next.change_contracts.models import Exit, Record
from owlbear_delivery_next.change_flow import delivery_target
from owlbear_delivery_next.project_host import runner_end
from owlbear_delivery_next.state_store import machine_settings
from owlbear_delivery_next.state_store.registry import RegistryError
from owlbear_delivery_next.state_store.store import LockHeldError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store


class RecoveryBody(Record):
    """The stop the page showed: its action and when it stopped."""

    action: str
    at: datetime


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


def unset(store: Store) -> str | None:
    """Why no work may start for want of settings, this machine's included (D-01M61SBWK4VE4MNTD35TR0VPS8), or None."""
    try:  # until #808, an unset update-check interval stops only its timed check (D-01M63ZYZT2RGZ0AFZW775FV16E)
        machine = [n for n in machine_settings.current().missing if not n.startswith("update_check_hours_")]
        missing = [*store.settings().missing, *machine]
    except (StoreError, RegistryError) as exc:
        return f"The settings can't be read ({exc}); fix them on the Settings page to run the step again"
    if missing:
        more = " and others" if missing[1:] else ""
        return f"Settings unset: {missing[0]}{more}; fill them in on the Settings page to run the step again"
    return None


def shown(c: Change, store: Store) -> dict[str, Any] | None:
    """The stop the owner may clear and why its rerun waits on the settings, or None."""
    if clearable(c):
        return None
    return c.stop.model_dump(mode="json", include={"reason", "action", "at"}) | {"unset": unset(store)}


def _owner(request: Request) -> None:
    if request.headers.get("x-owlbear-use", "").lower() == "chat":
        raise HTTPException(403, "Only the owner clears a stop, on the Changes page")


def router(store: Store, read: Callable[[str], Change], wake: Callable[[], None]) -> APIRouter:
    """The recovery route; *read* is the API's Change reader, *wake* starts the host's next pass."""
    routes = APIRouter()

    @routes.post("/changes/{slug}/recovery", dependencies=[Depends(_owner)])
    def recovery(slug: str, body: RecoveryBody) -> dict[str, str]:
        read(slug)
        try:  # under the lock no pass can stop the Change again between the check and the queueing
            with store.lock(slug):
                c = store.read(slug)
                if why := clearable(c) or unset(store):
                    raise HTTPException(409, why)
                if (c.stop.action, c.stop.at) != (body.action, body.at):
                    raise HTTPException(409, "The stop changed since the page showed it; reload")
                store.put_inbox(slug, Recovery(at=datetime.now(UTC), action=c.stop.action))
        except (LockHeldError, StoreError) as exc:
            raise HTTPException(409, f"change: {exc}; try again") from exc
        wake()
        return {"accepted": "recovery"}

    return routes
