"""Challenge loops (TD-208): a subject's loop, with the policy it pins from the settings when it starts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.round_records import RoundLoop, RoundPolicy

if TYPE_CHECKING:
    from owlbear_delivery_next.config import Settings
    from owlbear_delivery_next.models import Change, Role

FINAL = "final"  # the final review's subject


def policy(settings: Settings, subject: str, role: Role = "builder") -> RoundPolicy:
    """The values a loop of *role*'s work runs with: the final review's own (TD-211), else the role's."""
    if subject == FINAL:
        return settings.final_review.model_copy()
    return RoundPolicy.model_validate(settings.agents[role].model_dump(include=set(RoundPolicy.model_fields)))


def loop(c: Change, subject: str, settings: Settings, role: Role = "builder") -> RoundLoop:
    """The subject's loop; a new one pins the policy in force now, so later setting edits never change it."""
    return c.loops.setdefault(subject, RoundLoop(subject=subject, policy=policy(settings, subject, role)))
