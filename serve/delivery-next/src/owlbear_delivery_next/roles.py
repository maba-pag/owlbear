"""Model and reasoning effort per session role (TD-27): the role of each session, defaults and project overrides."""

from __future__ import annotations

from typing import get_args

from pydantic import ValidationError

from owlbear_delivery_next.models import Effort, Profile, Role, RoleModel, StepKind

DEFAULTS: dict[Role, RoleModel] = {
    "planner": RoleModel(model="claude-opus-5.5", effort="high"),
    "builder": RoleModel(model="gpt-6-luna", effort="max"),
    "reviewer": RoleModel(model="gpt-6.1-sol", effort="high"),
    "challenger": RoleModel(model="gpt-6.1-sol", effort="medium"),
}
EFFORTS: tuple[str, ...] = get_args(Effort.__value__)
SESSIONS: dict[str, Role] = {
    StepKind.PLAN: "planner",
    StepKind.BUILD: "builder",
    StepKind.CHECK: "builder",
    StepKind.REVIEW: "reviewer",  # task and final review
    "visual-review": "reviewer",
    "plan-review": "challenger",
    "brief-review": "challenger",
}


def effective(profile: Profile | None, role: Role) -> RoleModel:
    """The project's override for *role*, else its default."""
    return (profile.roles.get(role) if profile else None) or DEFAULTS[role]


def chosen(profile: Profile | None, session: str) -> RoleModel:
    """The model and effort a session kind or reviewer label runs with."""
    return effective(profile, SESSIONS[session])


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


def table(profile: Profile | None) -> str:
    """The effective role table, marking project overrides."""
    lines = ["Models"]
    for role in DEFAULTS:
        rm, own = effective(profile, role), bool(profile and role in profile.roles)
        lines.append(f"  {role}: {rm.model} effort {rm.effort}{' (project)' if own else ''}")
    return "\n".join(lines)
