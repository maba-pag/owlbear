"""Forward migrations of stored records, keyed by the format they upgrade from."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from owlbear_delivery_next.config import Agent, Layer
from owlbear_delivery_next.models import Role
from owlbear_delivery_next.profile_record import RoleModel

if TYPE_CHECKING:
    from collections.abc import Callable

type Migrations = dict[int, Callable[[dict[str, Any]], dict[str, Any]]]
ROLES: TypeAdapter[dict[Role, RoleModel]] = TypeAdapter(dict[Role, RoleModel])


def roles_moved(data: dict[str, Any]) -> dict[str, Any]:
    """Profile format 1 to 2: the role overrides moved to the project settings; each is checked, then dropped."""
    ROLES.validate_python(data.pop("roles", {}))
    return data


def with_roles(layer: Layer, found: dict[Role, RoleModel]) -> Layer:
    """The layer with old role overrides filling only the model and effort fields it leaves empty."""
    agents = dict(layer.agents)
    for role, old in found.items():
        own = agents.get(role, Agent())
        agents[role] = own.model_copy(update={"model": own.model or old.model, "effort": own.effort or old.effort})
    return layer.model_copy(update={"agents": agents})


def _challenged(brief: object) -> None:
    if isinstance(brief, dict):
        if "reviewed" in brief:
            brief["challenged"] = brief.pop("reviewed")
        for snapshot in brief.get("approved") or []:
            _challenged(snapshot)


def brief_challenged(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 1 to 2: the brief review is a challenge (TD-73); the field is renamed in every brief snapshot.

    A format-1 consent may still carry ``queued_at`` from the removed merge queue (340cb6d59); it is dropped.
    """
    _challenged(data.get("brief"))
    if isinstance(consent := data.get("consent"), dict):
        consent.pop("queued_at", None)
    return data


def visual_decided(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 2 to 3: the owner decides a visual round (TD-79); a capture keeps no accept or repair answer."""
    for capture in (data.get("visual"), data.get("before")):
        if isinstance(capture, dict):
            capture.pop("decision", None)
            capture.pop("note", None)
    return data


def seed_dropped(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 1 to 2: declared preparation options replace the seed command (TD-96); it is dropped.

    A seed command names no isolation or cleanup, so it cannot become an option; the owner declares one instead.
    """
    data.pop("seed", None)
    return data


def rounds_kept(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 3 to 4: TD-208's loops replace TD-189's round fields on tasks and disputes; they are dropped."""
    for task in (data.get("plan") or {}).get("tasks") or []:
        if isinstance(task, dict):
            task.pop("found_in", None)
            for d in task.get("disputes") or []:
                if isinstance(d, dict):
                    d.pop("direct", None)
                    d.pop("repeat_of", None)
    return data


def judge_renamed(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 2 to 3: the designer role is the design judge (TD-169); its settings keep their values."""
    agents = data.get("agents")
    if isinstance(agents, dict) and "designer" in agents:
        agents["design-judge"] = agents.pop("designer")
    return data


CHANGE: Migrations = {1: brief_challenged, 2: visual_decided, 3: rounds_kept}
PROFILE: Migrations = {1: roles_moved}
CONFIG: Migrations = {1: seed_dropped, 2: judge_renamed}
