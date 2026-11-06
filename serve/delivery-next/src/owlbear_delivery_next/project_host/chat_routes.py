"""The chat's own reads (chat contract 1): a Change's brief as the shaping chat saved it, and a challenge's progress.

Contract 7 adds the draft's shaping capture: its pictures at the first width, for the chat to write expectations by.

A chat's owlbear-delivery server reads no state itself (D-01M5Q5GKHX7BJTXPEW2MHGS9E0), so what it used to read
from the store is answered here, by the host's own code, in the shape contract 1 gives the chat.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Query

from owlbear_delivery_next.change_contracts import chat_contract
from owlbear_delivery_next.change_flow import brief_rounds, picks, shaping_capture
from owlbear_delivery_next.state_store import briefs

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.visual_records import ShapingCapture

INLINE = 4 * 1024 * 1024  # bytes of one picture the chat gets inline; a larger one it opens on the Changes page


def brief(change: Change) -> dict[str, Any]:
    """The Change's current brief as the chat saved it, decisions and non-goals included, to read back."""
    b = change.brief
    out = b.model_dump(mode="json", include={"version", "title", "outcome", "scope", "non_goals"})
    out["decisions"] = [d.model_dump(mode="json", exclude={"id", "replaces"}) for d in b.decisions]  # as drafted
    owner, placed = set(b.specified), briefs.positions(b)  # sent back as saved: a resave keeps who stated what
    states = [{"name": s.name, "owner": f"screen:{s.name}" in owner} for s in b.visual]
    checks = [{"name": p.id, "covers": [placed.get(k, k) for k in p.criteria], "owner": f"check:{p.id}" in owner}
              for p in change.checks]  # fmt: skip
    out |= {"specified": [placed[k.id] for k in b.criteria if k.id in owner], "states": states, "person_checks": checks}
    # a candidate the owner adopts in chat, such as a merged Change's follow-up; the rest went their path (TD-185)
    shown = {"field", "key", "remove", "old", "new", "why", "path", "actions", "steps", "covers", "visual", "question"}
    proposed = [i.model_dump(mode="json", include=shown) | {"verdict": a.verdict or "not judged"}
                for a in change.amendments if a.state == "recorded" for i in a.items]  # fmt: skip
    out |= {"challenge": brief_rounds.status(change)}  # TD-221: the brief challenge's findings by ID
    return out | {"criteria": [k.text for k in b.criteria], "proposed_wording": proposed}


def capture(c: Change, folder: Path) -> dict[str, Any]:
    """The draft's shaping capture (D-01M61V2GR0C6JV2R6KJ0WR4PNB): running, or its pictures and findings.

    Each state's picture at the first width comes in base64, none when over `INLINE` or missing; findings come whole.
    """
    b, s, out = c.brief, c.shaped, {"version": c.brief.version}
    if not shaping_capture.needed(b):
        return out | {"running": False, "needed": False}
    if shaping_capture.waiting(c) or s is None or s.result is None:
        return out | {"running": True}
    r, states, root = s.result, [], folder.resolve()
    width = r.widths[0] if r.widths else 0
    for v in b.visual:
        name = f"{v.name}-{width}.png"
        path = (root / name).resolve()  # only a picture the capture lists, inside its own folder
        data = path.read_bytes() if name in r.files and path.parent == root and path.is_file() else b""
        shown = base64.b64encode(data).decode() if data and len(data) <= INLINE else None
        states.append({"name": v.name, "width": width, "bytes": len(data), "png": shown})
    return out | {"running": False, "head": r.head, "at": r.at.isoformat(), "states": states, "findings": r.findings}


def contract() -> dict[str, Any]:
    """The chat contracts this host serves, and that it refuses a chat's save past its deadline (`admit_by`, #846)."""
    return {"supported": sorted(chat_contract.SUPPORTED), "admit_by": True}


def router(read: Callable[[str], Change], folder: Callable[[str, ShapingCapture], Path]) -> APIRouter:
    """GET /chat/brief|challenge|capture/{slug}: what a chat reads, answered from the host's state.

    *folder* is where a Change's ended shaping capture keeps its pictures.
    """
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
            return {"running": True, "version": c.brief.version}  # the draft it answers for (chat contract 3)
        return {"running": False, **brief_rounds.status(c)}

    @routes.get("/chat/capture/{slug}")
    def chat_capture(slug: str) -> dict[str, Any]:
        c = read(slug)  # one of the store's own Changes: its folder comes from the record
        return capture(c, folder(c.slug, c.shaped) if c.shaped and c.shaped.result else Path())

    routes.add_api_route("/chat/contract", contract, methods=["GET"])
    return routes
