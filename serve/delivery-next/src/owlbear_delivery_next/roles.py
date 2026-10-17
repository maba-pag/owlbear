"""Model and reasoning effort per session role (TD-27): the role of each session, its defaults, the settings table."""

from __future__ import annotations

from typing import TYPE_CHECKING, get_args

from pydantic import ValidationError

from owlbear_delivery_next.models import Effort, Role, StepKind
from owlbear_delivery_next.profile_record import RoleModel

if TYPE_CHECKING:
    from owlbear_delivery_next.config import Settings

DEFAULTS: dict[Role, RoleModel] = {
    "planner": RoleModel(model="claude-opus-5.5", effort="high"),
    "builder": RoleModel(model="claude-opus-5.5", effort="medium"),
    "reviewer": RoleModel(model="gpt-6.1-sol", effort="xhigh"),
    "challenger": RoleModel(model="gpt-6.1-sol", effort="high"),
    "designer": RoleModel(model="claude-opus-5.5", effort="high"),  # the visual review's design judge
    "preparer": RoleModel(model="claude-haiku-5.5", effort="low"),  # check prep: finds the launch recipe
    "shaper": RoleModel(model="claude-opus-5.5", effort="medium"),  # the New Change chat (TD-83); owner's effort
    "updater": RoleModel(model="claude-opus-5.5", effort="high"),  # writes the design pack's skills (TD-125)
}
EFFORTS: tuple[str, ...] = get_args(Effort.__value__)
SESSIONS: dict[str, Role] = {
    StepKind.PLAN: "planner",
    StepKind.BUILD: "builder",
    StepKind.CHECK: "preparer",
    StepKind.REVIEW: "reviewer",  # task and final review
    "visual-review": "reviewer",
    "design-review": "designer",
    "plan-challenge": "challenger",
    "brief-challenge": "challenger",
    "amendment-challenge": "challenger",  # a worker's proposed brief wording (TD-179)
    "dispute-reconsider": "reviewer",  # a finding the owner sent back with a note (TD-193)
    "plan-reconsider": "challenger",  # a plan finding the owner sent back with a note (TD-190)
    "brief-reconsider": "challenger",  # a brief finding the owner sent back with a note (TD-221)
    "pack-challenge": "challenger",  # a design pack update, before it is activated (TD-101)
    "pack-reconsider": "challenger",  # a pack finding the owner sent back with a note (TD-220)
    "pack-update": "updater",  # the design pack update's writing session (TD-125)
}


def chosen(settings: Settings, session: str) -> RoleModel:
    """The model, effort and context tier a session kind or reviewer label runs with, from the resolved settings."""
    agent = settings.agents[SESSIONS[session]]
    return RoleModel(model=agent.model, effort=agent.effort, context=agent.context)


def parse(text: str) -> tuple[Role, RoleModel]:
    """``ROLE=MODEL:EFFORT``.

    Raises:
        ValueError: Unknown role, or a model and effort :class:`RoleModel` refuses.
    """
    role, _, rest = text.partition("=")
    model, _, effort = rest.rpartition(":")
    if role not in DEFAULTS:
        raise ValueError(f"role must be one of {', '.join(DEFAULTS)}, got {role!r}")  # noqa: EM102, TRY003
    try:
        return role, RoleModel(model=model.strip(), effort=effort)
    except ValidationError as exc:
        why = "; ".join(e["msg"] for e in exc.errors())
        msg = f"expected ROLE=MODEL:EFFORT with effort one of {', '.join(EFFORTS)}, got {text!r}: {why}"
        raise ValueError(msg) from exc


def table(settings: Settings) -> str:
    """The effective role table, marking values set in the global or project settings."""
    lines = ["Models"]
    for role, agent in settings.agents.items():
        set_in = sorted({settings.sources[f"agents.{role}.{f}"] for f in ("model", "effort")} - {"default"})
        lines.append(f"  {role}: {agent.model} effort {agent.effort}{f' ({"/".join(set_in)})' if set_in else ''}")
    return "\n".join(lines)
