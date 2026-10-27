"""Model and reasoning effort per session role (TD-27): the role of each session, its defaults, the settings table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, get_args

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.models import Effort, Role, StepKind
from owlbear_delivery_next.change_contracts.profile_record import RoleModel

if TYPE_CHECKING:
    from owlbear_delivery_next.settings.config import Settings

ROLES: tuple[Role, ...] = get_args(Role.__value__)  # their values come from the settings layers, none from code
EFFORTS: tuple[str, ...] = get_args(Effort.__value__)
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
    "memory-curation": "curator",  # one memory folder's automatic curation (item 5 slice 4)
    "decision-pick": "picker",  # a brief version's decisions, before its challenge (TD-459)
    "clarification-check": "picker",  # an owner's clarification against the approved brief (TD-461)
}


USER_CONFIG = ("load_user_instructions", "load_user_skills")  # D-01M5YE4P5317N1HWD0QN6N05E0: every step's session


@dataclass(frozen=True)
class UserConfig:
    """Whether a step's session loads the owner's own instructions and skills (D-01M5YE4P5317N1HWD0QN6N05E0)."""

    instructions: bool
    skills: bool


USER_OFF = UserConfig(instructions=False, skills=False)  # a session no site switched on: never more than its own


def chosen(settings: Settings, session: str) -> RoleModel:
    """The model, effort and context tier a session kind or reviewer label runs with, from the resolved settings.

    A step's session also needs both user-config switches set (D-01M5YE4P5317N1HWD0QN6N05E0): unset refuses here,
    before any session opens. The shaper's chat and the Spotter read ``Settings.agent`` and do not need them.
    """
    settings.need(*USER_CONFIG)
    agent = settings.agent(SESSIONS[session])
    return RoleModel(model=agent.model, effort=agent.effort, context=agent.context)


def user_config(settings: Settings) -> UserConfig:
    """The user-config switches a step's session runs with; ``SettingsUnset`` while either is unset."""
    settings.need(*USER_CONFIG)
    return UserConfig(instructions=bool(settings.load_user_instructions), skills=bool(settings.load_user_skills))


def limit(settings: Settings, session: str) -> float:
    """Seconds one session of this kind or reviewer label may run in total, from the resolved settings (TD-286)."""
    return settings.agent(SESSIONS[session]).minutes * 60.0


def subagents(settings: Settings, session: str) -> bool:
    """Whether a session of this kind or reviewer label may start built-in subagents (TD-374, TD-376)."""
    return settings.agent(SESSIONS[session]).subagents


def parse(text: str) -> tuple[Role, RoleModel]:
    """``ROLE=MODEL:EFFORT``.

    Raises:
        ValueError: Unknown role, or a model and effort :class:`RoleModel` refuses.
    """
    role, _, rest = text.partition("=")
    model, _, effort = rest.rpartition(":")
    if role not in ROLES:
        raise ValueError(f"role must be one of {', '.join(ROLES)}, got {role!r}")  # noqa: EM102, TRY003
    try:
        return role, RoleModel(model=model.strip(), effort=effort)
    except ValidationError as exc:
        why = "; ".join(e["msg"] for e in exc.errors())
        msg = f"expected ROLE=MODEL:EFFORT with effort one of {', '.join(EFFORTS)}, got {text!r}: {why}"
        raise ValueError(msg) from exc


def table(settings: Settings) -> str:
    """The effective role table, marking values set in the global or project settings."""
    lines = ["Models"]
    for role, agent in settings.roles.items():
        if agent["model"] is None or agent["effort"] is None:
            lines.append(f"  {role}: unset; fill it in on the Settings page")
            continue
        set_in = sorted({settings.sources[f"agents.{role}.{f}"] for f in ("model", "effort")} - {"default"})
        lines.append(f"  {role}: {agent['model']} effort {agent['effort']}{f' ({"/".join(set_in)})' if set_in else ''}")
    return "\n".join(lines)
