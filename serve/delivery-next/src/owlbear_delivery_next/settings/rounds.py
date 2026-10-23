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
    settings.need(*(f"agents.{role}.{name}" for name in RoundPolicy.model_fields))  # only its round values
    return RoundPolicy.model_validate({name: settings.roles[role][name] for name in RoundPolicy.model_fields})


def pinned(c: Change, subject: str, settings: Settings, role: Role = "builder") -> RoundPolicy:
    """The policy the subject's loop pinned, else the one in force now: a running loop never reads the settings."""
    lp = c.loops.get(subject)
    return lp.policy if lp is not None else policy(settings, subject, role)


def loop(c: Change, subject: str, settings: Settings, role: Role = "builder") -> RoundLoop:
    """The subject's loop; a new one pins the policy in force now, so later setting edits never change it."""
    if subject not in c.loops:
        c.loops[subject] = RoundLoop(subject=subject, policy=policy(settings, subject, role))
    return c.loops[subject]
