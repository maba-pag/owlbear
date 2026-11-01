"""The chat's own reads (chat contract 1): a Change's brief as the shaping chat saved it, and a challenge's progress.

A chat's owlbear-delivery server reads no state itself (D-01M5Q5GKHX7BJTXPEW2MHGS9E0), so what it used to read
from the store is answered here, by the host's own code, in the shape contract 1 gives the chat.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Query

from owlbear_delivery_next.change_contracts import chat_contract
from owlbear_delivery_next.change_flow import brief_rounds, picks

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change


def brief(change: Change) -> dict[str, Any]:
    """The Change's current brief as the chat saved it, decisions and non-goals included, to read back."""
    b = change.brief
    out = b.model_dump(mode="json", include={"version", "title", "outcome", "scope", "non_goals"})
    out["decisions"] = [d.model_dump(mode="json", exclude={"id", "replaces"}) for d in b.decisions]  # as drafted
    owner = set(b.specified)  # sent back as saved, so a resave keeps who stated what
    states = [{"name": s.name, "owner": f"screen:{s.name}" in owner} for s in b.visual]
    checks = [{"name": p.id, "owner": f"check:{p.id}" in owner} for p in change.checks]
    out |= {"specified": [k.id for k in b.criteria if k.id in owner], "states": states, "person_checks": checks}
    proposed = [i.model_dump(include={"criterion", "old", "new", "why"}) | {"verdict": a.verdict or "not judged"}
                for a in change.amendments for i in a.items]  # fmt: skip
    out |= {"challenge": brief_rounds.status(change)}  # TD-221: the brief challenge's findings by ID
    return out | {"criteria": [k.text for k in b.criteria], "proposed_wording": proposed}


def contract() -> dict[str, Any]:
    """The chat contracts this host serves, and that it refuses a chat's save past its deadline (`admit_by`, #846)."""
    return {"supported": sorted(chat_contract.SUPPORTED), "admit_by": True}


def router(read: Callable[[str], Change]) -> APIRouter:
    """GET /chat/brief/{slug} and GET /chat/challenge/{slug}: what a chat reads, answered from the host's state."""
    routes = APIRouter()

    @routes.get("/chat/brief/{slug}")
    def chat_brief(slug: str) -> dict[str, Any]:
        return brief(read(slug))

    @routes.get("/chat/challenge/{slug}")
    def chat_challenge(
        slug: str, version: Annotated[int, Query(ge=0)], attempt: Annotated[int, Query(ge=0)]
    ) -> dict[str, Any]:
        c = read(slug)
        if brief_rounds.running(c, version, attempt) or picks.owed(c):
            return {"running": True}
        return {"running": False, **brief_rounds.status(c)}

    routes.add_api_route("/chat/contract", contract, methods=["GET"])
    return routes
