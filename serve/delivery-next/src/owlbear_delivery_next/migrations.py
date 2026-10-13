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
    """Change format 1 to 2: the brief review is a challenge (TD-73); the field is renamed in every brief snapshot."""
    _challenged(data.get("brief"))
    return data


CHANGE: Migrations = {1: brief_challenged}
PROFILE: Migrations = {1: roles_moved}
