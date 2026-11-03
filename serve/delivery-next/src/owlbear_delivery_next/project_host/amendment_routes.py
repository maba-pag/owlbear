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
        "version": c.brief.version,
        "reference": amend_apply.reference(c),
        "versions": [b.version for b in c.brief.approved],
        "running": c.amending.model_dump(mode="json") if c.amending else None,
        "list": [
            a.model_dump(mode="json") | ({"object": amending.objectable(c, a.id)} if a.state == "applied" else {})
            for a in c.amendments
        ],
    }


def router(read: Callable[[str], Change], put: Callable[[str, InboxItem], dict[str, str]]) -> APIRouter:
    """POST /changes/{slug}/amendments/{ident}/objection: queued while he may object, else 409 with why."""
    routes = APIRouter()

    @routes.post("/changes/{slug}/amendments/{ident}/objection")
    def objection(slug: str, ident: str, body: ObjectionBody) -> dict[str, str]:
        if why := amending.objectable(read(slug), ident):
            raise HTTPException(409, why)
        return put(slug, ObjectionItem(at=datetime.now(UTC), amendment=ident, text=body.text.strip()))

    return routes
