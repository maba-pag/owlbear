"""The shaping chat's request for a brief challenge (TD-249): the version, with the shaper's rejections.

The request is checked and recorded under the Change's lock; the host then runs the challenger, and the chat reads
the verdict from the Change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next import brief_rounds, rounds, tools
from owlbear_delivery_next.inbox import BriefApproval
from owlbear_delivery_next.round_records import BRIEF
from owlbear_delivery_next.store import LockHeldError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.inbox import InboxItem
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.store import Store


class ChallengeBody(BaseModel):
    """The brief version the shaper saved and asks to be challenged, and the findings it rejects."""

    change: str = Field(min_length=1, max_length=20)
    version: int = Field(ge=1)
    rejected: list[tools.Rejection] = Field(default_factory=list, max_length=20)


class ApproveBody(BaseModel):
    """Approve one brief version."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)


def slug_of(store: Store, handle: str) -> str | None:
    """The Change a chat handle names."""
    for slug in store.slugs():
        try:
            if store.read(slug).handle == handle:
                return slug
        except StoreError:
            continue
    return None


def router(
    store: Store,
    read: Callable[[str], Change],
    put: Callable[[str, InboxItem], dict[str, str]],
    wake: Callable[[], None],
) -> APIRouter:
    """POST /briefs/challenge records the shaper's request; POST /changes/{slug}/approve-brief the owner's approval."""
    routes = APIRouter()

    @routes.post("/changes/{slug}/approve-brief")
    def approve(slug: str, body: ApproveBody) -> dict[str, str]:
        c = read(slug)
        brief = c.brief
        if body.version != brief.version:
            raise HTTPException(409, f"brief version {body.version} is not the current draft")
        if why := brief_rounds.approvable(c):  # TD-249: only a version its challenge loop ended on
            raise HTTPException(409, f"brief v{brief.version} cannot be approved yet: {why}")
        if (stepped := [s.name for s in brief.visual if s.steps]) and not store.settings().preparations:
            raise HTTPException(
                409,
                f"The visual states {', '.join(stepped)} have clicks or typing, which run only on a prepared test copy "
                "(TD-96); declare the project's preparation options in its settings first, or revise the brief "
                "without those steps",
            )
        return put(slug, BriefApproval(at=datetime.now(UTC), version=body.version))

    @routes.post("/briefs/challenge")
    def challenge(body: ChallengeBody) -> dict[str, Any]:
        if (slug := slug_of(store, body.change)) is None:
            raise HTTPException(422, f"change: {body.change} is not a Change here - use a handle from show_status")
        keys = [r.finding for r in body.rejected]
        if twice := sorted({k for k in keys if keys.count(k) > 1}):
            raise HTTPException(422, f"rejected: {', '.join(twice)} listed twice - one entry per finding")
        try:
            with store.lock(slug) as lock:
                c = store.read(slug)
                policy = rounds.policy(store.settings(), BRIEF, "shaper")
                said = {r.finding: r.reason for r in body.rejected}
                if why := brief_rounds.request(c, body.version, said, policy, datetime.now(UTC)):
                    raise HTTPException(409, why)
                store.write(lock, c)
        except (LockHeldError, StoreError) as exc:
            raise HTTPException(409, f"change: {exc}; try again") from exc
        wake()
        return {"requested": True, "change": body.change, "version": body.version} | brief_rounds.status(c)

    return routes
