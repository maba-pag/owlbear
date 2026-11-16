"""The Brief panel's amendments (TD-185): the reference and current versions, the list, and the owner's objection."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts.inbox import ObjectionItem
from owlbear_delivery_next.change_flow import amend_apply, amending

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.inbox import InboxItem
    from owlbear_delivery_next.change_contracts.models import Change


class ObjectionBody(BaseModel):
    """Why the owner objects to an applied amendment, if he says."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(default="", max_length=2000)


def shown(c: Change) -> dict[str, Any]:
    """The versions and every amendment, each applied one with why he may not object to it now, or ""."""
    return {
        "request": None if c.tests else amending.requestable(c),
        "version": c.brief.version,
        "reference": amend_apply.reference(c),
        "versions": [b.version for b in c.brief.approved],
        "list": [
            a.model_dump(mode="json") | ({"object": amending.objectable(c, a.id)} if a.state == "applied" else {})
            for a in c.amendments
        ],
    }


def admit_request(c: Change, text: str) -> None:
    """Reject an unavailable amendment or an empty request before it enters the inbox."""
    if why := amending.requestable(c):
        raise HTTPException(409, why)
    if not text.strip():
        raise HTTPException(422, "Say what you want to change in the brief")


def router(read: Callable[[str], Change], put: Callable[[str, InboxItem], dict[str, str]]) -> APIRouter:
    """POST /changes/{slug}/amendments/{ident}/objection: queued while he may object, else 409 with why."""
    routes = APIRouter()

    @routes.post("/changes/{slug}/amendments/{ident}/objection")
    def objection(slug: str, ident: str, body: ObjectionBody) -> dict[str, str]:
        if why := amending.objectable(read(slug), ident):
            raise HTTPException(409, why)
        return put(slug, ObjectionItem(at=datetime.now(UTC), amendment=ident, text=body.text.strip()))

    return routes
