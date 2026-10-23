"""Challenge loops (TD-208): a subject's loop, with the policy it pins from the settings when it starts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.round_records import FINAL, RoundLoop, RoundPolicy

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Role
    from owlbear_delivery_next.settings.config import Settings


def policy(settings: Settings, subject: str, role: Role = "builder") -> RoundPolicy:
    """The values a loop of *role*'s work runs with: the final review's own (TD-211), else the role's."""
    if subject == FINAL:
        settings.need("final_review")
        return settings.final_review.model_copy()
    return RoundPolicy.model_validate(settings.agent(role).model_dump(include=set(RoundPolicy.model_fields)))


def loop(c: Change, subject: str, settings: Settings, role: Role = "builder") -> RoundLoop:
    """The subject's loop; a new one pins the policy in force now, so later setting edits never change it."""
    return c.loops.setdefault(subject, RoundLoop(subject=subject, policy=policy(settings, subject, role)))
