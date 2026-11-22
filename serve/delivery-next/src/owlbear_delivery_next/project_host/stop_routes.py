"""The owner clears a stop he resolved, and Delivery reruns its step (#754); a chat can't."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from owlbear_delivery_next.change_contracts.inbox import Recovery
from owlbear_delivery_next.change_contracts.models import Exit, Record
from owlbear_delivery_next.change_flow import asking, delivery_target, repair_recovery, stuck
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.project_host import runner_end
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.state_store import work_block
from owlbear_delivery_next.state_store.store import LockHeldError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store


class RecoveryBody(Record):
    """The stop the page showed: its action and when it stopped."""

    action: str
    at: datetime
    remedy: int | None = None


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
    if (
        (asking.inventory_stop(c) or stuck.exhausted(c))
        and repair_recovery.offered(c) is None
        and not repair_recovery.deadline(c)
    ):
        return (
            "No repair ran for this step; an unchanged rerun cannot resolve it. Pause or abandon the Change"
            if asking.inventory_stop(c)
            else "The repair ended without resolving this cause; an unchanged rerun cannot resolve it"
        )
    return None


def _wait(block: work_block.Block) -> str | None:
    """Why no work may start for want of settings, this machine's included (D-01M61SBWK4VE4MNTD35TR0VPS8), or None."""
    if block.reason:
        return f"The settings can't be read ({block.reason}); fix them on the Settings page to run the step again"
    if missing := block.keys:
        more = " and others" if missing[1:] else ""
        return f"Settings unset: {missing[0]}{more}; fill them in on the Settings page to run the step again"
    return None


def _rerun(c: Change, store: Store, block: work_block.Block) -> dict[str, Any]:
    """Which step runs again, whose session timed out and each such role's current limit, never the historical one."""
    role, repairer = roles.SESSIONS[c.step.kind], repair_recovery.repairer_timed_out(c)
    timed = [role, *([roles.SESSIONS["step-repair"]] if repairer else [])]
    try:
        agents = {} if block.reason else store.settings().agents
    except StoreError:
        agents = {}
    task = next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan and c.step.task else None
    return {
        "step": str(c.step.kind),
        "task": c.step.task,
        "title": task.title if task else "",
        "role": role,
        "repairer": repairer,
        "limits": [{"role": r, "minutes": agents[r].minutes if r in agents else None, "current": True} for r in timed],
    }


def unset(store: Store) -> str | None:
    """The words for the settings in force now, or None."""
    return _wait(work_block.of_store(store))


def shown(c: Change, store: Store) -> dict[str, Any] | None:
    """The stop the owner may clear and why its rerun waits on the settings, or None.

    ``unset`` is the words; ``settings`` holds the count of unset settings and the reason they can't be read, from the
    same read, so the page can say how many are unset without their keys.
    """
    if clearable(c):
        return None
    block = work_block.of_store(store)
    remedy = repair_recovery.offered(c)
    continuation = repair_recovery.action(c, remedy) if remedy else ""
    fixed = (
        (
            f"OwlBear {repair_recovery.version(c)} stopped this step. "
            if repair_recovery.version(c)
            else "An earlier OwlBear stopped this step. "
        )
        + f"The running {codebase.release()} contains the fix for Delivery defect #{remedy}."
        if remedy
        else ""
    )
    recovery = c.stop.model_dump(mode="json", include={"reason", "action", "at"}) | {
        "unset": _wait(block),
        "settings": {"count": len(block.keys), "reason": block.reason},
    }
    if remedy:
        recovery |= {"action": continuation, "remedy": remedy, "label": continuation, "fixed": fixed}
    elif repair_recovery.deadline(c):
        recovery |= {"action": stuck.RERUN, "label": stuck.RERUN, "rerun": _rerun(c, store, block)}
    return recovery


def evidence(c: Change) -> dict[str, str] | None:
    """The recorded stop, independent of pauses, settings and whether a continuation is safe."""
    if not (c.stop and c.outcome and c.outcome.exit == Exit.STOP):
        return None
    return {"reason": c.stop.reason, "action": stuck.action(c)}


def retained(c: Change) -> dict[str, str] | None:
    """A refused or declined patch, shown even when the stop has no recovery action."""
    r = c.repairs.done[-1] if c.repairs.done else None
    if not (
        c.stop
        and c.outcome
        and c.outcome.exit == Exit.STOP
        and r
        and r.phase == "stopped"
        and r.cause == c.outcome.cause
        and r.fix == "patch"
        and r.diff
    ):
        return None
    return {"reason": c.stop.reason.removesuffix(f"\n\nThe fix kept (not applied):\n{r.diff}"), "diff": r.diff}


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
                remedy = repair_recovery.offered(c)
                action = (
                    repair_recovery.action(c, remedy)
                    if remedy
                    else stuck.RERUN
                    if repair_recovery.deadline(c)
                    else c.stop.action
                )
                if (action, c.stop.at, remedy) != (body.action, body.at, body.remedy):
                    raise HTTPException(409, "The stop changed since the page showed it; reload")
                store.put_inbox(slug, Recovery(at=datetime.now(UTC), action=action, stop_at=c.stop.at, remedy=remedy))
        except (LockHeldError, StoreError) as exc:
            raise HTTPException(409, f"change: {exc}; try again") from exc
        wake()
        return {"accepted": "recovery"}

    return routes
