"""The owner's brief-scoped choice to judge OwlBear's look after its release (#1323)."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Literal, Protocol

from owlbear_delivery_next.change_contracts.merge_records import ReleaseLook

if TYPE_CHECKING:
    from collections.abc import Iterable

    from owlbear_delivery_next.change_contracts.decision_records import Origin
    from owlbear_delivery_next.change_contracts.models import Change

REPOSITORY = "maba-pag/owlbear"
QUESTION = "When does the owner judge the look?"
ANSWER = "After the release; browser tests must pass before merge."
REASON = "The owner chose to judge the look after the release; browser tests must pass before merge."
# The exact owner-approved proof statement in the pre-feature c3 A1, not a general natural-language parser.
LEGACY = "d3ff6617b3272020cdb6bab1ddf4bdd205abdc2f70d15d5471c54a7a144eb700"
INSTRUCTIONS = (
    f"For OwlBear ({REPOSITORY}) only, and only on the owner's word, a UI Change may defer his look until after "
    f"release. Keep ui true and browser tests before merge. Record a Change-scoped decision with question "
    f"'{QUESTION}' and answer '{ANSWER}'. Add it as a new decision if an existing proof decision has another "
    "question; replacing a decision's answer does not change its question. Remove conflicting pre-merge person "
    "checks only through the ordinary approved amendment path. Never choose this timing autonomously."
)


class Choice(Protocol):
    """The decision fields shared by a draft and a retained brief."""

    question: str
    answer: str
    origin: Origin
    scope: Literal["change", "project"]


def chosen(decisions: Iterable[Choice]) -> bool:
    """An explicit owner-origin choice, never arbitrary mentions or an agent's own proposal."""
    return any(
        d.scope == "change"
        and d.origin in {"decided", "approved"}
        and ((d.question == QUESTION and d.answer == ANSWER) or hashlib.sha256(d.answer.encode()).hexdigest() == LEGACY)
        for d in decisions
    )


def approved(c: Change) -> bool:
    """Only the current UI version's retained approval can authorize its deferred look."""
    b = c.brief
    if not b.ui or b.approved_version != b.version or not chosen(b.decisions):
        return False
    return any(
        old.version == b.version and old.ui == b.ui and old.decisions == b.decisions and old.visual == b.visual
        for old in b.approved
    )


def delivered(c: Change, commit: str, repository: str) -> None:
    """Keep the intended delivery's receipt, preserving a matching acknowledgement on cleanup retries."""
    if c.step.mode == "abandon" or c.intent.abandoned_at:
        c.release_look = None
        return
    if not commit or repository.lower() != REPOSITORY or not approved(c):
        return
    look = c.release_look
    if look is None or (look.version, look.commit) != (c.brief.version, commit):
        c.release_look = ReleaseLook(version=c.brief.version, commit=commit)
