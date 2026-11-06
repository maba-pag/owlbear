"""The project host's part in a brief version saved after its challenge loop ended (#986, D-01M6P1685N1R5W2PPV5SHKR2H0).

On every pass, before the pause decides what may start: the owner's recorded approval takes effect once the loop ended
on its version with nothing raised, paused or not, as his own approval does (TD-287); a waiting version gets its start
time from the shaper's set wait after its latest save, and its challenge starts once that time has passed, neither
while Delivery nor while the Change is paused.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import Exit, Outcome, Waiting
from owlbear_delivery_next.change_flow import brief_starts
from owlbear_delivery_next.project_host import brief_routes
from owlbear_delivery_next.workflow_steps import decision_publication

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Lock, Store


def passed(store: Store, lock: Lock, c: Change, now: datetime, *, paused: bool) -> Change:
    """*c* after this pass's part; the host's own write keeps it, and only an approval writes here, as the owner's."""
    if brief_starts.approving(c):  # only while the Change is shaped: an abandoned one never approves
        return _approved(store, lock, c, now)
    o = c.outcome
    if not brief_starts.waiting(c) or o is None:
        return c
    if o.wake_at is None:
        wait = store.settings().roles["shaper"]["challenge_wait"]
        if wait is None:  # unset: Settings lists it, and the project's work waits for it
            return c
        o.wake_at = o.at + timedelta(minutes=wait)
    if paused or c.intent.paused_at or o.wake_at > now:
        return c
    if why := brief_routes.asked(store, c, brief_routes.ChallengeBody(change=c.handle, version=c.brief.version)):
        store.log(lock, c.slug, {"event": "brief-challenge-refused", "at": now.isoformat(), "reason": why})
    return c


def _approved(store: Store, lock: Lock, c: Change, now: datetime) -> Change:
    """The owner's approval, made as his Approve makes it; a refusal leaves the version waiting, its reason whole."""
    n = c.brief.version
    store.write(lock, c)  # the approval reads the Change from the store, and spends the owner's with its own write
    why = brief_routes.approved(store, lock, brief_routes.ApproveBody(version=n))
    c = store.read(lock.slug)
    if why:
        c.brief.approve_if_clean = None
        reason = f"approve brief v{n}: the approval you asked for was refused: {why}"
        c.outcome = Outcome(
            exit=Exit.PENDING, waiting=Waiting.CHAT, who="you", cause=brief_starts.REFUSED, reason=reason, at=now
        )
        if not why.startswith(decision_publication.REFUSED):  # the publication logs its own refusal
            store.log(lock, c.slug, {"event": "approval-refused", "at": now.isoformat(), "reason": why})
    return c
