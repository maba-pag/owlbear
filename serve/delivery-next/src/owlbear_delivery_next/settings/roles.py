"""Model and reasoning effort per session role (TD-27): the role of each session, its defaults, the settings table."""

from __future__ import annotations

from typing import TYPE_CHECKING, get_args

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.models import Effort, Role, StepKind
from owlbear_delivery_next.change_contracts.profile_record import RoleModel

if TYPE_CHECKING:
    from owlbear_delivery_next.settings.config import Settings

DEFAULTS: dict[Role, RoleModel] = {
    "planner": RoleModel(model="claude-opus-5.5", effort="high"),
    "builder": RoleModel(model="claude-opus-5.5", effort="medium"),
    "reviewer": RoleModel(model="gpt-6.1-sol", effort="xhigh"),
    "challenger": RoleModel(model="gpt-6.1-sol", effort="high"),
    "design-judge": RoleModel(model="claude-opus-5.5", effort="high"),  # the visual review's design judge (TD-169)
    "preparer": RoleModel(model="claude-haiku-5.5", effort="low"),  # check prep: finds the launch recipe
    "shaper": RoleModel(model="claude-opus-5.5", effort="medium"),  # the New Change chat (TD-83); owner's effort
    "updater": RoleModel(model="claude-opus-5.5", effort="high"),  # writes the design pack's skills (TD-125)
    "test-reviewer": RoleModel(model="gpt-6.1-sol", effort="medium"),  # one share of a test review (TD-339)
    "test-curator": RoleModel(model="claude-opus-5.5", effort="high", context="long"),  # applies what holds
    "picker": RoleModel(model="gpt-6.1-sol", effort="medium"),  # picks a brief's decisions from the list (TD-459)
}
EFFORTS: tuple[str, ...] = get_args(Effort.__value__)
MINUTES: dict[Role, int] = {  # TD-286: each session's total running time; the shaper's chat has none (TD-285)
    "planner": 30,
    "builder": 40,
    "reviewer": 20,
    "challenger": 20,
    "design-judge": 20,
    "preparer": 30,
    "shaper": 40,
    "updater": 40,
    "test-reviewer": 20,  # the reviewer's
    "test-curator": 40,  # the builder's
    "picker": 10,  # a pick takes about a minute
}
SESSIONS: dict[str, Role] = {
    StepKind.PLAN: "planner",
    StepKind.TESTS: "test-reviewer",  # a test review's shares (TD-373)
    StepKind.BUILD: "builder",
    StepKind.CHECK: "preparer",
    StepKind.REVIEW: "reviewer",  # task and final review
    "visual-review": "reviewer",
    "design-review": "design-judge",
    "plan-challenge": "challenger",
    "brief-challenge": "challenger",
    "amendment-challenge": "challenger",  # a worker's proposed brief wording (TD-179)
    "dispute-reconsider": "reviewer",  # a finding the owner sent back with a note (TD-193)
    "plan-reconsider": "challenger",  # a plan finding the owner sent back with a note (TD-190)
    "brief-reconsider": "challenger",  # a brief finding the owner sent back with a note (TD-221)
    "pack-challenge": "challenger",  # a design pack update, before it is activated (TD-101)
    "pack-reconsider": "challenger",  # a pack finding the owner sent back with a note (TD-220)
    "pack-update": "updater",  # the design pack update's writing session (TD-125)
    "test-review": "test-reviewer",  # one share of a test review (TD-373)
    "test-curation": "test-curator",  # a test review's build (TD-339)
    "decision-pick": "picker",  # a brief version's decisions, before its challenge (TD-459)
    "clarification-check": "picker",  # an owner's clarification against the approved brief (TD-461)
}


def chosen(settings: Settings, session: str) -> RoleModel:
    """The model, effort and context tier a session kind or reviewer label runs with, from the resolved settings."""
    agent = settings.agents[SESSIONS[session]]
    return RoleModel(model=agent.model, effort=agent.effort, context=agent.context)


def limit(settings: Settings, session: str) -> float:
    """Seconds one session of this kind or reviewer label may run in total, from the resolved settings (TD-286)."""
    return settings.agents[SESSIONS[session]].minutes * 60.0


def subagents(settings: Settings, session: str) -> bool:
    """Whether a session of this kind or reviewer label may start built-in subagents (TD-374, TD-376)."""
    return settings.agents[SESSIONS[session]].subagents


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
