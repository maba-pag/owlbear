"""The shaping chat's request for a brief challenge (TD-249): the version, with the shaper's rejections.

The request is checked and recorded under the Change's lock; the host then runs the challenger, and the chat reads
the verdict from the Change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.inbox import BriefApproval
from owlbear_delivery_next.change_contracts.round_records import BRIEF
from owlbear_delivery_next.change_flow import brief_rounds, picks
from owlbear_delivery_next.settings import rounds
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store.store import LockHeldError, StoreError
from owlbear_delivery_next.workflow_steps import decision_publication, decisions_gate, pick

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.decision_store import DataView
    from owlbear_delivery_next.state_store.store import Lock, Store


class ChallengeBody(BaseModel):
    """The brief version the shaper saved and asks to be challenged, and the findings it rejects."""

    change: str = Field(min_length=1, max_length=20)
    version: int = Field(ge=1)
    rejected: list[tools.Rejection] = Field(default_factory=list, max_length=20)
    retry_pick: bool = False  # pick the version's decisions again, without a challenge round (TD-459)


class ApproveBody(BaseModel):
    """Approve one brief version; *unreviewed* says the owner accepts a last revision no challenger judged."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    unreviewed: bool = False


def slug_of(store: Store, handle: str) -> str | None:
    """The Change a chat handle names."""
    for slug in store.slugs():
        try:
            if store.read(slug).handle == handle:
                return slug
        except StoreError:
            continue
    return None


def refused(store: Store, c: Change, body: ApproveBody, view: DataView | None) -> str:
    """Why the owner's approval of this brief version is refused, or ""; *view* is the decisions read it pins."""
    brief = c.brief
    if body.version != brief.version:
        return f"brief version {body.version} is not the current draft"
    if why := brief_rounds.approvable(c):  # TD-249: only a version its challenge loop ended on
        return f"brief v{brief.version} cannot be approved yet: {why}"
    if brief_rounds.unreviewed(c) and not body.unreviewed:  # TD-255: the owner ticks that he accepts it
        return f"brief v{brief.version}'s last revision was not reviewed; accept that to approve"
    if why := pick.unapproved(store, c, view):  # TD-459: approval pins the pick, never picks
        return f"brief v{brief.version} cannot be approved yet: {why}"
    if (stepped := [s.name for s in brief.visual if s.steps]) and not store.settings().preparations:
        return (
            f"The visual states {', '.join(stepped)} have clicks or typing, which run only on a prepared test copy "
            "(TD-96); declare the project's preparation options in its settings first, or revise the brief "
            "without those steps"
        )
    return ""


def approved(store: Store, lock: Lock, body: ApproveBody) -> str:
    """Check and record the owner's approval under *lock*, its project decisions published; or why it is refused."""
    c = store.read(lock.slug)
    view = decisions_gate.loaded(store)  # one read: the pick is checked against the list the baseline pins
    if why := refused(store, c, body, view):
        return why
    now = datetime.now(UTC)  # the decisions in force now are the Change's baseline (TD-419)
    baseline, owed = decisions_gate.pinned(store, c, now, view)
    approval = BriefApproval(at=now, version=body.version, baseline=baseline, unpinned=owed, picked=c.brief.picked)
    return decision_publication.approve(store, lock, c, approval)  # TD-453: in force at approval


def asked(store: Store, c: Change, body: ChallengeBody) -> str:
    """Record the shaper's request on *c*: a challenge, whose first for a version owes its pick, or a pick retry.

    Returns:
        Why it is refused, or "".
    """
    if body.retry_pick:
        return picks.retry(c, body.version) if store.shared else "there are no decisions to pick here"
    try:
        policy = rounds.policy(store.settings(), BRIEF, "shaper")
    except SettingsUnset as exc:
        return str(exc)
    said = {r.finding: r.reason for r in body.rejected}
    if why := brief_rounds.request(c, body.version, said, policy, datetime.now(UTC)):
        return why
    if store.shared is not None:  # without a data repository there are no decisions to pick
        picks.owe(c)
    return ""


def router(
    store: Store,
    read: Callable[[str], Change],
    wake: Callable[[], None],
    held: Callable[[], bool] = lambda: False,
) -> APIRouter:
    """POST /briefs/challenge records the shaper's request; POST /changes/{slug}/approve-brief the owner's approval.

    Both are checked and recorded under the Change's lock, so the brief cannot change in between. The challenge runs
    at once, even while Delivery is paused (TD-287); *held* says a stop when idle keeps it until Resume.
    """
    routes = APIRouter()

    @routes.post("/changes/{slug}/approve-brief")
    def approve(slug: str, body: ApproveBody) -> dict[str, str]:
        read(slug)
        try:
            with store.lock(slug) as lock:
                if why := approved(store, lock, body):
                    raise HTTPException(409, why)
        except (LockHeldError, StoreError) as exc:
            raise HTTPException(409, f"change: {exc}; try again") from exc
        wake()
        return {"accepted": "brief-approval"}

    @routes.post("/briefs/challenge")
    def challenge(body: ChallengeBody) -> dict[str, Any]:
        if (slug := slug_of(store, body.change)) is None:
            raise HTTPException(422, f"change: {body.change} is not a Change here - use a handle from show_status")
        keys = [r.finding for r in body.rejected]
        if twice := sorted({k for k in keys if keys.count(k) > 1}):
            raise HTTPException(422, f"rejected: {', '.join(twice)} listed twice - one entry per finding")
        if body.retry_pick and keys:
            raise HTTPException(422, "rejected: a pick retry answers no findings - ask for the challenge without it")
        try:
            with store.lock(slug) as lock:
                c = store.read(slug)
                if why := asked(store, c, body):
                    raise HTTPException(409, why)
                store.write(lock, c)
        except (LockHeldError, StoreError) as exc:
            raise HTTPException(409, f"change: {exc}; try again") from exc
        wake()
        out = {"requested": True, "change": body.change, "version": body.version, "paused": held()}
        return out | brief_rounds.status(c)

    return routes
